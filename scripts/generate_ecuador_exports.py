"""
Genera un dataset sintético de exportaciones florícolas de Ecuador (NANDINA 0603)
calibrado con la Ficha Sectorial de Flores de la CFN (sept. 2023), que cita datos
del Banco Central del Ecuador, INEC (ESPAC 2022) y la Superintendencia de Compañías.

Calibración:
- Registros por año proporcionales al FOB anual exportado (BCE 2018-2022; 2023+ proyectado).
- Participación por país destino según BCE por año (incluye la caída de Rusia y el
  crecimiento de Kazajistán en 2022-2023). "Otros países" se reparte en mercados supuestos.
- Mezcla de especies según producción INEC 2022 (Rosa 75%, transitorias 13%, ...).
- Provincia de las empresas y tamaño según Ranking de Compañías 2022.
- Precio promedio anual por kg igual al costo promedio por tonelada del BCE.

Uso:
    python scripts/generate_ecuador_exports.py [--rows 10000] [--seed 42] [--out data/exportaciones_ecuador_flores.csv]
"""
import argparse
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

START_DATE = date(2018, 1, 1)
END_DATE = date(2026, 9, 30)

# FOB exportado por año en USD millones (BCE). 2023 en adelante: proyección (+3% anual).
ANNUAL_FOB = {
    2018: 843.37, 2019: 879.78, 2020: 827.14, 2021: 927.28, 2022: 950.50,
    2023: 979.0, 2024: 1008.4, 2025: 1038.6, 2026: 1069.8 * 9 / 12,  # 2026 hasta septiembre
}

# Precio promedio FOB en USD por kg (BCE: costo promedio por tonelada / 1000). 2024+: supuesto.
ANNUAL_PRICE_KG = {
    2018: 5.448, 2019: 5.554, 2020: 5.409, 2021: 5.526, 2022: 5.762,
    2023: 5.631, 2024: 5.75, 2025: 5.85, 2026: 5.95,
}

# Participación FOB por destino en % (BCE). 2023 = enero-mayo 2023; 2024+ igual a 2023.
MAIN_SHARES = {
    #        EE.UU. Kazaj. P.Bajos Italia Canadá Rusia
    2018: (41.1, 2.0, 9.6, 4.2, 2.5, 18.6),
    2019: (45.1, 2.3, 8.6, 3.7, 2.5, 14.6),
    2020: (37.3, 2.0, 10.0, 3.2, 4.1, 13.8),
    2021: (43.0, 2.3, 9.3, 3.6, 2.9, 10.7),
    2022: (39.2, 10.1, 10.0, 4.0, 3.6, 3.6),
    2023: (32.5, 13.6, 10.8, 3.9, 3.8, 0.1),
}
MAIN_COUNTRIES = ("Estados Unidos", "Kazajistán", "Países Bajos", "Italia", "Canadá", "Rusia")

# Reparto supuesto del rubro "Otros países" del BCE (pesos relativos)
OTHER_COUNTRIES = {
    "España": 14, "Chile": 12, "México": 11, "Alemania": 10, "Ucrania": 8,
    "Emiratos Árabes Unidos": 9, "Japón": 7, "Reino Unido": 7, "Francia": 6,
    "Suiza": 4, "Polonia": 6, "Corea del Sur": 6,
}

# País: (rango de días de tránsito, multiplicador de precio)
COUNTRY_INFO = {
    "Estados Unidos": ((1, 3), 1.00), "Kazajistán": ((5, 9), 1.18), "Países Bajos": ((3, 5), 1.05),
    "Italia": ((3, 6), 1.06), "Canadá": ((2, 4), 1.04), "Rusia": ((4, 7), 1.15),
    "España": ((3, 6), 1.05), "Chile": ((2, 4), 0.94), "México": ((2, 4), 0.92),
    "Alemania": ((3, 6), 1.08), "Ucrania": ((4, 8), 1.10), "Emiratos Árabes Unidos": ((3, 5), 1.15),
    "Japón": ((5, 8), 1.25), "Reino Unido": ((3, 5), 1.08), "Francia": ((3, 6), 1.07),
    "Suiza": ((3, 6), 1.12), "Polonia": ((4, 7), 1.06), "Corea del Sur": ((5, 8), 1.20),
}

