"""Alta, modificación y baja lógica de equipos (solo uso local, aún sin login/CSRF)."""
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort
from mysql.connector import IntegrityError, Error

equipos_bp = Blueprint('equipos_abm', __name__)


def registrar_equipos(conectar):
    def opciones(cur):
        cur.execute('SELECT id_torneo, nombre, estado FROM torneo ORDER BY anio DESC, semestre DESC')
        torneos = cur.fetchall()
        cur.execute('SELECT id_facultad, nombre FROM facultad ORDER BY nombre')
        facultades = cur.fetchall()
        return torneos, facultades

    def validar(form):
        nombre = form.get('nombre', '').strip()
        if not 1 <= len(nombre) <= 100:
            raise ValueError('El nombre debe tener entre 1 y 100 caracteres.')
        try:
            id_torneo = int(form.get('id_torneo', ''))
            id_facultad = int(form.get('id_facultad', ''))
        except ValueError as exc:
            raise ValueError('Seleccioná una edición y una facultad.') from exc
        if id_torneo <= 0 or id_facultad <= 0:
            raise ValueError('Edición o facultad inválida.')
        return nombre, id_torneo, id_facultad

    def verificar_inscripcion(cur, id_torneo):
        cur.execute('SELECT estado FROM torneo WHERE id_torneo=%s', (id_torneo,))
        torneo = cur.fetchone()
        if not torneo:
            raise ValueError('La edición del torneo no existe.')
        if torneo['estado'] != 'inscripción':
            raise ValueError('Solo se pueden modificar equipos durante la inscripción.')

    @equipos_bp.route('/equipos/nuevo', methods=['GET', 'POST'])
    def nuevo():
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                torneos, facultades = opciones(cur)
                if request.method == 'POST':
                    try:
                        nombre, id_torneo, id_facultad = validar(request.form)
                        cn.start_transaction() if not cn.in_transaction else None
                        verificar_inscripcion(cur, id_torneo)
                        cur.execute('''INSERT INTO equipo (nombre,id_torneo,id_facultad,ci_capitan)
                                       VALUES (%s,%s,%s,NULL)''', (nombre,id_torneo,id_facultad))
                        cn.commit()
                        flash('Equipo creado. Ahora falta inscribir el plantel y asignar capitán.')
                        return redirect(url_for('listar_equipos'))
                    except (ValueError, IntegrityError) as exc:
                        cn.rollback()
                        flash('No se pudo crear el equipo: ' + str(exc))
                return render_template('equipo_form.html', titulo='Nuevo equipo', equipo=request.form if request.method == 'POST' else None,
                                       torneos=torneos, facultades=facultades, nuevo=True)
            finally:
                cur.close()
        finally:
            cn.close()

    @equipos_bp.route('/equipos/<int:id_equipo>/editar', methods=['GET', 'POST'])
    def editar(id_equipo):
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                cur.execute('SELECT * FROM equipo WHERE id_equipo=%s', (id_equipo,))
                equipo = cur.fetchone()
                if not equipo:
                    abort(404)
                torneos, facultades = opciones(cur)
                if request.method == 'POST':
                    try:
                        nombre, nuevo_torneo, nueva_facultad = validar(request.form)
                        verificar_inscripcion(cur, equipo['id_torneo'])
                        if nuevo_torneo != equipo['id_torneo']:
                            raise ValueError('No se puede trasladar un equipo a otra edición. Creá otro equipo.')
                        if nueva_facultad != equipo['id_facultad']:
                            cur.execute('''SELECT COUNT(*) AS n FROM equipo_jugador_torneo
                                           WHERE id_equipo=%s''', (id_equipo,))
                            if cur.fetchone()['n']:
                                raise ValueError('No se puede cambiar la facultad si ya tiene jugadores inscriptos.')
                        cur.execute('''UPDATE equipo SET nombre=%s, id_facultad=%s
                                       WHERE id_equipo=%s AND activo=TRUE''', (nombre, nueva_facultad, id_equipo))
                        if cur.rowcount == 0 and not equipo['activo']:
                            raise ValueError('El equipo ya está dado de baja.')
                        cn.commit()
                        flash('Equipo actualizado.')
                        return redirect(url_for('listar_equipos'))
                    except (ValueError, IntegrityError) as exc:
                        cn.rollback()
                        flash('No se pudo modificar: ' + str(exc))
                    equipo = dict(equipo, nombre=request.form.get('nombre',''), id_facultad=request.form.get('id_facultad',''))
                return render_template('equipo_form.html', titulo='Editar equipo', equipo=equipo,
                                       torneos=torneos, facultades=facultades, nuevo=False)
            finally:
                cur.close()
        finally:
            cn.close()

    @equipos_bp.post('/equipos/<int:id_equipo>/baja')
    def baja(id_equipo):
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                cur.execute('SELECT id_torneo, activo FROM equipo WHERE id_equipo=%s', (id_equipo,))
                equipo = cur.fetchone()
                if not equipo:
                    abort(404)
                try:
                    verificar_inscripcion(cur, equipo['id_torneo'])
                    cur.execute('UPDATE equipo SET activo=FALSE WHERE id_equipo=%s AND activo=TRUE', (id_equipo,))
                    cn.commit()
                    flash('Equipo dado de baja sin borrar su historial.' if cur.rowcount else 'El equipo ya estaba inactivo.')
                except ValueError as exc:
                    cn.rollback()
                    flash('No se pudo dar de baja: ' + str(exc))
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for('listar_equipos'))

    return equipos_bp
