"""Programación de partidos. Sin ORM; solo entorno local de desarrollo."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from mysql.connector import Error
from secrets import token_hex
from hmac import compare_digest

bp = Blueprint('partidos', __name__)


def registrar_partidos(conectar):
    def csrf():
        if 'partidos_csrf' not in session:
            session['partidos_csrf'] = token_hex(24)
        return session['partidos_csrf']

    def check_csrf():
        if not compare_digest(request.form.get('_csrf', ''), csrf()):
            abort(400, 'Token de formulario inválido')

    def catalogos(cur):
        cur.execute('SELECT id_torneo, nombre, estado FROM torneo ORDER BY anio DESC, semestre DESC')
        torneos = cur.fetchall()
        cur.execute('''SELECT e.id_equipo,e.nombre,e.id_torneo,e.activo,
                       COUNT(p.ci_jugador) AS integrantes
                       FROM equipo e LEFT JOIN equipo_jugador_torneo p
                         ON p.id_equipo=e.id_equipo AND p.id_torneo=e.id_torneo
                       GROUP BY e.id_equipo,e.nombre,e.id_torneo,e.activo ORDER BY e.nombre''')
        equipos = cur.fetchall()
        cur.execute('SELECT id_turno,hora_inicio,hora_fin FROM turno ORDER BY hora_inicio')
        turnos = cur.fetchall()
        cur.execute('''SELECT c.nombre_cancha,c.id_complejo,x.nombre AS complejo
                       FROM cancha c JOIN complejo x ON x.id_complejo=c.id_complejo
                       ORDER BY x.nombre,c.nombre_cancha''')
        canchas = cur.fetchall()
        return torneos,equipos,turnos,canchas

    @bp.get('/partidos')
    def lista():
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                cur.execute('''SELECT p.id_partido,p.numero_fecha,p.dia,p.estado,
                     t.nombre AS torneo, l.nombre AS local, v.nombre AS visitante,
                     p.nombre_cancha, x.nombre AS complejo, h.hora_inicio
                     FROM partido p JOIN torneo t ON t.id_torneo=p.id_torneo
                     JOIN equipo l ON l.id_equipo=p.id_equipo_local
                     JOIN equipo v ON v.id_equipo=p.id_equipo_visitante
                     JOIN complejo x ON x.id_complejo=p.id_complejo
                     JOIN turno h ON h.id_turno=p.id_turno
                     ORDER BY p.dia,p.id_turno,p.id_partido''')
                filas=cur.fetchall()
            finally: cur.close()
        finally: cn.close()
        return render_template('partidos.html',partidos=filas)

    def validar(cur, d, id_actual=None):
        try:
            tid=int(d.get('id_torneo','')); fecha=int(d.get('numero_fecha',''))
            local=int(d.get('id_equipo_local','')); visitante=int(d.get('id_equipo_visitante',''))
            turno=int(d.get('id_turno','')); complejo=int(d.get('id_complejo',''))
            dia=date.fromisoformat(d.get('dia',''))
        except (ValueError,TypeError):
            raise ValueError('Completá los campos con valores válidos.')
        cancha=d.get('nombre_cancha','').strip()
        if fecha < 1: raise ValueError('El número de fecha debe ser mayor que cero.')
        if local==visitante: raise ValueError('El equipo no puede jugar contra sí mismo.')
        if not cancha: raise ValueError('Seleccioná una cancha.')
        # Serializar operaciones de programación por edición, evitando carreras concurrentes.
        cur.execute('SELECT estado,fecha_inicio,fecha_fin FROM torneo WHERE id_torneo=%s FOR UPDATE',(tid,))
        torneo=cur.fetchone()
        if not torneo: raise ValueError('La edición seleccionada no existe.')
        if torneo['estado']=='finalizado': raise ValueError('No se pueden programar partidos en una edición finalizada.')
        if not torneo['fecha_inicio'] <= dia <= torneo['fecha_fin']:
            raise ValueError('El día debe estar dentro de las fechas de la edición.')
        cur.execute('''SELECT e.id_equipo,e.activo,COUNT(p.ci_jugador) AS integrantes
                       FROM equipo e LEFT JOIN equipo_jugador_torneo p
                       ON p.id_equipo=e.id_equipo AND p.id_torneo=e.id_torneo
                       WHERE e.id_torneo=%s AND e.id_equipo IN (%s,%s)
                       GROUP BY e.id_equipo,e.activo''',(tid,local,visitante))
        equipos={x['id_equipo']:x for x in cur.fetchall()}
        if len(equipos)!=2: raise ValueError('Ambos equipos deben pertenecer a la edición seleccionada.')
        if any(not x['activo'] or x['integrantes']<5 for x in equipos.values()):
            raise ValueError('Ambos equipos deben estar activos y tener al menos 5 jugadores inscriptos.')
        cur.execute('SELECT 1 FROM turno WHERE id_turno=%s',(turno,))
        if not cur.fetchone(): raise ValueError('Seleccioná un turno válido.')
        cur.execute('SELECT 1 FROM cancha WHERE id_complejo=%s AND nombre_cancha=%s',(complejo,cancha))
        if not cur.fetchone(): raise ValueError('La cancha no corresponde al complejo seleccionado.')
        excluir=id_actual or -1
        cur.execute('''SELECT 1 FROM partido WHERE id_torneo=%s AND id_partido<>%s
                       AND estado<>'cancelado' AND
                      ((id_equipo_local=%s AND id_equipo_visitante=%s) OR
                       (id_equipo_local=%s AND id_equipo_visitante=%s)) LIMIT 1''',
                    (tid,excluir,local,visitante,visitante,local))
        if cur.fetchone(): raise ValueError('Estos equipos ya tienen un partido no cancelado en esta edición.')
        cur.execute('''SELECT 1 FROM partido WHERE id_torneo=%s AND numero_fecha=%s
                       AND id_partido<>%s AND estado<>'cancelado' AND
                       (id_equipo_local IN (%s,%s) OR id_equipo_visitante IN (%s,%s)) LIMIT 1''',
                    (tid,fecha,excluir,local,visitante,local,visitante))
        if cur.fetchone(): raise ValueError('Uno de los equipos ya tiene partido en esa fecha del torneo.')
        cur.execute('''SELECT 1 FROM partido WHERE dia=%s AND id_turno=%s
                       AND nombre_cancha=%s AND id_complejo=%s AND id_partido<>%s
                       AND estado IN ('programado','jugado') LIMIT 1''',
                    (dia,turno,cancha,complejo,excluir))
        if cur.fetchone(): raise ValueError('La cancha ya está ocupada ese día y turno.')
        # También evitar superposición de un mismo equipo en dos partidos simultáneos.
        cur.execute('''SELECT 1 FROM partido WHERE dia=%s AND id_turno=%s
                       AND id_partido<>%s AND estado IN ('programado','jugado') AND
                       (id_equipo_local IN (%s,%s) OR id_equipo_visitante IN (%s,%s)) LIMIT 1''',
                    (dia,turno,excluir,local,visitante,local,visitante))
        if cur.fetchone(): raise ValueError('Uno de los equipos ya juega en ese día y turno.')
        return tid,fecha,local,visitante,dia,turno,cancha,complejo

    @bp.route('/partidos/nuevo',methods=['GET','POST'])
    def nuevo():
        cn=conectar()
        try:
            cur=cn.cursor(dictionary=True)
            try:
                if request.method=='POST':
                    check_csrf()
                    try:
                        datos=validar(cur,request.form)
                        cur.execute('''INSERT INTO partido
                           (id_torneo,numero_fecha,id_equipo_local,id_equipo_visitante,
                           dia,id_turno,nombre_cancha,id_complejo,estado)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'programado')''',datos)
                        cn.commit()
                        flash('Partido programado correctamente.')
                        return redirect(url_for('partidos.lista'))
                    except (ValueError,Error) as exc:
                        cn.rollback()
                        flash(str(exc) if isinstance(exc,ValueError) else 'No se pudo programar el partido. Revisá los datos.')
                torneos,equipos,turnos,canchas=catalogos(cur)
            finally: cur.close()
        finally: cn.close()
        return render_template('partido_form.html',torneos=torneos,equipos=equipos,turnos=turnos,
                               canchas=canchas,csrf=csrf(),valores=request.form)

    @bp.post('/partidos/<int:id_partido>/cancelar')
    def cancelar(id_partido):
        check_csrf()
        cn=conectar()
        try:
            cur=cn.cursor(dictionary=True)
            try:
                cur.execute('''SELECT p.estado,t.estado AS torneo_estado FROM partido p
                               JOIN torneo t ON t.id_torneo=p.id_torneo
                               WHERE id_partido=%s FOR UPDATE''',(id_partido,))
                p=cur.fetchone()
                if not p: abort(404)
                if p['estado'] not in ('programado','postergado') or p['torneo_estado']=='finalizado':
                    flash('Solo se puede cancelar un partido pendiente de una edición no finalizada.')
                else:
                    cur.execute("UPDATE partido SET estado='cancelado' WHERE id_partido=%s",(id_partido,))
                    cn.commit()
                    flash('Partido cancelado; se conserva su historial.')
            except Error:
                cn.rollback()
                raise
            finally: cur.close()
        finally: cn.close()
        return redirect(url_for('partidos.lista'))

    # Exponer token de formulario también al listado
    @bp.app_context_processor
    def contexto():
        return {'partidos_csrf':csrf}

    return bp
