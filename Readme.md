# Proyect Bloomtrade

## 1. Instalación inicial

Solo la primera vez: crea el entorno virtual e instala las dependencias.

```bash
# Crea el entorno virtual
py -m venv venv
# Activa el entorno virtual
source venv/Scripts/activate
# Instalar dependencias
pip install -r requirements.txt
```

## 2. Activar el entorno y levantar el proyecto

Cada vez que vayas a trabajar en el proyecto:

```bash
# Activa el entorno virtual
source venv/Scripts/activate
# Levanta el proyecto
python app.py
```

## 3. Rutas del proyecto

| Ruta | Qué muestra |
|---|---|
| http://127.0.0.1:5000/ | Dashboard global: pronóstico por flor y mercado (interactivo) |
| http://127.0.0.1:5000/modelos | Carga de CSV de mercado, entrenamiento y versiones del modelo |
| http://127.0.0.1:5000/predicciones | Carga del inventario de la finca y plan de ventas por lote |
| http://127.0.0.1:5000/api/v1/docs | Documentación Swagger de la API |

El frontend vive en la carpeta `web/`, separado de la API:

```
web/
├── routes.py          # rutas de las páginas HTML
├── index.html         # layout común (Tailwind por CDN, estilos, navbar y footer)
└── pages/
    ├── dashboard.html, model-uptodate.html, predicciones.html
    ├── components/    # navbar.html, footer.html
    └── js/            # api.js, ui.js y la lógica de cada página
```

## 4. Flujo de uso

1. **Modelos** → carga un CSV de exportaciones (ej. `docs/exportaciones_ecuador_flores.csv`) y entrena.
   El modelo nuevo se activa solo si tiene menor error que el activo; también se puede activar a mano.
2. **Predicciones** → carga el inventario de la finca (ej. `docs/inventario_finca.csv`) y obtén el
   reparto recomendado de cada lote por mercado.
3. **Dashboard** → explora el pronóstico del modelo activo por flor y mercado.

La lógica de Machine Learning está en `ml/` (sin dependencias de Flask) y los modelos entrenados se
guardan en `ml/artifacts/` (fuera de git). Datos de ejemplo: `scripts/generate_ecuador_exports.py` y
`scripts/generate_inventario_finca.py`.
