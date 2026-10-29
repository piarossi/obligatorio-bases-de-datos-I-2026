USE torneo_interfacultades;

SELECT id_torneo, nombre, estado
FROM torneo;

UPDATE torneo
SET estado = 'en curso'
WHERE anio = 2026
  AND semestre = 2
  AND estado = 'inscripción';

UPDATE torneo
SET estado = 'inscripción'
WHERE anio = 2026
  AND semestre = 2
  AND estado = 'en curso';