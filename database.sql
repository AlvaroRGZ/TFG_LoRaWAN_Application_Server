-- Realizado por: Álvaro Rodríguez Gómez (alu0101362953@ull.edu.es)

--
-- Creación de la base de datos
--
DROP DATABASE app;
CREATE DATABASE app WITH TEMPLATE = template0 ENCODING = 'UTF8';
ALTER DATABASE app OWNER TO admin;

--
-- Realizamos la conexión a la base de datos
-- 

\connect app
SET default_tablespace = '';

--------------------------------------------
-------- TABLAS DE LA BASE DE DATOS --------
--------------------------------------------

GRANT ALL PRIVILEGES ON DATABASE app TO admin;

-- Tabla gateway
-- Almacena los datos de los gateways
CREATE TABLE public.gateway (
  eui varchar(16),
  name varchar(50),
  latitude  double precision,
  longitude double precision,
  altitude integer,

  PRIMARY KEY(eui)
);

-- Tabla device
-- Almacena los datos de los dispositivos
CREATE TABLE public.device (
  eui varchar(16),
  name varchar(50),
  latitude  double precision,
  longitude double precision,
  altitude integer,

  PRIMARY KEY(eui)
);

-- Tabla data
-- Almacena los registros de los dispositivos con la fecha de recepción
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

-- Tabla alerts
-- Almacena los registros que han traspasado los
-- limites impuestos y cuando se recibieron
CREATE TABLE public.alerts (
  eui varchar(16),
  descrip varchar(250),
  param varchar(80),
  value numeric,
  date timestamp,

  CONSTRAINT fk_eui
    FOREIGN KEY(eui)
    REFERENCES device(eui)
    ON DELETE CASCADE
);

-- Tabla web_preferences
-- Almacena las preferencias para mostrar los datos
CREATE TABLE public.web_preferences (
  eui varchar(16),
  begin_time timestamp,
  end_time timestamp,
  nrows numeric,

  PRIMARY KEY(eui),
  CONSTRAINT fk_eui
    FOREIGN KEY(eui)
    REFERENCES device(eui)
    ON DELETE CASCADE
);