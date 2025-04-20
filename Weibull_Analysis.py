import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reliability.Fitters import Fit_Weibull_2P
from reliability.Probability_plotting import plot_points
from scipy.special import gamma

# Configuración de parámetros ajustables
MIN_VEHICULOS_SOSPECHOSO = 20
MIN_RECLAMOS_SOSPECHOSO = 25
TAZA_FALLA_ALERTA = 1.2
INTERVALOS_KM = list(range(10000, 310000, 10000))  # De 10k en 10k hasta 300k

def preprocesar_datos(df):
    # Limpieza inicial de datos
    df = df.dropna(subset=['model', 'part_item_id', 'in_distance_measure'])
    df = df[(df['in_distance_measure'] > 0) & (df['repr_ord_amt_total'] >= 0)]
    
    # Calcular MTBF incluyendo primera falla
    df = df.sort_values(['vin', 'part_item_id', 'in_distance_measure'])
    df['km_anterior'] = df.groupby(['vin', 'part_item_id'])['in_distance_measure'].shift(1).fillna(0)
    df['mtbf'] = df['in_distance_measure'] - df['km_anterior']
    
    return df[df['mtbf'] > 0]

def calcular_metricas_agregadas(df):
    agg_config = {
        'total_reclamos': ('repr_ord_nbr', 'nunique'),
        'costo_total': ('repr_ord_amt_total', 'sum'),
        'mtbf_values': ('mtbf', list),
        'vehiculos_unicos': ('vin', 'nunique')
    }
    return df.groupby(['model', 'part_item_id']).agg(**agg_config).reset_index()

def weibull_cdf(x, beta, eta):
    """Calcula la CDF de Weibull manualmente"""
    try:
        return 1 - np.exp(-(x/eta)**beta) if eta > 0 else 0.0
    except:
        return np.nan

def analizar_weibull(mtbf_values, intervalos, show_plot=False):
    """Realiza el análisis de Weibull con manejo robusto de errores"""
    if len(mtbf_values) < 3:
        return None, None, None, [np.nan]*len(intervalos), np.nan
    
    try:
        # Filtrado adaptativo de outliers
        q25, q75 = np.quantile(mtbf_values, [0.25, 0.75])
        iqr = q75 - q25
        upper_bound = q75 + 1.5 * iqr
        filtered_data = [x for x in mtbf_values if x <= upper_bound]
        
        if len(filtered_data) < 3:
            return None, None, None, [np.nan]*len(intervalos), np.nan
        
        # Suavizar datos idénticos
        if len(set(filtered_data)) == 1:
            np.random.seed(42)
            filtered_data = [x + np.random.normal(0, 0.1*x) for x in filtered_data]
        
        # Ajustar modelo Weibull
        weibull = Fit_Weibull_2P(failures=filtered_data, show_probability_plot=show_plot)
        beta = weibull.beta
        eta = weibull.alpha
        
        # Calcular media teórica de Weibull
        media = eta * gamma(1 + 1/beta) if beta and eta else np.nan
        
        # Calcular probabilidades para cada intervalo
        probs = []
        for k in intervalos:
            try:
                prob = weibull_cdf(k, beta, eta) if k > 0 else 0.0
                probs.append(prob)
            except:
                probs.append(np.nan)
        
        # Probabilidad de superar 300k km
        prob_mas_300k = 1 - weibull_cdf(300000, beta, eta) if (300000 > np.min(filtered_data)) and beta and eta else np.nan
        
        # Personalizar gráfico si se muestra
        if show_plot:
            plt.title(f'Análisis Weibull - {len(filtered_data)} fallas')
            plt.grid(True)
            plt.gcf().set_size_inches(8, 6)
        
        return beta, eta, media, probs, prob_mas_300k
    
    except Exception as e:
        print(f"Error en Weibull: {str(e)}")
        return None, None, None, [np.nan]*len(intervalos), np.nan

