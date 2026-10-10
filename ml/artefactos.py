"""Guarda y carga el modelo entrenado. Los archivos viven en ml/artifacts/ (no en la base de datos)."""
import pickle
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "artifacts"


def guardar(pronosticador, version):
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA / f"modelo_v{version}.pkl"
    with ruta.open("wb") as archivo:
        pickle.dump(pronosticador, archivo)
    # Ruta relativa al proyecto: es lo que se guarda en modelos.ruta_artefacto
    return str(ruta.relative_to(CARPETA.parent.parent)).replace("\\", "/")


def cargar(ruta_relativa):
    ruta = CARPETA.parent.parent / ruta_relativa
    with ruta.open("rb") as archivo:
        return pickle.load(archivo)
