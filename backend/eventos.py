"""Goles, tarjetas y cierre de partidos. Consultas MySQL directas, sin ORM."""
from datetime import datetime, timedelta
from hmac import compare_digest
from secrets import token_hex
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from sanciones import recalcular_sanciones
from historial_partidos import registrar_historial

bp = Blueprint('eventos', __name__)


def registrar_eventos(conectar):
    def csrf():
        if 'eventos_csrf' not in session:
            session['eventos_csrf'] = token_hex(24)
        return session['eventos_csrf']

    def proteger():
        if not compare_digest(request.form.get('_csrf', ''), csrf()):
            abort(400, 'Formulario no válido')

    def obtener_partido(cur, id_partido, lock=False):
        cur.execute('''SELECT p.*, el.nombre AS nombre_local, ev.nombre AS nombre_visitante,
                       t.estado AS estado_torneo, h.hora_fin
                       FROM partido p JOIN equipo el ON el.id_equipo=p.id_equipo_local
                       JOIN equipo ev ON ev.id_equipo=p.id_equipo_visitante
                       JOIN torneo t ON t.id_torneo=p.id_torneo
                       JOIN turno h ON h.id_turno=p.id_turno
                       WHERE p.id_partido=%s''' + (' FOR UPDATE' if lock else ''), (id_partido,))
        p = cur.fetchone()
        if p is None:
            abort(404)
        return p

    def fin_del_turno(p):
        return datetime.combine(p['dia'], (datetime.min + timedelta(seconds=p['hora_fin'].total_seconds())).time())

    def validar_edicion(p):
        if p['estado_torneo'] == 'finalizado' or p['estado'] in ('cancelado', 'postergado'):
            raise ValueError('Este partido no admite registro de eventos por su estado.')
        fin = fin_del_turno(p)
        ahora = datetime.now()
        if ahora < fin:
            raise ValueError('La planilla y los eventos solo pueden registrarse después de terminado el turno.')
        if p['estado'] == 'jugado' and ahora > fin + timedelta(hours=48):
            raise ValueError('Las 48 horas para corregir este partido ya transcurrieron.')
        if p['estado'] not in ('programado','jugado'):
            raise ValueError('El estado del partido no admite cambios.')

    def participantes(cur, pid):
        cur.execute('''SELECT pp.ci_jugador, pp.id_equipo, j.nombre,j.apellido,
                              pj.numero_camiseta
                       FROM planilla_partido pp
                       JOIN jugador j ON j.ci=pp.ci_jugador
                       JOIN partido p ON p.id_partido=pp.id_partido
                       LEFT JOIN equipo_jugador_torneo pj ON pj.ci_jugador=pp.ci_jugador
                         AND pj.id_equipo=pp.id_equipo AND pj.id_torneo=p.id_torneo
                       WHERE pp.id_partido=%s ORDER BY pp.id_equipo,pj.numero_camiseta''', (pid,))
        return cur.fetchall()

    def calcular(cur, p):
        cur.execute('''SELECT pp.id_equipo,g.autogol, COUNT(*) cantidad FROM gol g
                       JOIN planilla_partido pp ON pp.id_partido=g.id_partido
                          AND pp.ci_jugador=g.ci_jugador
                       WHERE g.id_partido=%s GROUP BY pp.id_equipo,g.autogol''', (p['id_partido'],))
        local = visitante = 0
        for x in cur.fetchall():
            # Un autogol le suma un tanto al contrario del autor.
            para_local = (x['id_equipo'] == p['id_equipo_local']) != bool(x['autogol'])
            if para_local: local += x['cantidad']
            else: visitante += x['cantidad']
        return local, visitante

    @bp.route('/partidos/<int:id_partido>/eventos', methods=['GET', 'POST'])
    def detalle(id_partido):
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                if request.method == 'POST':
                    proteger()
                    try:
                        # Bloquear la edición compartida para serializar modificaciones.
                        cur.execute('''SELECT id_partido FROM partido
                                       WHERE id_partido=%s FOR UPDATE''', (id_partido,))
                        p = obtener_partido(cur, id_partido, lock=False)
                        validar_edicion(p)
                        accion = request.form.get('accion','')
                        if accion in ('gol','tarjeta'):
                            ci = request.form.get('ci_jugador','').strip()
                            validos = {j['ci_jugador']:j for j in participantes(cur,id_partido)}
                            if ci not in validos:
                                raise ValueError('Elegí un jugador que figure en la planilla de este partido.')
                            try: minuto=int(request.form.get('minuto',''))
                            except ValueError: raise ValueError('Indicá un minuto válido.')
                            if not 0 <= minuto <= 60:
                                raise ValueError('El minuto debe estar entre 0 y 60.')
                            if accion == 'gol':
                                autogol = 1 if request.form.get('autogol') == '1' else 0
                                cur.execute('''INSERT INTO gol(id_partido,ci_jugador,minuto,autogol)
                                               VALUES (%s,%s,%s,%s)''', (id_partido,ci,minuto,autogol))
                                flash('Gol registrado correctamente.')
                            else:
                                color=request.form.get('color','')
                                if color not in ('amarilla','roja'):
                                    raise ValueError('Seleccioná una tarjeta amarilla o roja.')
                                # No permitir tarjetas luego de una expulsión,
                                # ni una tercera amarilla en el mismo partido.
                                cur.execute('''SELECT color,origen,minuto FROM tarjeta
                                               WHERE id_partido=%s AND ci_jugador=%s''',
                                            (id_partido,ci))
                                previas = cur.fetchall()
                                if any(t['color'] == 'roja' for t in previas):
                                    raise ValueError('El jugador ya fue expulsado en este partido.')
                                amarillas = [t for t in previas if t['color'] == 'amarilla']
                                if color == 'amarilla' and len(amarillas) >= 2:
                                    raise ValueError('No puede recibir una tercera amarilla en el mismo partido.')
                                if color == 'roja' and len(amarillas) >= 2:
                                    raise ValueError('Ya corresponde expulsión por doble amarilla.')
                                if color == 'amarilla' and amarillas and minuto < max(t['minuto'] for t in amarillas):
                                    raise ValueError('La segunda amarilla no puede ser anterior a la primera.')
                                cur.execute('''INSERT INTO tarjeta(id_partido,ci_jugador,minuto,color,origen)
                                               VALUES (%s,%s,%s,%s,'manual')''',
                                            (id_partido,ci,minuto,color))
                                if color == 'amarilla' and len(amarillas) == 1:
                                    cur.execute('''INSERT INTO tarjeta(id_partido,ci_jugador,minuto,color,origen)
                                                   VALUES (%s,%s,%s,'roja','doble_amarilla')''',
                                                (id_partido,ci,minuto))
                                    flash('Segunda amarilla: expulsión automática registrada.')
                                else:
                                    flash('Tarjeta registrada correctamente.')
                        elif accion in ('quitar_gol','quitar_tarjeta'):
                            try: id_evento=int(request.form.get('id_evento',''))
                            except ValueError: raise ValueError('Evento no válido.')
                            tabla,col = ('gol','id_gol') if accion=='quitar_gol' else ('tarjeta','id_tarjeta')
                            if accion == 'quitar_tarjeta':
                                cur.execute('''SELECT ci_jugador, origen FROM tarjeta
                                               WHERE id_tarjeta=%s AND id_partido=%s''',
                                            (id_evento,id_partido))
                                tarjeta = cur.fetchone()
                                if tarjeta and tarjeta['origen'] == 'doble_amarilla':
                                    raise ValueError('Quitá una amarilla; la roja automática se corregirá sola.')
                                if tarjeta:
                                    # Quitar la roja derivada ANTES de quitar la amarilla,
                                    # dentro de la misma transacción.
                                    cur.execute('''DELETE FROM tarjeta
                                                   WHERE id_partido=%s AND ci_jugador=%s
                                                     AND origen='doble_amarilla' ''',
                                                (id_partido,tarjeta['ci_jugador']))
                            cur.execute(f'DELETE FROM {tabla} WHERE {col}=%s AND id_partido=%s', (id_evento,id_partido))
                            if cur.rowcount!=1:
                                raise ValueError('El evento no existe en este partido.')
                            flash('Evento retirado correctamente.')
                        elif accion == 'finalizar':
                            cur.execute('''SELECT id_equipo,COUNT(*) n FROM planilla_partido
                                           WHERE id_partido=%s GROUP BY id_equipo''', (id_partido,))
                            ids={x['id_equipo'] for x in cur.fetchall() if x['n']>0}
                            if not {p['id_equipo_local'],p['id_equipo_visitante']}.issubset(ids):
                                raise ValueError('Registrá al menos un participante de cada equipo antes de cerrar el partido.')
                            if p['estado'] != 'programado':
                                raise ValueError('El partido ya está marcado como jugado.')
                            cur.execute("UPDATE partido SET estado='jugado' WHERE id_partido=%s",(id_partido,))
                            registrar_historial(cur, p, {**p, 'estado': 'jugado'}, 'jugado',
                                                 motivo='Cierre de planilla y resultado')
                            flash('Partido marcado como jugado. Resultado calculado desde los goles.')
                        else:
                            raise ValueError('Acción desconocida.')
                        if accion in ('tarjeta', 'quitar_tarjeta', 'finalizar'):
                            recalcular_sanciones(cur, p['id_torneo'])
                        cn.commit()
                        return redirect(url_for('eventos.detalle',id_partido=id_partido))
                    except (ValueError,Error) as exc:
                        print('ERROR AL GUARDAR EVENTO:', repr(exc), flush=True)
                        cn.rollback()
                        flash(str(exc) if isinstance(exc,ValueError) else 'No se pudo guardar el evento. Revisá los datos.')
                p=obtener_partido(cur,id_partido)
                cur.execute('''SELECT g.id_gol,g.minuto,g.autogol,j.nombre,j.apellido
                               FROM gol g JOIN jugador j ON j.ci=g.ci_jugador
                               WHERE g.id_partido=%s ORDER BY g.minuto,g.id_gol''',(id_partido,))
                goles=cur.fetchall()
                cur.execute('''SELECT t.id_tarjeta,t.minuto,t.color,j.nombre,j.apellido
                               FROM tarjeta t JOIN jugador j ON j.ci=t.ci_jugador
                               WHERE t.id_partido=%s ORDER BY t.minuto,t.id_tarjeta''',(id_partido,))
                tarjetas=cur.fetchall()
                jugadores=participantes(cur,id_partido)
                gl,gv=calcular(cur,p)
                try: validar_edicion(p); editable=True
                except ValueError: editable=False
            finally: cur.close()
        finally: cn.close()
        return render_template('eventos_partido.html',p=p,goles=goles,tarjetas=tarjetas,
                               jugadores=jugadores,local_goles=gl,visitante_goles=gv,
                               editable=editable,csrf=csrf(),fin=fin_del_turno(p).strftime('%d/%m/%Y %H:%M'))
    return bp
