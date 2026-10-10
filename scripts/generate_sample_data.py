"""
Genera un dataset sintético de exportaciones florícolas de Ecuador.

Columnas: Exportador, Pais_Destino, Tipo_Flor, Volumen_Kg, Precio_FOB_USD,
Valor_FOB, Fecha_Despacho, Tiempo_Transito_Dias.

El dataset incluye estacionalidad (San Valentín, Día de la Mujer, Día de la
Madre, temporada baja de verano) y una tendencia de crecimiento anual.

Uso:
    python scripts/generate_sample_data.py [--rows 10000] [--seed 42] [--out data/exportaciones_flores.csv]
"""
import argparse
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

START_DATE = date(2023, 1, 1)
END_DATE = date(2026, 9, 30)

# País: (peso de participación, rango de tránsito en días, multiplicador de precio)
COUNTRIES = {
    "Estados Unidos": (40, (1, 3), 1.00),
    "Rusia": (14, (4, 7), 1.15),
    "Países Bajos": (8, (3, 6), 1.05),
    "Kazajistán": (5, (5, 9), 1.20),
    "Canadá": (5, (2, 4), 1.05),
    "España": (5, (3, 6), 1.05),
    "Italia": (4, (3, 6), 1.05),
    "Chile": (4, (2, 4), 0.95),
    "Ucrania": (3, (4, 8), 1.10),
    "Alemania": (4, (3, 6), 1.08),
    "México": (4, (2, 4), 0.95),
    "Japón": (4, (5, 8), 1.25),
}

# Flor: (peso de participación, volumen medio por despacho en kg, precio base USD/kg)
FLOWERS = {
    "Rosas": (72, 850, 6.50),
    "Gypsophila": (10, 500, 4.50),
    "Claveles": (5, 450, 3.60),
    "Crisantemos": (4, 400, 3.20),
    "Hortensias": (4, 300, 6.00),
    "Flores de verano": (5, 350, 4.10),
}

EXPORTERS = [f"Exportador_{i:02d}" for i in range(1, 16)]
# Distribución tipo Zipf: pocos exportadores concentran la mayor parte del volumen
EXPORTER_WEIGHTS = [1 / (i ** 0.8) for i in range(1, len(EXPORTERS) + 1)]

WOMENS_DAY_MARKETS = {"Rusia", "Kazajistán", "Ucrania"}
MOTHERS_DAY_MARKETS = {"Estados Unidos", "Canadá", "México", "Chile", "España", "Italia", "Japón", "Alemania"}


def in_window(d, month_start, day_start, month_end, day_end):
    return date(d.year, month_start, day_start) <= d <= date(d.year, month_end, day_end)


def seasonal_factor(d, country):
    """Multiplicador de demanda para una fecha y mercado (fecha de despacho, antes del evento)."""
    factor = 1.0
    if in_window(d, 1, 25, 2, 10):  # San Valentín
        factor += 2.5
    if in_window(d, 2, 22, 3, 5):  # Día de la Mujer (8 de marzo)
        factor += 3.0 if country in WOMENS_DAY_MARKETS else 0.3
    if in_window(d, 4, 22, 5, 8) and country in MOTHERS_DAY_MARKETS:  # Día de la Madre
        factor += 1.8
    if in_window(d, 8, 20, 8, 31) and country in WOMENS_DAY_MARKETS:  # 1 de septiembre
        factor += 0.8
    if in_window(d, 6, 1, 8, 15):  # temporada baja
        factor *= 0.7
    return factor


def trend_factor(d):
    """Crecimiento del mercado de ~5% anual."""
    years = (d - START_DATE).days / 365.25
    return 1.05 ** years


def pick_date(rng, country, days_span, max_weight):
    # Muestreo por rechazo según estacionalidad y tendencia
    while True:
        d = START_DATE + timedelta(days=rng.randrange(days_span))
        if rng.random() * max_weight <= seasonal_factor(d, country) * trend_factor(d):
            return d


def generate(rows, seed):
    rng = random.Random(seed)
    days_span = (END_DATE - START_DATE).days + 1
    max_weight = (1.0 + 2.5 + 3.0 + 1.8) * trend_factor(END_DATE)

    countries = list(COUNTRIES)
    country_weights = [COUNTRIES[c][0] for c in countries]
    flowers = list(FLOWERS)
    flower_weights = [FLOWERS[f][0] for f in flowers]

    records = []
    for _ in range(rows):
        country = rng.choices(countries, country_weights)[0]
        flower = rng.choices(flowers, flower_weights)[0]
        exporter = rng.choices(EXPORTERS, EXPORTER_WEIGHTS)[0]
        _, (transit_min, transit_max), price_mult = COUNTRIES[country]
        _, mean_volume, base_price = FLOWERS[flower]

        shipped = pick_date(rng, country, days_span, max_weight)
        is_peak = seasonal_factor(shipped, country) > 1.5

        # Volumen log-normal; en temporada pico los despachos son más grandes
        volume = rng.lognormvariate(math.log(mean_volume), 0.55) * (1.3 if is_peak else 1.0)
        volume = max(20.0, round(volume, 1))

        price = base_price * price_mult * (1.25 if is_peak else 1.0) * rng.uniform(0.9, 1.1)
        price = round(price, 2)

        records.append({
            "Exportador": exporter,
            "Pais_Destino": country,
            "Tipo_Flor": flower,
            "Volumen_Kg": volume,
            "Precio_FOB_USD": price,
            "Valor_FOB": round(volume * price, 2),
            "Fecha_Despacho": shipped.isoformat(),
            "Tiempo_Transito_Dias": rng.randint(transit_min, transit_max),
        })

    records.sort(key=lambda r: (r["Fecha_Despacho"], r["Exportador"]))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "exportaciones_flores.csv"))
    args = parser.parse_args()

    records = generate(args.rows, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"{len(records)} registros escritos en {out}")


if __name__ == "__main__":
    main()
