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
| http://127.0.0.1:5000/ | Frontend (dashboard) |
| http://127.0.0.1:5000/api/v1/docs | Documentación Swagger de la API |

El frontend vive en la carpeta `web/`, separado de la API:

```
web/
├── routes.py          # rutas de las páginas HTML
├── index.html         # página principal (Tailwind por CDN y estilos incluidos)
└── pages/
    ├── components/    # piezas reutilizables (navbar, footer)
    └── js/            # lógica de la página y llamadas a la API
```
