-- Obligatorio BD I - Etapa 3: equipos, jugadores y planteles.
USE torneo_interfacultades;
START TRANSACTION;

-- Equipos: uno por facultad, asociados a la edicion 2026 S2.
INSERT INTO equipo (nombre, id_torneo, id_facultad, ci_capitan)
SELECT CONCAT('Equipo ' , f.nombre), t.id_torneo, f.id_facultad, NULL
FROM facultad f
CROSS JOIN torneo t
WHERE t.anio = 2026 AND t.semestre = 2
  AND t.estado = 'inscripción';

-- Planteles variados: 5, 7, 6, 9, 8 y 10 jugadores por facultad.
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('PRUEBA0101', 'Jugador1', 'Facultad1', 'jugador0101@example.com', '2001-04-15', 1, 'grado'),
('PRUEBA0102', 'Jugador2', 'Facultad1', 'jugador0102@example.com', '2001-04-15', 1, 'grado'),
('PRUEBA0103', 'Jugador3', 'Facultad1', 'jugador0103@example.com', '2001-04-15', 1, 'grado'),
('PRUEBA0104', 'Jugador4', 'Facultad1', 'jugador0104@example.com', '2001-04-15', 1, 'grado'),
('PRUEBA0105', 'Jugador5', 'Facultad1', 'jugador0105@example.com', '2001-04-15', 1, 'posgrado'),
('PRUEBA0201', 'Jugador1', 'Facultad2', 'jugador0201@example.com', '2001-04-15', 2, 'grado'),
('PRUEBA0202', 'Jugador2', 'Facultad2', 'jugador0202@example.com', '2001-04-15', 2, 'grado'),
('PRUEBA0203', 'Jugador3', 'Facultad2', 'jugador0203@example.com', '2001-04-15', 2, 'grado'),
('PRUEBA0204', 'Jugador4', 'Facultad2', 'jugador0204@example.com', '2001-04-15', 2, 'grado'),
('PRUEBA0205', 'Jugador5', 'Facultad2', 'jugador0205@example.com', '2001-04-15', 2, 'posgrado'),
('PRUEBA0206', 'Jugador6', 'Facultad2', 'jugador0206@example.com', '2001-04-15', 2, 'funcionario'),
('PRUEBA0207', 'Jugador7', 'Facultad2', 'jugador0207@example.com', '2000-06-12', 2, 'grado'),
('PRUEBA0301', 'Jugador1', 'Facultad3', 'jugador0301@example.com', '2001-04-15', 3, 'grado'),
('PRUEBA0302', 'Jugador2', 'Facultad3', 'jugador0302@example.com', '2001-04-15', 3, 'grado'),
('PRUEBA0303', 'Jugador3', 'Facultad3', 'jugador0303@example.com', '2001-04-15', 3, 'grado'),
('PRUEBA0304', 'Jugador4', 'Facultad3', 'jugador0304@example.com', '2001-04-15', 3, 'grado'),
('PRUEBA0305', 'Jugador5', 'Facultad3', 'jugador0305@example.com', '2001-04-15', 3, 'posgrado'),
('PRUEBA0306', 'Jugador6', 'Facultad3', 'jugador0306@example.com', '2001-04-15', 3, 'docente'),
('PRUEBA0401', 'Jugador1', 'Facultad4', 'jugador0401@example.com', '2001-04-15', 4, 'grado'),
('PRUEBA0402', 'Jugador2', 'Facultad4', 'jugador0402@example.com', '2001-04-15', 4, 'grado'),
('PRUEBA0403', 'Jugador3', 'Facultad4', 'jugador0403@example.com', '2001-04-15', 4, 'grado'),
('PRUEBA0404', 'Jugador4', 'Facultad4', 'jugador0404@example.com', '2001-04-15', 4, 'grado'),
('PRUEBA0405', 'Jugador5', 'Facultad4', 'jugador0405@example.com', '2001-04-15', 4, 'posgrado'),
('PRUEBA0406', 'Jugador6', 'Facultad4', 'jugador0406@example.com', '2001-04-15', 4, 'funcionario'),
('PRUEBA0407', 'Jugador7', 'Facultad4', 'jugador0407@example.com', '2000-06-12', 4, 'grado'),
('PRUEBA0408', 'Jugador8', 'Facultad4', 'jugador0408@example.com', '2000-06-12', 4, 'grado'),
('PRUEBA0409', 'Jugador9', 'Facultad4', 'jugador0409@example.com', '2000-06-12', 4, 'docente'),
('PRUEBA0501', 'Jugador1', 'Facultad5', 'jugador0501@example.com', '2001-04-15', 5, 'grado'),
('PRUEBA0502', 'Jugador2', 'Facultad5', 'jugador0502@example.com', '2001-04-15', 5, 'grado'),
('PRUEBA0503', 'Jugador3', 'Facultad5', 'jugador0503@example.com', '2001-04-15', 5, 'grado'),
('PRUEBA0504', 'Jugador4', 'Facultad5', 'jugador0504@example.com', '2001-04-15', 5, 'grado'),
('PRUEBA0505', 'Jugador5', 'Facultad5', 'jugador0505@example.com', '2001-04-15', 5, 'posgrado'),
('PRUEBA0506', 'Jugador6', 'Facultad5', 'jugador0506@example.com', '2001-04-15', 5, 'docente'),
('PRUEBA0507', 'Jugador7', 'Facultad5', 'jugador0507@example.com', '2000-06-12', 5, 'grado'),
('PRUEBA0508', 'Jugador8', 'Facultad5', 'jugador0508@example.com', '2000-06-12', 5, 'grado'),
('PRUEBA0601', 'Jugador1', 'Facultad6', 'jugador0601@example.com', '2001-04-15', 6, 'grado'),
('PRUEBA0602', 'Jugador2', 'Facultad6', 'jugador0602@example.com', '2001-04-15', 6, 'grado'),
('PRUEBA0603', 'Jugador3', 'Facultad6', 'jugador0603@example.com', '2001-04-15', 6, 'grado'),
('PRUEBA0604', 'Jugador4', 'Facultad6', 'jugador0604@example.com', '2001-04-15', 6, 'grado'),
('PRUEBA0605', 'Jugador5', 'Facultad6', 'jugador0605@example.com', '2001-04-15', 6, 'posgrado'),
('PRUEBA0606', 'Jugador6', 'Facultad6', 'jugador0606@example.com', '2001-04-15', 6, 'funcionario'),
('PRUEBA0607', 'Jugador7', 'Facultad6', 'jugador0607@example.com', '2000-06-12', 6, 'grado'),
('PRUEBA0608', 'Jugador8', 'Facultad6', 'jugador0608@example.com', '2000-06-12', 6, 'grado'),
('PRUEBA0609', 'Jugador9', 'Facultad6', 'jugador0609@example.com', '2000-06-12', 6, 'posgrado'),
('PRUEBA0610', 'Jugador10', 'Facultad6', 'jugador0610@example.com', '2000-06-12', 6, 'docente');

