-- Obligatorio Bases de Datos I - UCU - Segundo semestre 2026
-- Etapa 2: datos maestros ficticios para pruebas.
-- Ejecutar despues de 01_crear_base.sql.
USE torneo_interfacultades;

-- Facultades de ejemplo
INSERT INTO facultad (nombre) VALUES
('Ingenieria y Tecnologias'),
('Derecho'),
('Ciencias Empresariales'),
('Ciencias de la Salud'),
('Ciencias Humanas'),
('Arquitectura y Diseno');

-- Edicion del torneo.
INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado)
VALUES ('Interfacultades Futbol 5 - 2026 S2', 2026, 2, '2026-09-01', '2026-12-15', 'inscripción');

-- Complejos .
INSERT INTO complejo (nombre, direccion, departamento) VALUES
('Complejo Deportivo Norte', 'Calle de Prueba 100', 'Montevideo'),
('Complejo Deportivo Sur', 'Calle de Prueba 200', 'Montevideo');

-- Canchas asociadas a los complejos anteriores.
INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada)
SELECT 'Cancha 1', id_complejo, 'sintético', FALSE FROM complejo WHERE nombre = 'Complejo Deportivo Norte'
UNION ALL
SELECT 'Cancha 2', id_complejo, 'parquet', TRUE FROM complejo WHERE nombre = 'Complejo Deportivo Norte'
UNION ALL
SELECT 'Cancha 1', id_complejo, 'sintético', TRUE FROM complejo WHERE nombre = 'Complejo Deportivo Sur';

-- Turnos de una hora entre las 18:00 y las 23:00.
INSERT INTO turno (hora_inicio, hora_fin) VALUES
('18:00:00', '19:00:00'),
('19:00:00', '20:00:00'),
('20:00:00', '21:00:00'),
('21:00:00', '22:00:00'),
('22:00:00', '23:00:00');

-- Verificaciones
SELECT 'facultad' AS tabla, COUNT(*) AS cantidad FROM facultad
UNION ALL SELECT 'torneo', COUNT(*) FROM torneo
UNION ALL SELECT 'complejo', COUNT(*) FROM complejo
UNION ALL SELECT 'cancha', COUNT(*) FROM cancha
UNION ALL SELECT 'turno', COUNT(*) FROM turno;

SELECT id_turno, hora_inicio, hora_fin FROM turno ORDER BY hora_inicio;
USE torneo_interfacultades;

SELECT 'facultad' AS tabla, COUNT(*) AS cantidad FROM facultad
UNION ALL
SELECT 'torneo', COUNT(*) FROM torneo
UNION ALL
SELECT 'complejo', COUNT(*) FROM complejo
UNION ALL
SELECT 'cancha', COUNT(*) FROM cancha
UNION ALL
SELECT 'turno', COUNT(*) FROM turno;