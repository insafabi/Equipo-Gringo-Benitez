import urllib.parse
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Movilización Gringo Benítez", page_icon="🗳️", layout="wide"
)

st.title("🗳️ Panel de Movilización - Equipo Gringo Benítez")
st.write(
    "Sube tu padrón de Excel de forma privada para gestionar los envíos sin"
    " riesgos."
)

# Cuadro seguro para cargar el archivo Excel directamente desde tu PC
archivo_subido = st.file_uploader(
    "Sube tu archivo Excel de contactos (.xlsx)", type=["xlsx", "xls"]
)

if archivo_subido is not None:
  df = pd.read_excel(archivo_subido)

  st.success(f"¡Padrón cargado con éxito! Total de contactos: {len(df)}")

  # Control de bloques para no saturar el navegador
  batch_size = st.slider(
      "Selecciona cuántos contactos mostrar por página:", 10, 50, 20
  )
  pagina = st.number_input(
      "Bloque / Página",
      min_value=1,
      max_value=max(1, (len(df) // batch_size) + 1),
      step=1,
  )

  inicio = (pagina - 1) * batch_size
  fin = min(inicio + batch_size, len(df))
  lote_actual = df.iloc[inicio:fin]

  st.subheader(
      f"Mostrando contactos del {inicio + 1} al {fin} (Bloque {pagina})"
  )

  for idx, row in lote_actual.iterrows():
    # Asume las columnas: E (índice 4)=Nombre, C (índice 2)=Local, H (índice 7)=Mesa, I (índice 8)=Orden, J (índice 9)=Teléfono
    try:
      nombre = str(row.iloc[4])
      local = str(row.iloc[2])
      mesa = str(row.iloc[7])
      orden = str(row.iloc[8])
      telefono = str(row.iloc[9])
    except Exception:
      nombre = str(row.iloc[0])
      telefono = str(row.iloc[1])
      local = "Local"
      mesa = "Mesa"
      orden = "Orden"

    # Nuevo mensaje actualizado con tu diseño institucional
    mensaje = (
        f"¡Hola *{nombre}*\n\n"
        f"🇵🇾🎉 ¡Este *4 de octubre*, Asunción vivirá una gran fiesta cívica!\n\n"
        f"Soy *Gringo Benítez*, candidato a Concejal por la *Lista 1 - Opción 1*, "
        f"y junto a *Camilo, candidato a Intendente*, te invito a participar. 🗳️\n\n"
        f"📍 *{local}* |\n"
        f"🏫 *Mesa {mesa}* |\n"
        f"🔢 *Orden {orden}*\n\n"
        f"**¡Tu participación es clave! 🇵🇾**"
    )

    encoded_msg = urllib.parse.quote(mensaje)
    whatsapp_url = (
        f"https://web.whatsapp.com/send?phone={telefono}&text={encoded_msg}"
    )

    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
      st.markdown(f"**{nombre}** (Tel: {telefono})")
      st.caption(f"Local: {local} | Mesa: {mesa} | Orden: {orden}")
    with col2:
      st.markdown(
          f'<a href="{whatsapp_url}" target="_blank" style="background-color:#25D366;color:white;padding:8px'
          ' 12px;text-decoration:none;border-radius:5px;display:inline-block;">💬'
          " Abrir Chat</a>",
          unsafe_allow_html=True,
      )
    with col3:
      st.text(f"Fila Excel #{idx + 2}")

    st.divider()
else:
  st.info(
      "Por favor, sube tu archivo Excel en el botón de arriba para comenzar a"
      " ver los contactos."
  )
