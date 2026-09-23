import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Campaña Gringo Benítez - Meta API", page_icon="🗳️", layout="centered"
)

st.title("🗳️ Panel de Envío Masivo - Meta Cloud API")
st.write(
    "Automatización conectada directamente con tu padrón de votantes y la"
    " plantilla aprobada de forma segura."
)

# --- BARRA LATERAL: CREDENCIALES ---
st.sidebar.header("Credenciales de la API")
token = st.sidebar.text_input("Token de Acceso Permanente", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")
template_name = st.sidebar.text_input(
    "Nombre de la Plantilla",
    value="aviso_general",
    help="Debe coincidir exactamente con el registrado en Meta",
)

# --- CUERPO PRINCIPAL ---
st.subheader("1. Carga de Base de Datos")
archivo_subido = st.file_uploader(
    "Sube tu archivo Excel o CSV con las columnas: NOMBRE y celular",
    type=["xlsx", "csv"],
)

if archivo_subido is not None:
  try:
    # Leer el archivo según su extensión
    if archivo_subido.name.endswith(".csv"):
      df = pd.read_csv(archivo_subido)
    else:
      df = pd.read_excel(archivo_subido)

    # Validar que las columnas obligatorias existan
    columnas_requeridas = ["NOMBRE", "celular"]
    columnas_faltantes = [
        col for col in columnas_requeridas if col not in df.columns
    ]

    if columnas_faltantes:
      st.error(
          "⚠️ El archivo no tiene la estructura correcta. Faltan las siguientes"
          f" columnas obligatorias: {columnas_faltantes}. Por favor, verifica"
          " tu Excel."
      )
    else:
      st.success(
          f"¡Archivo cargado con éxito! Total de registros encontrados:"
          f" {len(df)}"
      )

      # Vista previa validando las columnas exactas
      with st.expander("Ver vista previa de los datos a enviar"):
        st.dataframe(df[["NOMBRE", "celular"]].head(5))

      st.subheader("2. Configuración de la Ráfaga")
      limite_defecto = min(150, len(df))
      limite_mensajes = st.slider(
          "Cantidad máxima de mensajes a enviar en este lote",
          min_value=1,
          max_value=len(df),
          value=limite_defecto,
      )

      st.info(
          f"Se enviarán mensajes de manera automatizada a los primeros"
          f" **{limite_mensajes}** votantes de la lista."
      )

      # Botón de ejecución
      if st.button("🚀 Iniciar Envío Masivo por API"):
        if not token or not phone_number_id:
          st.error(
              "⚠️ Por favor, ingresa tu Token de Meta y tu Phone Number ID en la"
              " barra lateral antes de continuar."
          )
        else:
          url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
          headers = {
              "Authorization": f"Bearer {token}",
              "Content-Type": "application/json",
          }

          progress_bar = st.progress(0)
          status_text = st.empty()
          log_expander = st.expander(
              "Registro detallado de envíos y posibles errores", expanded=True
          )

          enviados_exitosos = 0
          enviados_fallidos = 0
          df_subset = df.head(limite_mensajes)
          total = len(df_subset)

          with log_expander:
            for i, row in df_subset.iterrows():
              # Limpieza profunda del número de celular (quita espacios, guiones, decimales .0)
              raw_tel = (
                  str(row["celular"])
                  .strip()
                  .replace(" ", "")
                  .replace("-", "")
              )
              if raw_tel.endswith(".0"):
                raw_tel = raw_tel[:-2]
              if not raw_tel.startswith("+"):
                telefono = "+" + raw_tel
              else:
                telefono = raw_tel

              # Extraer y formatear el nombre
              nombre_raw = str(row["NOMBRE"]).strip()
              if not nombre_raw or nombre_raw.lower() == "nan":
                nombre = "Vecino/a"
              else:
                nombre = nombre_raw.title()

              # Payload oficial de la API de Meta
              payload = {
                  "messaging_product": "whatsapp",
                  "recipient_type": "individual",
                  "to": telefono,
                  "type": "template",
                  "template": {
                      "name": template_name,
                      "language": {"code": "es"},
                      "components": [
                          {
                              "type": "body",
                              "parameters": [
                                  {
                                      "type": "text",
                                      "text": (
                                          nombre
                                      ),  # Rellena el parámetro {{1}}
                                  }
                              ],
                          }
                      ],
                  },
              }

              try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=10
                )

                if response.status_code == 200:
                  enviados_exitosos += 1
                  status_text.text(
                      f"Procesando [{i + 1}/{total}] - Enviado con éxito a"
                      f" {nombre} ({telefono})"
                  )
                else:
                  enviados_fallidos += 1
                  st.warning(
                      f"❌ Error al enviar a {telefono} ({nombre}) | Código"
                      f" {response.status_code}: {response.text}"
                  )

              except requests.exceptions.RequestException as e:
                enviados_fallidos += 1
                st.error(f"🌐 Error de red/conexión con {telefono}: {e}")

              progress_bar.progress((i + 1) / total)
              time.sleep(
                  2
              )  # Pausa de seguridad de 2 segundos para evitar saturar la API

          st.balloons()
          st.success(
              f"✨ ¡Lote finalizado! Exitosos: {enviados_exitosos} | Fallidos:"
              f" {enviados_fallidos} de un total de {total} procesados."
          )

  except Exception as e:
    st.error(
        "❌ Ocurrió un error al leer el archivo. Asegúrate de que sea un Excel"
        f" (.xlsx) o CSV válido. Detalle: {e}"
    )
