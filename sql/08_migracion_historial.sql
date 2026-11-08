USE torneo_prueba_bd1;

CREATE TABLE IF NOT EXISTS historial_estado_partido (
  id_historial INT AUTO_INCREMENT PRIMARY KEY,
  id_partido INT NOT NULL,
  accion ENUM('creado','postergado','cancelado','reprogramado','jugado') NOT NULL,
  estado_anterior ENUM('programado','jugado','postergado','cancelado') NULL,
  estado_nuevo ENUM('programado','jugado','postergado','cancelado') NOT NULL,
  dia_anterior DATE NULL,
  dia_nuevo DATE NOT NULL,
  turno_anterior INT NULL,
  turno_nuevo INT NOT NULL,
  complejo_anterior INT NULL,
  complejo_nuevo INT NOT NULL,
  cancha_anterior VARCHAR(80) NULL,
  cancha_nueva VARCHAR(80) NOT NULL,
  correo_usuario VARCHAR(150) NULL,
  motivo VARCHAR(255) NULL,
  fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_historial_partido FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
  INDEX idx_historial_partido_fecha (id_partido, fecha_cambio)
) ENGINE=InnoDB;

-- Verificación de tabla (0 filas antes de registrar cambios nuevos es normal):
SELECT COUNT(*) AS cambios_registrados FROM historial_estado_partido;
