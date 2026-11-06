-- SOLO PARA UNA BASE NUEVA. No ejecutar sobre la base de trabajo.
-- Datos ficticios: nueve partidos en tres fechas, seis equipos participantes.
USE torneo_interfacultades;
START TRANSACTION;
-- Presupone la carga de 01, 02 y 03 en una base limpia, por lo que equipos tienen IDs 1 a 6.
INSERT INTO partido
(numero_fecha,id_equipo_local,id_equipo_visitante,dia,id_turno,nombre_cancha,id_complejo,estado,id_torneo)
SELECT v.numero_fecha,v.local,v.visitante,v.dia,v.turno,v.cancha,v.complejo,v.estado,t.id_torneo
FROM (
  SELECT 1 AS numero_fecha,1 AS local,6 AS visitante,'2026-10-01' AS dia,1 AS turno,'Cancha 1' AS cancha,1 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 1 AS numero_fecha,2 AS local,5 AS visitante,'2026-10-01' AS dia,2 AS turno,'Cancha 2' AS cancha,1 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 1 AS numero_fecha,3 AS local,4 AS visitante,'2026-10-01' AS dia,1 AS turno,'Cancha 1' AS cancha,2 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 2 AS numero_fecha,1 AS local,5 AS visitante,'2026-10-08' AS dia,1 AS turno,'Cancha 1' AS cancha,1 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 2 AS numero_fecha,6 AS local,4 AS visitante,'2026-10-08' AS dia,2 AS turno,'Cancha 2' AS cancha,1 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 2 AS numero_fecha,2 AS local,3 AS visitante,'2026-10-08' AS dia,1 AS turno,'Cancha 1' AS cancha,2 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 3 AS numero_fecha,1 AS local,4 AS visitante,'2026-10-15' AS dia,1 AS turno,'Cancha 1' AS cancha,1 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 3 AS numero_fecha,5 AS local,3 AS visitante,'2026-10-15' AS dia,2 AS turno,'Cancha 2' AS cancha,1 AS complejo,'jugado' AS estado
  UNION ALL
  SELECT 3 AS numero_fecha,6 AS local,2 AS visitante,'2026-10-15' AS dia,1 AS turno,'Cancha 1' AS cancha,2 AS complejo,'jugado' AS estado
) v
JOIN torneo t ON t.anio=2026 AND t.semestre=2;

-- Para cada partido anotamos un jugador habilitado de cada equipo.
INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo)
SELECT p.id_partido, ejt.ci_jugador,e.id_equipo
FROM partido p
JOIN equipo e ON e.id_equipo IN (p.id_equipo_local,p.id_equipo_visitante)
    AND e.id_torneo=p.id_torneo
JOIN equipo_jugador_torneo ejt ON ejt.id_equipo=e.id_equipo AND ejt.id_torneo=e.id_torneo
   AND ejt.numero_camiseta=1;

-- Un gol normal en cada partido, registrado por un participante local.
INSERT INTO gol (id_partido,ci_jugador,minuto,autogol)
SELECT p.id_partido,pp.ci_jugador,15,0
FROM partido p
JOIN planilla_partido pp ON pp.id_partido=p.id_partido AND pp.id_equipo=p.id_equipo_local;

-- Dos tarjetas de prueba para el reporte fair play, sin generar sanciones.
INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color,origen)
SELECT p.id_partido,pp.ci_jugador,20,'amarilla','manual'
FROM partido p JOIN planilla_partido pp ON pp.id_partido=p.id_partido AND pp.id_equipo=p.id_equipo_visitante
WHERE p.numero_fecha=1 AND p.id_equipo_local IN (1,2);

UPDATE torneo SET estado='en curso' WHERE anio=2026 AND semestre=2;
COMMIT;

SELECT numero_fecha,COUNT(*) AS partidos_jugados FROM partido WHERE estado='jugado' GROUP BY numero_fecha;
