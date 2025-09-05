import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

titulos_vistos = set()

# ========= FUNCIÓN PARA BUSCAR NOTICIAS ============

def buscar_noticias(query):
    print(f"🔍 Buscando noticias para: {query}")
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.bing.com/news/search?q={query.replace(' ', '+')}&FORM=HDRSC6"

    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    noticias = []
    fecha_hora_busqueda = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Palabras clave a excluir
    palabras_clave = {"LAVADO DE ACTIVOS", "FRAUDE", "PROCESO", "NOTICIA", "PECULADO", "CORRUPCION", "INVESTIGACION", "DENUNCIA"}

    # Palabras de búsqueda útiles (sin las palabras clave)
    palabras_utiles = [pal for pal in query.upper().split() if pal not in palabras_clave]

    for item in soup.select(".news-card")[:10]:
        titulo_tag = item.select_one("a.title")
        if titulo_tag:
            titulo = titulo_tag.text.strip()
            if titulo in titulos_vistos:
                continue

            palabras_en_titulo = set(titulo.upper().split())
            coincidencias = sum(1 for pal in palabras_utiles if pal in palabras_en_titulo)

            if coincidencias >= 2:
                titulos_vistos.add(titulo)
                noticias.append({
                    "Título": titulo,
                    "Link": titulo_tag["href"],
                    "Búsqueda": query,
                    "Fecha y Hora de Búsqueda": fecha_hora_busqueda
                })

    # ✅ Si no se encontró ninguna noticia, registrar igual la búsqueda
    if not noticias:
        noticias.append({
            "Título": "Sin resultados",
            "Link": "No se encontró",
            "Búsqueda": query,
            "Fecha y Hora de Búsqueda": fecha_hora_busqueda
        })

    return noticias

# ========= FUNCIÓN PARA OBTENER DATOS SUNAT ============
def buscar_ruc(ruc):
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    representantes = []
    empresa = ""
    fecha_inicio_actividades = None
    actividad_economica = None
    tipo_contribuyente = None
    domicilio_fiscal = None
    tipo_persona_juridica = None
    deuda_coactiva = "No encontrado"  # NUEVO: Variable para deuda coactiva

    try:
        driver.get("https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp")
        ruc_input = wait.until(EC.presence_of_element_located((By.ID, "txtRuc")))
        ruc_input.send_keys(ruc)

        btn_buscar = wait.until(EC.element_to_be_clickable((By.ID, "btnAceptar")))
        btn_buscar.click()

        time.sleep(5)
        elementos = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "list-group-item-heading")))
        ruc_nombre = elementos[1].text
        print("✅ RUC y Razón Social:", ruc_nombre)
        empresa = ruc_nombre.split(" - ", 1)[1] if " - " in ruc_nombre else ruc_nombre

        list_groups = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list-group-item"))
        )
        
        for item in list_groups:
            if "Fecha de Inicio de Actividades" in item.text:
                paragraphs = item.find_elements(By.CLASS_NAME, "list-group-item-text")
                if len(paragraphs) >= 2:
                    fecha_inicio_actividades = paragraphs[1].text.strip()
                    print("Fecha de Inicio de Actividades:", fecha_inicio_actividades)
            
            if "Actividad(es) Económica(s)" in item.text:
                td = item.find_element(By.TAG_NAME, "td")
                actividad_economica = td.text.strip()
                print("Actividad económica:", actividad_economica)
            
            if "Tipo Contribuyente" in item.text:
                parrafos = item.find_elements(By.CLASS_NAME, "list-group-item-text")
                if parrafos:
                    tipo_contribuyente = parrafos[0].text.strip()
                    print("Tipo Contribuyente:", tipo_contribuyente)
            
            if "Domicilio Fiscal" in item.text:
                parrafos = item.find_elements(By.CLASS_NAME, "list-group-item-text")
                if parrafos:
                    domicilio_fiscal = parrafos[0].text.strip()
                    print("Domicilio Fiscal:", domicilio_fiscal)

         # ----------------- Obtener Numero de trabajdores -----------------
        try:
            btn_cant_trab = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btnInfNumTra")))
            btn_cant_trab.click()
            time.sleep(3)
            tabla_trab = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody")))
            filas_trab = tabla_trab.find_elements(By.TAG_NAME, "tr")
            
            if filas_trab:
                ultima_fila = filas_trab[-1]
                celdas = ultima_fila.find_elements(By.TAG_NAME, "td")
                
                if len(celdas) >= 2:
                    num_trabajadores = celdas[1].text.strip()   # ✅ guardar correctamente
                
            print(f"✅ Número de Trabajadores (último registro): {num_trabajadores}")
            driver.back()
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ No se pudo obtener el Número de Trabajadores: {e}")

        # ----------------- NUEVO: Obtener deuda coactiva -----------------
        try:
            btn_deuda_coactiva = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btnInfDeuCoa")))
            btn_deuda_coactiva.click()
            print("✅ Botón Deuda Coactiva presionado.")
            
            deuda_panel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel.panel-primary")))
            deuda_item = deuda_panel.find_element(By.CSS_SELECTOR, "div.list-group-item")
            deuda_coactiva = deuda_item.text.strip()
            print(f"✅ Deuda Coactiva: {deuda_coactiva}")
            
            driver.back() # Regresar a la página anterior para seguir con otros datos
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ No se pudo obtener la Deuda Coactiva: {e}")

        # ----------------- Obtener representantes legales -----------------
        btn_rep_leg = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btnInfRepLeg")))
        btn_rep_leg.click()
        time.sleep(5)

        tabla = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody")))
        filas = tabla.find_elements(By.TAG_NAME, "tr")

        for fila in filas:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) == 5:
                representantes.append({
                    "Tipo Documento": celdas[0].text.strip(),
                    "Nro Documento": celdas[1].text.strip(),
                    "Nombre": celdas[2].text.strip(),
                    "Cargo": celdas[3].text.strip(),
                    "Fecha Desde": celdas[4].text.strip()
                })

        df_representantes = pd.DataFrame(representantes)
        print(df_representantes)

    except Exception as e:
        print("❌ Error:", str(e))
    finally:
        driver.quit()
    
    # ✅ devolver también num_trabajadores
    return empresa, representantes, fecha_inicio_actividades, actividad_economica, tipo_persona_juridica, deuda_coactiva, num_trabajadores

