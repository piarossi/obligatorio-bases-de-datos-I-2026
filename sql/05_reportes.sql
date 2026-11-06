-- OBLIGATORIO BASES DE DATOS I - REPORTES
-- Archivo acumulativo: 9 reportes obligatorios + 3 adicionales + 1 auxiliar.
-- Consultas SELECT exclusivamente: NO crean tablas ni modifican datos.
-- Edición analizada: 2026, semestre 2. MySQL 8+.
-- El primer reporte es una consulta histórica de tarjetas por jugador.
-- ATENCION: amarillas históricas NO es el contador vigente para suspensiones.
-- Ejecutar consultas SELECT en DataGrip. No modifica datos.

USE torneo_interfacultades;

-- REPORTE AUXILIAR 01: Historial de tarjetas por jugador.
-- INNER JOIN relaciona jugador con tarjeta por ci.
-- SUM(CASE ...) distingue amarillas, rojas directas y expulsiones
-- por doble amarilla. Una expulsión por doble amarilla conserva
-- las dos tarjetas amarillas históricas.
SELECT
    j.ci,
    j.nombre,
    j.apellido,
    SUM(CASE WHEN t.color = 'amarilla' THEN 1 ELSE 0 END)
        AS amarillas,
    SUM(CASE WHEN t.color = 'roja'
              AND t.origen = 'manual' THEN 1 ELSE 0 END)
        AS rojas_directas,
    SUM(CASE WHEN t.color = 'roja'
              AND t.origen = 'doble_amarilla' THEN 1 ELSE 0 END)
        AS expulsiones_doble_amarilla
FROM jugador j
INNER JOIN tarjeta t
    ON j.ci = t.ci_jugador
GROUP BY
    j.ci,
    j.nombre,
    j.apellido
ORDER BY amarillas DESC, j.apellido;

-- REPORTE OBLIGATORIO 01: Tabla de posiciones (edición 2026, semestre 2).
-- Se consideran SOLO partidos con estado = 'jugado'.
-- Los goles en contra (autogoles) suman para el equipo contrario.
-- Se muestran también equipos sin partidos jugados, con estadísticas en cero.
-- Desempate: puntos, diferencia de goles y goles a favor.
-- Requiere MySQL 8 o posterior (CTE con WITH).

WITH marcadores AS (
    SELECT
        p.id_partido,
        p.id_torneo,
        p.id_equipo_local,
        p.id_equipo_visitante,
        SUM(CASE
            WHEN (pp.id_equipo = p.id_equipo_local AND g.autogol = 0)
              OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol = 1)
            THEN 1 ELSE 0 END) AS goles_local,
        SUM(CASE
            WHEN (pp.id_equipo = p.id_equipo_visitante AND g.autogol = 0)
              OR (pp.id_equipo = p.id_equipo_local AND g.autogol = 1)
            THEN 1 ELSE 0 END) AS goles_visitante
    FROM partido p
    LEFT JOIN gol g ON g.id_partido = p.id_partido
    LEFT JOIN planilla_partido pp
        ON pp.id_partido = g.id_partido
       AND pp.ci_jugador = g.ci_jugador
    WHERE p.estado = 'jugado'
    GROUP BY p.id_partido, p.id_torneo,
             p.id_equipo_local, p.id_equipo_visitante
),
actuaciones AS (
    SELECT id_torneo, id_equipo_local AS id_equipo,
           goles_local AS goles_favor,
           goles_visitante AS goles_contra
    FROM marcadores
    UNION ALL
    SELECT id_torneo, id_equipo_visitante AS id_equipo,
           goles_visitante AS goles_favor,
           goles_local AS goles_contra
    FROM marcadores
)
SELECT
    e.nombre AS equipo,
    COUNT(a.id_equipo) AS partidos_jugados,
    SUM(CASE WHEN a.goles_favor > a.goles_contra THEN 1 ELSE 0 END) AS ganados,
    SUM(CASE WHEN a.goles_favor = a.goles_contra THEN 1 ELSE 0 END) AS empatados,
    SUM(CASE WHEN a.goles_favor < a.goles_contra THEN 1 ELSE 0 END) AS perdidos,
    COALESCE(SUM(a.goles_favor), 0) AS goles_favor,
    COALESCE(SUM(a.goles_contra), 0) AS goles_contra,
    COALESCE(SUM(a.goles_favor - a.goles_contra), 0) AS diferencia_goles,
    3 * SUM(CASE WHEN a.goles_favor > a.goles_contra THEN 1 ELSE 0 END)
      + SUM(CASE WHEN a.goles_favor = a.goles_contra THEN 1 ELSE 0 END)
        AS puntos