def generar_reporte(df, intervalos):
    """Genera el reporte final con formato profesional"""
    resultados = []
    
    for _, row in df.iterrows():
        beta, eta, media, probs, mas_300k = analizar_weibull(row['mtbf_values'], intervalos)
        
        # Cálculo de métricas básicas
        try:
            tasa_fallas = row['total_reclamos'] / row['vehiculos_unicos']
        except:
            tasa_fallas = 0
        
        try:
            costo_promedio = row['costo_total'] / row['total_reclamos']
        except:
            costo_promedio = np.nan
        
        # Lógica de alerta mejorada
        cond_volumen = (
            (row['total_reclamos'] >= MIN_RECLAMOS_SOSPECHOSO) and 
            ((row['total_reclamos'] > 100) or 
            (tasa_fallas > TAZA_FALLA_ALERTA and row['vehiculos_unicos'] >= MIN_VEHICULOS_SOSPECHOSO))
        )
        
        cond_weibull = (probs[0] > 0.25) if (probs and not np.isnan(probs[0])) else False
        sospechoso = cond_volumen or (cond_weibull and row['total_reclamos'] >= MIN_RECLAMOS_SOSPECHOSO)
        
        # Clasificación de patrones de falla
        if beta is None:
            patron = 'No calculado'
        elif beta < 1:
            patron = 'Falla infantil'
        elif 1 <= beta < 3:
            patron = 'Aleatorio'
        else:
            patron = 'Por desgaste'
        
        # Construir registro
        registro = {
            'Modelo': row['model'],
            'Componente': row['part_item_id'],
            'Total Reclamos': row['total_reclamos'],
            'Vehiculos Unicos': row['vehiculos_unicos'],
            'Costo Total': f"${row['costo_total']:,.2f}",
            'Costo Promedio': f"${costo_promedio:,.2f}" if not np.isnan(costo_promedio) else 'N/A',
            'MTBF Promedio': f"{np.mean(row['mtbf_values']):,.0f} km" if row['mtbf_values'] else 'N/A',
            'Sospechoso': 'SÍ' if sospechoso else 'NO',
            'Patron Fallas': patron,
            'Beta Weibull': f"{beta:.2f}" if beta else 'N/A',
            'Eta Weibull': f"{eta:,.0f} km" if eta else 'N/A',
            'Media Esperada': f"{media:,.0f} km" if media else 'N/A',
        }
        
        # Agregar probabilidades con formato
        for k, prob in zip(intervalos, probs):
            registro[f'Prob {int(k/1000)}k km'] = f"{prob:.1%}" if not np.isnan(prob) else 'N/A'
        registro['Prob >300k km'] = f"{mas_300k:.1%}" if not np.isnan(mas_300k) else 'N/A'
        
        resultados.append(registro)
    
    return pd.DataFrame(resultados)

def main():
    # Cargar y muestrear datos (10% aleatorio)
    df_raw = pd.read_csv(r"")
    df_raw = df_raw.sample(frac=0.1, random_state=42)  # Muestra del 10%
    
    df_limpio = preprocesar_datos(df_raw)
    df_metricas = calcular_metricas_agregadas(df_limpio)
    
    # Generar y formatear reporte
    reporte = generar_reporte(df_metricas, INTERVALOS_KM)
    columnas_orden = [
        'Modelo', 'Componente', 'Total Reclamos', 'Vehiculos Unicos',
        'Costo Total', 'Costo Promedio', 'MTBF Promedio', 'Sospechoso',
        'Patron Fallas', 'Beta Weibull', 'Eta Weibull', 'Media Esperada'
    ] + [f'Prob {int(k/1000)}k km' for k in INTERVALOS_KM] + ['Prob >300k km']
    
    # Guardar resultados
    reporte_final = reporte[columnas_orden]
    reporte_final['Componente_MOD'] = reporte_final['Componente'].str.replace(r'\*/|\*\$|\*S|\*O|\*|/|\.', '', regex=True)
    
    ruta_guardado = r""
    reporte_final.to_excel(ruta_guardado, index=False, engine='openpyxl')
    
    print("Reporte generado exitosamente en:", ruta_guardado)
    
    # Generar gráfico de ejemplo para el primer componente sospechoso
    if not reporte_final.empty:
        componentes_sospechosos = reporte_final[reporte_final['Sospechoso'] == 'SÍ']
        if not componentes_sospechosos.empty:
            # Tomar el primer componente sospechoso con parámetros Weibull válidos
            primer_sospechoso = componentes_sospechosos.iloc[0]
            modelo = primer_sospechoso['Modelo']
            componente = primer_sospechoso['Componente']
            
            # Obtener los datos originales
            datos_componente = df_metricas[
                (df_metricas['model'] == modelo) & 
                (df_metricas['part_item_id'] == componente)
            ]['mtbf_values'].iloc[0]
            
            # Generar gráfico
            print(f"\nGenerando gráfico para: Modelo {modelo} - Componente {componente}")
            analizar_weibull(datos_componente, INTERVALOS_KM, show_plot=True)
            plt.show()

if __name__ == "__main__":
    main()