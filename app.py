import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas Personales", page_icon="💰", layout="wide")

# --- ESTILOS CSS PERSONALIZADOS (Para que se vea "Chuzo") ---
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
    }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #41444C;
    }
    h1, h2, h3 {
        color: #FAFAFA;
    }
    </style>
    """, unsafe_allow_html=True)


# --- CONEXIÓN A GOOGLE SHEETS (CON CACHÉ PARA RAPIDEZ) ---
@st.cache_data(ttl=60)  # Actualiza los datos cada 60 segundos
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Finanzas_Bot_DB").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Limpieza de datos
    if not df.empty:
        # Convertir montos a números
        df['monto'] = pd.to_numeric(df['monto'])
        # Convertir fecha a datetime
        df['fecha'] = pd.to_datetime(df['fecha'])
        # Crear columna de Mes y Año para filtros
        df['mes'] = df['fecha'].dt.month_name()
        df['año'] = df['fecha'].dt.year
        df['mes_num'] = df['fecha'].dt.month  # Para ordenar
    return df


try:
    df = load_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# --- SIDEBAR (FILTROS) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2344/2344132.png", width=100)
st.sidebar.header("Filtros")

if not df.empty:
    # Filtro Año
    años_disponibles = sorted(df['año'].unique(), reverse=True)
    año_sel = st.sidebar.selectbox("Año", años_disponibles)

    # Filtro Mes
    meses_disponibles = df[df['año'] == año_sel].sort_values('mes_num')['mes'].unique()
    mes_sel = st.sidebar.selectbox("Mes", meses_disponibles,
                                   index=len(meses_disponibles) - 1)  # Selecciona el último por defecto

    # Filtrar el DataFrame
    df_filtrado = df[(df['año'] == año_sel) & (df['mes'] == mes_sel)]
else:
    st.warning("Ainda no hay datos. ¡Usa el bot para registrar algo!")
    st.stop()

# --- CÁLCULOS PRINCIPALES ---
ingresos = df_filtrado[df_filtrado['tipo'] == 'Ingreso']['monto'].sum()
gastos = df_filtrado[df_filtrado['tipo'] == 'Gasto']['monto'].sum()  # Viene negativo
gastos_abs = abs(gastos)
balance = ingresos + gastos  # Como gastos es negativo, se resta solo
tasa_ahorro = (balance / ingresos * 100) if ingresos > 0 else 0

# Gastos Hormiga
hormiga = df_filtrado[df_filtrado['es_hormiga'] == 'TRUE'][
    'monto'].sum()  # Ojo: gspread a veces trae booleanos como string 'TRUE'
hormiga_abs = abs(hormiga)

# --- INTERFAZ PRINCIPAL ---

st.title(f"Dashboard Financiero - {mes_sel} {año_sel}")

# 1. FILA DE KPIs (Métricas grandes)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ingresos", f"₡{ingresos:,.0f}")
col2.metric("Gastos Totales", f"₡{gastos_abs:,.0f}", delta=f"{balance:,.0f} Balance")
col3.metric("Tasa de Ahorro", f"{tasa_ahorro:.1f}%", delta_color="normal")
col4.metric("Gastos Hormiga 🐜", f"₡{hormiga_abs:,.0f}", delta_color="inverse")

st.markdown("---")

# 2. GRÁFICOS PRINCIPALES
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Gasto por Categoría")
    # Agrupar gastos por categoría
    gastos_cat = df_filtrado[df_filtrado['tipo'] == 'Gasto'].groupby('categoria')['monto'].sum().abs().reset_index()

    if not gastos_cat.empty:
        fig_bar = px.bar(gastos_cat, x='categoria', y='monto', color='categoria',
                         text_auto='.2s', template="plotly_dark",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_bar.update_layout(showlegend=False, margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No hay gastos registrados este mes.")

with c2:
    st.subheader("Distribución")
    if not gastos_cat.empty:
        fig_pie = px.pie(gastos_cat, values='monto', names='categoria', hole=0.4, template="plotly_dark")
        fig_pie.update_layout(margin=dict(t=0, l=0, r=0, b=0), showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

# 3. TABLA DE DETALLE (Últimos movimientos)
st.subheader("📝 Últimos Movimientos")
# Mostrar tabla bonita
st.dataframe(
    df_filtrado[['fecha', 'concepto', 'categoria', 'monto', 'es_hormiga']].sort_values('fecha', ascending=False),
    use_container_width=True,
    hide_index=True
)