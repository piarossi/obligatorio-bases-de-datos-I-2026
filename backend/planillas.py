"""Registro de participantes de partidos ya disputados. Sin ORM."""
from datetime import datetime, timedelta
from secrets import token_hex
from hmac import compare_digest
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from mysql.connector import Error

bp = Blueprint('planillas', __name__)


def registrar_planillas(conectar):
    def token():
        if 'planillas_csrf' not in session:
            session['planillas_csrf'] = token_hex(24)
        return session['planillas_csrf']

    def partido(cur, id_partido, bloquear=False):
        cur.execute('''SELECT p.id_partido,p.id_torneo,p.numero_fecha,p.id_equipo_local,
                       p.id_equipo_visitante,p.dia,p.estado,h.hora_fin,
                       el.nombre AS local, ev.nombre AS visitante, t.estado AS estado_torneo
                       FROM partido p JOIN turno h ON h.id_turno=p.id_turno
                       JOIN equipo el ON el.id_equipo=p.id_equipo_local
                       JOIN equipo ev ON ev.id_equipo=p.id_equipo_visitante
                       JOIN torneo t ON t.id_torneo=p.id_torneo
                       WHERE p.id_partido=%s''',(id_partido,))
        resultado=cur.fetchone()
        if not resultado: abort(404)
        return resultado

    def fin_partido(p):
        return datetime.combine(p['dia'], (datetime.min + timedelta(seconds=p['hora_fin'].total_seconds())).time())

    def modificable(p):
        fin=fin_partido(p)
        ahora=datetime.now()  # Hora local del servidor donde corre la app
        if p['estado_torneo']=='finalizado' or p['estado'] in ('cancelado','postergado'):
            return False
        if ahora < fin:
            return False
        if p['estado']=='jugado' and ahora > fin + timedelta(hours=48):
            return False
        return p['estado'] in ('programado','jugado')

    def candidatos(cur,p):
        cur.execute('''SELECT j.ci,j.nombre,j.apellido,j.activo,pj.id_equipo,
                           pj.numero_camiseta, e.nombre AS equipo,
                           EXISTS(SELECT 1 FROM sancion_jugador s
                             WHERE s.ci_jugador=j.ci AND s.id_torneo=%s
                             AND %s >= s.numero_fecha_inicio
                             AND %s < s.numero_fecha_inicio+s.cantidad_fechas) AS suspendido
                       FROM equipo_jugador_torneo pj JOIN jugador j ON j.ci=pj.ci_jugador
                       JOIN equipo e ON e.id_equipo=pj.id_equipo
                       WHERE pj.id_torneo=%s AND pj.id_equipo IN (%s,%s)
                       ORDER BY pj.id_equipo,pj.numero_camiseta''',
                    (p['id_torneo'],p['numero_fecha'],p['numero_fecha'],p['id_torneo'],
                     p['id_equipo_local'],p['id_equipo_visitante']))
        return cur.fetchall()

    @bp.route('/partidos/<int:id_partido>/planilla', methods=['GET','POST'])
    def editar(id_partido):
        cn=conectar()
        try:
            cur=cn.cursor(dictionary=True)
            try:
                if request.method=='POST':
                    if not compare_digest(request.form.get('_csrf',''),token()): abort(400)
                    try:
                        # Serializar con las modificaciones del partido y su edición.
                        cur.execute('''SELECT id_partido FROM partido
                                       WHERE id_partido=%s FOR UPDATE''',(id_partido,))
                        # Consumir el resultado del SELECT antes de ejecutar otra consulta.
                        # De lo contrario MySQL Connector genera 'Unread result found'.
                        if cur.fetchone() is None:
                            abort(404)
                        p=partido(cur,id_partido,bloquear=True)
                        if not modificable(p):
                            raise ValueError('Solo se puede registrar la planilla después del turno; un partido jugado admite correcciones durante 48 horas.')
                        cur.execute('SELECT COUNT(*) AS n FROM gol WHERE id_partido=%s',(id_partido,))
                        goles=cur.fetchone()['n']
                        cur.execute('SELECT COUNT(*) AS n FROM tarjeta WHERE id_partido=%s',(id_partido,))
                        tarjetas=cur.fetchone()['n']
                        if goles or tarjetas:
                            raise ValueError('Ya hay goles o tarjetas registrados. No se puede reemplazar la planilla sin revisar esos eventos.')
                        seleccionados=request.form.getlist('ci_jugador')
                        if len(seleccionados)!=len(set(seleccionados)):
                            raise ValueError('No puede repetirse un jugador en la planilla.')
                        habilitados={j['ci']:j for j in candidatos(cur,p) if j['activo'] and not j['suspendido']}
                        if not seleccionados:
                            raise ValueError('Seleccioná al menos un participante.')
                        if any(ci not in habilitados for ci in seleccionados):
                            raise ValueError('La selección contiene jugadores ajenos, inactivos o suspendidos.')
                        cur.execute('DELETE FROM planilla_partido WHERE id_partido=%s',(id_partido,))
                        cur.executemany('''INSERT INTO planilla_partido(id_partido,ci_jugador,id_equipo)
                                           VALUES (%s,%s,%s)''',[(id_partido,ci,habilitados[ci]['id_equipo']) for ci in seleccionados])
                        cn.commit()
                        flash('Planilla de participantes guardada correctamente. El partido todavía no está marcado como jugado.')
                        return redirect(url_for('planillas.editar',id_partido=id_partido))
                    except (ValueError,Error) as exc:
                        cn.rollback()
                        flash(str(exc) if isinstance(exc,ValueError) else 'No se pudo guardar la planilla. Verificá los datos.')
                p=partido(cur,id_partido)
                participantes=candidatos(cur,p)
                cur.execute('SELECT ci_jugador FROM planilla_partido WHERE id_partido=%s',(id_partido,))
                actuales={x['ci_jugador'] for x in cur.fetchall()}
            finally: cur.close()
        finally: cn.close()
        return render_template('planilla_partido.html',p=p,jugadores=participantes,
                               actuales=actuales,editable=modificable(p),csrf=token(),
                               hora_fin=fin_partido(p).strftime('%d/%m/%Y %H:%M'))
    return bp