# ========= FUNCIÓN PARA BUSCAR EN SBS ============
def buscar_sbs(ruc):
    options = webdriver.ChromeOptions()
    driver_sbs = webdriver.Chrome(options=options)
    driver_sbs.get("https://www.sbs.gob.pe/app/uif/voc/")

    input_ruc = WebDriverWait(driver_sbs, 10).until(
        EC.presence_of_element_located((By.ID, "txtRuc"))
    )
    input_ruc.send_keys(ruc)
    print("RUC ingresado en SBS")

    boton_buscar = WebDriverWait(driver_sbs, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.g-recaptcha.btn.btn-primary-custom-green"))
    )
    boton_buscar.click()
    print("Búsqueda iniciada en SBS")

    tabla = WebDriverWait(driver_sbs, 10).until(
        EC.presence_of_element_located((By.ID, "tblResultado"))
    )

    resultados = []
    for fila in tabla.find_elements(By.TAG_NAME, "tr")[1:]:
        celdas = fila.find_elements(By.TAG_NAME, "td")
        if len(celdas) == 3:
            resultados.append(celdas[2].text.strip())

    print("Resultado de la búsqueda en SBS:")
    print(resultados)
    driver_sbs.quit()
    return resultados

# ========= INICIO DEL FLUJO ============
ruc = "20518380762"
# NUEVO: Capturar el nuevo dato de deuda coactiva
empresa, representantes, fecha_inicio_actividades, actividad_economica, tipo_persona_juridica, deuda_coactiva, num_trabajadores = buscar_ruc(ruc)

resultados_sbs = buscar_sbs(ruc)

# ========= BÚSQUEDA DE NOTICIAS Y EXPORTACIÓN ============
# Agrupamos por tipo de búsqueda
resultados_agrupados = {
    "Nombre Representante Legal": [],
    "Nombre Empresa": [],
    "Representante + Empresa": [],
    "Representante + DNI": []
}
# Palabras clave a combinar en cada búsqueda
palabras_clave = ["LAVADO DE ACTIVOS", "FRAUDE", "PROCESO", "NOTICIA", "PECULADO", "CORRUPCION", "INVESTIGACION", "DENUNCIA"]

def buscar_con_claves(base_query, hoja_nombre):
    for palabra in palabras_clave:
        consulta = f"{base_query} {palabra}"
        noticias = buscar_noticias(consulta)
        resultados_agrupados[hoja_nombre].extend(noticias)

buscar_con_claves(empresa, "Nombre Empresa")

for rep in representantes:
    nombre = rep["Nombre"]
    dni = rep["Nro Documento"]
    buscar_con_claves(nombre, "Nombre Representante Legal")
    buscar_con_claves(f"{nombre} {empresa}", "Representante + Empresa")
    buscar_con_claves(f"{nombre} {dni}", "Representante + DNI")

# ========= CREAR HOJA PRINCIPAL ============
datos_principales = [
    ["RUC y Razón Social", f"{ruc} - {empresa}"],
    ["Fecha de Inicio de Actividades", fecha_inicio_actividades if fecha_inicio_actividades else "No encontrado"],
    ["Actividad económica", actividad_economica if actividad_economica else "No encontrada"],
    ["Cantidad de Trabajadores", num_trabajadores],   # ✅ ahora sí correcto
    ["Deuda Coactiva", deuda_coactiva],
    ["Resultado SBS", ", ".join(resultados_sbs) if resultados_sbs else "No encontrado"]
]

df_principal_info = pd.DataFrame(datos_principales, columns=["Dato", "Valor"])
df_representantes = pd.DataFrame(representantes)

nombre_archivo = f"C:/Users/kbarahona/OneDrive - Novopayment Inc/Documentos/PROYECTOS 2025/PROYECTO MONITOREO INTEGRAL/Noticias_{ruc}.xlsx"
with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
    df_principal_info.to_excel(writer, sheet_name="Principal", index=False, startrow=0)
    df_representantes.to_excel(writer, sheet_name="Principal", index=False, startrow=len(df_principal_info) + 3)
    for hoja, noticias in resultados_agrupados.items():
        df = pd.DataFrame(noticias)
        df.to_excel(writer, sheet_name=hoja[:31], index=False)