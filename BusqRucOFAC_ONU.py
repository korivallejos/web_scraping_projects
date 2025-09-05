import time 
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfReader   # 📌 para leer el PDF de la ONU
import os


# ================= FUNCION SUNAT =================
def buscar_representantes_sunat(ruc):
    """Busca en SUNAT los representantes legales de un RUC + agrega empresa"""
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    registros = []
    try:
        driver.get("https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp")

        ruc_input = wait.until(EC.presence_of_element_located((By.ID, "txtRuc")))
        ruc_input.send_keys(ruc)

        btn_buscar = wait.until(EC.element_to_be_clickable((By.ID, "btnAceptar")))
        btn_buscar.click()
        time.sleep(2)

        # 📌 Capturar razón social ANTES de entrar a representantes
        elementos = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "list-group-item-heading")))
        ruc_nombre = elementos[1].text
        razon_social = ruc_nombre.split(" - ", 1)[1] if " - " in ruc_nombre else ruc_nombre

        # 👉 Agregar registro para la EMPRESA en sí
        registros.append({
            "RUC": ruc,
            "Tipo Documento": "RUC",
            "Nro Documento": ruc,
            "Nombre": razon_social,
            "Cargo": "EMPRESA",
            "Fecha Desde": None,
            "Pais": "PERU"   # fijo porque las empresas son peruanas
        })

        # 📌 Ahora sacar Representantes Legales
        btn_rep_leg = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btnInfRepLeg")))
        btn_rep_leg.click()
        time.sleep(2)

        tabla = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody")))
        filas = tabla.find_elements(By.TAG_NAME, "tr")

        for fila in filas:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) == 5:
                fecha_desde_str = celdas[4].text.strip()
                try:
                    fecha_desde = datetime.strptime(fecha_desde_str, "%d/%m/%Y")
                except:
                    fecha_desde = None

                registros.append({
                    "RUC": ruc,
                    "Tipo Documento": celdas[0].text.strip(),
                    "Nro Documento": celdas[1].text.strip(),
                    "Nombre": celdas[2].text.strip(),
                    "Cargo": celdas[3].text.strip(),
                    "Fecha Desde": fecha_desde,
                    "Pais": "PERU" if celdas[0].text.strip().upper() == "DNI" else "OTROS"
                })

    except Exception as e:
        print(f"❌ Error con RUC {ruc}: {e}")
    finally:
        driver.quit()

    return registros


# ================= FUNCION OFAC =================
def buscar_ofac(df_reps):
    """Consulta OFAC con DNI y Nombre de representantes legales"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    driver.get("https://sanctionssearch.ofac.treas.gov/")

    resultados = []

    for _, fila in df_reps.iterrows():
        dni = fila["Nro Documento"].strip()
        nombre = fila["Nombre"].strip()

        try:
            # Limpiar campos
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_MainContent_txtLastName"))).clear()
            driver.find_element(By.ID, "ctl00_MainContent_txtLastName").send_keys(nombre)

            driver.find_element(By.ID, "ctl00_MainContent_txtID").clear()
            driver.find_element(By.ID, "ctl00_MainContent_txtID").send_keys(dni)

            # Click en Search
            driver.find_element(By.ID, "ctl00_MainContent_btnSearch").click()
            time.sleep(2)

            # Revisar mensaje
            try:
                mensaje = driver.find_element(By.ID, "ctl00_MainContent_lblMessage").text.strip()
                resultado = mensaje if mensaje else "Coincidencias encontradas"
            except:
                resultado = "Coincidencias encontradas"

            resultados.append({
                "RUC": fila["RUC"],
                "Nro Documento": dni,
                "Nombre": nombre,
                "Cargo": fila["Cargo"],
                "Resultado_OFAC": resultado
            })

            # Reset
            driver.find_element(By.ID, "ctl00_MainContent_btnReset").click()
            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error con {dni} - {nombre}: {e}")
            resultados.append({
                "RUC": fila["RUC"],
                "Nro Documento": dni,
                "Nombre": nombre,
                "Cargo": fila["Cargo"],
                "Resultado_OFAC": f"Error: {e}"
            })

    driver.quit()
    return pd.DataFrame(resultados)


# ================= FUNCION ONU (PDF) =================
def buscar_onu(df, ruta_pdf):
    """Busca coincidencias de Nombres en la lista ONU (PDF)"""
    reader = PdfReader(ruta_pdf)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text().lower() + " "   # pasamos todo a minúsculas

    resultados = []
    for _, fila in df.iterrows():
        nombre = fila["Nombre"].lower().strip()
        if nombre in texto:
            resultados.append("Coincidencia")
        else:
            resultados.append("No coincidencia")

    df["Resultado_ONU"] = resultados
    return df


# ================= FUNCION UE =================
def buscar_union_europea(df):
    """Busca coincidencias de Nombres o Nro Documento en la lista de la Unión Europea"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = "https://eur-lex.europa.eu/legal-content/es/TXT/HTML/?uri=CELEX:32019D1341&from=en"
    driver.get(url)
    time.sleep(3)

    # Obtener texto completo de la página en minúsculas
    texto_pagina = driver.page_source.lower()

    resultados = []
    for _, fila in df.iterrows():
        nombre = fila["Nombre"].lower().strip()
        nro_doc = fila["Nro Documento"].lower().strip()

        if nombre in texto_pagina or nro_doc in texto_pagina:
            resultados.append("Coincidencia")
        else:
            resultados.append("No coincidencia")

    df["Resultado_EU"] = resultados
    driver.quit()
    return df


