"""Regresión Ridge implementada con numpy."""
import numpy as np


def ajustar(X, y, alpha):
    """
    Mínimos cuadrados con una penalización alpha que evita coeficientes extremos.
    Resuelve (Zᵀ Z + alpha·I) β = Zᵀ (y - media), con Z = X estandarizada.
    """
    media, desv = X.mean(axis=0), X.std(axis=0)
    desv[desv == 0] = 1.0
    Z = (X - media) / desv
    y_media = y.mean()
    beta = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y_media))
    return {"media": media, "desv": desv, "beta": beta, "intercepto": y_media}


def predecir(modelo, X):
    return ((X - modelo["media"]) / modelo["desv"]) @ modelo["beta"] + modelo["intercepto"]
