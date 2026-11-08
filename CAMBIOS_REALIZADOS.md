# Qué se limpió y qué se mejoró

## Limpieza

- Se partió del ZIP `revision_completa_bd1.zip` y se conservaron únicamente archivos utilizados o necesarios para la entrega.
- Se excluyeron los respaldos `*.bak*`, SQL de parche anteriores, scripts de prueba improvisados, un `sql/app.py` duplicado, el archivo HTML `gestion_partidos_corregido.html` con nombre incorrecto y el Word preliminar duplicado.
- Se conservaron módulos Python separados, tal como pidió el docente. No se fusionaron `partidos.py` y `gestion_partidos.py`, porque cumplen tareas distintas; tampoco `sanciones.py` con `sanciones_disciplinarias.py`, ya que una calcula automáticamente y otra ofrece ABM manual.
- Los SQL se reorganizaron en siete scripts de instalación/reportes/auditoría y dos scripts **solo para actualizar bases ya existentes**.

## Funcionalidades y correcciones

1. **Historial de partidos:** la sección ahora está realmente en `templates/gestion_partidos.html` dentro de `block content`; se registra cambio de programación/estado en la misma transacción con motivo, usuario, datos anteriores y nuevos.
2. **Menú por perfil:** navegación común a equipos, jugadores, partidos, reportes y, para administradores, gestión de estados, instalaciones y sanciones; botón Salir por POST protegido.
3. **Reportes web:** nueva ruta `/reportes` de solo lectura que ejecuta las consultas de `sql/05_reportes.sql`. Los scripts SQL siguen siendo la fuente original y pueden abrirse en DataGrip.
4. **Seguridad en formularios:** protección CSRF complementaria para login, logout y ABM de jugadores/equipos, que antes dependían solo de sesión y restricciones de ruta. Se mantienen los tokens ya existentes en los otros módulos.
5. **Interfaz y permisos:** se ocultan enlaces de administración para visitantes y planilleros; instalaciones y sanciones usan ahora el menú compartido.
6. **Auditoría y modelo:** se mantienen 14 tablas de consigna + historial; se eliminaron en el script de creación algunas restricciones UNIQUE redundantes con PK sin modificar el significado lógico.
7. **Documentación:** informe final con justificación de decisiones, alternativas, bitácora cronológica y bibliografía; README de instalación y checklist de pruebas finales.

## Qué NO se puede afirmar sin probar en la Mac

- No se ejecutó aquí un servidor MySQL real ni se hizo una prueba end-to-end de la versión nueva.
- Los módulos agregados/ajustados deben probarse sobre una copia: `/gestion-partidos/`, creación/postergación/reprogramación, `/reportes`, cierre de sesión y roles.
- El historial no agrega retroactivamente modificaciones realizadas antes de crear la tabla; una edición directa desde DataGrip no crea un registro de historial de Flask.
- No se agregaron triggers para garantizar todas las reglas multitabla ante inserciones directas con privilegios administrativos; el backend usa SQL dentro de transacciones para esas reglas.

## Seguridad antes de publicar

- Jamás subir `.env`, respaldos `mysqldump`, contraseñas editadas en SQL ni versiones temporales. Si una contraseña estuvo en GitHub anteriormente, rotarla: eliminar el archivo de la última versión no borra commits anteriores.
- Mantener esta carpeta como una **copia separada** hasta terminar las pruebas; nunca sustituir todo directamente en el repositorio que ya funciona.
