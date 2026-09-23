import time
import random
import json
import urllib.request
import urllib.error
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
token_raw = st.sidebar.text_input("Token de Acceso Permanente", type="password")
phone_raw = st.sidebar.text_input("Phone Number ID")
template_raw = st.sidebar.text_input("Nombre de la Plantilla", value="")

# Limpiar automáticamente credenciales de cualquier emoji o caracter invisible pegado por error
def limpiar_ascii(texto):
    if not texto:
        return ""
    return "".join(c for c in str(texto) if ord(c) < 128).strip()

token = limpiar_ascii(token_raw)
phone_number_id = limpiar_ascii(phone_raw)
template_name = limpiar_ascii(template_raw)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Controles de Envío")

max_msgs = st.sidebar.slider(
    "Cantidad de mensajes a enviar",
    min_value=1,
    max_value=500,
    value=1,
    step=1,
    help="Úsalo en 1 para hacer tu prueba de fuego con tu número.",
)

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
    " **local**, **apellido**, **nombre**, **mesa**, **orden**, **celular**."
)

uploaded_file = st.file_uploader(
    "Sube tu archivo aquí",
    type=["xlsx", "csv"],
)

if uploaded_file is not None:
  try:
    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file, encoding="utf-8", errors="ignore")
    else:
      df = pd.read_excel(uploaded_file)

    # Limpiar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    columnas_map = {str(col).strip().lower(): col for col in df.columns}

    requeridas = ["nombre", "celular", "local", "mesa", "orden"]
    faltantes = [req for req in requeridas if req not in columnas_map]

    if faltantes:
      st.error(
          f"❌ El archivo no tiene las columnas obligatorias. Faltan: {faltantes}"
          ". Por favor, verifica los encabezados en tu Excel."
      )
    else:
      col_nombre = columnas_map["nombre"]
      col_celular = columnas_map["celular"]
      col_local = columnas_map["local"]
      col_mesa = columnas_map["mesa"]
      col_orden = columnas_map["orden"]

      st.success(
          f"✅ Archivo cargado correctamente. Total de registros en archivo:"
          f" {len(df)}"
      )

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
              " lateral (Token, Phone ID y Plantilla) sin dejar espacios ni símbolos extraños."
          )
        else:
          barra_progreso = st.progress(0)
          status_text = st.empty()
          total = len(df_procesar)
          exitosos = 0
          fallidos = 0

          log_container = st.container()

          url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"

          for index, row in df_procesar.iterrows():
            def limpiar_texto(valor):
              if pd.isna(valor):
                return ""
              return str(valor).strip()

            nombre = limpiar_texto(row[col_nombre])
            
            celular_raw = str(row[col_celular]).strip()
            celular = (
                celular_raw.split(".")[0]
                .replace(" ", "")
                .replace("-", "")
                .replace("+", "")
            )

            local_votacion = limpiar_texto(row[col_local])
            mesa_votacion = limpiar_texto(row[col_mesa])
            orden_votacion = limpiar_texto(row[col_orden])

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
              data_json = json.dumps(payload).encode("utf-8")
              
              req = urllib.request.Request(url, data=data_json, method="POST")
              req.add_header("Authorization", f"Bearer {token}")
              req.add_header("Content-Type", "application/json; charset=utf-8")

              with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                  exitosos += 1
                  with log_container:
                    st.success(f"✅ Enviado a {nombre} ({celular})")
                else:
                  fallidos += 1
                  with log_container:
                    st.error(
                        f"❌ Error con {nombre} ({celular}): código {response.status}"
                    )
            except urllib.error.HTTPError as e:
              fallidos += 1
              error_body = e.read().decode("utf-8", errors="ignore")
              with log_container:
                st.error(
                    f"❌ Error HTTP de Meta con {nombre} ({celular}): {error_body}"
                )
            except Exception as e:
              fallidos += 1
              with log_container:
                st.error(
                    f"⚠️ Excepción de red con {nombre} ({celular}): {str(e)}"
                )

            porcentaje = int(((index + 1) / total) * 100)
            barra_progreso.progress(porcentaje)
            status_text.text(
                f"Procesando {index + 1} de {total} (Éxitos: {exitosos} |"
                f" Fallidos: {fallidos})"
            )

            if index < total - 1:
              tiempo_pausa = random.randint(pausa_min, pausa_max)
              time.sleep(tiempo_pausa)

          st.balloons()
          st.success(
              f"🎉 ¡Proceso finalizado! Total exitosos: {exitosos} | Total"
              f" fallidos: {fallidos}"
          )

  except Exception as e:
    st.error(
        f"❌ Ocurrió un error al leer el archivo. Detalle: {str(e)}"
    )
