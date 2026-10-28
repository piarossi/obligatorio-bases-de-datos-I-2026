-- Ejecutar UNA sola vez sobre la base existente. No borra ni modifica registros anteriores.
USE torneo_interfacultades;
ALTER TABLE jugador
  ADD COLUMN activo BOOLEAN NOT NULL DEFAULT TRUE;

-- Debe devolver 45 jugadores activos y 0 inactivos antes de probar el ABM.
SELECT COUNT(*) AS total,
       SUM(activo = TRUE) AS activos,
       SUM(activo = FALSE) AS inactivos
FROM jugador;

-- Confirma que el campo quedó creado.
SHOW COLUMNS FROM jugador LIKE 'activo';