# Flor: (participación % INEC 2022, subpartida NANDINA, volumen medio por despacho kg, precio relativo)
FLOWERS = {
    "Rosas": (75, "0603.11.00", 700, 1.06),
    "Flores de verano": (13, "0603.19.90", 650, 0.78),
    "Gypsophila": (7, "0603.19.10", 650, 0.85),
    "Claveles": (2, "0603.12.00", 600, 0.65),
    "Otras flores": (3, "0603.19.90", 600, 0.75),
}

# Provincia: (participación % de empresas, probabilidad de salir por UIO frente a GYE)
PROVINCES = {
    "Pichincha": (68, 0.97), "Cotopaxi": (15, 0.97), "Imbabura": (5, 0.97),
    "Carchi": (4, 0.95), "Azuay": (5, 0.40), "Guayas": (3, 0.10),
}
AIRPORTS = ("UIO - Mariscal Sucre (Quito)", "GYE - José Joaquín de Olmedo (Guayaquil)")

# Tamaño: (cantidad de exportadores ficticios, peso de envíos, multiplicador de volumen)
# Proporción aproximada al Ranking 2022: 43 grandes, 70 medianas, 75 pequeñas, 99 micro.
SIZES = {
    "Grande": (5, 12.0, 1.5),
    "Mediana": (8, 3.0, 1.0),
    "Pequeña": (8, 1.0, 0.6),
    "Microempresa": (9, 0.35, 0.3),
}

WOMENS_DAY_MARKETS = {"Rusia", "Kazajistán", "Ucrania", "Polonia"}
MOTHERS_DAY_MARKETS = {
    "Estados Unidos", "Canadá", "México", "Chile", "España", "Italia", "Japón",
    "Alemania", "Países Bajos", "Suiza", "Corea del Sur",
}


def in_window(d, month_start, day_start, month_end, day_end):
    return date(d.year, month_start, day_start) <= d <= date(d.year, month_end, day_end)


def season(d, country):
    """Temporada comercial de la fecha de despacho (días antes de cada celebración)."""
    if in_window(d, 1, 25, 2, 10):
        return "San Valentín"
    if in_window(d, 2, 22, 3, 5) and country in WOMENS_DAY_MARKETS:
        return "Día de la Mujer"
    if in_window(d, 4, 22, 5, 8) and country in MOTHERS_DAY_MARKETS:
        return "Día de la Madre"
    if in_window(d, 6, 1, 8, 15):
        return "Temporada baja"
    return "Normal"


SEASON_FACTOR = {
    "San Valentín": 3.5, "Día de la Mujer": 4.0, "Día de la Madre": 2.8,
    "Temporada baja": 0.7, "Normal": 1.0,
}
SEASON_PRICE = {
    "San Valentín": 1.25, "Día de la Mujer": 1.20, "Día de la Madre": 1.15,
    "Temporada baja": 0.92, "Normal": 1.0,
}
SEASON_VOLUME = {
    "San Valentín": 1.3, "Día de la Mujer": 1.3, "Día de la Madre": 1.2,
    "Temporada baja": 0.9, "Normal": 1.0,
}


def demand_factor(d, country):
    factor = SEASON_FACTOR[season(d, country)]
    if date(2020, 3, 16) <= d <= date(2020, 5, 31):  # cierre por COVID-19
        factor *= 0.35
    return factor


def country_weights(year):
    main = MAIN_SHARES[min(year, 2023)]
    other_share = 100 - sum(main)
    other_total = sum(OTHER_COUNTRIES.values())
    weights = dict(zip(MAIN_COUNTRIES, main))
    for c, w in OTHER_COUNTRIES.items():
        weights[c] = other_share * w / other_total
    return list(weights), list(weights.values())


