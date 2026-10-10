-- Agrega el precio pronosticado a cada pronóstico (necesario para recomendar mercado).
-- Ejecutar una sola vez sobre una base creada con la versión anterior de init.sql.
ALTER TABLE pronosticos
  ADD COLUMN precio_usd_kg_pred DECIMAL(10, 2) NULL AFTER volumen_kg_pred;
