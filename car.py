from flask import Flask, request
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import os

app = Flask(__name__)

def get_all_auto_data(plaka):
    try:
        url = f"https://auto.bir23.com/az/searchCar?country_id=1&plateNumber={plaka}"
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        imgs = set()
        videos = set()
        infos = {}
        social_links = {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}

        # Resimler
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if any(x in src for x in ["/images/cars/", "/az/cars/", "medias/photos"]):
                imgs.add(src)

        # Videolar
        for video in soup.find_all("video"):
            src = video.get("src", "")
            if src and any(x in src for x in ["/images/cars/", "/az/cars/", "medias/photos"]):
                videos.add(src)
            for source in video.find_all("source"):
                src = source.get("src", "")
                if any(x in src for x in ["/images/cars/", "/az/cars/", "medias/photos"]):
                    videos.add(src)

        # Bilgiler (table satırlarında olabilir)
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                infos[key] = val

        # Sosyal medya linkleri class'lara göre
        for a in soup.find_all("a", href=True):
            href = a["href"]
            classes = " ".join(a.get("class", []))
            if "tiktok-gradient" in classes:
                social_links["tiktok"] = href
            elif "insta-gradient" in classes:
                social_links["instagram"] = href
            elif "wp-gradient" in classes:
                social_links["whatsapp"] = href

        return list(imgs), list(videos), infos, social_links
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return [], [], {}, {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}

@app.route("/")
def index():
    plaka = request.args.get("plaka")
    images, videos, infos, socials = [], [], {}, {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}
    if plaka:
        images, videos, infos, socials = get_all_auto_data(plaka)

    message = ""
    if plaka and not images and not videos and not infos:
        message = f"Plaka '{plaka}' üçün məlumat tapılmadı :("

    images_html = "".join(
        f'<div class="led"><img src="{url}" style="max-width:90%; border-radius:10px; max-height:300px;"></div>'
        for url in images
    )

    videos_html = "".join(
        f'''
        <div class="led">
            <video controls style="max-width:90%; border-radius:10px; max-height:300px;">
                <source src="{url}" type="video/mp4">
            </video>
        </div>
        '''
        for url in videos
    )

    info_html = ""
    if infos:
        info_html += "<table style='margin: 20px auto; border-collapse: collapse;'>"
        for k, v in infos.items():
            info_html += f"<tr><td style='padding:5px; border:1px solid #555;'>{k}</td><td style='padding:5px; border:1px solid #555;'>{v}</td></tr>"
        info_html += "</table>"

    social_html = f"""
        <div style="margin-top: 20px;">
            <div class="led"><b>TikTok:</b> {socials['tiktok']}</div>
            <div class="led"><b>Instagram:</b> {socials['instagram']}</div>
            <div class="led"><b>WhatsApp:</b> {socials['whatsapp']}</div>
        </div>
    """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Plaka Axtarışı</title>
        <style>
            body {{
                background: #111;
                color: white;
                text-align: center;
                font-family: sans-serif;
                padding: 20px;
            }}
            .led {{
                display: inline-block;
                background: black;
                color: cyan;
                border: 2px solid cyan;
                padding: 10px;
                margin: 10px;
                border-radius: 10px;
            }}
            input, button {{
                padding: 10px;
                font-size: 16px;
                margin: 5px;
                border-radius: 6px;
            }}
            .message {{
                margin-top: 20px;
                color: #f66;
                font-weight: bold;
            }}
            table td {{
                background: #222;
                color: #0ff;
            }}
        </style>
    </head>
    <body>
        <h1>🚗 CekaMods Maşın Axtarış Sistemi</h1>
        <form method="get">
            <input class="led" name="plaka" placeholder="Məs: 10FF110" required value="{plaka or ''}">
            <button class="led" type="submit">Axtar</button>
        </form>

        {images_html}
        {videos_html}
        {info_html}
        {social_html}

        <div class="message">{message}</div>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 1111))  # Render'da PORT gelir, yoksa 1111
    app.run(host="0.0.0.0", port=port)
