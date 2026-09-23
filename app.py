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
    " plantilla aprobada."
)

# --- BARRA LATERAL: CREDENCIALES ---
st.sidebar.header("Credenciales de la API")
token = st.sidebar.text_input("Token de Acceso Permanente", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")
template_name = st.sidebar.text_input(
    "Nombre de la Plantilla",
    value="aviso_general",
    help="Debe coincidir exactamente con el de Meta",
)

# --- CUERPO PRINCIPAL ---
st.subheader("1. Carga de Base de Datos")
archivo_subido = st.file_uploader(
    "Sube tu archivo Excel con la estructura de columnas NOMBRE y celular",
    type=["xlsx", "csv"],
)

if archivo_subido is not None:
  if archivo_subido.name.endswith(".csv"):
    df = pd.read_csv(archivo_subido)
  else:
    df = pd.read_excel(archivo_subido)

  st.success(f"¡Archivo cargado con éxito! Total de registros: {len(df)}")

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

  if st.button("🚀 Iniciar Envío Masivo por API"):
    if not token or not phone_number_id:
      st.error(
          "⚠️ Por favor, ingresa tu Token de Meta y tu Phone Number ID en la"
          " barra lateral."
      )
    else:
      url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
      headers = {
          "Authorization": f"Bearer {token}",
          "Content-Type": "application/json",
      }

      progress_bar = st.progress(0)
      status_text = st.empty()
      log_area = st.container()

      enviados_exitosos = 0
      df_subset = df.head(limite_mensajes)
      total = len(df_subset)

      for i, row in df_subset.iterrows():
        raw_tel = str(row["celular"]).strip()
        if raw_tel.endswith(".0"):
          raw_tel = raw_tel[:-2]
        if not raw_tel.startswith("+"):
          telefono = "+" + raw_tel
        else:
          telefono = raw_tel

        nombre_raw = str(row["NOMBRE"]).strip()
        if not nombre_raw or nombre_raw.lower() == "nan":
          nombre = "Vecino/a"
        else:
          nombre = nombre_raw.title()

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
                        "parameters": [{"type": "text", "text": nombre}],
                    }
                ],
            },
        }

        try:
          response = requests.post(url, headers=headers, json=payload)

          if response.status_code == 200:
            enviados_exitosos += 1
            status_text.text(
                f"Procesando [{i + 1}/{total}] - Enviado a {nombre} ({telefono})"
            )
          else:
            with log_area:
              st.warning(
                  f"Error al enviar a {telefono} ({nombre}):"
                  f" {response.text}"
              )

        except Exception as e:
          with log_area:
            st.error(f"Excepción de red con {telefono}: {e}")

        progress_bar.progress((i + 1) / total)
        time.sleep(2)

      st.balloons()
      st.success(
          f"✨ ¡Lote finalizado! Se procesaron y enviaron"
          f" {enviados_exitosos} de {total} mensajes correctamente."
      )
