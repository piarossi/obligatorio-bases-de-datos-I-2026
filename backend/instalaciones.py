"""ABM de complejos y canchas; consultas SQL directas, sin ORM."""
from hmac import compare_digest
from secrets import token_hex
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error, IntegrityError


def registrar_instalaciones(conectar):
    bp = Blueprint('instalaciones', __name__, url_prefix='/instalaciones')

    @bp.before_request
    def exigir_administrador():
        if session.get('rol') != 'administrador' or not session.get('correo'):
            abort(403)

    def token():
        if 'instalaciones_csrf' not in session:
            session['instalaciones_csrf'] = token_hex(24)
        return session['instalaciones_csrf']

    def verificar():
        if not compare_digest(request.form.get('_csrf', ''), token()):
            abort(400, 'Formulario no válido.')

    def texto(campo, maximo=150):
        valor = request.form.get(campo, '').strip()
        if not valor or len(valor) > maximo:
            raise ValueError(f'El campo {campo} es obligatorio (máximo {maximo} caracteres).')
        return valor

    def id_complejo():
        try:
            valor = int(request.form.get('id_complejo', ''))
        except ValueError:
            raise ValueError('Seleccioná un complejo válido.')
        if valor <= 0:
            raise ValueError('Seleccioná un complejo válido.')
        return valor

    @bp.route('/', methods=['GET', 'POST'])
    def lista():
        if request.method == 'POST':
            verificar()
            cn = conectar()
            try:
                cur = cn.cursor(dictionary=True, buffered=True)
                try:
                    try:
                        accion = request.form.get('accion', '')
                        if accion == 'crear_complejo':
                            nombre = texto('nombre', 100)
                            direccion = texto('direccion', 200)
                            departamento = texto('departamento', 100)
                            cur.execute('''INSERT INTO complejo(nombre, direccion, departamento)
                                           VALUES (%s,%s,%s)''', (nombre, direccion, departamento))
                            flash('Complejo creado correctamente.')
                        elif accion == 'editar_complejo':
                            identificador = id_complejo()
                            nombre = texto('nombre', 100)
                            direccion = texto('direccion', 200)
                            departamento = texto('departamento', 100)
                            cur.execute('''UPDATE complejo SET nombre=%s, direccion=%s, departamento=%s
                                           WHERE id_complejo=%s''',
                                        (nombre, direccion, departamento, identificador))
                            if cur.rowcount == 0:
                                cur.execute('SELECT 1 FROM complejo WHERE id_complejo=%s', (identificador,))
                                if cur.fetchone() is None:
                                    raise ValueError('No existe el complejo.')
                            flash('Complejo actualizado.')
                        elif accion == 'eliminar_complejo':
                            identificador = id_complejo()
                            cur.execute('SELECT COUNT(*) AS total FROM cancha WHERE id_complejo=%s',
                                        (identificador,))
                            if cur.fetchone()['total']:
                                raise ValueError('No se puede eliminar un complejo que tiene canchas. Conservamos las relaciones.')
                            cur.execute('DELETE FROM complejo WHERE id_complejo=%s', (identificador,))
                            if cur.rowcount != 1:
                                raise ValueError('El complejo no existe.')
                            flash('Complejo eliminado.')
                        elif accion == 'crear_cancha':
                            identificador = id_complejo()
                            nombre = texto('nombre_cancha', 100)
                            superficie = request.form.get('superficie', '')
                            if superficie not in ('sintético', 'parquet'):
                                raise ValueError('Seleccioná una superficie válida.')
                            techada = 1 if request.form.get('techada') == '1' else 0
                            cur.execute('''INSERT INTO cancha(nombre_cancha,id_complejo,superficie,techada)
                                           VALUES (%s,%s,%s,%s)''',
                                        (nombre, identificador, superficie, techada))
                            flash('Cancha creada correctamente.')
                        elif accion == 'editar_cancha':
                            identificador = id_complejo()
                            nombre = texto('nombre_cancha', 100)
                            superficie = request.form.get('superficie', '')
                            if superficie not in ('sintético', 'parquet'):
                                raise ValueError('Seleccioná una superficie válida.')
                            techada = 1 if request.form.get('techada') == '1' else 0
                            # No se altera la PK compuesta si está referenciada por partidos.
                            cur.execute('''UPDATE cancha SET superficie=%s, techada=%s
                                           WHERE id_complejo=%s AND nombre_cancha=%s''',
                                        (superficie, techada, identificador, nombre))
                            if cur.rowcount == 0:
                                cur.execute('''SELECT 1 FROM cancha
                                               WHERE id_complejo=%s AND nombre_cancha=%s''',
                                            (identificador, nombre))
                                if cur.fetchone() is None:
                                    raise ValueError('La cancha no existe.')
                            flash('Cancha actualizada.')
                        elif accion == 'eliminar_cancha':
                            identificador = id_complejo()
                            nombre = texto('nombre_cancha', 100)
                            cur.execute('''SELECT COUNT(*) AS total FROM partido
                                           WHERE id_complejo=%s AND nombre_cancha=%s''',
                                        (identificador, nombre))
                            if cur.fetchone()['total']:
                                raise ValueError('No se puede eliminar una cancha usada por partidos, incluso históricos.')
                            cur.execute('''DELETE FROM cancha
                                           WHERE id_complejo=%s AND nombre_cancha=%s''',
                                        (identificador, nombre))
                            if cur.rowcount != 1:
                                raise ValueError('La cancha no existe.')
                            flash('Cancha eliminada.')
                        else:
                            raise ValueError('Acción no reconocida.')
                        cn.commit()
                        return redirect(url_for('.lista'))
                    except ValueError as exc:
                        cn.rollback()
                        flash(str(exc))
                    except IntegrityError:
                        cn.rollback()
                        flash('No se pudo realizar la operación: hay un duplicado o una relación que debe conservarse.')
                    except Error:
                        cn.rollback()
                        flash('No se pudo guardar el cambio en MySQL.')
                finally:
                    cur.close()
            finally:
                cn.close()

        cn = conectar()
        try:
            cur = cn.cursor(dictionary=True, buffered=True)
            try:
                cur.execute('''SELECT c.id_complejo, c.nombre, c.direccion, c.departamento,
                                      COUNT(a.nombre_cancha) AS cantidad_canchas
                               FROM complejo c LEFT JOIN cancha a ON a.id_complejo=c.id_complejo
                               GROUP BY c.id_complejo,c.nombre,c.direccion,c.departamento
                               ORDER BY c.nombre''')
                complejos = cur.fetchall()
                cur.execute('''SELECT a.nombre_cancha,a.id_complejo,a.superficie,a.techada,
                                      c.nombre AS complejo,
                                      COUNT(p.id_partido) AS partidos_asociados
                               FROM cancha a
                               JOIN complejo c ON c.id_complejo=a.id_complejo
                               LEFT JOIN partido p ON p.id_complejo=a.id_complejo
                                                 AND p.nombre_cancha=a.nombre_cancha
                               GROUP BY a.nombre_cancha,a.id_complejo,a.superficie,a.techada,c.nombre
                               ORDER BY c.nombre,a.nombre_cancha''')
                canchas = cur.fetchall()
            finally:
                cur.close()
        finally:
            cn.close()
        return render_template('instalaciones.html', complejos=complejos,
                               canchas=canchas, csrf=token())

    return bp
