"""Prueba estática: no necesita MySQL ni modifica datos.
Ejecutar: python tests/validar_estructura.py
"""
from pathlib import Path
import ast
import re

from jinja2 import Environment, FileSystemLoader

RAIZ = Path(__file__).resolve().parent.parent

# Verificar sintaxis Python y nombres de endpoints usados en los templates.
endpoints = {'static'}
for ruta in sorted((RAIZ / 'backend').glob('*.py')):
    tree = ast.parse(ruta.read_text(encoding='utf-8'), filename=str(ruta))
    blueprint = None
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'Blueprint':
            if n.args and isinstance(n.args[0], ast.Constant):
                blueprint = n.args[0].value
    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in n.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and deco.func.attr in ('get','post','route'):
                obj = deco.func.value
                if isinstance(obj, ast.Name):
                    if obj.id == 'app':
                        endpoints.add(n.name)
                    elif blueprint and obj.id in ('bp','jugadores_bp','equipos_bp'):
                        endpoints.add(blueprint + '.' + n.name)

env = Environment(loader=FileSystemLoader(str(RAIZ / 'templates')))
referencias = set()
for plantilla in sorted((RAIZ / 'templates').glob('*.html')):
    env.get_template(plantilla.name)
    referencias.update(re.findall(r'url_for\([\'\"]([^\'\"]+)[\'\"]', plantilla.read_text(encoding='utf-8')))
no_encontradas = sorted(referencias - endpoints)
if no_encontradas:
    raise SystemExit('ERROR: rutas sin definición: ' + ', '.join(no_encontradas))

sql = (RAIZ / 'sql' / '01_esquema.sql').read_text(encoding='utf-8')
tablas = re.findall(r'CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)', sql, re.I)
if len(tablas) != 15 or len(set(tablas)) != 15:
    raise SystemExit(f'ERROR: se esperaban 15 tablas; hay {len(tablas)}')
if 'historial_estado_partido' not in tablas:
    raise SystemExit('ERROR: falta la tabla de historial')

consultas = (RAIZ / 'sql/05_reportes.sql').read_text(encoding='utf-8')
lineas = [l for l in consultas.splitlines() if l.strip() and not l.lstrip().startswith('--')]
instrucciones = [x.strip() for x in '\n'.join(lineas).split(';') if x.strip()]
reportes = [x for x in instrucciones if x.split(None, 1)[0].upper() in ('SELECT','WITH')]
if len(reportes) != 14:
    raise SystemExit(f'ERROR: se esperaban 14 consultas de lectura (auxiliar + 13), hay {len(reportes)}')

inadecuados = list(RAIZ.rglob('*.bak*'))
if inadecuados:
    raise SystemExit('ERROR: hay respaldos/caché en la entrega: ' + str(inadecuados[:5]))
# Regression test: historia debe aparecer en el contenido, no en el título HTML.
plantilla_hist = (RAIZ / 'templates/gestion_partidos.html').read_text(encoding='utf-8')
separador = '{% block content %}'
if separador not in plantilla_hist or 'Historial reciente de cambios' not in plantilla_hist.split(separador, 1)[1]:
    raise SystemExit('ERROR: la sección de historial está fuera del contenido de la página')
if not (RAIZ / 'backend/reportes.py').exists() or not (RAIZ / 'templates/reportes.html').exists():
    raise SystemExit('ERROR: no se incluyó la pantalla web de reportes')

if (RAIZ / '.env').exists():
    raise SystemExit('ERROR: se incluyó el .env privado en la entrega')

print('OK — archivos Python analizados y plantillas Jinja verificadas')
print(f'OK — {len(endpoints)} rutas reconocidas, {len(referencias)} referencias URL verificadas')
print('OK — 15 tablas: 14 requeridas y 1 historial')
print('OK — 9 reportes obligatorios + 3 adicionales + auxiliar + 5A/5B')
print('OK — sin respaldos ni credenciales .env')
print('Esta validación NO prueba la conexión real con MySQL ni transacciones.')
