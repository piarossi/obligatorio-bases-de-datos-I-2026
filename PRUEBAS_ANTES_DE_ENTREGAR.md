# Pruebas finales — sin afectar los datos históricos

**Estado:** se validó estáticamente la versión depurada. Hay que correr **estas pruebas de integración en MySQL local** antes de reemplazar definitivamente la versión del repositorio. El modelo exige una cuenta con permisos de administración de MySQL para instalar tablas y permisos.

## Preparación

1. Respaldar base original y carpeta actual. Usar una **copia** de la aplicación y, preferentemente, una base de prueba independiente.
2. Comprobar 15 tablas con `SHOW TABLES;`, incluyendo `historial_estado_partido`.
3. Configurar `.env` para esa base y los dos usuarios MySQL. Crear cuentas del sistema con `python backend/crear_usuario.py`.
4. Abrir Flask y verificar el menú: visitante ve equipos/jugadores/partidos/reportes; administrador ve además instalaciones/sanciones/gestión; planillero no puede acceder a ABM.

## Funciones y evidencias sugeridas

- [ ] Crear un partido nuevo válido entre equipos que no se hayan enfrentado, mientras la edición no esté finalizada.
- [ ] En Gestión de partidos, **Postergar** indicando un motivo. Comprobar un registro en `historial_estado_partido`.
- [ ] **Reprogramar** cambiando día/turno/cancha con otro motivo; verificar estados/programaciones anterior y nueva y `correo_usuario`.
- [ ] **Cancelar** un encuentro de prueba sin planilla, confirmando que queda en la tabla y se registra en historial.
- [ ] Acceder a `/reportes` y consultar al menos posiciones, goleadores y sanciones, contrastando con `sql/05_reportes.sql` en DataGrip.
- [ ] Probar alta y baja lógica de jugador; en la base permanece con `activo=0`.
- [ ] Rechazar un número de camiseta repetido y un segundo equipo para un mismo jugador en una edición.
- [ ] Comprobar máximo dos docentes/funcionarios, plantel entre 5 y 10 al programar, y cambios solo durante inscripción.
- [ ] Bloquear programación de dos partidos en una cancha, día y turno y el mismo equipo en una fecha.
- [ ] Planillero: registrar planilla, gol y tarjeta en un partido elegible que ya terminó; cerrar el partido y revisar la fila de historial `jugado`.
- [ ] Verificar que suspendidos/inactivos no figuren como elegibles, dos amarillas generan roja derivada, tres amarillas suspenden la próxima fecha y el fair play no cuenta doble la expulsión.
- [ ] Intentar ingresar como planillero a `/instalaciones/`, `/sanciones/` y `/gestion-partidos/`: debe responder 403.
- [ ] Ejecutar `sql/07_auditoria_integridad.sql`: las consultas de inconsistencias deberían devolver cero registros, salvo que los datos de prueba busquen deliberadamente una violación.

## Comandos de consulta del historial

```sql
SELECT id_historial, id_partido, accion, estado_anterior,
       estado_nuevo, dia_anterior, dia_nuevo,
       correo_usuario, motivo, fecha_cambio
FROM historial_estado_partido
ORDER BY id_historial DESC;
```

## Precauciones

- No volver a ejecutar `01_esquema.sql` ni los `INSERT` de datos demo en la base original.
- No usar el usuario `root` en `.env` de Flask.
- No copiar el `.env` ni hashes reales a GitHub; rotar contraseñas que se hubieran publicado en commits antiguos.
- Esta lista no reemplaza un ensayo de recuperación de backup o una revisión de concurrencia con varias sesiones.
