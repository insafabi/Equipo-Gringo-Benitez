import requests
import streamlit as st

st.set_page_config(
    page_title="Connecta Py - WhatsApp API", page_icon="💬", layout="centered"
)

st.title("💬 Connecta Py - Automatización WhatsApp")
st.markdown("Panel de pruebas e integración con Meta Cloud API.")

# Configuración de credenciales fijas de la app
PHONE_NUMBER_ID = "1240549692484084"

# Interfaz visual en Streamlit
st.sidebar.header("Credenciales y Configuración")
access_token = st.sidebar.text_input(
    "Token de Acceso de Meta", type="password"
)

st.subheader("Enviar Mensaje de Texto")

# Entrada para el número de destino (ej: 595992021341)
recipient_phone = st.text_input(
    "Número de destino (con código de país, sin '+' ej: 595992021341)",
    value="595992021341",
)

message_body = st.text_area(
    "Mensaje",
    value=(
        "¡Hola! Este es un mensaje automatizado de prueba desde Connecta"
        " Py 🚀"
    ),
)

if st.button("Enviar Mensaje a través de WhatsApp", type="primary"):
  if not access_token:
    st.error("Por favor ingresa tu Token de Acceso en la barra lateral.")
  elif not recipient_phone:
    st.error("Por favor ingresa un número de destino.")
  else:
    # Endpoint oficial de Meta Graph API (v21.0)
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone.strip(),
        "type": "text",
        "text": {"preview_url": False, "body": message_body},
    }

    with st.spinner("Enviando mensaje a través de la API..."):
      try:
        response = requests.post(url, json=payload, headers=headers)
        res_data = response.json()

        if response.status_code == 200:
          st.success("¡Mensaje enviado con éxito!")
          st.json(res_data)
        else:
          st.error(f"Error en el envío (Código {response.status_code})")
          st.json(res_data)
      except Exception as e:
        st.error(f"Ocurrió un error de conexión: {e}")
