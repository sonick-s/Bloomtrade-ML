"""
Genera un inventario sintético de una finca florícola (dataset 'interno').

Cada fila es un lote con su stock estimado y su ventana de salida. Incluye casos para probar
las reglas del recomendador: un lote despachado y uno descartado (se ignoran), un lote con
precio mínimo muy alto y uno fuera del horizonte pronosticado.

Uso:
    python scripts/generate_inventario_finca.py [--lotes 30] [--seed 7] [--out docs/inventario_finca.csv]
"""
import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

INICIO = date(2026, 10, 12)
FIN = date(2027, 8, 31)

# Flor: (variedades, peso por tallo kg, vida útil (min, max), costo USD/kg (min, max), largo tallo cm)
FLORES = {
    "Rosas": (["Freedom", "Explorer", "Mondial", "Vendela", "Pink Floyd", "Playa Blanca"], 0.045, (12, 16), (3.2, 4.4), [50, 60, 70, 80]),
    "Flores de verano": (["Hypericum", "Limonium", "Aster", "Delphinium"], 0.035, (9, 12), (2.4, 3.3), [60, 70, 80]),
    "Gypsophila": (["Xlence", "Million Stars"], 0.030, (10, 14), (2.8, 3.6), [70, 80]),
    "Claveles": (["Standard", "Mini"], 0.025, (14, 18), (1.9, 2.6), [50, 60]),
}
PESOS_FLOR = [60, 18, 15, 7]
COLORES = ["Rojo", "Blanco", "Rosado", "Amarillo", "Bicolor", "Naranja"]
GRADOS = ["Premium", "Select", "Standard"]


def lote(rng, numero, flor, cosecha, estado=None, precio_minimo_factor=None):
    variedades, peso, vida, costo_rango, largos = FLORES[flor]
    tallos = rng.randrange(4000, 36000, 500)
    costo = round(rng.uniform(*costo_rango), 2)
    desde = cosecha + timedelta(days=rng.randint(1, 3))
    return {
        "Codigo_Lote": f"L-{cosecha:%y%m}-{numero:03d}",
        "Bloque": f"B{rng.randint(1, 12):02d}",
        "Tipo_Flor": flor,
        "Variedad": rng.choice(variedades),
        "Color": rng.choice(COLORES),
        "Grado_Calidad": rng.choices(GRADOS, [30, 50, 20])[0],
        "Longitud_Tallo_Cm": rng.choice(largos),
        "Stock_Tallos": tallos,
        "Stock_Kg": round(tallos * peso * rng.uniform(0.92, 1.08), 1),
        "Estado": estado or ("cosechado" if cosecha <= INICIO + timedelta(days=10) else "en_cultivo"),
        "Fecha_Cosecha": cosecha.isoformat(),
        "Fecha_Salida_Desde": desde.isoformat(),
        "Fecha_Salida_Hasta": (desde + timedelta(days=rng.randint(7, 21))).isoformat(),
        "Vida_Util_Dias": rng.randint(*vida),
        "Costo_Produccion_Usd_Kg": costo,
        "Precio_Minimo_Usd_Kg": round(costo * (precio_minimo_factor or rng.uniform(1.15, 1.45)), 2),
        "Observaciones": "",
    }


def generar(cantidad, seed):
    rng = random.Random(seed)
    dias = (FIN - INICIO).days
    lotes = []
    for n in range(1, cantidad + 1):
        flor = rng.choices(list(FLORES), PESOS_FLOR)[0]
        lotes.append(lote(rng, n, flor, INICIO + timedelta(days=rng.randrange(dias))))

    # Casos para probar las reglas del recomendador
    especiales = [
        (lote(rng, 901, "Rosas", INICIO + timedelta(days=2), estado="despachado"), "Ya despachado: se ignora"),
        (lote(rng, 902, "Rosas", INICIO + timedelta(days=4), estado="descartado"), "Descartado por calidad: se ignora"),
        (lote(rng, 903, "Rosas", date(2027, 1, 20), precio_minimo_factor=3.0), "Precio mínimo muy alto"),
        (lote(rng, 904, "Gypsophila", date(2027, 11, 5)), "Fuera del horizonte pronosticado"),
    ]
    for fila, nota in especiales:
        fila["Observaciones"] = nota
        lotes.append(fila)
    return sorted(lotes, key=lambda f: f["Fecha_Salida_Desde"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lotes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "docs" / "inventario_finca.csv"))
    args = parser.parse_args()

    filas = generar(args.lotes, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0]))
        writer.writeheader()
        writer.writerows(filas)
    print(f"{len(filas)} lotes escritos en {out}")


if __name__ == "__main__":
    main()
