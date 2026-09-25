import time
import random
import json
import urllib.request
import urllib.error
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Panel de Envío Masivo - Meta Cloud API (Balanceado)",
    page_icon="📱",
    layout="wide",
)

# --- BARRA LATERAL: CREDENCIALES Y CONTROLES ---
st.sidebar.header("🔑 Credenciales de la API")
token_raw = st.sidebar.text_input("Token de Acceso Permanente", type="password")

# Dos campos para los números de teléfono (Round-Robin)
phone1_raw = st.sidebar.text_input("Phone Number ID 1 (Principal)")
phone2_raw = st.sidebar.text_input("Phone Number ID 2 (Secundario)")

template_raw = st.sidebar.text_input("Nombre de la Plantilla", value="")

# Función ultra estricta para limpiar caracteres extraños
def limpiar_estricto(texto):
    if not texto or pd.isna(texto):
        return ""
    return "".join(c for c in str(texto) if ord(c) < 128 and (c.isalnum() or c.isspace() or c in "áéíóúÁÉÍÓÚñÑ.,-_")).strip()

token = limpiar_estricto(token_raw)
phone_ids = [limpiar_estricto(phone1_raw), limpiar_estricto(phone2_raw)]
template_name = limpiar_estricto(template_raw)

# Inicializar contadores y turnos en st.session_state para el balanceo
if 'conteo_envios' not in st.session_state:
    st.session_state.conteo_envios = {phone_ids[0] if phone_ids[0] else "p1": 0, phone_ids[1] if phone_ids[1] else "p2": 0}

if 'turno_actual' not in st.session_state:
    st.session_state.turno_actual = 0

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Controles de Envío")

max_msgs = st.sidebar.slider(
    "Cantidad de mensajes a enviar",
    min_value=1,
    max_value=500,
    value=1,
    step=1,
    help="Configura hasta 500 (repartidos 250 por número).",
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

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Estado de las Líneas (Máx 250 c/u)")
if phone_ids[0] and phone_ids[1]:
    st.sidebar.text(f"Número 1: {st.session_state.conteo_envios.get(phone_ids[0], 0)} / 250")
    st.sidebar.text(f"Número 2: {st.session_state.conteo_envios.get(phone_ids[1], 0)} / 250")

# --- CUERPO PRINCIPAL ---
st.title("📩 Panel de Envío Masivo - Meta Cloud API (Balanceado)")
st.markdown(
    "Automatización conectada con tu padrón, inyección de variables en plantilla y balanceo de carga entre dos números."
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
      if st.button("🚀 Iniciar Envío Masivo Balanceado"):
        if not token or not phone_ids[0] or not phone_ids[1] or not template_name:
          st.warning(
              "⚠️ Por favor, completa el Token, ambos Phone Number IDs y el nombre de la plantilla correctamente."
          )
        else:
            # Sincronizar diccionario de contadores por si cambiaron los IDs
            st.session_state.conteo_envios = {
                phone_ids[0]: st.session_state.conteo_envios.get(phone_ids[0], 0), 
                phone_ids[1]: st.session_state.conteo_envios.get(phone_ids[1], 0)
            }

            barra_progreso = st.progress(0)
            status_text = st.empty()
            total = len(df_procesar)
            exitosos = 0
            fallidos = 0

            log_container = st.container()

            for index, row in df_procesar.iterrows():
                # Determinar qué número toca usar (Round-Robin) y verificar límite de 250
                activo_id = phone_ids[st.session_state.turno_actual]
                
                if st.session_state.conteo_envios[activo_id] >= 250:
                    otro_turno = 1 - st.session_state.turno_actual
                    otro_id = phone_ids[otro_turno]
                    if st.session_state.conteo_envios[otro_id] < 250:
                        st.session_state.turno_actual = otro_turno
                        activo_id = otro_id
                    else:
                        with log_container:
                            st.error("⚠️ Se ha alcanzado el límite máximo diario de 250 mensajes en ambos números (500 total).")
                        break

                url = f"https://graph.facebook.com/v20.0/{activo_id}/messages"

                nombre = limpiar_estricto(row[col_nombre])
                
                celular_raw = str(row[col_celular]).strip()
                celular = (
                    celular_raw.split(".")[0]
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("+", "")
                )

                local_votacion = limpiar_estricto(row[col_local])
                mesa_votacion = limpiar_estricto(row[col_mesa])
                orden_votacion = limpiar_estricto(row[col_orden])

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
                    response_body = response.read().decode("utf-8")
                    response_data = json.loads(response_body)

                    if response.status == 200:
                      exitosos += 1
                      # Incrementar contador del número activo y alternar turno
                      st.session_state.conteo_envios[activo_id] += 1
                      st.session_state.turno_actual = 1 - st.session_state.turno_actual

                      msg_id = "N/D"
                      try:
                        msg_id = response_data.get("messages", [{}])[0].get("id", "N/D")
                      except Exception:
                        pass

                      with log_container:
                        st.success(f"✅ Enviado a {nombre} ({celular}) vía `{activo_id}` | ID Meta: `{msg_id}`")
                    else:
                      fallidos += 1
                      with log_container:
                        st.error(
                            f"❌ Error con {nombre} ({celular}) en {activo_id}: código {response.status}"
                        )
                except urllib.error.HTTPError as e:
                  fallidos += 1
                  error_body = e.read().decode("utf-8", errors="ignore")
                  with log_container:
                    st.error(
                        f"❌ Error HTTP con {nombre} ({celular}): {error_body}"
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
