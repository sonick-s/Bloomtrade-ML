# Bloomtrade ML

El sector florícola de Ecuador es uno de los sectores con mayor produccion y exportacion a nivel mundial, este caso de estudio se basa en el analisis de este sector, el cual tratara de responder a:

- ¿Cuánto volumen total de rosas (o flores de verano) demandará cada mercado en los próximos 6 a 12 meses?
- ¿apartir de mi volumen de producciona ctual a que mercados deberia apuntar?

**Variables clave a consolidar:** Exportador, País_Destino, Tipo_Flor, Volumen_Kg, Valor_FOB, Fecha_Despacho, Tiempo_Tránsito_Días.

## Objetivo del proyecto
El objetivo de esta aplicación es servir como un asistente inteligente de inteligencia de mercado para empresas florícolas, cruzando la data interna de la finca con la data macro del mercado global.
 
## Flujo del proyecto

1. **Carga:** 
El usuario arrastra y suelta el archivo de Excel con la información de su finca. 

2. **Validación del Dataset Interno:** 
Se verifica que las columnas obligatorias (`Fecha`, `Tipo_Flor`, `Pais_Destino`, `Volumen_Kg`, `Precio_FOB_USD`) estén presentes.

3. **Proyección de Demanda Global (Forecasting 6-12 Meses):** 
El usuario selecciona la pestaña **Pronóstico de Demanda**:
* Filtra por variedad de flor (ej. *Rosas*) y horizonte temporal (*6 o 12 meses*).
* La aplicación despliega un gráfico de series de tiempo con la **curva de demanda proyectada del mercado global**, resaltando las semanas pico (San Valentín, Día de la Madre, Día de la Mujer).
* Se contrasta la curva del mercado global con la curva histórica de despachos de la finca para detectar ventanas de oportunidad desaprovechadas.

4. **Generación de Recomendaciones (Matchmaking Prescriptivo):** 
El usuario ingresa a la pestaña **Planificador de Ventas**:
* Introduce su volumen de producción estimado para los próximos meses o deja que el sistema tome la pestaña `Capacidad_Produccion` de su Excel.
* Presiona el botón **"Optimizar Asignación de Mercado"**.
* El algoritmo procesa el Score de Oportunidad y genera una matriz de distribución:
* *"Para tu producción de Rosas en Febrero (20,000 Kg): Destinar 55% a EE.UU. (Contratos estables), 30% a Kazajistán (Mercado transitorio de alto margen) y 15% a Canadá"*.

6. **6. Exportación de Reporte Ejecutivo:** Generación de entregable final.
El usuario hace clic en **"Exportar Informe Ejecutivo (PDF / Excel)"**. El sistema descarga un informe listo para reuniones de directorio o de gerencia comercial con los gráficos de ML, tablas de precios esperados y el plan recomendado de envíos.

## Tecnologias
- Interfaz + Servidor Web: Streamlit
- Procesamiento de Datos: Pandas, NumPy, OpenPyXL (para leer Excel)
- Machine Learning: Scikit-Learn (K-Means, StandardScaler) y Prophet / XGBoost (para series de tiempo)
- Visualizaciones Interactivas: Plotly Express (gráficos dinámicos y mapas de calor)
- Base de datos: Mysql (Opcional)

