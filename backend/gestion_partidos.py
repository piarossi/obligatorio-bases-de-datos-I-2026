"""Gestión de estados y reprogramación de partidos; consultas SQL directas, sin ORM."""
from datetime import date
from hmac import compare_digest
from secrets import token_hex

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from historial_partidos import registrar_historial


def registrar_gestion_partidos(conectar):
    bp = Blueprint('gestion_partidos', __name__, url_prefix='/gestion-partidos')

    @bp.before_request
    def exigir_admin():
        if not session.get('correo') or session.get('rol') != 'administrador':
            abort(403)

    def token():
        if 'gestion_partidos_csrf' not in session:
            session['gestion_partidos_csrf'] = token_hex(24)
        return session['gestion_partidos_csrf']

    def validar_token():
        if not compare_digest(request.form.get('_csrf', ''), token()):
            abort(400, 'Formulario inválido.')

    def obtener_partido(cur, identificador, bloquear=False):
        sql = '''SELECT p.id_partido, p.id_torneo, p.numero_fecha,
                        p.id_equipo_local, p.id_equipo_visitante, p.dia,
                        p.id_turno, p.nombre_cancha, p.id_complejo, p.estado
                 FROM partido p WHERE p.id_partido=%s'''
        if bloquear:
            sql += ' FOR UPDATE'
        cur.execute(sql, (identificador,))
        return cur.fetchone()

    def bloquear_torneo(cur, identificador):
        cur.execute('''SELECT id_torneo, estado, fecha_inicio, fecha_fin
                       FROM torneo WHERE id_torneo=%s FOR UPDATE''', (identificador,))
        return cur.fetchone()

    def sin_eventos(cur, identificador):
        # No se altera programación/historial de un encuentro que ya tiene una planilla.
        cur.execute('SELECT 1 FROM planilla_partido WHERE id_partido=%s LIMIT 1', (identificador,))
        if cur.fetchone():
            raise ValueError('El partido tiene planilla registrada y no puede postergarse ni reprogramarse.')
        cur.execute('SELECT 1 FROM gol WHERE id_partido=%s LIMIT 1', (identificador,))
        if cur.fetchone():
            raise ValueError('El partido tiene goles registrados.')
        cur.execute('SELECT 1 FROM tarjeta WHERE id_partido=%s LIMIT 1', (identificador,))
        if cur.fetchone():
            raise ValueError('El partido tiene tarjetas registradas.')

    def comprobar_programacion(cur, p, dia, turno, complejo, cancha):
        if dia is None:
            raise ValueError('Seleccioná un día válido.')
        cur.execute('SELECT 1 FROM turno WHERE id_turno=%s', (turno,))
        if cur.fetchone() is None:
            raise ValueError('El turno no existe.')
        cur.execute('SELECT 1 FROM cancha WHERE nombre_cancha=%s AND id_complejo=%s', (cancha, complejo))
        if cur.fetchone() is None:
            raise ValueError('La cancha no pertenece al complejo seleccionado.')
        # Otro encuentro no cancelado entre los mismos equipos en la edición.
        cur.execute('''SELECT 1 FROM partido q
                       WHERE q.id_torneo=%s AND q.id_partido<>%s AND q.estado<>'cancelado'
                         AND ((q.id_equipo_local=%s AND q.id_equipo_visitante=%s)
                           OR (q.id_equipo_local=%s AND q.id_equipo_visitante=%s)) LIMIT 1''',
                    (p['id_torneo'], p['id_partido'], p['id_equipo_local'], p['id_equipo_visitante'],
                     p['id_equipo_visitante'], p['id_equipo_local']))
        if cur.fetchone():
            raise ValueError('Ya existe otro encuentro no cancelado entre estos equipos.')
        # Máximo un partido por equipo y fecha del torneo, incluso si el otro está postergado.
        cur.execute('''SELECT 1 FROM partido q
                       WHERE q.id_torneo=%s AND q.numero_fecha=%s AND q.id_partido<>%s
                         AND q.estado<>'cancelado'
                         AND (q.id_equipo_local IN (%s,%s) OR q.id_equipo_visitante IN (%s,%s)) LIMIT 1''',
                    (p['id_torneo'], p['numero_fecha'], p['id_partido'],
                     p['id_equipo_local'], p['id_equipo_visitante'],
                     p['id_equipo_local'], p['id_equipo_visitante']))
        if cur.fetchone():
            raise ValueError('Uno de los equipos ya tiene partido en esa fecha del torneo.')
        cur.execute('''SELECT 1 FROM partido q
                       WHERE q.dia=%s AND q.id_turno=%s AND q.id_complejo=%s
                         AND q.nombre_cancha=%s AND q.id_partido<>%s
                         AND q.estado IN ('programado','jugado') LIMIT 1''',
                    (dia, turno, complejo, cancha, p['id_partido']))
        if cur.fetchone():
            raise ValueError('La cancha ya está reservada para ese día y turno.')
        cur.execute('''SELECT 1 FROM partido q
                       WHERE q.dia=%s AND q.id_turno=%s AND q.id_partido<>%s
                         AND q.estado IN ('programado','jugado')
                         AND (q.id_equipo_local IN (%s,%s) OR q.id_equipo_visitante IN (%s,%s)) LIMIT 1''',
                    (dia, turno, p['id_partido'], p['id_equipo_local'], p['id_equipo_visitante'],
                     p['id_equipo_local'], p['id_equipo_visitante']))
        if cur.fetchone():
            raise ValueError('Uno de los equipos ya juega en ese día y turno.')
        cur.execute('''SELECT e.id_equipo, e.activo, COUNT(ejt.ci_jugador) AS integrantes
                       FROM equipo e LEFT JOIN equipo_jugador_torneo ejt
                         ON ejt.id_equipo=e.id_equipo AND ejt.id_torneo=e.id_torneo
                       WHERE e.id_torneo=%s AND e.id_equipo IN (%s,%s)
                       GROUP BY e.id_equipo,e.activo''',
                    (p['id_torneo'], p['id_equipo_local'], p['id_equipo_visitante']))
        equipos = cur.fetchall()
        if len(equipos) != 2 or any(not x['activo'] or x['integrantes'] < 5 for x in equipos):
            raise ValueError('Los equipos deben estar activos y tener al menos cinco integrantes.')

    @bp.get('/')
    def lista():
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                cur.execute('''SELECT p.id_partido,p.numero_fecha,p.dia,p.estado,
                               l.nombre AS local, v.nombre AS visitante,
                               c.nombre AS complejo, p.nombre_cancha, tu.hora_inicio
                               FROM partido p
                               JOIN equipo l ON l.id_equipo=p.id_equipo_local
                               JOIN equipo v ON v.id_equipo=p.id_equipo_visitante
                               JOIN complejo c ON c.id_complejo=p.id_complejo
                               JOIN turno tu ON tu.id_turno=p.id_turno
                               ORDER BY p.numero_fecha,p.dia,p.id_partido''')
                partidos = cur.fetchall()
                cur.execute('''SELECT h.id_historial,h.id_partido,h.accion,h.fecha_cambio,
                                      h.estado_anterior,h.estado_nuevo,
                                      h.dia_anterior,h.dia_nuevo,
                                      h.correo_usuario,h.motivo
                               FROM historial_estado_partido h
                               ORDER BY h.id_historial DESC LIMIT 40''')
                historial = cur.fetchall()
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template('gestion_partidos.html', partidos=partidos, historial=historial, csrf=token())

    @bp.post('/<int:id_partido>/estado')
    def cambiar_estado(id_partido):
        validar_token()
        accion = request.form.get('accion')
        motivo = request.form.get('motivo', '').strip()
        if accion not in ('postergar', 'cancelar'):
            abort(400)
        if not 5 <= len(motivo) <= 255:
            flash('Indicá el motivo del cambio (entre 5 y 255 caracteres).')
            return redirect(url_for('gestion_partidos.lista'))
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                try:
                    # Primero identificar el torneo y bloquearlo para coordinar con nuevo().
                    p = obtener_partido(cur, id_partido)
                    if p is None:
                        abort(404)
                    torneo = bloquear_torneo(cur, p['id_torneo'])
                    p = obtener_partido(cur, id_partido, bloquear=True)
                    if p is None:
                        abort(404)
                    if torneo is None or torneo['estado'] == 'finalizado':
                        raise ValueError('No se modifica un torneo finalizado.')
                    if (accion == 'postergar' and p['estado'] != 'programado') or (accion == 'cancelar' and p['estado'] not in ('programado', 'postergado')):
                        raise ValueError('La operación no está permitida para el estado actual.')
                    sin_eventos(cur, id_partido)
                    estado_nuevo = 'postergado' if accion == 'postergar' else 'cancelado'
                    cur.execute('UPDATE partido SET estado=%s WHERE id_partido=%s',
                                (estado_nuevo, id_partido))
                    registrar_historial(cur, p, {**p, 'estado': estado_nuevo},
                                       'postergado' if accion == 'postergar' else 'cancelado',
                                       motivo=motivo)
                    cn.commit()
                    flash('Partido ' + ('postergado' if accion == 'postergar' else 'cancelado') + ' correctamente.')
                except ValueError as exc:
                    cn.rollback()
                    flash(str(exc))
                except Error:
                    cn.rollback()
                    flash('No se pudo cambiar el estado del partido. Revisá los datos.')
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for('gestion_partidos.lista'))

    @bp.route('/<int:id_partido>/reprogramar', methods=['GET', 'POST'])
    def reprogramar(id_partido):
        if request.method == 'POST':
            validar_token()
            cn = conectar()
            try:
                cur = cn.cursor(dictionary=True, buffered=True)
                try:
                    try:
                        p = obtener_partido(cur, id_partido)
                        if p is None:
                            abort(404)
                        torneo = bloquear_torneo(cur, p['id_torneo'])
                        p = obtener_partido(cur, id_partido, bloquear=True)
                        if p is None:
                            abort(404)
                        if torneo is None or torneo['estado'] == 'finalizado':
                            raise ValueError('La edición está finalizada.')
                        if p['estado'] not in ('programado', 'postergado'):
                            raise ValueError('No se pueden reprogramar partidos jugados o cancelados.')
                        sin_eventos(cur, id_partido)
                        try:
                            dia = date.fromisoformat(request.form.get('dia', ''))
                            turno = int(request.form.get('id_turno', ''))
                            complejo = int(request.form.get('id_complejo', ''))
                            cancha = request.form.get('nombre_cancha', '').strip()
                        except (ValueError, TypeError):
                            raise ValueError('Completá día, turno, complejo y cancha válidos.')
                        if not torneo['fecha_inicio'] <= dia <= torneo['fecha_fin']:
                            raise ValueError('El día debe estar comprendido en el período de la edición.')
                        comprobar_programacion(cur, p, dia, turno, complejo, cancha)
                        motivo = request.form.get('motivo', '').strip()
                        if not 5 <= len(motivo) <= 255:
                            raise ValueError('Indicá el motivo de la reprogramación (5 a 255 caracteres).')
                        cur.execute('''UPDATE partido
                                       SET dia=%s, id_turno=%s, id_complejo=%s,
                                           nombre_cancha=%s, estado='programado'
                                       WHERE id_partido=%s''',
                                    (dia, turno, complejo, cancha, id_partido))
                        registrar_historial(cur, p,
                            {**p, 'dia': dia, 'id_turno': turno, 'id_complejo': complejo,
                             'nombre_cancha': cancha, 'estado': 'programado'},
                            'reprogramado', motivo=motivo)
                        cn.commit()
                        flash('Partido reprogramado correctamente.')
                        return redirect(url_for('gestion_partidos.lista'))
                    except ValueError as exc:
                        cn.rollback()
                        flash(str(exc))
                    except Error:
                        cn.rollback()
                        flash('No se pudo reprogramar. Revisá los datos.')
                finally:
                    cur.close()
            finally:
                cn.close()
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                p = obtener_partido(cur, id_partido)
                if p is None:
                    abort(404)
                if p['estado'] not in ('programado', 'postergado'):
                    flash('Solo se reprograman partidos pendientes.')
                    return redirect(url_for('gestion_partidos.lista'))
                cur.execute('SELECT id_turno,hora_inicio,hora_fin FROM turno ORDER BY hora_inicio')
                turnos = cur.fetchall()
                cur.execute('''SELECT ca.id_complejo,ca.nombre_cancha,c.nombre AS complejo
                               FROM cancha ca JOIN complejo c ON c.id_complejo=ca.id_complejo
                               ORDER BY c.nombre,ca.nombre_cancha''')
                canchas = cur.fetchall()
                cur.execute('SELECT nombre FROM equipo WHERE id_equipo=%s', (p['id_equipo_local'],))
                local = cur.fetchone()['nombre']
                cur.execute('SELECT nombre FROM equipo WHERE id_equipo=%s', (p['id_equipo_visitante'],))
                visitante = cur.fetchone()['nombre']
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template('reprogramar_partido.html', p=p, turnos=turnos, canchas=canchas,
                               local=local, visitante=visitante, csrf=token())

    return bp