-- Relacionar jugadores con el equipo de su facultad y la misma edicion.
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta)
SELECT e.id_equipo, j.ci, e.id_torneo, CAST(RIGHT(j.ci,2) AS UNSIGNED)
FROM jugador j
JOIN equipo e ON e.id_facultad = j.id_facultad
JOIN torneo t ON t.id_torneo = e.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
  AND t.estado = 'inscripción'
  AND j.ci LIKE 'PRUEBA%';

-- Designar capitan: jugador con camiseta 1 del propio plantel.
UPDATE equipo e
JOIN equipo_jugador_torneo ejt ON ejt.id_equipo=e.id_equipo
  AND ejt.id_torneo=e.id_torneo AND ejt.numero_camiseta=1
JOIN torneo t ON t.id_torneo=e.id_torneo
SET e.ci_capitan=ejt.ci_jugador
WHERE t.anio=2026 AND t.semestre=2 AND t.estado='inscripción';

COMMIT;

-- Verificaciones: planteles variados entre 5 y 10, maximo 2 docentes/funcionarios, capitan valido.
SELECT e.id_equipo, e.nombre, COUNT(ejt.ci_jugador) AS jugadores,
 SUM(j.tipo IN ('docente','funcionario')) AS docentes_funcionarios,
 e.ci_capitan,
 MAX(ejt.ci_jugador=e.ci_capitan) AS capitan_en_plantel
FROM equipo e
JOIN torneo t ON t.id_torneo=e.id_torneo
LEFT JOIN equipo_jugador_torneo ejt ON ejt.id_equipo=e.id_equipo AND ejt.id_torneo=e.id_torneo
LEFT JOIN jugador j ON j.ci=ejt.ci_jugador
WHERE t.anio=2026 AND t.semestre=2
GROUP BY e.id_equipo,e.nombre,e.ci_capitan
ORDER BY e.id_equipo;

-- Deben devolver cero filas (infracciones en los datos cargados).
SELECT ejt.ci_jugador, ejt.id_torneo, COUNT(*) AS equipos
FROM equipo_jugador_torneo ejt
GROUP BY ejt.ci_jugador,ejt.id_torneo HAVING COUNT(*)>1;

SELECT e.nombre, j.ci, j.id_facultad AS facultad_jugador, e.id_facultad AS facultad_equipo
FROM equipo_jugador_torneo ejt
JOIN equipo e ON e.id_equipo=ejt.id_equipo AND e.id_torneo=ejt.id_torneo
JOIN jugador j ON j.ci=ejt.ci_jugador
WHERE j.id_facultad<>e.id_facultad;
USE torneo_interfacultades;

SELECT
    e.nombre AS equipo,
    COUNT(ejt.ci_jugador) AS jugadores,
    SUM(j.tipo IN ('docente', 'funcionario')) AS docentes_funcionarios,
    SUM(e.ci_capitan = ejt.ci_jugador) AS capitan_en_plantel
FROM equipo e
JOIN equipo_jugador_torneo ejt
    ON e.id_equipo = ejt.id_equipo
JOIN jugador j
    ON j.ci = ejt.ci_jugador
GROUP BY e.id_equipo, e.nombre, e.ci_capitan
ORDER BY e.id_equipo;