"""ABM inicial de jugadores para uso LOCAL. Falta autenticación y CSRF."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from mysql.connector import IntegrityError

jugadores_bp = Blueprint('jugadores', __name__)
TIPOS = ('grado', 'posgrado', 'docente', 'funcionario')


def registrar(conectar):
    """Vincula las rutas con la función de conexión ya existente."""
    def validar(form, nuevo=True):
        ci = form.get('ci', '').strip()
        nombre = form.get('nombre', '').strip()
        apellido = form.get('apellido', '').strip()
        email = form.get('email', '').strip().lower()
        nacimiento = form.get('fecha_nacimiento', '').strip()
        try:
            facultad = int(form.get('id_facultad', ''))
            fecha = date.fromisoformat(nacimiento)
        except (ValueError, TypeError):
            raise ValueError('Revisá la facultad y la fecha de nacimiento.')
        if nuevo and (not ci.isdigit() or not 5 <= len(ci) <= 20):
            raise ValueError('La CI debe contener entre 5 y 20 dígitos.')
        if not nombre or not apellido or len(nombre)>80 or len(apellido)>80:
            raise ValueError('Nombre y apellido son obligatorios (máximo 80 caracteres).')
        if '@' not in email or len(email)>150:
            raise ValueError('Correo inválido.')
        if fecha > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura.')
        if form.get('tipo') not in TIPOS or facultad <= 0:
            raise ValueError('Tipo o facultad inválidos.')
        return (ci, nombre, apellido, email, nacimiento, facultad, form['tipo'])

    def facultades(cursor):
        cursor.execute('SELECT id_facultad, nombre FROM facultad ORDER BY nombre')
        return cursor.fetchall()

    @jugadores_bp.get('/jugadores')
    def lista():
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                cur.execute('''SELECT j.ci, j.nombre, j.apellido, j.tipo, j.activo,
                                      f.nombre AS facultad
                               FROM jugador j JOIN facultad f ON j.id_facultad=f.id_facultad
                               ORDER BY j.apellido, j.nombre''')
                datos = cur.fetchall()
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template('jugadores.html', jugadores=datos)

    @jugadores_bp.route('/jugadores/nuevo', methods=['GET','POST'])
    def nuevo():
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                opciones = facultades(cur)
                if request.method=='POST':
                    try:
                        d = validar(request.form)
                        cur.execute('''INSERT INTO jugador
                            (ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)''', d)
                        cn.commit()
                        flash('Jugador creado correctamente.')
                        return redirect(url_for('jugadores.lista'))
                    except (ValueError, IntegrityError) as e:
                        cn.rollback()
                        flash('Error al crear: ' + str(e))
                return render_template('jugador_form.html', jugador=request.form if request.method=='POST' else None,
                                       facultades=opciones, titulo='Nuevo jugador', nuevo=True)
            finally:
                cur.close()
        finally:
            cn.close()

    @jugadores_bp.route('/jugadores/<ci>/editar', methods=['GET','POST'])
    def editar(ci):
        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True)
            try:
                cur.execute('SELECT * FROM jugador WHERE ci=%s', (ci,))
                jugador = cur.fetchone()
                if not jugador:
                    abort(404)
                opciones = facultades(cur)
                if request.method=='POST':
                    try:
                        d = validar(request.form, nuevo=False)
                        cur.execute('''SELECT COUNT(*) AS n FROM equipo_jugador_torneo p
                                       JOIN equipo e ON p.id_equipo=e.id_equipo AND p.id_torneo=e.id_torneo
                                       WHERE p.ci_jugador=%s AND e.id_facultad<>%s''', (ci, d[5]))
                        if cur.fetchone()['n']:
                            raise ValueError('No se puede cambiar la facultad: ya integra un plantel de otra facultad.')
                        cur.execute('''UPDATE jugador SET nombre=%s, apellido=%s, email=%s,
                                        fecha_nacimiento=%s, id_facultad=%s, tipo=%s WHERE ci=%s''',
                                    (d[1], d[2], d[3], d[4], d[5], d[6], ci))
                        cn.commit()
                        flash('Jugador actualizado correctamente.')
                        return redirect(url_for('jugadores.lista'))
                    except (ValueError, IntegrityError) as e:
                        cn.rollback()
                        flash('Error al editar: ' + str(e))
                    jugador = dict(request.form, ci=ci)
                return render_template('jugador_form.html', jugador=jugador, facultades=opciones,
                                       titulo='Editar jugador', nuevo=False)
            finally:
                cur.close()
        finally:
            cn.close()

    @jugadores_bp.post('/jugadores/<ci>/baja')
    def baja(ci):
        cn = conectar()
        try:
            cur = cn.cursor()
            try:
                cur.execute('UPDATE jugador SET activo=FALSE WHERE ci=%s AND activo=TRUE', (ci,))
                cn.commit()
                flash('Baja lógica registrada: se conserva el historial.' if cur.rowcount else 'Jugador inexistente o ya inactivo.')
            finally:
                cur.close()
        finally:
            cn.close()
        return redirect(url_for('jugadores.lista'))

    return jugadores_bp
