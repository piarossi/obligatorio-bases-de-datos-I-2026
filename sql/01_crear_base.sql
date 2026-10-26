-- Obligatorio Bases de Datos I - UCU - Segundo semestre 2026
-- Etapa 1: estructura de datos. Ejecutar en una base nueva.
CREATE DATABASE IF NOT EXISTS torneo_interfacultades
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE torneo_interfacultades;

CREATE TABLE login (
  correo VARCHAR(150) PRIMARY KEY,
  contrasena VARCHAR(255) NOT NULL, -- almacenar hash, nunca contrasena en texto plano
  rol ENUM('administrador','planillero') NOT NULL
);

CREATE TABLE facultad (
  id_facultad INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE jugador (
  ci VARCHAR(20) PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  apellido VARCHAR(80) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  fecha_nacimiento DATE NOT NULL,
  id_facultad INT NOT NULL,
  tipo ENUM('grado','posgrado','docente','funcionario') NOT NULL,
  CONSTRAINT fk_jugador_facultad FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad)
);

CREATE TABLE torneo (
  id_torneo INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  anio SMALLINT NOT NULL,
  semestre TINYINT NOT NULL,
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NOT NULL,
  estado ENUM('inscripción','en curso','finalizado') NOT NULL DEFAULT 'inscripción',
  CONSTRAINT chk_torneo_semestre CHECK (semestre IN (1,2)),
  CONSTRAINT chk_torneo_fechas CHECK (fecha_fin >= fecha_inicio),
  CONSTRAINT uq_torneo_edicion UNIQUE (anio,semestre)
);

CREATE TABLE equipo (
  id_equipo INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  id_torneo INT NOT NULL,
  id_facultad INT NOT NULL,
  ci_capitan VARCHAR(20) NULL,
  CONSTRAINT fk_equipo_torneo FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
  CONSTRAINT fk_equipo_facultad FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad),
  CONSTRAINT fk_equipo_capitan FOREIGN KEY (ci_capitan) REFERENCES jugador(ci),
  CONSTRAINT uq_equipo_nombre UNIQUE (id_torneo,nombre),
  CONSTRAINT uq_equipo_torneo UNIQUE (id_equipo,id_torneo)
);

CREATE TABLE equipo_jugador_torneo (
  id_equipo INT NOT NULL,
  ci_jugador VARCHAR(20) NOT NULL,
  id_torneo INT NOT NULL,
  numero_camiseta TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (id_equipo,ci_jugador,id_torneo),
  CONSTRAINT fk_plantel_equipo_edicion FOREIGN KEY (id_equipo,id_torneo)
    REFERENCES equipo(id_equipo,id_torneo),
  CONSTRAINT fk_plantel_jugador FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
  CONSTRAINT fk_plantel_torneo FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
  CONSTRAINT uq_jugador_por_edicion UNIQUE (ci_jugador,id_torneo),
  CONSTRAINT uq_camiseta_equipo UNIQUE (id_equipo,id_torneo,numero_camiseta),
  CONSTRAINT chk_numero_camiseta CHECK (numero_camiseta BETWEEN 1 AND 99)
);

CREATE TABLE complejo (
  id_complejo INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  direccion VARCHAR(180) NOT NULL,
  departamento VARCHAR(80) NOT NULL
);

CREATE TABLE cancha (
  nombre_cancha VARCHAR(80) NOT NULL,
  id_complejo INT NOT NULL,
  superficie ENUM('sintético','parquet') NOT NULL,
  techada BOOLEAN NOT NULL,
  PRIMARY KEY (nombre_cancha,id_complejo),
  CONSTRAINT fk_cancha_complejo FOREIGN KEY (id_complejo) REFERENCES complejo(id_complejo)
);

CREATE TABLE turno (
  id_turno INT AUTO_INCREMENT PRIMARY KEY,
  hora_inicio TIME NOT NULL,
  hora_fin TIME NOT NULL,
  CONSTRAINT uq_turno_inicio UNIQUE (hora_inicio),
  CONSTRAINT chk_turno_horario CHECK (
    hora_inicio >= '18:00:00' AND hora_fin <= '23:00:00'
    AND TIME_TO_SEC(hora_fin)-TIME_TO_SEC(hora_inicio)=3600
    AND MINUTE(hora_inicio)=0 AND SECOND(hora_inicio)=0
  )
);