def assign_provinces(rng, n):
    """Reparte las provincias en proporción a la participación de empresas (no al azar)."""
    quotas = {p: n * w / 100 for p, (w, _) in PROVINCES.items()}
    counts = {p: max(1, int(q)) for p, q in quotas.items()}
    while sum(counts.values()) < n:
        p = max(quotas, key=lambda k: quotas[k] - counts[k])
        counts[p] += 1
    provinces = [p for p, c in counts.items() for _ in range(c)][:n]
    rng.shuffle(provinces)
    return provinces


def build_exporters(rng):
    provinces = assign_provinces(rng, sum(count for count, _, _ in SIZES.values()))
    exporters = []
    n = 1
    for size, (count, ship_weight, vol_mult) in SIZES.items():
        for _ in range(count):
            exporters.append({
                "name": f"Exportador_{n:02d}",
                "size": size,
                "province": provinces[n - 1],
                "weight": ship_weight * rng.uniform(0.7, 1.3),
                "vol_mult": vol_mult,
            })
            n += 1
    return exporters


def year_counts(rows):
    total = sum(ANNUAL_FOB.values())
    counts = {y: int(rows * v / total) for y, v in ANNUAL_FOB.items()}
    # Reparte el residuo de redondeo empezando por los años más grandes
    for y in sorted(ANNUAL_FOB, key=ANNUAL_FOB.get, reverse=True)[: rows - sum(counts.values())]:
        counts[y] += 1
    return counts


def pick_date(rng, year, country):
    start = date(year, 1, 1)
    end = min(date(year, 12, 31), END_DATE)
    span = (end - start).days + 1
    max_weight = max(SEASON_FACTOR.values())
    while True:
        d = start + timedelta(days=rng.randrange(span))
        if rng.random() * max_weight <= demand_factor(d, country):
            return d


def generate(rows, seed):
    rng = random.Random(seed)
    exporters = build_exporters(rng)
    exporter_weights = [e["weight"] for e in exporters]
    flowers = list(FLOWERS)
    flower_weights = [FLOWERS[f][0] for f in flowers]

    records = []
    for year, n in year_counts(rows).items():
        countries, weights = country_weights(year)
        year_records = []
        for _ in range(n):
            country = rng.choices(countries, weights)[0]
            flower = rng.choices(flowers, flower_weights)[0]
            exp = rng.choices(exporters, exporter_weights)[0]
            (transit_min, transit_max), price_mult = COUNTRY_INFO[country]
            _, nandina, mean_volume, flower_price = FLOWERS[flower]

            shipped = pick_date(rng, year, country)
            temporada = season(shipped, country)

            volume = rng.lognormvariate(math.log(mean_volume), 0.5) * exp["vol_mult"] * SEASON_VOLUME[temporada]
            price = flower_price * price_mult * SEASON_PRICE[temporada] * rng.uniform(0.9, 1.1)
            airport = AIRPORTS[0] if rng.random() < PROVINCES[exp["province"]][1] else AIRPORTS[1]

            year_records.append({
                "Fecha_Despacho": shipped.isoformat(),
                "Anio": shipped.year,
                "Mes": shipped.month,
                "Temporada": temporada,
                "Exportador": exp["name"],
                "Tamano_Empresa": exp["size"],
                "Provincia_Origen": exp["province"],
                "Aeropuerto_Salida": airport,
                "Subpartida_NANDINA": nandina,
                "Tipo_Flor": flower,
                "Pais_Destino": country,
                "Tiempo_Transito_Dias": rng.randint(transit_min, transit_max),
                "Volumen_Kg": max(15.0, round(volume, 1)),
                "_price": price,
            })

        # Ajusta precios para que el promedio ponderado del año coincida con el BCE
        total_kg = sum(r["Volumen_Kg"] for r in year_records)
        avg_price = sum(r["Volumen_Kg"] * r["_price"] for r in year_records) / total_kg
        scale = ANNUAL_PRICE_KG[year] / avg_price
        for r in year_records:
            price = round(r.pop("_price") * scale, 2)
            r["Precio_FOB_USD_Kg"] = price
            r["Valor_FOB_USD"] = round(r["Volumen_Kg"] * price, 2)
        records.extend(year_records)

    records.sort(key=lambda r: (r["Fecha_Despacho"], r["Exportador"]))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "exportaciones_ecuador_flores.csv"))
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