FROM equipo e
JOIN torneo t ON t.id_torneo = e.id_torneo
LEFT JOIN actuaciones a
    ON a.id_equipo = e.id_equipo
   AND a.id_torneo = e.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
GROUP BY e.id_equipo, e.nombre
ORDER BY puntos DESC, diferencia_goles DESC, goles_favor DESC, e.nombre;



-- ================================================================
-- REPORTE OBLIGATORIO 02: Diez máximos goleadores de la edición.
-- Un autogol favorece al rival, pero NO suma al autor como goleador.
-- Solo se cuentan partidos jugados, nunca partidos aún programados.
-- ================================================================
SELECT
    j.ci,
    j.nombre,
    j.apellido,
    COUNT(*) AS goles
FROM gol g
JOIN jugador j ON j.ci = g.ci_jugador
JOIN partido p ON p.id_partido = g.id_partido
JOIN torneo t ON t.id_torneo = p.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
  AND p.estado = 'jugado'
  AND g.autogol = 0
GROUP BY j.ci, j.nombre, j.apellido
ORDER BY goles DESC, j.apellido, j.nombre
LIMIT 10;


-- ================================================================
-- REPORTE OBLIGATORIO 03: Fair play por equipo.
-- La letra indica amarilla=1 punto, roja=3 puntos; menor es mejor.
-- DECISIÓN ADOPTADA para evitar contar doble una expulsión:
--   doble amarilla -> 3 puntos por expulsión (no 2+3).
--   roja directa -> 3 puntos, y otra amarilla previa independiente
--                   en ese partido suma 1 si corresponde.
-- Las dos amarillas de la doble amarilla SIGUEN conservadas y
-- contando como DOS para la acumulación disciplinaria, que es OTRO
-- cálculo distinto del fair play. Solo partidos jugados.
-- ================================================================
WITH tarjetas_fairplay AS (
    SELECT
        p.id_torneo,
        pp.id_equipo,
        ta.id_partido,
        ta.ci_jugador,
        ta.color,
        ta.origen,
        CASE
            WHEN ta.color = 'roja' THEN 3
            WHEN ta.color = 'amarilla' AND EXISTS (
                SELECT 1 FROM tarjeta expuls
                WHERE expuls.id_partido = ta.id_partido
                  AND expuls.ci_jugador = ta.ci_jugador
                  AND expuls.color = 'roja'
                  AND expuls.origen = 'doble_amarilla'
            ) THEN 0
            WHEN ta.color = 'amarilla' THEN 1
            ELSE 0
        END AS puntos_tarjeta
    FROM tarjeta ta
    JOIN partido p ON p.id_partido = ta.id_partido
    JOIN planilla_partido pp
      ON pp.id_partido = ta.id_partido
     AND pp.ci_jugador = ta.ci_jugador
    WHERE p.estado = 'jugado'
)
SELECT
    e.nombre AS equipo,
    COALESCE(SUM(tf.puntos_tarjeta), 0) AS puntos_fair_play
