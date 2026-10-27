"""Prueba de conexión a MySQL para el obligatorio BD I."""
import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / '.env')


def main():
    try:
        conexion = mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.getenv('DB_NAME', 'torneo_interfacultades'),
            connection_timeout=5,
        )
        with conexion.cursor() as cursor:
            cursor.execute('''
                SELECT e.nombre, f.nombre, COUNT(ejt.ci_jugador) AS jugadores
                FROM equipo AS e
                JOIN facultad AS f ON f.id_facultad = e.id_facultad
                LEFT JOIN equipo_jugador_torneo AS ejt
                    ON ejt.id_equipo = e.id_equipo AND ejt.id_torneo = e.id_torneo
                GROUP BY e.id_equipo, e.nombre, f.nombre
                ORDER BY e.nombre
            ''')
            equipos = cursor.fetchall()
        print(f'Conexión correcta. Equipos encontrados: {len(equipos)}')
        for equipo, facultad, cantidad in equipos:
            print(f'- {equipo} | {facultad} | {cantidad} jugadores')
        conexion.close()
    except KeyError as e:
        print(f'Falta configurar {e.args[0]} en el archivo .env')
        sys.exit(1)
    except (Error, ValueError) as e:
        print(f'No se pudo conectar o consultar MySQL: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
