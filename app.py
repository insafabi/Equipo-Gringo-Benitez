import streamlit as st
import requests
import json
import time

# Configuración de credenciales desde los secretos de Streamlit
ACCESS_TOKEN = st.secrets.get("WHATSAPP_TOKEN", "")
WHATSAPP_API_URL = "https://graph.facebook.com/v17.0"

st.subheader("Sistema de Envío Masivo (500 diarios / 250 por número)")

# Definir los dos IDs de los números de teléfono registrados en la WABA
phone_ids = [
    st.secrets.get("PHONE_ID_1", ""),  # Número principal
    st.secrets.get("PHONE_ID_2", "")   # Segundo número
]

# Validar que los IDs y el Token estén configurados
if not ACCESS_TOKEN or not phone_ids[0] or not phone_ids[1]:
    st.error("Por favor, configura tu WHATSAPP_TOKEN, PHONE_ID_1 y PHONE_ID_2 en los secretos de Streamlit.")
    st.stop()

# Inicializar contadores y el turno actual en el estado de la sesión
if 'conteo_envios' not in st.session_state:
    st.session_state.conteo_envios = {phone_ids[0]: 0, phone_ids[1]: 0}

if 'turno_actual' not in st.session_state:
    st.session_state.turno_actual = 0  # 0 para el primer número, 1 para el segundo

# Mostrar métricas actualizadas al límite de 250 por número
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Envíos Número 1", value=f"{st.session_state.conteo_envios[phone_ids[0]]} / 250")
with col2:
    st.metric(label="Envíos Número 2", value=f"{st.session_state.conteo_envios[phone_ids[1]]} / 250")

def enviar_mensaje_balanceado(telefono_destino, template_name, lang_code="es"):
    """
    Envía un mensaje alternando entre los dos números (Round-Robin)
    respetando el límite máximo de 250 mensajes por número.
    """
    activo_id = phone_ids[st.session_state.turno_actual]
    
    # Verificar si el número actual alcanzó su límite de 250
    if st.session_state.conteo_envios[activo_id] >= 250:
        otro_turno = 1 - st.session_state.turno_actual
        otro_id = phone_ids[otro_turno]
        if st.session_state.conteo_envios[otro_id] < 250:
            st.session_state.turno_actual = otro_turno
            activo_id = otro_id
        else:
            st.error("¡Se ha alcanzado el límite diario de 250 mensajes en ambos números (total 500)!")
            return False

    url = f"{WHATSAPP_API_URL}/{activo_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": str(telefono_destino).strip(),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": lang_code
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        
        if response.status_code == 200:
            # Incrementar el contador del número que hizo el envío exitoso
            st.session_state.conteo_envios[activo_id] += 1
            # Rotar el turno para la siguiente iteración
            st.session_state.turno_actual = 1 - st.session_state.turno_actual
            return True
        else:
            st.error(f"Error de API con el número {activo_id}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión al intentar enviar a {telefono_destino}: {e}")
        return False

# Sección de control para ejecución masiva
nombre_template = st.text_input("Nombre de la plantilla aprobada (Utility):", value="")
lista_destinatarios = st.text_area("Lista de teléfonos (uno por línea, ej: 5959XXXXXXXX):")

if st.button("Iniciar Envío Masivo Balanceado (Hasta 500)"):
    if not nombre_template:
        st.warning("Debes ingresar el nombre de la plantilla de WhatsApp.")
    elif not lista_destinatarios:
        st.warning("La lista de destinatarios está vacía.")
    else:
        telefonos = [t.strip() for t in lista_destinatarios.split("\n") if t.strip()]
        total_enviados = 0
        
        barra_progreso = st.progress(0)
        total_contactos = len(telefonos)
        
        for i, tel in enumerate(telefonos):
            # Validar si ya se llegó al tope máximo global (500)
            if sum(st.session_state.conteo_envios.values()) >= 500:
                st.warning("Se ha alcanzado el límite máximo combinado de 500 mensajes diarios.")
                break
                
            exito = enviar_mensaje_balanceado(tel, nombre_template)
            if exito:
                total_enviados += 1
                
            # Actualizar barra de progreso
            barra_progreso.progress((i + 1) / total_contactos)
            
            # Pausa de seguridad para evitar restricciones de la API
            time.sleep(0.5)
            
        st.success(f"Proceso finalizado. Mensajes enviados exitosamente: {total_enviados}")
