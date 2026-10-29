"""Gestión de planteles durante inscripción. Proyecto local, sin login todavía."""
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort, session
from mysql.connector import IntegrityError
import secrets, hmac

bp = Blueprint('planteles', __name__)


def registrar_planteles(conectar):
    def token():
        if 'planteles_csrf' not in session:
            session['planteles_csrf'] = secrets.token_hex(24)
        return session['planteles_csrf']

    def validar_token():
        if not hmac.compare_digest(request.form.get('_csrf', ''), token()):
            abort(400, 'Token de formulario inválido.')

    def equipo_y_torneo(cur, id_equipo, lock=False):
        cur.execute('''SELECT e.id_equipo, e.nombre AS nombre_equipo, e.id_torneo,
                              e.id_facultad, e.ci_capitan, e.activo, t.estado
                       FROM equipo e JOIN torneo t ON t.id_torneo=e.id_torneo
                       WHERE e.id_equipo=%s''', (id_equipo,))
        e = cur.fetchone()
        if not e:
            abort(404)
        if lock:
            # Se bloquea la edición del torneo para serializar cambios de plantel.
            cur.execute('SELECT estado FROM torneo WHERE id_torneo=%s FOR UPDATE', (e['id_torneo'],))
            e['estado'] = cur.fetchone()['estado']
        return e

    def exigir_inscripcion(e):
        if not e['activo']:
            raise ValueError('El equipo está dado de baja.')
        if e['estado'] != 'inscripción':
            raise ValueError('El plantel solo puede modificarse durante la inscripción.')

    @bp.get('/equipos/<int:id_equipo>/plantel/gestionar')
    def gestionar(id_equipo):
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                e = equipo_y_torneo(cur, id_equipo)
                cur.execute('''SELECT j.ci, j.nombre, j.apellido, j.tipo, j.activo,
                                      p.numero_camiseta
                               FROM equipo_jugador_torneo p JOIN jugador j ON j.ci=p.ci_jugador
                               WHERE p.id_equipo=%s AND p.id_torneo=%s
                               ORDER BY p.numero_camiseta''', (id_equipo, e['id_torneo']))
                plantel = cur.fetchall()
                cur.execute('''SELECT j.ci,j.nombre,j.apellido,j.tipo FROM jugador j
                               WHERE j.activo=TRUE AND j.id_facultad=%s
                               AND NOT EXISTS (SELECT 1 FROM equipo_jugador_torneo p
                                               WHERE p.ci_jugador=j.ci AND p.id_torneo=%s)
                               ORDER BY j.apellido,j.nombre''', (e['id_facultad'],e['id_torneo']))
                candidatos = cur.fetchall()
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template('gestionar_plantel.html', equipo=e, plantel=plantel,
                               candidatos=candidatos, csrf=token(), editable=e['activo'] and e['estado']=='inscripción')

    @bp.post('/equipos/<int:id_equipo>/plantel/agregar')
    def agregar(id_equipo):
        validar_token()
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                try:
                    e = equipo_y_torneo(cur,id_equipo,lock=True)
                    exigir_inscripcion(e)
                    ci = request.form.get('ci','').strip()
                    try:
                        numero = int(request.form.get('numero_camiseta',''))
                    except ValueError:
                        raise ValueError('La camiseta debe ser un número entero entre 1 y 99.')
                    if not 1 <= numero <= 99:
                        raise ValueError('La camiseta debe estar entre 1 y 99.')
                    cur.execute('''SELECT id_facultad,tipo,activo FROM jugador WHERE ci=%s''', (ci,))
                    j = cur.fetchone()
                    if not j or not j['activo'] or j['id_facultad'] != e['id_facultad']:
                        raise ValueError('Jugador inexistente, inactivo o de otra facultad.')
                    cur.execute('SELECT COUNT(*) AS n FROM equipo_jugador_torneo WHERE id_equipo=%s AND id_torneo=%s', (id_equipo,e['id_torneo']))
                    if cur.fetchone()['n'] >= 10:
                        raise ValueError('El plantel no puede superar los 10 jugadores.')
                    if j['tipo'] in ('docente','funcionario'):
                        cur.execute('''SELECT COUNT(*) AS n FROM equipo_jugador_torneo p
                                       JOIN jugador j ON j.ci=p.ci_jugador
                                       WHERE p.id_equipo=%s AND p.id_torneo=%s
                                       AND j.tipo IN ('docente','funcionario')''', (id_equipo,e['id_torneo']))
                        if cur.fetchone()['n'] >= 2:
                            raise ValueError('Máximo 2 docentes o funcionarios por plantel.')
                    cur.execute('''INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo,numero_camiseta)
                                   VALUES (%s,%s,%s,%s)''', (id_equipo,ci,e['id_torneo'],numero))
                    cn.commit()
                    flash('Jugador inscripto correctamente.')
                except ValueError as exc:
                    cn.rollback()
                    flash('No se pudo inscribir: ' + str(exc))
                except IntegrityError as exc:
                    cn.rollback()
                    if exc.errno == 1062 and 'uq_camiseta_equipo' in str(exc):
                        flash('No se pudo inscribir: el número de camiseta ya está utilizado por otro jugador de este equipo. Elegí uno diferente.')
                    elif exc.errno == 1062:
                        flash('No se pudo inscribir: el jugador ya está inscripto en esta edición del torneo o existe un dato duplicado.')
                    else:
                        flash('No se pudo inscribir por una restricción de integridad de la base de datos.')
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for('planteles.gestionar',id_equipo=id_equipo))

    @bp.post('/equipos/<int:id_equipo>/plantel/retirar')
    def retirar(id_equipo):
        validar_token()
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                try:
                    e = equipo_y_torneo(cur,id_equipo,lock=True)
                    exigir_inscripcion(e)
                    ci = request.form.get('ci','').strip()
                    if e['ci_capitan'] == ci:
                        raise ValueError('Primero designá otro capitán antes de retirarlo.')
                    cur.execute('''DELETE FROM equipo_jugador_torneo
                                   WHERE id_equipo=%s AND id_torneo=%s AND ci_jugador=%s''', (id_equipo,e['id_torneo'],ci))
                    if cur.rowcount != 1:
                        raise ValueError('El jugador no pertenece al plantel.')
                    cn.commit()
                    flash('Jugador retirado durante la inscripción.')
                except (ValueError,IntegrityError) as exc:
                    cn.rollback()
                    flash('No se pudo retirar: ' + str(exc))
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for('planteles.gestionar',id_equipo=id_equipo))

    @bp.post('/equipos/<int:id_equipo>/plantel/capitan')
    def capitan(id_equipo):
        validar_token()
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                try:
                    e = equipo_y_torneo(cur,id_equipo,lock=True)
                    exigir_inscripcion(e)
                    ci = request.form.get('ci','').strip()
                    cur.execute('''SELECT 1 FROM equipo_jugador_torneo p JOIN jugador j ON j.ci=p.ci_jugador
                                   WHERE p.id_equipo=%s AND p.id_torneo=%s AND p.ci_jugador=%s AND j.activo=TRUE''', (id_equipo,e['id_torneo'],ci))
                    if not cur.fetchone():
                        raise ValueError('El capitán debe ser un jugador activo de este plantel.')
                    cur.execute('UPDATE equipo SET ci_capitan=%s WHERE id_equipo=%s', (ci,id_equipo))
                    cn.commit()
                    flash('Capitán actualizado.')
                except (ValueError,IntegrityError) as exc:
                    cn.rollback()
                    flash('No se pudo designar capitán: ' + str(exc))
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for('planteles.gestionar',id_equipo=id_equipo))
    return bp
