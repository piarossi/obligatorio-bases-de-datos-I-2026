# Torneo Interfacultades de Fútbol 5 — Bases de Datos I (UCU)

Aplicación web local en **Python + Flask + MySQL 8**, sin ORM. Incluye los 14 objetos relacionales requeridos y una **15.ª tabla de historial de cambios de partidos**, con reporte técnico en `docs/INFORME_FINAL_BD_I.docx`.

## 1. Qué incluye

- ABM de jugadores y equipos (baja lógica), gestión de planteles, capitanes, complejos y canchas.
- Partidos: programación, cancelación, postergación, reprogramación y cierre; planillas, goles normales/autogoles y tarjetas.
- Sanciones automáticas por expulsión y acumulación de amarillas; sanciones disciplinarias administrables.
- Inicio/cierre de sesión, administrador y planillero con distintos permisos MySQL.
- Menú por rol y **Reportes** de solo lectura: 9 apartados obligatorios y 3 adicionales; el reporte de canchas/turnos se divide en 5A y 5B. Las consultas originales están en `sql/05_reportes.sql`.
- Historial de cambios: crea registro de alta, postergación, reprogramación, cancelación y cierre; conserva fecha/programación, responsable y motivo cuando se solicita.

## 2. Instalación desde cero — solo en una base NUEVA

**No ejecutes estos scripts de creación/datos sobre `torneo_interfacultades` si ya tiene datos.** Para probar desde cero usá una instancia de MySQL vacía o una base aislada con los nombres adaptados.

1. Tener MySQL 8+ y Python 3.11+ instalados. En la raíz de esta carpeta:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. En DataGrip con una conexión administradora de MySQL, ejecutar en este orden, sobre una base vacía llamada `torneo_interfacultades`:
   - `sql/01_esquema.sql` — 15 tablas (14 de la letra + historial).
   - `sql/02_datos_base.sql` — facultades, torneo, complejos, canchas y turnos.
   - `sql/03_equipos_jugadores.sql` — 6 equipos con jugadores y planteles.
   - `sql/04_partidos_demo.sql` — 9 encuentros jugados en 3 fechas, con planillas/goles/tarjetas de prueba.
3. Editar **una copia local privada** de `sql/06_permisos_mysql.sql` y reemplazar los marcadores `REEMPLAZAR_CON_CLAVE_APP_MYSQL` y `REEMPLAZAR_CON_CLAVE_LARGA_UNICA` por **dos contraseñas fuertes distintas**. Ejecutar la copia local con permisos administrativos; no subir ese archivo editado. Si `torneo_app` ya existía, el script **no le cambia** su clave: usar la vigente en `.env`.
4. Ejecutar `cp .env.example .env`. Completar `DB_USER`, `DB_PASSWORD`, `DB_PLANILLERO_USER`, `DB_PLANILLERO_PASSWORD`, `DB_NAME` y `FLASK_SECRET_KEY` de manera coherente con MySQL. **No publicar `.env`**.
5. Crear usuarios de **la aplicación**, separados de las cuentas técnicas MySQL:
   ```bash
   python backend/crear_usuario.py
   ```
   Ejecutar una vez para el **administrador** y otra para el **planillero**, ingresando correo, rol y una contraseña segura (se guarda su hash). No existe una contraseña predeterminada en el repositorio.
6. Levantar Flask: `python backend/app.py`; abrir `http://127.0.0.1:5000/`.
7. Visitar `/equipos`, `/partidos`, `/gestion-partidos/` (administrador), `/instalaciones/`, `/sanciones/` y `/reportes`.
8. Consultas: `sql/05_reportes.sql`; verificación de inconsistencias: `sql/07_auditoria_integridad.sql`. **Cero filas en los controles de inconsistencias significa que no se detectaron errores de ese tipo**, no que todas las reglas sean infalibles.

## 3. Actualizar una instalación EXISTENTE

- **No ejecutar `01_esquema.sql` ni los scripts de carga de datos** sobre la base existente.
- Hacer antes una copia privada mediante `mysqldump` y conservarla fuera del repositorio.
- Si todavía no existe el historial, ejecutar **solo** `sql/08_migracion_historial.sql` con administrador MySQL.
- Para que el planillero pueda registrar el cierre en el historial, ejecutar `sql/09_permiso_historial_existente.sql` con administrador MySQL.
- Reemplazar los archivos activos `backend/`, `templates/`, `backend/static/` en la carpeta de la aplicación. La tabla de historial registra cambios desde su instalación, **no reconstruye cambios antiguos**.
- El SQL de instalación no debe ejecutarse dos veces con datos ya insertados.

## 4. Menú y permisos

- **Visitante:** consultar equipos, jugadores, partidos y reportes.
- **Administrador:** ABM de equipos, jugadores, planteles, instalaciones, sanciones y gestión de partidos.
- **Planillero:** consultar información y gestionar planillas, goles, tarjetas y cierre. Sus permisos MySQL limitan escrituras a las tablas correspondientes; no puede administrar los ABM.
- El menú muestra opciones acordes al rol, pero **la seguridad real se aplica en rutas Flask y privilegios de MySQL**, no solo ocultando botones.

## 5. Estructura mínima y justificación

```text
backend/                  Módulos Python por dominio y estilos CSS
  app.py                  Inicialización, conexión y permisos centralizados
  auth.py                 Autenticación y sesiones
  jugadores.py            ABM de jugadores
  equipos_abm.py          ABM de equipos
  planteles.py            Inscripciones y capitanes
  partidos.py             Alta y listado de fixture
  gestion_partidos.py     Postergar, cancelar y reprogramar
  planillas.py            Participantes de partidos
  eventos.py              Goles, tarjetas y cierre
  sanciones.py            Cálculo de sanciones automáticas
  sanciones_disciplinarias.py  ABM de sanciones manuales
  instalaciones.py        Complejos y canchas
  historial_partidos.py   INSERT de auditoría dentro de la transacción
  reportes.py             Consulta web de consultas SQL existentes
  crear_usuario.py        Alta de cuentas de aplicación
sql/                      Instalación, datos, informes, auditoría y migración
  01_esquema.sql
  02_datos_base.sql
  03_equipos_jugadores.sql
  04_partidos_demo.sql
  05_reportes.sql
  06_permisos_mysql.sql
  07_auditoria_integridad.sql
  08_migracion_historial.sql       Solo en bases existentes
  09_permiso_historial_existente.sql   Solo en bases existentes
templates/                Plantillas HTML (solo una versión por pantalla)
docs/                     Informe final y consigna de referencia
tests/                    Verificación estática sin modificar MySQL
```

Mantener Python modular es deliberado: **evita un único archivo enorme**, aísla reglas y facilita su revisión. Los scripts evolutivos, `.bak`, copias `actualizado`, `prueba.sql` y `sql/app.py` anteriores **no forman parte de esta entrega**.

## 6. Comprobación rápida antes de entregar

```bash
python -m compileall -q backend
python tests/validar_estructura.py
```

Estas pruebas comprueban estructura y plantillas, **no sustituyen** una prueba real contra MySQL. Ver `PRUEBAS_ANTES_DE_ENTREGAR.md` para comprobar login por rol, alta/reprogramación/cierre, registro del historial y reportes. El sistema fue desarrollado para ejecución local, no para exposición directa a Internet.

## 7. Referencias

Explicaciones, decisiones de diseño, alternativas descartadas, bitácora y bibliografía: `docs/INFORME_FINAL_BD_I.docx`.
