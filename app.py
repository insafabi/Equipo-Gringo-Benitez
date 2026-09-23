import time
import random
import requests
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Panel de Envío Masivo - Meta Cloud API",
    page_icon="📱",
    layout="wide",
)

# --- BARRA LATERAL: CREDENCIALES Y CONTROLES ---
st.sidebar.header("🔑 Credenciales de la API")
token = st.sidebar.text_input("Token de Acceso Permanente", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")
template_name = st.sidebar.text_input("Nombre de la Plantilla", value="")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Controles de Envío")

# Deslizador de cantidad de mensajes
max_msgs = st.sidebar.slider(
    "Cantidad de mensajes a enviar",
    min_value=1,
    max_value=500,
    value=1,
    step=1,
    help="Úsalo en 1 para hacer tu prueba de fuego con tu número.",
)

# Deslizadores de pausa (Mínimo y Máximo)
pausa_min = st.sidebar.slider(
    "Pausa Mínima entre mensajes (segundos)",
    min_value=1,
    max_value=30,
    value=3,
    step=1,
)
pausa_max = st.sidebar.slider(
    "Pausa Máxima entre mensajes (segundos)",
    min_value=pausa_min,
    max_value=60,
    value=7,
    step=1,
)


# --- CUERPO PRINCIPAL ---
st.title("📩 Panel de Envío Masivo - Meta Cloud API")
st.markdown(
    "Automatización conectada directamente con tu padrón y la plantilla aprobada de forma segura."
)

st.markdown("### 1. Carga de Base de Datos")
st.markdown(
    "Tu archivo Excel o CSV debe contener obligatoriamente las columnas:"
    " **NOMBRE**, **celular**, **local**, **mesa**, **orden** (sin importar"
    " mayúsculas o minúsculas)."
)

uploaded_file = st.file_uploader(
    "Sube tu archivo aquí",
    type=["xlsx", "csv"],
)

if uploaded_file is not None:
  try:
    # Leer el archivo según su extensión
    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file)
    else:
      df = pd.read_excel(uploaded_file)

    # Crear un diccionario para mapear los nombres reales de las columnas en minúsculas sin espacios
    columnas_map = {str(col).strip().lower(): col for col in df.columns}

    # Definir las columnas requeridas que el sistema necesita buscar
    requeridas = ["nombre", "celular", "local", "mesa", "orden"]
    faltantes = [req for req in requeridas if req not in columnas_map]

    if faltantes:
      st.error(
          f"❌ El archivo no tiene las columnas obligatorias. Faltan: {faltantes}"
          ". Por favor, verifica los encabezados en tu Excel."
      )
    else:
      # Extraer los nombres reales de las columnas del DataFrame usando el mapa flexible
      col_nombre = columnas_map["nombre"]
      col_celular = columnas_map["celular"]
      col_local = columnas_map["local"]
      col_mesa = columnas_map["mesa"]
      col_orden = columnas_map["orden"]

      st.success(
          f"✅ Archivo cargado correctamente. Total de registros en archivo:"
          f" {len(df)}"
      )

      # Mostrar vista previa limitada a lo que el usuario configuró en el slider
      df_procesar = df.head(max_msgs)
      st.info(
          f"ℹ️ Se procesarán los primeros **{len(df_procesar)}** registros según"
          " el control de cantidad seleccionado."
      )
      st.dataframe(df_procesar.head(10))

      st.markdown("### 2. Ejecución de Envíos")
      if st.button("🚀 Iniciar Envío Masivo"):
        if not token or not phone_number_id or not template_name:
          st.warning(
              "⚠️ Por favor, completa todas las credenciales en la barra"
              " lateral (Token, Phone ID y Plantilla)."
          )
        else:
          barra_progreso = st.progress(0)
          status_text = st.empty()
          total = len(df_procesar)
          exitosos = 0
          fallidos = 0

          # Contenedor para el registro de resultados en tiempo real
          log_container = st.container()

          headers = {
              "Authorization": f"Bearer {token}",
              "Content-Type": "application/json",
          }
          # Actualizado a la versión v20.0 para garantizar compatibilidad y evitar rechazos de autorización
          url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"

          for index, row in df_procesar.iterrows():
            nombre = str(row[col_nombre]).strip()
            
            # Limpiar número de celular (quita decimales .0 de excel, espacios y guiones)
            celular_raw = str(row[col_celular]).strip()
            celular = (
                celular_raw.split(".")[0]
                .replace(" ", "")
                .replace("-", "")
                .replace("+", "")
            )

            # Capturar los datos del padrón electoral utilizando las columnas detectadas dinámicamente
            local_votacion = str(row[col_local]).strip()
            mesa_votacion = str(row[col_mesa]).strip()
            orden_votacion = str(row[col_orden]).strip()

            # Estructura del payload con los 4 parámetros ordenados para la plantilla de Meta:
            # {{1}} = Nombre | {{2}} = Local | {{3}} = Mesa | {{4}} = Orden
            payload = {
                "messaging_product": "whatsapp",
                "to": celular,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "es"},
                    "components": [{
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": nombre},
                            {"type": "text", "text": local_votacion},
                            {"type": "text", "text": mesa_votacion},
                            {"type": "text", "text": orden_votacion},
                        ],
                    }],
                },
            }

            try:
              response = requests.post(
                  url, json=payload, headers=headers, timeout=10
              )
              if response.status_code == 200:
                exitosos += 1
                with log_container:
                  st.success(f"✅ Enviado a {nombre} ({celular})")
              else:
                fallidos += 1
                with log_container:
                  st.error(
                      f"❌ Error con {nombre} ({celular}):"
                      f" {response.text}"
                  )
            except Exception as e:
              fallidos += 1
              with log_container:
                st.error(
                    f"⚠️ Excepción de red/sistema con {nombre} ({celular}): {e}"
                )

            # Actualizar barra de progreso
            porcentaje = int(((index + 1) / total) * 100)
            barra_progreso.progress(porcentaje)
            status_text.text(
                f"Procesando {index + 1} de {total} (Éxitos: {exitosos} |"
                f" Fallidos: {fallidos})"
            )

            # Pausa aleatoria configurable entre mínimo y máximo para proteger la cuenta
            if index < total - 1:  # No pausar después del último mensaje
              tiempo_pausa = random.randint(pausa_min, pausa_max)
              time.sleep(tiempo_pausa)

          st.balloons()
          st.success(
              f"🎉 ¡Proceso finalizado! Total exitosos: {exitosos} | Total"
              f" fallidos: {fallidos}"
          )

  except Exception as e:
    st.error(
        f"❌ Ocurrió un error al leer el archivo. Verifica que sea un Excel o"
        f" CSV válido. Detalle: {e}"
    )
