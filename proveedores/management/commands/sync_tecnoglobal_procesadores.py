from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import time

load_dotenv()

LOGIN_URL = "https://www.tecnoglobal.cl/tiendaonline/webapp/login"
CATEG_URL = "https://www.tecnoglobal.cl/tiendaonline/webapp/almacenamiento-de-datos/disco-duro-externo/256?pagina=1&disponible=1"

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 20)

# 1) Login
driver.get(LOGIN_URL)

email = wait.until(EC.presence_of_element_located((By.ID, "emailEmpresa")))
rut   = driver.find_element(By.ID, "rutEmpresa")
pwd   = driver.find_element(By.ID, "passwordEmpresa")

email.send_keys(os.environ["TECNOGLOBAL_USER"])
rut.send_keys(os.environ["TECNOGLOBAL_RUT"])
pwd.send_keys(os.environ["TECNOGLOBAL_PASS"])
pwd.send_keys(Keys.RETURN)

# esperar a que la página post-login cargue algo estable, por ejemplo el body
wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
# print("Login OK")




# 2) Ir a la categoría
driver.get(CATEG_URL)

# esperamos a que aparezcan los li de productos
wait.until(EC.presence_of_all_elements_located(
    (By.CSS_SELECTOR, "li.columnas__item--minifichas")
))

import re

try:
    dolar_el = driver.find_element(By.CSS_SELECTOR, "ul.cabecera-superior__contenidos li.ng-binding")
    dolar_texto = dolar_el.text.strip()
    match = re.search(r"\$([\d,\.]+)", dolar_texto)
    if match:
        dolar_valor = float(match.group(1).replace(",", "."))
    else:
        dolar_valor = 950.0
    print("Dólar T.G. del día:", dolar_valor)
except Exception:
    dolar_valor = 950.0
    print("⚠️ No se pudo obtener el valor del dólar, usando 950 por defecto.")




productos = driver.find_elements(By.CSS_SELECTOR, "li.columnas__item--minifichas")
print(f"Productos en esta página: {len(productos)}")

for i, item in enumerate(productos, start=1):
    print(f"\nProducto #{i}")

    # Nombre
    try:
        nombre_el = item.find_element(By.CSS_SELECTOR, "h1.minificha__nombre-producto a")
        nombre = nombre_el.text.strip()
    except Exception:
        nombre = "(sin nombre)"
    print("Nombre:", nombre)

    # SKU
    try:
        sku_el = item.find_element(By.CSS_SELECTOR, "div.grupo__sku span.minificha__sku")
        sku = sku_el.text.strip().replace("Código TG:", "").strip()
    except Exception:
        sku = "(sin SKU)"
    print("SKU:", sku)

    # Stock
    try:
        stock_el = item.find_element(By.CSS_SELECTOR, "div.minificha__disponibilidad")
        stock = stock_el.text.strip()
    except Exception:
        stock = "(sin stock)"
    print("Stock:", stock)

    # Precio
    try:
        precio_el = item.find_element(By.CSS_SELECTOR, "div.minificha__precio-preferencial")
        precio = precio_el.text.strip()
    except Exception:
        precio = "(sin precio)"
    print("Precio:", precio)





