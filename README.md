# Análisis de Confiabilidad de Componentes con Distribución de Weibull

Este proyecto implementa un análisis de confiabilidad para componentes automotrices usando datos históricos de fallas. Se calcula el MTBF (tiempo medio entre fallas), se ajusta un modelo de distribución Weibull 2P para estimar comportamientos de fallas, y se genera un reporte automatizado en Excel con métricas clave, alertas de sospecha y clasificación de patrones de falla.

---

## 📊 Objetivo

Detectar **componentes sospechosos de fallar prematuramente o con alta frecuencia** a partir de datos de mantenimiento, utilizando técnicas de confiabilidad como el modelo **Weibull de dos parámetros (2P)**. El sistema evalúa:

- Frecuencia de reclamos por componente y modelo.
- Confiabilidad a lo largo de intervalos de kilometraje.
- Clasificación del tipo de falla (infantil, aleatoria o por desgaste).
- Probabilidad de supervivencia del componente más allá de los 300,000 km.

---

## ⚙️ Estructura del Proyecto

### 1. **Preprocesamiento de Datos**
Función: `preprocesar_datos(df)`

- Filtra registros inválidos (distancias nulas o negativas, costos negativos).
- Ordena los registros por vehículo y componente.
- Calcula el MTBF (tiempo entre eventos) como la diferencia entre distancias de fallas sucesivas.

---

### 2. **Cálculo de Métricas Agregadas**
Función: `calcular_metricas_agregadas(df)`

Agrupa los datos por `modelo` y `componente`, generando:

- Total de reclamos únicos.
- Costo total asociado.
- Lista de valores MTBF por grupo.
- Número de vehículos únicos afectados.

---

### 3. **Ajuste Weibull y Probabilidades**
Función: `analizar_weibull(mtbf_values, intervalos)`

Para cada componente:

- Aplica limpieza estadística (filtro de outliers con IQR).
- Ajusta una distribución **Weibull 2P** sobre los MTBF.
- Calcula parámetros `β (beta)` y `η (eta)` de forma robusta.
- Estima:
  - **Media esperada** de fallas.
  - **Probabilidad acumulada** de falla para cada intervalo de 10,000 km hasta 300,000 km.
  - **Probabilidad de supervivencia más allá de los 300k km**.

> ⚠️ Si los datos son homogéneos, se aplica un suavizado con ruido gaussiano controlado para permitir el ajuste.

---

### 4. **Clasificación y Alertas**
Función: `generar_reporte(df_metricas, intervalos)`

- Determina si un componente es **"sospechoso"** bajo estas condiciones:
  - Más de 25 reclamos totales.
  - Relación de reclamos por vehículo superior a `1.2`.
  - Alta probabilidad de falla antes de 10k km (`P(x < 10k km) > 25%`).
- Clasifica el patrón de falla según el parámetro β:
  - **β < 1.0** → Falla infantil (problemas de fabricación o ensamblaje).
  - **1.0 ≤ β < 3.0** → Falla aleatoria (influencias externas o condiciones de uso).
  - **β ≥ 3.0** → Falla por desgaste (uso prolongado, envejecimiento).
- Calcula costo promedio por reclamo y MTBF promedio.

---

### 5. **Reporte Final en Excel**
Función: `main()`

- Muestra aleatoriamente el 10% de los datos para pruebas.
- Ejecuta todas las funciones anteriores.
- Exporta un archivo Excel estructurado con todas las métricas, alertas y probabilidades.

Columnas clave del reporte:
- Modelo
- Componente
- Total de Reclamos
- Vehículos Únicos
- Costo Total / Promedio
- MTBF promedio
- Sospechoso (sí/no)
- Tipo de falla
- Parámetros Weibull: `β`, `η`, `media esperada`
- Probabilidades de falla acumulada a distintos kilómetros
- Probabilidad de superar los 300k km

---

