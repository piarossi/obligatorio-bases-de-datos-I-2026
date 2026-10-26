-- Obligatorio BD I - Auditoria de planteles
--
USE torneo_interfacultades;

-- 1. Jugadores registrados en mas de un equipo de la misma edicion.
SELECT 'Jugador en multiples equipos' AS infraccion,
       ejt.ci_jugador AS referencia,
       ejt.id_torneo,
       COUNT(*) AS cantidad
FROM equipo_jugador_torneo ejt
GROUP BY ejt.ci_jugador, ejt.id_torneo
HAVING COUNT(DISTINCT ejt.id_equipo) > 1;

-- 2. Jugadores cuya facultad no coincide con la del equipo.
SELECT 'Facultad incorrecta' AS infraccion,
       j.ci AS referencia,
       e.id_torneo,
       e.id_equipo
FROM equipo_jugador_torneo ejt
JOIN jugador j ON j.ci = ejt.ci_jugador
JOIN equipo e ON e.id_equipo = ejt.id_equipo
             AND e.id_torneo = ejt.id_torneo
WHERE j.id_facultad <> e.id_facultad;

-- 3. Equipos con planteles fuera del rango 5 a 10.
-- El minimo debe exigirse al cerrar inscripciones/programar partidos;
-- durante la inscripcion pueden existir planteles incompletos.
SELECT 'Plantel fuera de rango' AS infraccion,
       e.id_equipo AS referencia,
       e.id_torneo,
       COUNT(ejt.ci_jugador) AS cantidad
FROM equipo e
LEFT JOIN equipo_jugador_torneo ejt
  ON ejt.id_equipo = e.id_equipo AND ejt.id_torneo = e.id_torneo
GROUP BY e.id_equipo, e.id_torneo
HAVING COUNT(ejt.ci_jugador) NOT BETWEEN 5 AND 10;

-- 4. Equipos con mas de 2 docentes/funcionarios.
SELECT 'Exceso de docentes/funcionarios' AS infraccion,
       e.id_equipo AS referencia,
       e.id_torneo,
       SUM(CASE WHEN j.tipo IN ('docente','funcionario') THEN 1 ELSE 0 END) AS cantidad
FROM equipo e
LEFT JOIN equipo_jugador_torneo ejt
  ON ejt.id_equipo = e.id_equipo AND ejt.id_torneo = e.id_torneo
LEFT JOIN jugador j ON j.ci = ejt.ci_jugador
GROUP BY e.id_equipo, e.id_torneo
HAVING SUM(CASE WHEN j.tipo IN ('docente','funcionario') THEN 1 ELSE 0 END) > 2;

-- 5. Capitan que no pertenece al plantel de su equipo (o no designado).
SELECT 'Capitan invalido/no designado' AS infraccion,
       e.id_equipo AS referencia,
       e.id_torneo,
       e.ci_capitan
FROM equipo e
LEFT JOIN equipo_jugador_torneo ejt
  ON ejt.id_equipo = e.id_equipo
 AND ejt.id_torneo = e.id_torneo
 AND ejt.ci_jugador = e.ci_capitan
WHERE e.ci_capitan IS NULL OR ejt.ci_jugador IS NULL;

-- 6. Resumen positivo del estado de los seis equipos.
SELECT e.nombre AS equipo,
       COUNT(ejt.ci_jugador) AS jugadores,
       SUM(CASE WHEN j.tipo IN ('docente','funcionario') THEN 1 ELSE 0 END) AS docentes_funcionarios,
       MAX(CASE WHEN ejt.ci_jugador = e.ci_capitan THEN 1 ELSE 0 END) AS capitan_en_plantel
FROM equipo e
LEFT JOIN equipo_jugador_torneo ejt
  ON ejt.id_equipo = e.id_equipo AND ejt.id_torneo = e.id_torneo
LEFT JOIN jugador j ON j.ci = ejt.ci_jugador
GROUP BY e.id_equipo, e.nombre, e.ci_capitan
ORDER BY e.id_equipo;
