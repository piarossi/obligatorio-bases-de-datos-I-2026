"""Consulta web de los 9 reportes obligatorios y las tres consultas adicionales.

Reutiliza literalmente las consultas SQL de sql/05_reportes.sql.
No acepta SQL de usuarios: el selector solamente utiliza un índice dentro de un listado fijo.
"""
from pathlib import Path

from flask import Blueprint, render_template, request
from mysql.connector import Error

ARCHIVO_SQL = Path(__file__).resolve().parent.parent / 'sql' / '05_reportes.sql'
TITULOS = (
    'Auxiliar · Tarjetas por jugador',
    '01 · Tabla de posiciones',
    '02 · Diez máximos goleadores',
    '03 · Fair play por equipo',
    '04 · Promedio de goles por fecha y edición',
    '05A · Canchas más utilizadas',
    '05B · Turnos más utilizados',
    '06 · Jugadores por facultad y tipo',
    '07 · Inscriptos que no participaron',
    '08 · Sanciones por equipo y motivo',
    '09 · Porcentaje de partidos por estado',
    'Extra 01 · Participaciones por jugador',
    'Extra 02 · Vallas invictas por equipo',
    'Extra 03 · Máximo goleador por equipo',
)


def cargar_consultas():
    # Líneas comentadas comienzan con --. El SQL es un archivo interno
    # versionado, no una entrada del navegador.
    lineas = [line for line in ARCHIVO_SQL.read_text(encoding='utf-8').splitlines()
              if line.strip() and not line.lstrip().startswith('--')]
    instrucciones = [q.strip() for q in '\n'.join(lineas).split(';') if q.strip()]
    seleccion = [q for q in instrucciones if q.lstrip().split(None, 1)[0].upper() in ('SELECT', 'WITH')]
    if len(seleccion) != len(TITULOS):
        raise RuntimeError('La lista de reportes no coincide con sql/05_reportes.sql.')
    return seleccion


def registrar_reportes(conectar):
    bp = Blueprint('reportes', __name__)

    @bp.get('/reportes')
    def vista():
        try:
            indice = int(request.args.get('reporte', '1'))
        except (ValueError, TypeError):
            indice = 1
        if not 0 <= indice < len(TITULOS):
            indice = 1
        columnas, filas, mensaje = [], [], None
        try:
            sql = cargar_consultas()[indice]
            cn = conectar()
            try:
                cursor = cn.cursor(dictionary=True, buffered=True)
                try:
                    cursor.execute(sql)
                    columnas = [x[0] for x in cursor.description]
                    filas = cursor.fetchall()
                finally:
                    cursor.close()
            finally:
                cn.close()
        except (Error, OSError, RuntimeError, KeyError, ValueError) as exc:
            # No exponer datos de conexión al navegador; preservar en logs servidor.
            from flask import current_app
            current_app.logger.error('Error de reporte SQL: %s', exc)
            mensaje = 'No se pudo consultar el reporte. Verificá MySQL y el archivo SQL.'
        return render_template('reportes.html', titulos=TITULOS, seleccionado=indice,
                               columnas=columnas, filas=filas, mensaje=mensaje)

    return bp