## 📈 Gráfico Weibull (Opcional)

Si se encuentra un componente sospechoso, el script grafica el ajuste Weibull con la distribución de datos reales. Esto es útil para validación visual y comunicación técnica.

---

## 🧪 Dependencias

Instala las librerías necesarias con:

```bash
pip install pandas numpy matplotlib reliability openpyxl scipy
```
## 🛠️ Ejecución del Script

1. Coloca tu archivo CSV original con los datos de reclamos.

2. Ajusta estas rutas en el código:

   * Línea para df_raw = pd.read_csv(r"TU_ARCHIVO.csv")

   * Línea para ruta_guardado = r"TU_REPORTE.xlsx"

Ejecuta el script:

```bash
Weibull_Analysis.py
```
## 🧾 Estructura Esperada del CSV
El archivo de entrada debe contener al menos las siguientes columnas:


## 📋 Descripción de Columnas

| Columna                 | Descripción                                  |
|-------------------------|----------------------------------------------|
| `vin`                   | Identificador único del vehículo            |
| `model`                 | Modelo del vehículo                         |
| `part_item_id`          | Código del componente                       |
| `in_distance_measure`   | Kilometraje de ocurrencia de falla (km)     |
| `repr_ord_amt_total`    | Costo total del reclamo                     |
| `repr_ord_nbr`          | Número de orden del reclamo                 |

---

## 📌 Parámetros Configurables

```python
MIN_VEHICULOS_SOSPECHOSO = 20      # Mínimo de vehículos únicos para alertar
MIN_RECLAMOS_SOSPECHOSO = 25       # Mínimo de reclamos para considerar componente
TAZA_FALLA_ALERTA = 1.2            # Umbral de reclamos/vehículo para alerta
INTERVALOS_KM = list(range(10000, 310000, 10000))  # Rangos de análisis (10k-300k)
```

## 📚 Fundamentos Técnicos
### 🔧 Distribución Weibull 2P
Función de Distribución Acumulada (CDF):

$$ F(x) = 1 - e^{-\left(\frac{x}{\eta}\right)^\beta} $$

#### Parámetros Clave:


β (beta): Forma del patrón de falla
β<1: Tasa de falla decreciente (falla infantil)
β=1: Fallas aleatorias
β>1: Desgaste por edad
η (eta): Parámetro de escala (tiempo característico a falla)

MTTF: η⋅Γ(1+1/β) (Función Gamma)

### 🧠 Ventajas del Modelo Weibull
✔️ Modela múltiples patrones de falla
✔️ Calcula probabilidades de falla acumulada
✔️ Identifica modos de falla dominantes
✔️ Permite comparación entre componentes

### 🧩 Casos de Uso
Confiabilidad de producto: Validar diseño de componentes
Gestión de garantías: Estimar vida útil esperada
Mejora continua: Priorizar componentes críticos
Benchmarking técnico: Comparar modelos/versiones
Optimización de mantenimiento: Planificar intervenciones

### 📤 Salida del Modelo
Ejemplo de estructura del reporte generado:

| Modelo | Componente | Total Reclamos | Costo Total | Sospechoso | Patron Fallas | Beta | ... | Prob 10k km | ... | Prob >300k km |
|--------|------------|----------------|-------------|------------|---------------|------|-----|-------------|-----|---------------|
| X1     | 54321      | 32             | $12,000.00  | SÍ         | Falla infantil| 0.73 | ... | 34.5%       | ... | 12.1%         |

### Campos Destacados:

Sospechoso: Alertas basadas en parámetros configurables
Patron Fallas: Clasificación según valor beta
Prob [X] km: Probabilidad acumulada por intervalo

### 🧾 Licencia

Este proyecto está desarrollado con fines educativos y demostrativos. 
Puedes adaptarlo libremente para:
- Portafolio profesional
- Análisis internos
- Investigación académica

Se prohíbe su uso comercial sin autorización expresa.
