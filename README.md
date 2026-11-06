# Torneo Interfacultades de Fútbol 5 — Bases de Datos I (UCU)

Aplicación local con MySQL 8, Python y Flask, sin ORM.

## Instalación desde cero (NO ejecutar esto sobre la base existente)

1. Instalar MySQL 8 y Python; crear un entorno virtual: `python3 -m venv .venv` y `source .venv/bin/activate`.
2. Instalar dependencias con `pip install -r requirements.txt`.
3. Con una conexión administradora de MySQL en DataGrip, ejecutar **en orden**:
   - `sql/01_esquema.sql` (14 tablas; usar una base VACÍA)
   - `sql/02_datos_base.sql` (facultades, edición, complejos, canchas, turnos)
   - `sql/03_equipos_jugadores.sql` (6 equipos con planteles)
   - `sql/04_partidos_demo.sql` (9 partidos disputados en 3 fechas y eventos de muestra)
4. Crear la cuenta `torneo_app` de MySQL con SELECT/INSERT/UPDATE/DELETE sobre `torneo_interfacultades.*`, **sin** CREATE/ALTER/DROP. Desde usuario administrador: `CREATE USER 'torneo_app'@'localhost' IDENTIFIED BY 'CLAVE_PROPIA'; GRANT SELECT,INSERT,UPDATE,DELETE ON torneo_interfacultades.* TO 'torneo_app'@'localhost';`. Si ya existe, NO ejecutar CREATE USER; configurar su clave actual.
5. Editar **antes de ejecutar** `sql/06_permisos_mysql.sql`: reemplazar las dos ocurrencias de `REEMPLAZAR_CON_CLAVE_LARGA_UNICA` con una contraseña única y segura. Ejecutar con administrador MySQL. No subir a GitHub una copia editada con la clave real.
6. Copiar `.env.example` a `.env` y completar las claves reales y una `FLASK_SECRET_KEY` larga, aleatoria. El `.env` no se publica.
7. Crear el administrador de aplicación: `python backend/crear_usuario.py` (usa el usuario de MySQL `torneo_app`). Ese comando crea solo el perfil administrador; para el planillero insertar un hash generado con `werkzeug.security.generate_password_hash` en `login` con rol `planillero`, como hicimos durante las pruebas. No guardar contraseñas en claro.
8. Iniciar: `python backend/app.py` y abrir `http://127.0.0.1:5000/`.
9. Los reportes están en `sql/05_reportes.sql` y las auditorías de integridad en `sql/07_auditoria_integridad.sql`.

## Funciones

Administración de jugadores, equipos, planteles, partidos y estados, complejos/canchas, sanciones; registro de planillas, goles, tarjetas, resultado y sanciones automáticas. Dos perfiles de login: administrador y planillero. Consultas de reportes ejecutables en DataGrip.

## Datos de muestra

`04_partidos_demo.sql` genera **datos ficticios reproducibles**, no los resultados exactos de la base de desarrollo. Asegura el requisito de seis equipos y nueve partidos disputados en tres fechas. Para recuperar el historial exacto de las pruebas de desarrollo, usar el respaldo MySQL privado (no incluirlo con contraseñas).

## Seguridad

El backend elige la cuenta técnica MySQL según la sesión autenticada; las rutas Flask verifican roles y CSRF en formularios. El usuario del planillero tiene permisos limitados a planillas, goles, tarjetas, sanciones automáticas y cierre de partido. La cuenta técnica de administrador no tiene permisos estructurales. Mantener claves fuera del repositorio.

## Advertencia

Esta copia fue revisada estáticamente (compilación Python y parsing Jinja), pero **no fue probada contra una instalación nueva de MySQL**. Probar los scripts de cero sobre una base NUEVA antes de presentar la entrega como verificada.
