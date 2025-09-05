# Análisis de código: Búsqueda de información de empresas y noticias

## 🚀 Proyecto 1: Búsqueda de Información de Empresas (Debida Diligencia)

Objetivo: Automatizar la recolección de datos de empresas (representantes, sanciones, etc.) de múltiples fuentes.

* Herramientas Clave: Selenium (para interactuar con páginas web dinámicas como SUNAT y OFAC) y PyPDF2 (para leer archivos PDF de la ONU y CSNU/FT).

Funcionalidades:

* Consulta en SUNAT: Extrae la razón social y los representantes legales de un RUC.

* Verificación de Listas Negras: Cruza la información obtenida con listas de sanciones internacionales (OFAC, ONU, Unión Europea, GAFI).

* Procesamiento de Datos: Usa pandas para consolidar los resultados de todas las fuentes en un único DataFrame.

* Producto Final: Un archivo de Excel (.xlsx) con un informe completo sobre la empresa y sus representantes.

## 🚀 Proyecto 2: Búsqueda de Noticias de Alto Riesgo

Objetivo: Monitorear y consolidar noticias de alto riesgo (fraude, corrupción, etc.) relacionadas con empresas y sus representantes.

* Herramientas Clave: requests y BeautifulSoup (para web scraping estático de Bing News) y Selenium (para obtener datos dinámicos de SUNAT y SBS).

Funcionalidades:

* Búsqueda Masiva de Noticias: Combina nombres de empresas y personas con palabras clave de riesgo para generar cientos de consultas de forma automática.

* Extracción de Datos de Perfil: Obtiene información detallada de la empresa (número de trabajadores, deuda coactiva) de la página de la SUNAT.

* Verificación en SBS: Consulta bases de datos de la Superintendencia de Banca y Seguros.

* Producto Final: Un archivo de Excel (.xlsx) organizado en varias hojas, que contiene un informe principal y los resultados detallados de la búsqueda de noticias.

## 📃 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
