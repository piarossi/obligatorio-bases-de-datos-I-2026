"""Registro auditable de modificaciones del partido dentro de la transacción existente.

No abre otra conexión ni hace COMMIT: la operación principal y su historial
se guardan juntos o se revierten juntos con ROLLBACK.
"""
from flask import session


def registrar_historial(cur, anterior, nuevo, accion, motivo=None):
    """anterior/nuevo: diccionarios con los campos de partido, o None al crearlo."""
    actual = nuevo or anterior
    if actual is None:
        raise ValueError('Se necesita identificar un partido.')
    cur.execute("""INSERT INTO historial_estado_partido
        (id_partido, accion, estado_anterior, estado_nuevo,
         dia_anterior, dia_nuevo, turno_anterior, turno_nuevo,
         complejo_anterior, complejo_nuevo, cancha_anterior, cancha_nueva,
         correo_usuario, motivo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (actual['id_partido'], accion,
         anterior['estado'] if anterior else None, nuevo['estado'] if nuevo else None,
         anterior['dia'] if anterior else None, nuevo['dia'] if nuevo else None,
         anterior['id_turno'] if anterior else None, nuevo['id_turno'] if nuevo else None,
         anterior['id_complejo'] if anterior else None, nuevo['id_complejo'] if nuevo else None,
         anterior['nombre_cancha'] if anterior else None, nuevo['nombre_cancha'] if nuevo else None,
         session.get('correo'), motivo))