FROM equipo e
JOIN torneo t ON t.id_torneo = e.id_torneo
LEFT JOIN tarjetas_fairplay tf
  ON tf.id_equipo = e.id_equipo AND tf.id_torneo = e.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
GROUP BY e.id_equipo, e.nombre
ORDER BY puntos_fair_play ASC, e.nombre;


-- ================================================================
-- REPORTE OBLIGATORIO 04: Promedio de goles por fecha y edición.
-- Un autogol también es un gol del partido; se cuenta UNA vez.
-- UNION ALL agrega la fila global 'Toda la edición'.
-- Fechas sin partidos jugados no intervienen en promedios.
-- ================================================================
WITH goles_partido AS (
    SELECT p.id_partido, p.id_torneo, p.numero_fecha,
           COUNT(g.id_gol) AS cantidad_goles
    FROM partido p
    LEFT JOIN gol g ON g.id_partido = p.id_partido
    JOIN torneo t ON t.id_torneo = p.id_torneo
    WHERE t.anio = 2026 AND t.semestre = 2 AND p.estado = 'jugado'
    GROUP BY p.id_partido, p.id_torneo, p.numero_fecha
)
SELECT CONCAT('Fecha ', numero_fecha) AS periodo,
       COUNT(*) AS partidos_jugados,
       SUM(cantidad_goles) AS goles_totales,
       ROUND(AVG(cantidad_goles), 2) AS promedio_goles
FROM goles_partido
GROUP BY numero_fecha
UNION ALL
SELECT 'Toda la edición' AS periodo,
       COUNT(*) AS partidos_jugados,
       COALESCE(SUM(cantidad_goles), 0) AS goles_totales,
       COALESCE(ROUND(AVG(cantidad_goles), 2), 0) AS promedio_goles
FROM goles_partido;


-- ================================================================
-- REPORTE OBLIGATORIO 05 A: Canchas más utilizadas.
-- Definimos 'uso' como partidos efectivamente jugados.
-- La clave de una cancha es (id_complejo, nombre_cancha),
-- no solamente el nombre de la cancha.
-- ================================================================
SELECT
    c.nombre AS complejo,
    ca.nombre_cancha AS cancha,
    COUNT(p.id_partido) AS partidos_jugados
FROM cancha ca
JOIN complejo c ON c.id_complejo = ca.id_complejo
LEFT JOIN partido p
  ON p.id_complejo = ca.id_complejo
 AND p.nombre_cancha = ca.nombre_cancha
 AND p.estado = 'jugado'
 AND p.id_torneo IN (
     SELECT id_torneo FROM torneo WHERE anio = 2026 AND semestre = 2
 )
GROUP BY ca.id_complejo, ca.nombre_cancha, c.nombre
ORDER BY partidos_jugados DESC, c.nombre, ca.nombre_cancha;


-- ================================================================
-- REPORTE OBLIGATORIO 05 B: Turnos más utilizados.
-- Uso = partidos jugados en ese turno.
-- ================================================================
SELECT
    tu.hora_inicio,
    tu.hora_fin,
    COUNT(p.id_partido) AS partidos_jugados
FROM turno tu
LEFT JOIN partido p
  ON p.id_turno = tu.id_turno
 AND p.estado = 'jugado'
 AND p.id_torneo IN (
     SELECT id_torneo FROM torneo WHERE anio = 2026 AND semestre = 2
 )
GROUP BY tu.id_turno, tu.hora_inicio, tu.hora_fin
ORDER BY partidos_jugados DESC, tu.hora_inicio;


-- ================================================================
-- REPORTE OBLIGATORIO 06: Jugadores inscriptos por facultad y tipo.
-- Contamos INSCRIPCIONES en los planteles de esta edición,
-- no todos los jugadores existentes en la tabla jugador.
-- ================================================================
SELECT
    f.nombre AS facultad,
    j.tipo,
    COUNT(DISTINCT ejt.ci_jugador) AS cantidad_jugadores
