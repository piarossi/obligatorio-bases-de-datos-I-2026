"""Alta independiente de usuarios de la aplicación (administrador/planillero).

Ejecutar desde la raíz del proyecto: python backend/crear_usuario.py
No imprime ni guarda la contraseña en texto plano.
"""
import os
from pathlib import Path
from getpass import getpass

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

print('Crear usuario de la aplicación (no una cuenta de MySQL)')
correo = input('Correo electrónico: ').strip().lower()
rol = input('Rol [administrador/planillero]: ').strip().lower()
if rol not in ('administrador', 'planillero'):
    raise SystemExit('Rol inválido. Usá administrador o planillero.')
if '@' not in correo or len(correo) > 150 or correo.startswith('@') or correo.endswith('@'):
    raise SystemExit('Ingresá un correo válido.')
contrasena = getpass('Contraseña nueva (mínimo 12 caracteres): ')
confirmacion = getpass('Repetir contraseña: ')
if len(contrasena) < 12 or contrasena != confirmacion:
    raise SystemExit('Contraseña demasiado corta o las contraseñas no coinciden.')

cn = None
try:
    cn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.getenv('DB_NAME', 'torneo_interfacultades'),
    )
    cur = cn.cursor()
    try:
        cur.execute(
            'INSERT INTO login (correo, contrasena, rol) VALUES (%s, %s, %s)',
            (correo, generate_password_hash(contrasena), rol),
        )
        cn.commit()
        print(f'Usuario {rol} creado correctamente en {cn.database}.')
    except mysql.connector.IntegrityError:
        cn.rollback()
        print('Ese correo ya existe. No se modificó ninguna cuenta.')
    finally:
        cur.close()
except (mysql.connector.Error, KeyError, ValueError) as exc:
    print('No se pudo crear el usuario. Revisá la conexión del .env y la base seleccionada.')
    raise SystemExit(1) from exc
finally:
    if cn is not None and cn.is_connected():
        cn.close()
