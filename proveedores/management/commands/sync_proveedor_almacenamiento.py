import os
import time
import re
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from productos.models import Producto, Categoria


class Command(BaseCommand):
    help = "Sincroniza productos de 'Almacenamiento' desde Tecnoglobal al catálogo local."

    def handle(self, *args, **options):
        # 1. Leer credenciales desde variables de entorno
        login_url = os.environ.get("PROVEE_URL_LOGIN")
        user = os.environ.get("PROVEE_USER")
        rut = os.environ.get("PROVEE_RUT")
        password = os.environ.get("PROVEE_PASS")

        if not login_url or not user or not password or not rut:
            self.stderr.write(self.style.ERROR("Faltan variables PROVEE_URL_LOGIN / PROVEE_USER / PROVEE_RUT / PROVEE_PASS"))
            return

        # 2. Preparar Selenium (Chrome)
        self.stdout.write("Iniciando Selenium...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")  # sin abrir ventana
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        try:
            self.login(driver, login_url, user, rut, password)
            self.sync_almacenamiento(driver)
        finally:
            driver.quit()
            self.stdout.write(self.style.SUCCESS("Sincronización finalizada."))

    # -------------------------------------------------------------------------

    def login(self, driver, login_url, user, rut, password):
        self.stdout.write("Abriendo página de login...")
        driver.get(login_url)

        wait = WebDriverWait(driver, 20)

        # Campos de login Tecnoglobal
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
        rut_input = driver.find_element(By.CSS_SELECTOR, "input[name='rut']")
        pass_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")

        email_input.clear()
        email_input.send_keys(user)
        rut_input.clear()
        rut_input.send_keys(rut)
        pass_input.clear()
        pass_input.send_keys(password)
        pass_input.send_keys(Keys.RETURN)

        # Esperar a que cargue después del login
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.stdout.write(self.style.SUCCESS("Login correcto."))

    # -------------------------------------------------------------------------

    @transaction.atomic
    def sync_almacenamiento(self, driver):
        # 1. Ir a la categoría "Almacenamiento"
        url_almacenamiento = os.environ.get("PROVEE_URL_ALMACENAMIENTO")
        if not url_almacenamiento:
            raise RuntimeError("Falta PROVEE_URL_ALMACENAMIENTO en el entorno.")

        self.stdout.write(f"Abriendo categoría almacenamiento: {url_almacenamiento}")
        driver.get(url_almacenamiento)

        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.columnas__item--minifichas")))

        # Asegurar categoría local
        categoria, _ = Categoria.objects.get_or_create(nombre="Almacenamiento")

        # 2. Recorrer productos (maneja paginación)
        while True:
            productos = driver.find_elements(By.CSS_SELECTOR, "li.columnas__item--minifichas")
            self.stdout.write(f"Encontrados {len(productos)} productos en esta página.")

            for elemento in productos:
                try:
                    self.process_product_element(elemento, categoria)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error procesando producto: {e}"))

            # Intentar pasar a la siguiente página
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.paginacion__pagina--siguiente a#next")
                li_parent = next_button.find_element(By.XPATH, "..")
                if "disabled" in li_parent.get_attribute("class"):
                    break
                next_button.click()
                time.sleep(2)
            except Exception:
                break

    # -------------------------------------------------------------------------

    def process_product_element(self, elemento, categoria):
        """Extrae nombre, link, precio, stock y SKU desde un bloque de producto."""

        # ====== BLOQUE INFORMACIÓN ======
        try:
            info = elemento.find_element(
                By.XPATH,
                ".//div[contains(@class,'minificha') and contains(@class,'informacion')]"
            )
        except Exception:
            self.stderr.write("No se encontró bloque de información en este producto, se omite.")
            return

        # Nombre + link (link que contenga /detalle/)
        try:
            try:
                nombre_link_el = info.find_element(By.XPATH, ".//h1//a[contains(@href,'/detalle/')]")
            except Exception:
                nombre_link_el = info.find_element(By.XPATH, ".//a[contains(@href,'/detalle/')]")

            nombre = nombre_link_el.text.strip()
            link = nombre_link_el.get_attribute("href")
        except Exception:
            self.stderr.write("No se encontró link/título en este item, se omite.")
            return

        # SKU (Código TG)
        sku = None
        try:
            sku_spans = info.find_elements(
                By.XPATH,
                ".//div[contains(@class,'grupo') and contains(@class,'sku')]//span"
            )
            for span in sku_spans:
                texto = span.text.strip()
                if "Código TG" in texto:
                    sku = texto.split(":")[-1].strip()
                    break
        except Exception:
            pass

        if not sku:
            self.stderr.write(f"No se encontró Código TG para producto '{nombre}', se omite.")
            return

        # Stock
        try:
            stock_el = info.find_element(
                By.XPATH,
                ".//*[contains(@class,'disponibilidad') or contains(text(),'disponible')]"
            )
            stock_texto = stock_el.text.strip()
        except Exception:
            stock_texto = ""

        # ====== BLOQUE PRECIOS ======
        try:
            precios_contenedor = elemento.find_element(
                By.XPATH,
                ".//div[contains(@class,'minificha') and contains(@class,'precios')]"
            )
            precio_texto = precios_contenedor.text.strip()
        except Exception:
            precio_texto = ""

        # Normalizar precio
        precio_limpio = precio_texto
        for palabra in ["Precio preferente", "USD", "Unidad", "$"]:
            precio_limpio = precio_limpio.replace(palabra, "")
        precio_limpio = precio_limpio.replace(",", ".")
        nums = re.findall(r"[0-9]+(?:\.[0-9]+)?", precio_limpio)
        precio = Decimal(nums[0]) if nums else Decimal("0.00")

        # Normalizar stock
        nums_stock = re.findall(r"\d+", stock_texto)
        stock = int(nums_stock[0]) if nums_stock else 0

        # ====== Guardar / actualizar ======
        obj, creado = Producto.objects.update_or_create(
            codigo_proveedor=sku,
            defaults={
                "nombre": nombre,
                "precio": precio,
                "stock": stock,
                "descripcion": f"Importado desde Tecnoglobal. SKU: {sku}",
                "categoria": categoria,
                "url_proveedor": link,
            },
        )

        accion = "CREADO" if creado else "ACTUALIZADO"
        self.stdout.write(f"{accion}: {obj.nombre} (SKU {sku}) stock={stock} precio={precio}")