FROM equipo_jugador_torneo ejt
JOIN equipo e ON e.id_equipo = ejt.id_equipo
             AND e.id_torneo = ejt.id_torneo
JOIN jugador j ON j.ci = ejt.ci_jugador
JOIN facultad f ON f.id_facultad = e.id_facultad
JOIN torneo t ON t.id_torneo = ejt.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
GROUP BY f.id_facultad, f.nombre, j.tipo
ORDER BY f.nombre, j.tipo;


-- ================================================================
-- REPORTE OBLIGATORIO 07: Inscriptos que nunca estuvieron en planilla.
-- NOT EXISTS evita que otra edición o un partido de otro equipo
-- haga desaparecer incorrectamente a un jugador del listado.
-- ================================================================
SELECT
    e.nombre AS equipo,
    j.ci,
    j.nombre,
    j.apellido,
    ejt.numero_camiseta
FROM equipo_jugador_torneo ejt
JOIN equipo e ON e.id_equipo = ejt.id_equipo
             AND e.id_torneo = ejt.id_torneo
JOIN jugador j ON j.ci = ejt.ci_jugador
JOIN torneo t ON t.id_torneo = ejt.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
  AND NOT EXISTS (
      SELECT 1
      FROM planilla_partido pp
      JOIN partido p ON p.id_partido = pp.id_partido
      WHERE pp.ci_jugador = ejt.ci_jugador
        AND pp.id_equipo = ejt.id_equipo
        AND p.id_torneo = ejt.id_torneo
  )
ORDER BY e.nombre, ejt.numero_camiseta, j.apellido;


-- ================================================================
-- REPORTE OBLIGATORIO 08: Sanciones por equipo y motivo.
-- Las sanciones se vinculan al equipo de ese jugador EN ESA EDICIÓN.
-- Incluye equipos sin sanciones, con cero por cada motivo.
-- ================================================================
WITH motivos AS (
    SELECT 'roja' AS motivo
    UNION ALL SELECT 'acumulación de amarillas'
    UNION ALL SELECT 'disciplinaria'
)
SELECT
    e.nombre AS equipo,
    m.motivo,
    COUNT(s.id_sancion) AS cantidad_sanciones
FROM equipo e
JOIN torneo t ON t.id_torneo = e.id_torneo
CROSS JOIN motivos m
LEFT JOIN equipo_jugador_torneo ejt
  ON ejt.id_equipo = e.id_equipo AND ejt.id_torneo = e.id_torneo
LEFT JOIN sancion_jugador s
  ON s.ci_jugador = ejt.ci_jugador
 AND s.id_torneo = e.id_torneo
 AND s.motivo = m.motivo
WHERE t.anio = 2026 AND t.semestre = 2
GROUP BY e.id_equipo, e.nombre, m.motivo
ORDER BY e.nombre, m.motivo;


-- ================================================================
-- REPORTE OBLIGATORIO 09: Porcentaje de partidos por estado.
-- El porcentaje se calcula sobre TODOS los partidos registrados
-- de la edición, incluyendo los todavía programados.
-- ================================================================
SELECT
    p.estado,
    COUNT(*) AS cantidad_partidos,
    ROUND(100 * COUNT(*) / (
       SELECT COUNT(*)
       FROM partido p2
       JOIN torneo t2 ON t2.id_torneo = p2.id_torneo
       WHERE t2.anio = 2026 AND t2.semestre = 2
    ), 2) AS porcentaje
FROM partido p
JOIN torneo t ON t.id_torneo = p.id_torneo
WHERE t.anio = 2026 AND t.semestre = 2
GROUP BY p.estado
ORDER BY CASE p.estado
    WHEN 'jugado' THEN 1
    WHEN 'postergado' THEN 2
    WHEN 'cancelado' THEN 3
    ELSE 4 END;


