-- Ejecutar con un usuario MySQL administrador SOLO después de crear la tabla.
-- El planillero solamente agrega registros de auditoría; NO modifica ni elimina el historial.
GRANT INSERT ON torneo_interfacultades.historial_estado_partido
TO 'torneo_planillero'@'localhost';
SHOW GRANTS FOR 'torneo_planillero'@'localhost';
