
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import pandas as pd
import os

app = Flask(__name__)

@app.route("/tiktok", methods=["GET"])
def scrape_tiktok():
    key = request.args.get("q")

    if not key:
        return jsonify({
            "mensaje": "scraping tik toook",
            "error": "Actualmente este acceso devuelve un estado 400 (Bad Request)",
            "creador": "Carlos Villena",
        }), 400

    print(f"[INFO] Scraping con palabra clave: {key}")

    video_url = f"https://www.tiktok.com/search?q={key}"

    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(video_url)
    time.sleep(2)

    # Hacer scroll para cargar más resultados (opcional)
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    # Buscar todas las cajas de video
    video_boxes = driver.find_elements(
        By.CSS_SELECTOR,
        'div.css-1soki6-DivItemContainerForSearch.e19c29qe9'
    )

    print(f"\nSe encontraron {len(video_boxes)} videos.\n")

    # Extraer URLs
    video_urls = []
    for index, box in enumerate(video_boxes):
        try:
            link_element = box.find_element(By.TAG_NAME, 'a')
            href = link_element.get_attribute('href')
            if href and "tiktok.com" in href:
                #print(f"Video {index + 1}: {href}")
                video_urls.append(href)
        except Exception as e:
            print(f"Video {index + 1}: Error - {e}")

    df = pd.DataFrame({
        "red_social": "tiktok",
        "palabra_clave": key,
        "url": video_urls
    })

    df = df.drop_duplicates()
    driver.quit()
    return jsonify(df.to_dict(orient="records"))

    print("\n✅ Proceso completado. URLs guardadas en 'urls_videos_tiktok.txt'.")

@app.route("/facebook", methods=["GET"])
def scrape_facebook():
    key = request.args.get("q")

    if not key:
        return jsonify({
            "mensaje": "¡Hola! 😊 Si deseas hacer scraping en DeepFeel, intenta acceder a la URL con el formato: https://deepfeel-scrapper-facebook-516257126680.us-central1.run.app/?q=palabra_clave ",
            "error": "Actualmente este acceso devuelve un estado 400 (Bad Request)",
            "creador": "Carlos Villena",
        }), 400

    print(f"[INFO] Scraping con palabra clave: {key}")
    video_url = f"https://www.facebook.com/search/videos/?q={key}"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(video_url)

    try:
        with open('fb_cookies.json', 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            if "sameSite" not in cookie or cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                cookie["sameSite"] = "Lax"
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error al agregar cookie: {cookie.get('name', '')}, {e}")
        driver.refresh()
    except Exception as e:
        print(f"[ERROR] Cargando cookies: {e}")

    URL_df = []
    palabra_key = []
    flag = False

    while True:
        if flag:
            break

        driver.execute_script("window.scrollBy(0, 1500);")
        wait = WebDriverWait(driver, 15)
        cajas = wait.until(EC.presence_of_all_elements_located((
            By.XPATH, "//div[contains(@class, 'x78zum5') and .//a]"
        )))

        print(f"Se encontraron {len(cajas)} cajas.")
        url = []

        for i, caja in enumerate(cajas, 1):
            try:
                enlace = caja.find_element(By.XPATH, ".//a[@href]")
                href = enlace.get_attribute("href")
                url.append(href)
                palabra_key.append(key)

                if len(url) >= 15:
                    flag = True
            except Exception as e:
                print(f"URL {i}: No se encontró href - {e}")

        URL_df += url

    driver.quit()

    df = pd.DataFrame({
        "red_social": "facebook meta",
        "palabra_clave": palabra_key,
        "url": URL_df
    })

    df = df.drop_duplicates()

    return jsonify(df.to_dict(orient="records"))





if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)