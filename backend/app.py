# Aplicación Flask del Torneo Interfacultades.
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, abort, session, redirect, url_for, request, has_request_context
from mysql.connector import Error

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / '.env')

app = Flask(__name__, template_folder=str(RAIZ / 'templates'))
# Es imprescindible configurar FLASK_SECRET_KEY en el .env privado.
app.secret_key = os.environ['FLASK_SECRET_KEY']


def conectar():
    """Usa la cuenta MySQL del rol autenticado; el login usa la cuenta tecnica.

    Administradores: DB_USER / DB_PASSWORD (cuenta existente torneo_app).
    Planilleros: DB_PLANILLERO_USER / DB_PLANILLERO_PASSWORD (permisos limitados).
    """
    es_planillero = has_request_context() and session.get('rol') == 'planillero'
    if es_planillero:
        usuario = os.environ['DB_PLANILLERO_USER']
        clave = os.environ['DB_PLANILLERO_PASSWORD']
    else:
        usuario = os.environ['DB_USER']
        clave = os.environ['DB_PASSWORD']
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=usuario,
        password=clave,
        database=os.getenv('DB_NAME', 'torneo_interfacultades'),
        connection_timeout=5,
    )


@app.get('/')
def inicio():
    if session.get('correo'):
        return redirect(url_for('listar_equipos'))
    return redirect(url_for('auth.login'))


@app.get('/equipos')
def listar_equipos():
    try:
        cn = conectar()
        try:
            cursor = cn.cursor(dictionary=True)
            try:
                cursor.execute('''
                    SELECT e.id_equipo, e.activo, e.nombre AS equipo, f.nombre AS facultad,
                           COUNT(p.ci_jugador) AS jugadores
                    FROM equipo AS e
                    JOIN facultad AS f ON f.id_facultad = e.id_facultad
                    LEFT JOIN equipo_jugador_torneo AS p
                      ON p.id_equipo = e.id_equipo AND p.id_torneo = e.id_torneo
                    GROUP BY e.id_equipo, e.nombre, f.nombre
                    ORDER BY e.nombre
                ''')
                equipos = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            cn.close()
        return render_template('equipos.html', equipos=equipos)
    except (Error, KeyError, ValueError) as exc:
        app.logger.error('Error consultando equipos: %s', exc)
        return 'No se pudo consultar MySQL. Revisá .env y que MySQL esté iniciado.', 500


@app.get('/equipos/<int:id_equipo>')
def ver_plantel(id_equipo):
    try:
        cn = conectar()
        try:
            cursor = cn.cursor(dictionary=True)
            try:
                cursor.execute('''
                    SELECT e.id_equipo, e.nombre AS equipo, f.nombre AS facultad
                    FROM equipo e JOIN facultad f ON f.id_facultad = e.id_facultad
                    WHERE e.id_equipo = %s
                ''', (id_equipo,))
                equipo = cursor.fetchone()
                if equipo is None:
                    abort(404)
                cursor.execute('''
                    SELECT j.ci, j.nombre, j.apellido, j.tipo, p.numero_camiseta,
                           (e.ci_capitan = j.ci) AS es_capitan
                    FROM equipo_jugador_torneo p
                    JOIN jugador j ON j.ci = p.ci_jugador
                    JOIN equipo e ON e.id_equipo = p.id_equipo AND e.id_torneo = p.id_torneo
                    WHERE p.id_equipo = %s
                    ORDER BY p.numero_camiseta
                ''', (id_equipo,))
                jugadores = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            cn.close()
        return render_template('plantel.html', equipo=equipo, jugadores=jugadores)
    except (Error, KeyError, ValueError) as exc:
        app.logger.error('Error consultando plantel: %s', exc)
        return 'No se pudo consultar el plantel.', 500


@app.get('/jugadores/<ci>/detalle')
def detalle_jugador(ci):
    try:
        cn = conectar()
        try:
            cursor = cn.cursor(dictionary=True)
            try:
                cursor.execute('''
                    SELECT j.ci, j.nombre, j.apellido, j.email,
                           j.fecha_nacimiento, j.tipo, j.activo,
                           f.nombre AS facultad
                    FROM jugador j JOIN facultad f ON f.id_facultad = j.id_facultad
                    WHERE j.ci = %s
                ''', (ci,))
                jugador = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            cn.close()
    except (Error, KeyError, ValueError) as exc:
        app.logger.error('Error consultando ficha del jugador: %s', exc)
        return 'No se pudo consultar la ficha.', 500
    if jugador is None:
        abort(404)
    return render_template('jugador_detalle.html', jugador=jugador)


from auth import registrar_auth
app.register_blueprint(registrar_auth(conectar))

from jugadores import registrar
app.register_blueprint(registrar(conectar))

from equipos_abm import registrar_equipos
app.register_blueprint(registrar_equipos(conectar))

from planteles import registrar_planteles
app.register_blueprint(registrar_planteles(conectar))

from partidos import registrar_partidos
app.register_blueprint(registrar_partidos(conectar))

from planillas import registrar_planillas
app.register_blueprint(registrar_planillas(conectar))

from eventos import registrar_eventos
app.register_blueprint(registrar_eventos(conectar))


# ABM de sanciones disciplinarias (modulo 18).
from sanciones_disciplinarias import registrar_sanciones
app.register_blueprint(registrar_sanciones(conectar))

# ABM de complejos y canchas (modulo 19).
from instalaciones import registrar_instalaciones
app.register_blueprint(registrar_instalaciones(conectar))


# Estado de partidos: módulo 20 (sin modificar partidos.py).
from gestion_partidos import registrar_gestion_partidos
app.register_blueprint(registrar_gestion_partidos(conectar))


@app.before_request
def controlar_permisos():
    # Autorización centralizada; todas las rutas no listadas quedan bloqueadas.
    endpoint = request.endpoint

    if endpoint is None:
        return None  # Permite que Flask responda 404 a rutas inexistentes.

    if endpoint in {'static', 'inicio', 'auth.login'}:
        return None

    # Solo estas páginas pueden consultarse sin sesión. Nunca formularios de gestión.
    publicas = {
        'listar_equipos', 'ver_plantel', 'detalle_jugador',
        'jugadores.lista', 'partidos.lista',
    }
    if request.method == 'GET' and endpoint in publicas:
        return None

    if endpoint == 'auth.logout':
        return None  # La ruta solo acepta POST y borra la sesión.

    if not session.get('correo'):
        if request.method == 'GET':
            return redirect(url_for('auth.login'))
        abort(403)

    rol = session.get('rol')
    if rol == 'administrador':
        return None

    # El planillero puede consultar las páginas públicas y editar planillas/eventos.
    # No puede acceder a ABM de equipos, jugadores, fixture ni planteles.
    if rol == 'planillero' and endpoint in {'planillas.editar', 'eventos.detalle'}:
        return None

    abort(403)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
