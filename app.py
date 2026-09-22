import random
import time
import pandas as pd
import requests
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Connecta Py - Campaña Masiva Segura", layout="wide"
)

st.title("🚀 Connecta Py: Sistema de Envío Masivo Seguro (Meta API)")
st.markdown(
    "Herramienta optimizada para envíos controlados de WhatsApp con"
    " protecciones anti-spam, filtrado automático y gestión por lotes."
)

# Sidebar para Credenciales y Configuración de Seguridad
with st.sidebar:
  st.header("🔑 Credenciales de Meta")
  access_token = st.text_input(
      "Permanent Access Token", type="password", help="Tu token de sistema."
  )
  phone_number_id = st.text_input(
      "Phone Number ID",
      value="1348015601728218",
      help="ID numérico de tu teléfono.",
  )
  template_name = st.text_input(
      "Nombre de la Plantilla",
      value="aviso_general",
      help="Plantilla aprobada por Meta.",
  )

  st.header("🛡️ Parámetros Anti-Spam y Lotes")
  lote_size = st.slider(
      "Tamaño de cada lote",
      min_value=50,
      max_value=500,
      value=100,
      step=50,
      help="Cantidad de mensajes por tanda.",
  )
  delay_min = st.slider(
      "Retraso mínimo (segundos)",
      min_value=1.0,
      max_value=5.0,
      value=2.0,
      step=0.5,
  )
  delay_max = st.slider(
      "Retraso máximo (segundos)",
      min_value=3.0,
      max_value=10.0,
      value=5.0,
      step=0.5,
  )

# Área principal para cargar archivo Excel
st.header("📂 Carga de Base de Datos (Excel)")
uploaded_file = st.file_uploader(
    "Sube tu archivo con la columna de teléfonos y variables",
    type=["xlsx", "xls"],
)

if uploaded_file is not None:
  df = pd.read_excel(uploaded_file)
  st.success(f"Archivo cargado correctamente. Total de registros: {len(df)}")

  st.write("Vista previa de los datos:")
  st.dataframe(df.head())

  # Selección de la columna de teléfonos
  columnas = df.columns.tolist()
  tel_col = st.selectbox(
      "Selecciona la columna que contiene los números de teléfono:", columnas
  )

  if st.button("🚀 Iniciar Campaña Protegida"):
    if not access_token:
      st.error("Por favor, ingresa tu Access Token en la barra lateral.")
    else:
      url = (
          f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
      )
      headers = {
          "Authorization": f"Bearer {access_token}",
          "Content-Type": "application/json",
      }

      total_contactos = len(df)
      progress_bar = st.progress(0)
      status_text = st.empty()
      log_area = st.empty()

      logs = []
      enviados_exitosos = 0
      fallidos = 0
      omitidos = 0

      # Ciclo principal segmentado por lotes automáticos
      for i in range(0, total_contactos, lote_size):
        lote = df.iloc[i : i + lote_size]
        lote_num = (i // lote_size) + 1
        total_lotes = (total_contactos + lote_size - 1) // lote_size

        status_text.markdown(
            f"### ⚙️ Procesando Lote {lote_num} de {total_lotes} (Contactos"
            f" {i+1} al {min(i+lote_size, total_contactos)})"
        )

        for index, row in lote.iterrows():
          telefono_raw = str(row[tel_col]).strip()
          # Limpiar caracteres dejando solo dígitos numéricos
          telefono = "".join(filter(str.isdigit, telefono_raw))

          # 🚫 FILTRO DE SEGURIDAD ESTRICTO: Omitir vacíos, cortos o patrones de prueba (ej: 5950000...)
          if (
              not telefono
              or telefono.startswith("5950000")
              or len(telefono) < 8
          ):
            omitidos += 1
            logs.append(
                f"⚠️ [Omitido por seguridad] Número inválido o de prueba"
                f" detectado: {telefono_raw}"
            )
            continue  # Salta automáticamente este registro sin gastar peticiones

          payload = {
              "messaging_product": "whatsapp",
              "to": telefono,
              "type": "template",
              "template": {
                  "name": template_name,
                  "language": {"code": "es"},
              },
          }

          # Control de reintentos ante limitaciones de velocidad de Meta (Rate Limit / Error 429)
          intentos = 0
          exito = False
          while intentos < 3 and not exito:
            try:
              response = requests.post(url, headers=headers, json=payload)
              if response.status_code == 200:
                enviados_exitosos += 1
                logs.append(
                    f"✅ [Éxito] Mensaje enviado a: {telefono} (Lote"
                    f" {lote_num})"
                )
                exito = True
              elif response.status_code == 429:
                intentos += 1
                logs.append(
                    f"⚠️ [Rate Limit] Saturación detectada en {telefono}."
                    f" Pausa e intento {intentos}/3..."
                )
                time.sleep(15 * intentos)
              else:
                fallidos += 1
                logs.append(
                    f"❌ [Error {response.status_code}] Fallo en {telefono}:"
                    f" {response.text}"
                )
                break
            except Exception as e:
              fallidos += 1
              logs.append(f"❌ [Excepción de red] Error con {telefono}: {e}")
              break

          # Actualizar log visual en tiempo real
          log_area.text("\n".join(logs[-10:]))

          # Retraso dinámico aleatorio (Jitter) para imitar comportamiento orgánico
          pausa_actual = random.uniform(delay_min, delay_max)
          time.sleep(pausa_actual)

        # Actualizar barra de progreso global del envío
        progress_bar.progress(
            min((i + lote_size) / total_contactos, 1.0)
        )

        # Pausa estratégica de descanso entre lotes para cuidar la reputación del número en Meta
        if (i + lote_size) < total_contactos:
          status_text.markdown(
              f"☕ Lote {lote_num} completado. Pausa de descanso de 30 segundos"
              " antes del siguiente bloque..."
          )
          time.sleep(30)

      st.success(
          "🎉 ¡Campaña finalizada exitosamente! Resumen: Enviados:"
          f" {enviados_exitosos} | Omitidos por filtro: {omitidos} | Fallidos:"
          f" {fallidos}"
      )
