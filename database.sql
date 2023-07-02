-- TFG
-- Realizado por:
-- Álvaro Rodríguez Gómez      (alu0101362953)
-- 

--
-- Creación de la base de datos
--
DROP DATABASE app;
CREATE DATABASE app WITH TEMPLATE = template0 ENCODING = 'UTF8';
ALTER DATABASE app OWNER TO admin;

--
-- Realizamos la conexión a la base de datos
-- 
-- \connect parking_db user adminpark identified BY parksswd;
\connect app
SET default_tablespace = '';

--------------------------------------------
-------- TABLAS DE LA BASE DE DATOS --------
--------------------------------------------

GRANT ALL PRIVILEGES ON DATABASE app TO admin;

-- Tabla device
CREATE TABLE public.device (
  eui varchar(16),
  name varchar(50),
  latitude  double precision,
  longitude double precision,
  altitude integer,

  PRIMARY KEY(eui)
);

-- Tabla gateway
CREATE TABLE public.gateway (
  eui varchar(16),
  name varchar(50),
  latitude  double precision,
  longitude double precision,
  altitude integer,

  PRIMARY KEY(eui)
);

-- Tabla data
CREATE TABLE public.data (
  eui varchar(16),
  rec_date timestamp,
  frame_counter integer,
  obj json,

  PRIMARY KEY(eui, rec_date),
  CONSTRAINT fk_eui
    FOREIGN KEY(eui)
    REFERENCES device(eui)
    ON DELETE CASCADE
);

-- Tabla device_limits
-- Define los limites nominales de los
-- parametros de cada sensor
CREATE TABLE public.device_limits (
  eui varchar(16),
  parameter varchar(80),
  min decimal,
  max decimal,

  PRIMARY KEY(eui, parameter),
  CONSTRAINT fk_eui
    FOREIGN KEY(eui)
    REFERENCES device(eui)
    ON DELETE CASCADE
);

-- Tabla gateway_range
-- Almacena los dispositivos que tiene al alcance
-- cada gateway
CREATE TABLE public.gateway_range (
  gat_eui varchar(16),
  dev_eui varchar(16),

  PRIMARY KEY(gat_eui, dev_eui),
  CONSTRAINT fk_gat_eui
    FOREIGN KEY(gat_eui)
    REFERENCES gateway(eui)
    ON DELETE CASCADE,
  CONSTRAINT fk_dev_eui
    FOREIGN KEY(dev_eui)
    REFERENCES device(eui)
    ON DELETE CASCADE
);