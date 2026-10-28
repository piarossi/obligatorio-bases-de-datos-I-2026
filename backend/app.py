"""Primera interfaz web del obligatorio: listado de equipos y planteles."""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, abort
from mysql.connector import Error

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / '.env')

app = Flask(__name__, template_folder=str(RAIZ / 'templates'))
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'solo-desarrollo-local')


def conectar():
    """Abre una conexión nueva por consulta; nunca comparte conexiones globales."""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.getenv('DB_NAME', 'torneo_interfacultades'),
        connection_timeout=5,
    )


@app.get('/')
@app.get('/equipos')
def listar_equipos():
    try:
        cn = conectar()
        try:
            cursor = cn.cursor(dictionary=True)
            try:
                cursor.execute('''
                    SELECT e.id_equipo, e.nombre AS equipo, f.nombre AS facultad,
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

from jugadores import registrar
app.register_blueprint(registrar(conectar))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
