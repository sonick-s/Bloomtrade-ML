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

Documentación Swagger: http://127.0.0.1:5000/api/v1/docs