-- ================================================================
-- CONSULTA ADICIONAL 01: Participaciones por jugador.
-- Jugadores que aparecen más veces en planillas de partidos jugados.
-- ================================================================
SELECT
    j.ci, j.nombre, j.apellido,
    e.nombre AS equipo,
    COUNT(*) AS partidos_participados
FROM planilla_partido pp
JOIN partido p ON p.id_partido = pp.id_partido
JOIN torneo t ON t.id_torneo = p.id_torneo
JOIN jugador j ON j.ci = pp.ci_jugador
JOIN equipo e ON e.id_equipo = pp.id_equipo
WHERE t.anio = 2026 AND t.semestre = 2
  AND p.estado = 'jugado'
GROUP BY j.ci, j.nombre, j.apellido, e.id_equipo, e.nombre
ORDER BY partidos_participados DESC, j.apellido;


-- ================================================================
-- CONSULTA ADICIONAL 02: Equipos con partidos sin recibir goles.
-- 'Valla invicta' = partido jugado con goles en contra igual a 0.
-- Incluye equipos con cero vallas invictas.
-- ================================================================
WITH marcador AS (
    SELECT p.id_partido, p.id_equipo_local, p.id_equipo_visitante,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_local AND g.autogol = 0)
                        OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol = 1)
                    THEN 1 ELSE 0 END) AS goles_local,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_visitante AND g.autogol = 0)
                        OR (pp.id_equipo = p.id_equipo_local AND g.autogol = 1)
                    THEN 1 ELSE 0 END) AS goles_visitante
    FROM partido p
    JOIN torneo t ON t.id_torneo = p.id_torneo
    LEFT JOIN gol g ON g.id_partido = p.id_partido
    LEFT JOIN planilla_partido pp
      ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
    WHERE t.anio = 2026 AND t.semestre = 2 AND p.estado = 'jugado'
    GROUP BY p.id_partido, p.id_equipo_local, p.id_equipo_visitante
), vallas AS (
    SELECT id_equipo_local AS id_equipo, goles_visitante AS goles_recibidos FROM marcador
    UNION ALL
    SELECT id_equipo_visitante, goles_local FROM marcador
)
SELECT e.nombre AS equipo,
       SUM(CASE WHEN v.goles_recibidos = 0 THEN 1 ELSE 0 END)
           AS partidos_valla_invicta
FROM equipo e
JOIN torneo t ON t.id_torneo = e.id_torneo
LEFT JOIN vallas v ON v.id_equipo = e.id_equipo
WHERE t.anio = 2026 AND t.semestre = 2
GROUP BY e.id_equipo, e.nombre
ORDER BY partidos_valla_invicta DESC, e.nombre;


-- ================================================================
-- CONSULTA ADICIONAL 03: Máximo goleador por equipo.
-- Empates en el máximo se muestran todos (no se elige uno al azar).
-- Solo goles normales en partidos jugados; no autogoles.
-- ================================================================
WITH goles_jugador AS (
    SELECT pp.id_equipo, j.ci, j.nombre, j.apellido,
           COUNT(*) AS goles
    FROM gol g
    JOIN partido p ON p.id_partido = g.id_partido
    JOIN torneo t ON t.id_torneo = p.id_torneo
    JOIN planilla_partido pp
      ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
    JOIN jugador j ON j.ci = g.ci_jugador
    WHERE t.anio = 2026 AND t.semestre = 2
      AND p.estado = 'jugado' AND g.autogol = 0
    GROUP BY pp.id_equipo, j.ci, j.nombre, j.apellido
)
SELECT e.nombre AS equipo, gj.ci, gj.nombre, gj.apellido, gj.goles
FROM goles_jugador gj
JOIN equipo e ON e.id_equipo = gj.id_equipo
WHERE gj.goles = (
    SELECT MAX(gj2.goles)
    FROM goles_jugador gj2
    WHERE gj2.id_equipo = gj.id_equipo
)
ORDER BY e.nombre, gj.apellido;
