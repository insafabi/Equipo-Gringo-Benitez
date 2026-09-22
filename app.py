import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Connecta Py - Campaña WhatsApp", layout="centered"
)

st.title("🚀 Connecta Py - Automatización de Campaña")
st.markdown(
    "Envía mensajes masivos personalizados utilizando la API oficial de WhatsApp"
    " y una plantilla aprobada."
)

# Sección de Credenciales
st.sidebar.header("🔑 Credenciales de Meta")
access_token = st.sidebar.text_input("Access Token Permanente", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")
template_name = st.sidebar.text_input(
    "Nombre de la Plantilla", value="aviso_general"
)

# Sección de Carga de Datos
st.header("1. Carga tu base de datos de contactos")
uploaded_file = st.file_uploader(
    "Sube tu archivo de Excel (.xlsx)", type=["xlsx", "xls"]
)

if uploaded_file is not None:
  # Leer el Excel
  df = pd.read_excel(uploaded_file)
  st.success(
      f"¡Archivo cargado con éxito! Se encontraron {len(df)} registros."
  )

  with st.expander("Ver vista previa de los datos"):
    st.dataframe(df.head())

  st.header("2. Mapeo de Variables de la Plantilla")
  st.info(
      "Asocia cada columna de tu Excel con la variable correspondiente de la"
      " plantilla (`{{1}}` a `{{4}}`)."
  )

  columns = df.columns.tolist()

  col1, col2 = st.columns(2)
  with col1:
    phone_col = st.selectbox(
        "Columna de Teléfono (Ej: 595981...)", options=columns
    )
    var1_col = st.selectbox(
        "Variable 1 ({{1}} - Nombre)", options=columns
    )
    var2_col = st.selectbox(
        "Variable 2 ({{2}} - Local de Votación)", options=columns
    )
  with col2:
    var3_col = st.selectbox("Variable 3 ({{3}} - Mesa)", options=columns)
    var4_col = st.selectbox("Variable 4 ({{4}} - Orden)", options=columns)

  st.header("3. Ejecutar Campaña")
  if st.button("🚀 Iniciar Envío Masivo", type="primary"):
    if not access_token or not phone_number_id:
      st.error(
          "Por favor, completa el Access Token y el Phone Number ID en la"
          " barra lateral."
      )
    else:
      progress_bar = st.progress(0)
      status_text = st.empty()
      success_count = 0
      error_count = 0

      total_rows = len(df)
      url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"

      headers = {
          "Authorization": f"Bearer {access_token}",
          "Content-Type": "application/json",
      }

      for index, row in df.iterrows():
        phone = str(row[phone_col]).strip()
        v1 = str(row[var1_col])
        v2 = str(row[var2_col])
        v3 = str(row[var3_col])
        v4 = str(row[var4_col])

        # Estructura del payload para la API de Meta con 4 variables
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "es"},  # Cambiar si tu plantilla es 'es_PY'
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": v1},
                            {"type": "text", "text": v2},
                            {"type": "text", "text": v3},
                            {"type": "text", "text": v4},
                        ],
                    }
                ],
            },
        }

        try:
          response = requests.post(url, json=payload, headers=headers)
          if response.status_code == 200:
            success_count += 1
          else:
            error_count += 1
        except Exception as e:
          error_count += 1

        # Actualizar barra de progreso
        progress_bar.progress((index + 1) / total_rows)
        status_text.text(
            f"Procesando {index + 1} de {total_rows} (Éxitos: {success_count},"
            f" Errores: {error_count})"
        )

      st.success("¡Campaña de mensajes finalizada!")
      st.balloons()
      st.metric("Mensajes enviados con éxito", success_count)
      if error_count > 0:
        st.warning(
            f"Hubo {error_count} mensajes que no pudieron enviarse. Revisa los"
            " números o formatos."
        )