CREATE TABLE partido (
  id_partido INT AUTO_INCREMENT PRIMARY KEY,
  id_torneo INT NOT NULL,
  numero_fecha INT NOT NULL,
  id_equipo_local INT NOT NULL,
  id_equipo_visitante INT NOT NULL,
  dia DATE NOT NULL,
  id_turno INT NOT NULL,
  nombre_cancha VARCHAR(80) NOT NULL,
  id_complejo INT NOT NULL,
  estado ENUM('programado','jugado','postergado','cancelado') NOT NULL DEFAULT 'programado',
  CONSTRAINT fk_partido_torneo FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
  CONSTRAINT fk_partido_local FOREIGN KEY (id_equipo_local,id_torneo)
    REFERENCES equipo(id_equipo,id_torneo),
  CONSTRAINT fk_partido_visitante FOREIGN KEY (id_equipo_visitante,id_torneo)
    REFERENCES equipo(id_equipo,id_torneo),
  CONSTRAINT fk_partido_turno FOREIGN KEY (id_turno) REFERENCES turno(id_turno),
  CONSTRAINT fk_partido_cancha FOREIGN KEY (nombre_cancha,id_complejo)
    REFERENCES cancha(nombre_cancha,id_complejo),
  CONSTRAINT chk_equipos_distintos CHECK (id_equipo_local <> id_equipo_visitante),
  CONSTRAINT chk_numero_fecha CHECK (numero_fecha > 0),
  CONSTRAINT uq_partido_equipo_local UNIQUE (id_partido,id_equipo_local),
  CONSTRAINT uq_partido_equipo_visitante UNIQUE (id_partido,id_equipo_visitante)
);

CREATE TABLE planilla_partido (
  id_partido INT NOT NULL,
  ci_jugador VARCHAR(20) NOT NULL,
  id_equipo INT NOT NULL,
  PRIMARY KEY (id_partido,ci_jugador),
  CONSTRAINT fk_planilla_partido FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
  CONSTRAINT fk_planilla_jugador FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
  CONSTRAINT fk_planilla_equipo FOREIGN KEY (id_equipo) REFERENCES equipo(id_equipo),
  CONSTRAINT uq_planilla_partido_jugador UNIQUE (id_partido,ci_jugador)
);

CREATE TABLE gol (
  id_gol INT AUTO_INCREMENT PRIMARY KEY,
  id_partido INT NOT NULL,
  ci_jugador VARCHAR(20) NOT NULL,
  minuto TINYINT UNSIGNED NOT NULL,
  autogol BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_gol_planilla FOREIGN KEY (id_partido,ci_jugador)
    REFERENCES planilla_partido(id_partido,ci_jugador),
  CONSTRAINT chk_gol_minuto CHECK (minuto BETWEEN 0 AND 60)
);

CREATE TABLE tarjeta (
  id_tarjeta INT AUTO_INCREMENT PRIMARY KEY,
  id_partido INT NOT NULL,
  ci_jugador VARCHAR(20) NOT NULL,
  minuto TINYINT UNSIGNED NOT NULL,
  color ENUM('amarilla','roja') NOT NULL,
  CONSTRAINT fk_tarjeta_planilla FOREIGN KEY (id_partido,ci_jugador)
    REFERENCES planilla_partido(id_partido,ci_jugador),
  CONSTRAINT chk_tarjeta_minuto CHECK (minuto BETWEEN 0 AND 60)
);

CREATE TABLE sancion_jugador (
  id_sancion INT AUTO_INCREMENT PRIMARY KEY,
  ci_jugador VARCHAR(20) NOT NULL,
  id_torneo INT NOT NULL,
  motivo ENUM('roja','acumulación de amarillas','disciplinaria') NOT NULL,
  numero_fecha_inicio INT NOT NULL,
  cantidad_fechas INT NOT NULL,
  CONSTRAINT fk_sancion_jugador FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
  CONSTRAINT fk_sancion_torneo FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
  CONSTRAINT chk_sancion_inicio CHECK (numero_fecha_inicio > 0),
  CONSTRAINT chk_sancion_duracion CHECK (cantidad_fechas > 0)
);

-- Verificación
SHOW TABLES;
