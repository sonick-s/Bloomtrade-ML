-- =============================================================================
-- Bloomtrade ML - Esquema inicial (MySQL 8.0.16+)
-- Uso: mysql -u <usuario> -p < database/init.sql
-- El nombre de la base debe coincidir con DB_NAME del .env
-- =============================================================================

-- -----------------------------------------------------------------------------
-- datasets: cada CSV cargado, versionado
--   tipo = 'mercado' -> sus filas van a exportaciones y se usan para entrenar
--   tipo = 'interno' -> sus filas van a inventario_finca y NUNCA se entrenan
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS datasets (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  nombre           VARCHAR(150) NOT NULL,
  archivo_original VARCHAR(255) NOT NULL,
  tipo             ENUM('mercado', 'interno') NOT NULL DEFAULT 'mercado',
  origen           ENUM('base', 'usuario') NOT NULL DEFAULT 'usuario',
  filas            INT UNSIGNED NOT NULL DEFAULT 0,
  fecha_min        DATE NULL,
  fecha_max        DATE NULL,
  hash_sha256      CHAR(64) NOT NULL COMMENT 'Evita cargar el mismo archivo dos veces',
  estado           ENUM('pendiente', 'validado', 'con_errores') NOT NULL DEFAULT 'pendiente',
  errores          JSON NULL COMMENT 'Detalle de errores de validación',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_datasets_hash (hash_sha256),
  KEY ix_datasets_tipo (tipo, origen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- exportaciones: registros de cada dataset (mismas columnas del CSV)
-- anio y mes se calculan desde fecha_despacho
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exportaciones (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  dataset_id           INT NOT NULL,
  fecha_despacho       DATE NOT NULL,
  anio                 SMALLINT AS (YEAR(fecha_despacho)) STORED,
  mes                  TINYINT AS (MONTH(fecha_despacho)) STORED,
  temporada            VARCHAR(30) NULL,
  exportador           VARCHAR(100) NULL,
  tamano_empresa       VARCHAR(20) NULL,
  provincia_origen     VARCHAR(50) NULL,
  aeropuerto_salida    VARCHAR(80) NULL,
  subpartida_nandina   VARCHAR(12) NULL,
  tipo_flor            VARCHAR(50) NOT NULL,
  pais_destino         VARCHAR(80) NOT NULL,
  tiempo_transito_dias TINYINT UNSIGNED NULL,
  volumen_kg           DECIMAL(12, 2) NOT NULL,
  precio_fob_usd_kg    DECIMAL(10, 2) NULL,
  valor_fob_usd        DECIMAL(14, 2) NOT NULL,
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_exportaciones_dataset FOREIGN KEY (dataset_id)
    REFERENCES datasets (id) ON DELETE CASCADE,
  CONSTRAINT ck_exportaciones_volumen CHECK (volumen_kg >= 0),
  CONSTRAINT ck_exportaciones_valor CHECK (valor_fob_usd >= 0),
  KEY ix_exportaciones_serie (tipo_flor, pais_destino, fecha_despacho),
  KEY ix_exportaciones_fecha (fecha_despacho),
  KEY ix_exportaciones_dataset (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- inventario_finca: información interna de la florícola (stock y cosechas)
-- Se compara contra los pronósticos para estimar precio y mercado destino.
-- No se usa para entrenar. Pertenece a un dataset de tipo 'interno'.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventario_finca (
  id                      INT AUTO_INCREMENT PRIMARY KEY,
  dataset_id              INT NOT NULL,
  codigo_lote             VARCHAR(50) NULL,
  bloque                  VARCHAR(50) NULL COMMENT 'Invernadero o bloque de cultivo',
  tipo_flor               VARCHAR(50) NOT NULL COMMENT 'Mismos valores que exportaciones.tipo_flor',
  variedad                VARCHAR(80) NULL COMMENT 'Ej: Freedom, Explorer, Mondial',
  color                   VARCHAR(40) NULL,
  grado_calidad           VARCHAR(30) NULL COMMENT 'Ej: Premium, Select, Standard',
  longitud_tallo_cm       SMALLINT UNSIGNED NULL,
  stock_tallos            INT UNSIGNED NULL,
  stock_kg                DECIMAL(12, 2) NOT NULL COMMENT 'Aproximado; se compara con volumen_kg del mercado',
  estado                  ENUM('en_cultivo', 'cosechado', 'en_cuarto_frio', 'reservado', 'despachado', 'descartado')
                          NOT NULL DEFAULT 'en_cultivo',
  fecha_cosecha           DATE NOT NULL COMMENT 'Estimada si aún está en cultivo',
  fecha_salida_desde      DATE NOT NULL COMMENT 'Ventana en la que la flor puede salir',
  fecha_salida_hasta      DATE NOT NULL,
  vida_util_dias          TINYINT UNSIGNED NULL COMMENT 'Descarta mercados con tránsito demasiado largo',
  costo_produccion_usd_kg DECIMAL(10, 2) NULL,
  precio_minimo_usd_kg    DECIMAL(10, 2) NULL COMMENT 'Precio por debajo del cual no conviene vender',
  observaciones           VARCHAR(500) NULL,
  created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_inventario_dataset FOREIGN KEY (dataset_id)
    REFERENCES datasets (id) ON DELETE CASCADE,
  CONSTRAINT ck_inventario_stock CHECK (stock_kg >= 0),
  CONSTRAINT ck_inventario_ventana CHECK (fecha_salida_hasta >= fecha_salida_desde),
  KEY ix_inventario_flor_salida (tipo_flor, fecha_salida_desde),
  KEY ix_inventario_estado (estado),
  KEY ix_inventario_dataset (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- modelos: versiones entrenadas. El archivo .joblib vive en disco (ruta_artefacto)
-- Solo puede haber un modelo activo a la vez (columna activo_unico)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelos (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  version        INT UNSIGNED NOT NULL,
  algoritmo      VARCHAR(50) NOT NULL COMMENT 'prophet, xgboost, ...',
  ruta_artefacto VARCHAR(255) NOT NULL,
  parametros     JSON NULL,
  metricas       JSON NULL COMMENT 'Ej: {"mape": 0.12, "rmse": 340.5}',
  activo         BOOLEAN NOT NULL DEFAULT FALSE,
  activo_unico   TINYINT AS (IF(activo, 1, NULL)) STORED,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_modelos_version (version),
  UNIQUE KEY uq_modelos_activo (activo_unico)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- modelo_datasets: con qué datasets se entrenó cada versión (trazabilidad)
-- Un dataset usado en un entrenamiento no se puede borrar (RESTRICT)
-- Solo acepta datasets de tipo 'mercado' (ver trigger más abajo)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modelo_datasets (
  modelo_id  INT NOT NULL,
  dataset_id INT NOT NULL,
  PRIMARY KEY (modelo_id, dataset_id),
  CONSTRAINT fk_modelo_datasets_modelo FOREIGN KEY (modelo_id)
    REFERENCES modelos (id) ON DELETE CASCADE,
  CONSTRAINT fk_modelo_datasets_dataset FOREIGN KEY (dataset_id)
    REFERENCES datasets (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Impide entrenar un modelo con datos internos de la finca
DROP TRIGGER IF EXISTS trg_modelo_datasets_solo_mercado;
DELIMITER $$
CREATE TRIGGER trg_modelo_datasets_solo_mercado
BEFORE INSERT ON modelo_datasets
FOR EACH ROW
BEGIN
  IF (SELECT tipo FROM datasets WHERE id = NEW.dataset_id) <> 'mercado' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Solo los datasets de tipo mercado se pueden usar para entrenar';
  END IF;
END$$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- pronosticos: resultados precalculados por modelo (caché para el dashboard)
-- periodo = primer día del mes pronosticado
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pronosticos (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  modelo_id       INT NOT NULL,
  tipo_flor       VARCHAR(50) NOT NULL,
  pais_destino    VARCHAR(80) NOT NULL,
  periodo         DATE NOT NULL,
  volumen_kg_pred DECIMAL(14, 2) NOT NULL,
  limite_inf      DECIMAL(14, 2) NULL,
  limite_sup      DECIMAL(14, 2) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_pronosticos_modelo FOREIGN KEY (modelo_id)
    REFERENCES modelos (id) ON DELETE CASCADE,
  UNIQUE KEY uq_pronosticos_serie (modelo_id, tipo_flor, pais_destino, periodo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
