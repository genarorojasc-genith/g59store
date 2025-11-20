import os
import re
import time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from productos.models import Producto, Categoria

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from dotenv import load_dotenv


LOGIN_URL = "https://www.tecnoglobal.cl/tiendaonline/webapp/login"
CATEG_URL = "https://www.tecnoglobal.cl/tiendaonline/webapp/almacenamiento-de-datos/disco-duro-externo/256?pagina=1&disponible=1"


class Command(BaseCommand):
    help = "Sincroniza discos duros externos desde Tecnoglobal al catálogo local."

    def handle(self, *args, **options):
        load_dotenv()

        user = os.environ.get("TECNOGLOBAL_USER")
        rut = os.environ.get("TECNOGLOBAL_RUT")
        password = os.environ.get("TECNOGLOBAL_PASS")

        if not user or not rut or not password:
            self.stderr.write(self.style.ERROR(
                "Faltan variables TECNOGLOBAL_USER / TECNOGLOBAL_RUT / TECNOGLOBAL_PASS en el entorno."
            ))
            return

        # Configurar Chrome (puedes comentar headless si quieres ver la ventana)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)

        try:
            self.login(driver, wait, user, rut, password)
            dolar_valor = self.obtener_valor_dolar(driver)
            self.stdout.write(self.style.SUCCESS(f"Dólar T.G. del día: {dolar_valor}"))

            self.sync_categoria(driver, wait, dolar_valor)
        finally:
            driver.quit()
            self.stdout.write(self.style.SUCCESS("Sincronización finalizada."))

    # ------------------------------------------------------------------ #
    #  LOGIN
    # ------------------------------------------------------------------ #

    def login(self, driver, wait, user, rut, password):
        self.stdout.write("Haciendo login en Tecnoglobal...")
        driver.get(LOGIN_URL)

        email_el = wait.until(EC.presence_of_element_located((By.ID, "emailEmpresa")))
        rut_el = driver.find_element(By.ID, "rutEmpresa")
        pwd_el = driver.find_element(By.ID, "passwordEmpresa")

        email_el.clear()
        email_el.send_keys(user)

        rut_el.clear()
        rut_el.send_keys(rut)

        pwd_el.clear()
        pwd_el.send_keys(password)
        pwd_el.send_keys(Keys.RETURN)

        # Esperar a que cargue el body post login
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.stdout.write(self.style.SUCCESS("Login OK."))

    # ------------------------------------------------------------------ #
    #  VALOR DÓLAR
    # ------------------------------------------------------------------ #

    def obtener_valor_dolar(self, driver) -> Decimal:
        """
        Lee el texto tipo:
        'Valor dolar T.G: $951 - Lunes, 10 de Noviembre de 2025'
        y devuelve 951 como Decimal.
        """
        try:
            el = driver.find_element(
                By.CSS_SELECTOR,
                "ul.cabecera-superior__contenidos li.ng-binding"
            )
            texto = el.text.strip()
            match = re.search(r"\$([\d\.,]+)", texto)
            if not match:
                raise ValueError("No se encontró número en el texto del dólar.")

            bruto = match.group(1)
            # por si algún día ponen separador de miles
            bruto = bruto.replace(".", "").replace(",", ".")
            return Decimal(bruto)
        except Exception as e:
            self.stderr.write(
                self.style.WARNING(f"No se pudo obtener valor dólar ({e}). Usando 950 por defecto.")
            )
            return Decimal("950")

    # ------------------------------------------------------------------ #
    #  SINCRONIZAR CATEGORÍA
    # ------------------------------------------------------------------ #

    @transaction.atomic
    def sync_categoria(self, driver, wait, dolar_valor: Decimal):
        """
        Recorre las páginas de la categoría, extrae productos válidos
        y los guarda/actualiza en la tabla Producto.
        """
        categoria, _ = Categoria.objects.get_or_create(
            nombre="Disco Duro Externo"
        )

        pagina = 1

        while True:
            # si más adelante quieres cambiar la página base, ajusta esto
            url_pagina = CATEG_URL.replace("pagina=1", f"pagina={pagina}")
            self.stdout.write(f"\n=== Página {pagina} ===")
            self.stdout.write(url_pagina)

            driver.get(url_pagina)

            # esperar a que aparezcan los productos
            wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "li.columnas__item--minifichas")
            ))

            items = driver.find_elements(By.CSS_SELECTOR, "li.columnas__item--minifichas")
            self.stdout.write(f"Items en el DOM: {len(items)}")

            productos_validos = 0

            for elemento in items:
                try:
                    producto_data = self.extraer_producto(elemento)
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"  Error leyendo producto: {e}"))
                    continue

                if not producto_data:
                    # None => item vacío / sin nombre o sin SKU
                    continue

                nombre = producto_data["nombre"]
                sku = producto_data["sku"]
                stock_texto = producto_data["stock"]
                precio_texto = producto_data["precio"]
                url_detalle = producto_data["url"]

                
                precio_usd = self.parse_precio_usd(precio_texto)
                if precio_usd == Decimal("0"):
                    self.stderr.write(
                        self.style.WARNING(f"  '{nombre}' (SKU {sku}) con precio 0, se omite.")
                    )
                    continue

                stock = self.parse_stock(stock_texto)

                # Precio base proveedor en CLP
                precio_clp_base = (precio_usd * dolar_valor).quantize(Decimal("1"))

                # Margen de venta (10% extra)
                margen = Decimal("1.10")
                precio_clp_venta = (precio_clp_base * margen).quantize(Decimal("1"))



                obj, creado = Producto.objects.update_or_create(
                    codigo_proveedor=sku,
                    defaults={
                        "nombre": nombre,
                        "precio_costo": precio_clp_base,
                        "precio": precio_clp_venta,   # guardado en CLP con margen
                        "stock": stock,
                        "categoria": categoria,
                        "descripcion": f"Importado desde Tecnoglobal. SKU: {sku}",
                        "url_proveedor": url_detalle,
                    },
                )

                productos_validos += 1
                accion = "CREADO" if creado else "ACTUALIZADO"
                self.stdout.write(
                    f"  {accion}: {obj.nombre} (SKU {sku}) "
                    f"stock={stock} costo={precio_clp_base} CLP venta={precio_clp_venta} CLP (≈ {precio_usd} USD)"
                )



            if productos_validos == 0:
                self.stdout.write("  No se encontraron productos válidos en esta página. Deteniendo.")
                break

            # Intentar ir a la siguiente página.
            # Si no hay "siguiente" o está desactivado, salimos.
            try:
                next_li = driver.find_element(By.CSS_SELECTOR, "li.paginacion__pagina--siguiente")
                if "disabled" in next_li.get_attribute("class"):
                    self.stdout.write("  No hay más páginas (botón siguiente deshabilitado).")
                    break
                # si quieres click real:
                next_btn = next_li.find_element(By.TAG_NAME, "a")
                next_btn.click()
                time.sleep(2)
                pagina += 1
            except NoSuchElementException:
                self.stdout.write("  No se encontró botón de página siguiente. Fin.")
                break

    # ------------------------------------------------------------------ #
    #  EXTRACCIÓN DE UN PRODUCTO
    # ------------------------------------------------------------------ #

    def extraer_producto(self, item):
        """
        Dado un <li.columnas__item--minifichas>, devuelve un dict con:
        nombre, sku, stock, precio, url
        o None si no tiene nombre o SKU (placeholder, etc).
        """
        # Nombre + link detalle
        try:
            nombre_el = item.find_element(
                By.CSS_SELECTOR,
                "h1.minificha__nombre-producto a"
            )
            nombre = nombre_el.text.strip()
            url_detalle = nombre_el.get_attribute("href")
        except NoSuchElementException:
            return None

        # SKU TG (buscar el span que contiene 'Código TG')
        sku = None
        try:
            spans = item.find_elements(
                By.CSS_SELECTOR,
                "div.grupo__sku span.minificha__sku"
            )
            for sp in spans:
                txt = sp.text.strip()
                if "Código TG" in txt:
                    sku = txt.split(":")[-1].strip()
                    break
        except NoSuchElementException:
            pass

        if not sku:
            return None

        # Stock
        try:
            stock_el = item.find_element(By.CSS_SELECTOR, "div.minificha__disponibilidad")
            stock_texto = stock_el.text.strip()
        except NoSuchElementException:
            stock_texto = ""

        # Precio
        try:
            precio_el = item.find_element(By.CSS_SELECTOR, "div.minificha__precio-preferencial")
            precio_texto = precio_el.text.strip()
        except NoSuchElementException:
            # sin precio no nos sirve
            return None

        return {
            "nombre": nombre,
            "sku": sku,
            "stock": stock_texto,
            "precio": precio_texto,
            "url": url_detalle,
        }

    # ------------------------------------------------------------------ #
    #  HELPERS PARA LIMPIAR TEXTO
    # ------------------------------------------------------------------ #


    def parse_precio_usd(self, texto: str) -> Decimal:
        """
        Ejemplos posibles del texto:
        'Precio preferente\n67.68 USD  Unidad'
        'Precio preferente\n67,68 USD  Unidad'
        'Precio preferente\n1.234,56 USD  Unidad'
        """
        s = texto
        for basura in ["Precio preferente", "USD", "Unidad"]:
            s = s.replace(basura, "")
        s = s.strip()

        # Tomamos la primera “parte numérica” que tenga dígitos y opcionalmente . o ,
        match = re.search(r"(\d[\d\.,]*)", s)
        if not match:
            return Decimal("0")

        num_str = match.group(1)

        # Caso 1: tiene punto Y coma -> usualmente formato latino: 1.234,56
        #         . = miles, , = decimal
        if "." in num_str and "," in num_str:
            num_str = num_str.replace(".", "").replace(",", ".")
        # Caso 2: solo tiene coma -> asumimos coma decimal: 67,68
        elif "," in num_str:
            num_str = num_str.replace(",", ".")
        # Caso 3: solo tiene punto -> lo tomamos como decimal normal: 67.68
        # (no hacemos nada)

        try:
            return Decimal(num_str)
        except Exception:
            return Decimal("0")







    def parse_stock(self, texto: str) -> int:
        """
        Ejemplos:
        '7 unidades disponible'
        '+ de 20 disponible'
        """
        if not texto:
            return 0

        if "+ de" in texto:
            m = re.search(r"\+ de\s+(\d+)", texto)
            if m:
                return int(m.group(1))
            return 20

        m = re.search(r"(\d+)", texto)
        return int(m.group(1)) if m else 0