# ================= FUNCION GAFI =================
def buscar_gafi(df):
    """Busca coincidencias de País en las listas del GAFI"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    # --- Lista de Alto Riesgo ---
    driver.get("https://www.fatf-gafi.org/en/publications/High-risk-and-other-monitored-jurisdictions/Call-for-action-june-2025.html")
    time.sleep(3)
    html_alto = driver.page_source.lower()

    alto_riesgo = []
    if "corea" in html_alto or "dprk" in html_alto: alto_riesgo.append("COREA DEL NORTE")
    if "iran" in html_alto: alto_riesgo.append("IRÁN")
    if "myanmar" in html_alto: alto_riesgo.append("MYANMAR")

    # --- Lista Bajo Mayor Monitoreo ---
    driver.get("https://www.fatf-gafi.org/en/publications/High-risk-and-other-monitored-jurisdictions/increased-monitoring-june-2025.html")
    time.sleep(3)
    html_monitoreo = driver.page_source.lower()

    bajo_monitoreo = []
    for pais in ["argelia","angola","bolivia","bulgaria","burkina","camerún","costa de marfil",
                 "congo","haiti","kenia","lao","líbano","mónaco","mozambique","namibia",
                 "nepal","nigeria","sudáfrica","sudán","siria","venezuela","vietnam",
                 "islas vírgenes","yemen"]:
        if pais in html_monitoreo:
            bajo_monitoreo.append(pais.upper())

    # --- Comparación con DataFrame ---
    resultados = []
    for _, fila in df.iterrows():
        pais = fila["Pais"].strip().upper()
        if pais in alto_riesgo:
            resultados.append("Alto Riesgo")
        elif pais in bajo_monitoreo:
            resultados.append("Bajo Mayor Monitoreo")
        else:
            resultados.append("No listado")

    df["GAFI"] = resultados
    driver.quit()
    return df

# ================= FUNCION UE PAISES NO COOPERADORES =================
def buscar_ue_no_cooperadores(df):
    """Busca coincidencias de País en la lista de la UE de países no cooperadores"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = "https://www.consilium.europa.eu/es/policies/eu-list-of-non-cooperative-jurisdictions/#0"
    driver.get(url)
    time.sleep(3)

    # Extraer los países de la tabla
    paises = driver.find_elements(By.CSS_SELECTOR, "table tbody tr td, table tbody tr th")
    lista_paises_ue = [p.text.strip().upper() for p in paises if p.text.strip() != ""]

    driver.quit()

    # Comparar con la columna "Pais" de df
    resultados = []
    for _, fila in df.iterrows():
        pais = fila["Pais"].strip().upper()
        if pais in lista_paises_ue:
            resultados.append("Coincidencia Pais")
        else:
            resultados.append("No coincidencia")

    df["UE Paises no cooperadores"] = resultados
    return df

# ================= FUNCION CSNU/FT (dos PDFs) =================
def buscar_csnu_ft(df, rutas_pdfs):
    """Busca coincidencias de Nombres o DNI en dos PDFs locales"""
    textos = ""

    # Leer y concatenar todos los PDFs
    for ruta in rutas_pdfs:
        reader = PdfReader(ruta)
        for page in reader.pages:
            textos += page.extract_text().lower() + " "   # todo en minúsculas

    resultados = []
    for _, fila in df.iterrows():
        nombre = str(fila["Nombre"]).lower().strip()
        dni = str(fila["Nro Documento"]).lower().strip()

        if (nombre in textos) or (dni in textos):
            resultados.append("Coincidencia")
        else:
            resultados.append("No coincidencia")

    df["Resultado_CSNU_FT"] = resultados
    return df

# ================= FLUJO COMPLETO =================
rucs = ["20523683081",
"20375020905",
"20548544981",
"20609364310",
"20551464971",
"20603023928",
"20604251584",
"20606444894",
"20514526584",
"20515504045"]   # lista de RUCs
todos_reps = []

for r in rucs:
    reps = buscar_representantes_sunat(r)
    todos_reps.extend(reps)

df_reps = pd.DataFrame(todos_reps)

# Agregar campo País
df_reps["Pais"] = df_reps.apply(
    lambda row: row["Pais"] if pd.notnull(row["Pais"]) and row["Pais"] != "" 
    else ("PERU" if row["Tipo Documento"].strip().upper() == "DNI" else "OTROS"),
    axis=1
)
# Buscar en OFAC
df_ofac = buscar_ofac(df_reps)

# Unir resultados SUNAT + OFAC
df_final = df_reps.merge(df_ofac, on=["RUC", "Nro Documento", "Nombre", "Cargo"], how="left")

# Buscar en ONU (PDF)
ruta_pdf = r"C:\Users\kbarahona\Downloads\consolidatedLegacyByNAME (1).html.pdf"
df_final = buscar_onu(df_final, ruta_pdf)

# Buscar en Unión Europea (página)
df_final = buscar_union_europea(df_final)
# Buscar en UE países no cooperadores
df_final = buscar_ue_no_cooperadores(df_final)

# Buscar en GAFI
df_final = buscar_gafi(df_final)
# Buscar en CSNU/FT (dos PDFs locales)
rutas_pdfs = [
    r"C:\Users\kbarahona\Downloads\Legacy (13).html.pdf",
    r"C:\Users\kbarahona\Downloads\Legacy (12).html.pdf"
]
df_final = buscar_csnu_ft(df_final, rutas_pdfs)

# Ruta de la carpeta donde quieres guardar
ruta_carpeta = r"C:\Users\kbarahona\OFAC_ONU_POR_RUC"
# Crear carpeta si no existe
os.makedirs(ruta_carpeta, exist_ok=True)
# Definir ruta completa del archivo
ruta_archivo = os.path.join(ruta_carpeta, "representantes_sunat_ofac_onu_gafi.xlsx")

print(df_final)
df_final.to_excel(ruta_archivo, index=False)
