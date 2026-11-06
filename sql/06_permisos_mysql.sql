-- EJECUTAR DESDE DATAGRIP CON UN USUARIO MYSQL ADMINISTRADOR.
-- 1) Sustituir CAMBIAR_POR_CLAVE_LARGA_UNICA por una clave propia,
--    que coincida con DB_PLANILLERO_PASSWORD en .env.
-- 2) Este SQL NO cambia ninguna tabla ni los datos de partidos.
-- 3) El planillero solo puede leer la base, registrar/corregir
--    planillas, goles, tarjetas, y actualizar estado del partido
--    cuando se cierra el encuentro. Las sanciones automáticas
--    requieren escritura en sancion_jugador.
-- IMPORTANTE: la autorización a nivel aplicación sigue siendo necesaria.

CREATE USER IF NOT EXISTS 'torneo_planillero'@'localhost'
IDENTIFIED BY 'REEMPLAZAR_CON_CLAVE_LARGA_UNICA';

-- Si la cuenta ya existía, este ALTER establece la clave elegida.
ALTER USER 'torneo_planillero'@'localhost'
IDENTIFIED BY 'REEMPLAZAR_CON_CLAVE_LARGA_UNICA';

REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'torneo_planillero'@'localhost';
GRANT SELECT ON torneo_interfacultades.* TO 'torneo_planillero'@'localhost';
GRANT INSERT, DELETE ON torneo_interfacultades.planilla_partido TO 'torneo_planillero'@'localhost';
GRANT INSERT, DELETE ON torneo_interfacultades.gol TO 'torneo_planillero'@'localhost';
GRANT INSERT, DELETE ON torneo_interfacultades.tarjeta TO 'torneo_planillero'@'localhost';
GRANT UPDATE (estado) ON torneo_interfacultades.partido TO 'torneo_planillero'@'localhost';
GRANT INSERT, DELETE ON torneo_interfacultades.sancion_jugador TO 'torneo_planillero'@'localhost';

SHOW GRANTS FOR 'torneo_planillero'@'localhost';
