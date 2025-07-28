import time
import os
import json
import logging
from functools import wraps

from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# === MANEJO DE ERRORES GLOBALES ===
def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error en {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": str(e),
                "status": "failed"
            }), 500

    return wrapper


# === CONFIGURACIONES REUTILIZABLES ===
CHROME_OPTIONS = {
    "headless": False,
    "disable-gpu": True,
    "no-sandbox": True,
    "disable-dev-shm-usage": True,
}

WAIT_TIMEOUT = 10
MAX_SCROLL_TRIES = 4
SCROLL_PAUSE = 1.5


# === FUNCIONES AUXILIARES ===
def setup_chrome():
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    return webdriver.Chrome(options=options)


def load_cookies(driver, cookie_file="fb_cookies.json"):
    try:
        with open(cookie_file, 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            cookie["sameSite"] = "Lax" if "sameSite" not in cookie else cookie["sameSite"]
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Error al agregar cookie: {cookie.get('name', '')}, {e}")
        driver.refresh()
    except FileNotFoundError:
        logger.info("No se encontraron cookies.")
    except Exception as e:
        logger.warning(f"[ERROR] Cargando cookies: {e}")


def format_response(df, platform):
    df = df.drop_duplicates()
    return jsonify({
        "status": "success",
        "platform": platform,
        "data": df.to_dict(orient="records")
    })


# === RUTAS PRINCIPALES ===
@app.route("/tiktok", methods=["GET"])
@handle_errors
def scrape_tiktok():
    keyword = request.args.get("q")
    if not keyword:
        return jsonify({
            "status": "error",
            "mensaje": "Falta parámetro 'q'",
            "creador": "Carlos Villena"
        }), 400

    logger.info(f"[INFO] Scraping TikTok con palabra clave: {keyword}")

    url = f"https://www.tiktok.com/search?q= {keyword}"

    with setup_chrome() as driver:
        driver.get(url)
        time.sleep(4)

        for _ in range(2):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE)

        video_boxes = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.css-1soki6-DivItemContainerForSearch.e19c29qe9'))
        )

        video_urls = []
        usuarios_tiktok = []
        nombres_reales = []
        titulos = []
        descripciones = []
        fechas = []
        likes_list = []
        for i, box in enumerate(video_boxes):
            try:
                link_element = box.find_element(By.TAG_NAME, 'a')
                href = link_element.get_attribute('href')
                if href and "tiktok.com" in href:
                    video_urls.append(href)

                try:
                        desc_text = box.find_element(By.CSS_SELECTOR, 'div.css-f22ew5-DivMetaCaptionLine').text.strip()
                        descripciones.append(desc_text)

                        if desc_text.startswith('#'):
                            titulos.append("")
                        else:
                            titulo_libre = desc_text.split('#')[0].strip()
                            titulos.append(titulo_libre)
                except:
                        descripciones.append("")
                        titulos.append("")

                    # --- Usuario TikTok (@) ---
                try:
                        user_link = box.find_element(By.CSS_SELECTOR, 'a[href*="/@"]')
                        user_url = user_link.get_attribute('href')
                        usuario = user_url.split('/@')[-1].split('/')[0]
                        usuarios_tiktok.append(usuario)
                except:
                        usuarios_tiktok.append("")

                    # --- Nombre real (del aria-label) ---
                try:
                        aria_label = user_link.get_attribute('aria-label')
                        if aria_label and "Perfil de " in aria_label:
                            nombre_real = aria_label.replace("Perfil de ", "").strip()
                        else:
                            nombre_real = usuarios_tiktok[-1]  # fallback: usar @
                        nombres_reales.append(nombre_real)
                except:
                        nombres_reales.append("")

                    # --- Fecha ---
                try:
                        fecha = box.find_element(By.CSS_SELECTOR, 'div.css-1lf486f-DivTimeTag').text.strip()
                        fechas.append(fecha)
                except:
                        fechas.append("")

                try:
                        likes = box.find_element(By.CSS_SELECTOR, 'strong[data-e2e="video-views"]').text.strip()
                        likes_list.append(likes)
                except:
                        likes_list.append("")


            except Exception as e:
                logger.warning(f"Video {i + 1}: Error - {e}")



        df = pd.DataFrame({
            "red_social": "tiktok",
            "palabra_clave": keyword,
            "url": video_urls,
            "usuario_tiktok": usuarios_tiktok,
            "titulo": titulos,
            "descripcion": descripciones,
            "likes": likes_list,
            "fecha_publicacion": fechas
        })

    return format_response(df, "TikTok")


@app.route("/facebook", methods=["GET"])
@handle_errors
def scrape_facebook():
    keyword = request.args.get("q")
    if not keyword:
        return jsonify({
            "status": "error",
            "mensaje": "Falta parámetro 'q'",
            "creador": "Carlos Villena"
        }), 400

    logger.info(f"[INFO] Scraping Facebook con palabra clave: {keyword}")

    url = f"https://www.facebook.com/search/videos/?q= {keyword}"

    driver = setup_chrome()
    driver.get(url)

    load_cookies(driver)

    URL_df = []
    palabra_key = []

    scroll_tries = 0
    while scroll_tries < MAX_SCROLL_TRIES:
        try:
            cajas = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'x1a2cdl4') and .//a]"))
            )
            logger.info(f"Se encontraron {len(cajas)} videos.")

            for i, caja in enumerate(cajas):
                try:
                    enlace = caja.find_element(By.XPATH, ".//a[@href]")
                    href = enlace.get_attribute("href")
                    URL_df.append(href)
                    palabra_key.append(keyword)
                except Exception as e:
                    logger.warning(f"URL {i + 1}: No se encontró href - {e}")

            driver.execute_script("window.scrollBy(0, 1500);")
            time.sleep(SCROLL_PAUSE)
            scroll_tries += 1

        except TimeoutException:
            logger.warning("Tiempo de espera agotado al buscar elementos de video.")
            break

    driver.quit()

    df = pd.DataFrame({
        "red_social": "facebook meta",
        "palabra_clave": palabra_key,
        "url": URL_df
    })

    return format_response(df, "Facebook")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)