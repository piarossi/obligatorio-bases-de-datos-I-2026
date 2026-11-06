-- CONSULTAS DE AUDITORÍA. No modifican registros.
USE torneo_prueba_bd1;
-- 1. Conteos de tablas maestras y encuentros por estado.
SELECT 'equipo' AS entidad,COUNT(*) cantidad FROM equipo
UNION ALL SELECT 'jugador',COUNT(*) FROM jugador
UNION ALL SELECT 'partido',COUNT(*) FROM partido;
SELECT numero_fecha,estado,COUNT(*) AS partidos FROM partido GROUP BY numero_fecha,estado ORDER BY numero_fecha,estado;
-- 2. Planteles fuera de 5-10 y más de 2 docentes/funcionarios.
SELECT e.id_equipo,e.nombre,COUNT(ejt.ci_jugador) AS plantel,
 SUM(CASE WHEN j.tipo IN ('docente','funcionario') THEN 1 ELSE 0 END) AS personal
FROM equipo e LEFT JOIN equipo_jugador_torneo ejt
ON e.id_equipo=ejt.id_equipo AND e.id_torneo=ejt.id_torneo
LEFT JOIN jugador j ON j.ci=ejt.ci_jugador
WHERE e.activo=1 GROUP BY e.id_equipo,e.nombre
HAVING plantel<5 OR plantel>10 OR personal>2;
-- 3. Planteles con jugadores de facultad incorrecta.
SELECT e.nombre,j.ci FROM equipo_jugador_torneo ejt
JOIN equipo e ON e.id_equipo=ejt.id_equipo AND e.id_torneo=ejt.id_torneo
JOIN jugador j ON j.ci=ejt.ci_jugador
WHERE e.id_facultad<>j.id_facultad;
-- 4. Capitán que no figura en su propio plantel.
SELECT e.id_equipo,e.nombre,e.ci_capitan FROM equipo e
WHERE e.ci_capitan IS NOT NULL AND NOT EXISTS
(SELECT 1 FROM equipo_jugador_torneo ejt WHERE ejt.id_equipo=e.id_equipo AND ejt.id_torneo=e.id_torneo AND ejt.ci_jugador=e.ci_capitan);
-- 5. Canchas ocupadas más de una vez, por día y turno (no cancelados/postergados).
SELECT dia,id_turno,id_complejo,nombre_cancha,COUNT(*) AS cantidad
FROM partido WHERE estado IN ('jugado','programado')
GROUP BY dia,id_turno,id_complejo,nombre_cancha HAVING COUNT(*)>1;
-- 6. Equipos con más de un partido en la misma fecha, excluyendo cancelados.
SELECT p.id_torneo,p.numero_fecha,e.id_equipo,COUNT(*) AS cantidad FROM partido p
JOIN equipo e ON e.id_equipo IN (p.id_equipo_local,p.id_equipo_visitante)
WHERE p.estado<>'cancelado' GROUP BY p.id_torneo,p.numero_fecha,e.id_equipo HAVING COUNT(*)>1;
-- 7. Partidos de un mismo par en misma edición, no cancelados.
SELECT id_torneo, LEAST(id_equipo_local,id_equipo_visitante) e1,
GREATEST(id_equipo_local,id_equipo_visitante) e2,COUNT(*) cantidad
FROM partido WHERE estado<>'cancelado'
GROUP BY id_torneo,e1,e2 HAVING COUNT(*)>1;
-- 8. Jugadores en planilla pero fuera del plantel de ese equipo y torneo.
SELECT pp.id_partido,pp.ci_jugador,pp.id_equipo FROM planilla_partido pp
JOIN partido p ON p.id_partido=pp.id_partido
LEFT JOIN equipo_jugador_torneo ejt ON ejt.id_equipo=pp.id_equipo AND ejt.id_torneo=p.id_torneo AND ejt.ci_jugador=pp.ci_jugador
WHERE ejt.ci_jugador IS NULL OR pp.id_equipo NOT IN (p.id_equipo_local,p.id_equipo_visitante);
-- 9. Jugadores con planilla en fecha sancionada.
SELECT pp.id_partido,pp.ci_jugador,p.numero_fecha,s.id_sancion,s.motivo
FROM planilla_partido pp JOIN partido p ON p.id_partido=pp.id_partido
JOIN sancion_jugador s ON s.ci_jugador=pp.ci_jugador AND s.id_torneo=p.id_torneo
AND p.numero_fecha>=s.numero_fecha_inicio AND p.numero_fecha<s.numero_fecha_inicio+s.cantidad_fechas;
