from flask import Flask, request
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import os
import re # We'll use regex for more robust URL matching

# --- Configuration ---
# Base URL for the scraping target
BASE_SEARCH_URL = "https://bir23.com/az/searchCar?country_id=1&plateNumber={plaka}"
# Base URL for the storage where car media is kept (for better filtering)
MEDIA_BASE_URL = "https://auto-car-project.fra1.digitaloceanspaces.com/"

app = Flask(__name__)

# --- Core Scraping Function ---
def get_all_auto_data(plaka):
    """
    Fetches all car-related data (images, videos, info, social links) 
    for a given license plate number (plaka) from the target website.
    """
    # 1. Improved Request Resilience and Headers
    try:
        url = BASE_SEARCH_URL.format(plaka=plaka)
        
        # Use a session for more "natural" request handling
        session = requests.Session()
        ua = UserAgent()
        
        # More comprehensive and realistic headers
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/", # Pretend to come from Google
            "DNT": "1", # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Increased timeout for better resilience on slower connections
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        soup = BeautifulSoup(response.text, "html.parser")

        # --- Data Containers ---
        imgs = set()
        videos = set()
        infos = {}
        social_links = {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}

        # --- Data Extraction ---

        # 2. Resimler (Images)
        # We look for all <img> tags and filter based on the media base URL 
        # to ensure we only collect relevant car media.
        for img in soup.find_all("img"):
            src = img.get("src", "")
            # Use regex to robustly check if the src starts with the media base URL
            if re.match(r"^" + re.escape(MEDIA_BASE_URL), src):
                imgs.add(src)

        # 3. Videolar (Videos)
        # Search for <video> and <source> tags
        for video in soup.find_all("video"):
            # Check the video tag's 'src'
            src_video = video.get("src", "")
            if re.match(r"^" + re.escape(MEDIA_BASE_URL), src_video):
                videos.add(src_video)
            
            # Check for <source> tags inside the video
            for source in video.find_all("source"):
                src_source = source.get("src", "")
                if re.match(r"^" + re.escape(MEDIA_BASE_URL), src_source):
                    videos.add(src_source)

        # 4. Bilgiler (Info Table)
        # The structure is assumed to be within a table (<tr> with two <td>s)
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 2:
                # Use .get_text(strip=True) to clean up whitespace
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                # Filter out empty keys or values just in case
                if key and val:
                    infos[key] = val

        # 5. Sosyal medya linkleri (Social Media Links)
        # Filtering based on the known class names
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Get the classes as a list and join them for easy checking
            classes = " ".join(a.get("class", [])) 
            
            if "tiktok-gradient" in classes and href not in social_links.values():
                social_links["tiktok"] = href
            elif "insta-gradient" in classes and href not in social_links.values():
                social_links["instagram"] = href
            elif "wp-gradient" in classes and href not in social_links.values():
                # Whatsapp links are often special, so we might keep the original href
                social_links["whatsapp"] = href

        # Successful extraction
        return list(imgs), list(videos), infos, social_links
        
    except requests.exceptions.HTTPError as e:
        print(f"Hata: HTTP Status Code {e.response.status_code}. Məlumat tapılmadı və ya bloklandı.")
        # Return empty data on 4xx/5xx errors
        return [], [], {}, {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}
    except requests.exceptions.RequestException as e:
        print(f"Hata oluştu: Bağlantı sorunu veya zaman aşımı: {e}")
        # Return empty data on connection/timeout errors
        return [], [], {}, {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}
    except Exception as e:
        print(f"Bilinməyən Hata oluştu: {e}")
        # Return empty data for any other unexpected errors
        return [], [], {}, {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}


# --- Flask Route (Index) ---
@app.route("/")
def index():
    # ... (Keep the rest of the index function as is, it's mostly HTML generation) ...
    plaka = request.args.get("plaka")
    images, videos, infos, socials = [], [], {}, {"tiktok": "Yox", "instagram": "Yox", "whatsapp": "Yox"}
    
    # Clean and standardize the plaka input (e.g., remove spaces and convert to uppercase)
    if plaka:
        # Example cleaning: remove spaces and make it uppercase for consistency
        cleaned_plaka = plaka.replace(" ", "").upper() 
        images, videos, infos, socials = get_all_auto_data(cleaned_plaka)

    message = ""
    # Check for empty results to display a friendly message
    if plaka and not images and not videos and not infos:
        message = f"Plaka '{plaka}' üçün məlumat tapılmadı :( Zəhmət olmasa plakanı düzgün daxil edin."

    # --- HTML Generation ---

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
        # Improved table styling for better readability
        info_html += "<h2 style='color:#0ff;'>Avtomobil Məlumatları</h2>"
        info_html += "<table style='margin: 20px auto; border-collapse: collapse; border: 2px solid #0ff; border-radius: 10px; overflow: hidden;'>"
        for k, v in infos.items():
            # Alternating row colors for better visibility
            info_html += f"<tr><td style='padding:10px; border:1px solid #555; background:#333; color:white; text-align:left;'><b>{k}</b></td><td style='padding:10px; border:1px solid #555; background:#222; color:#0ff; text-align:left;'>{v}</td></tr>"
        info_html += "</table>"

    social_html = f"""
        <h2 style='color:#0ff;'>Əlaqə Linkləri</h2>
        <div style="margin-top: 20px;">
            <div class="led"><b>TikTok:</b> <a href="{socials['tiktok']}" target="_blank" style="color:#0ff;">{socials['tiktok'] if socials['tiktok'] != 'Yox' else 'Yoxdur'}</a></div>
            <div class="led"><b>Instagram:</b> <a href="{socials['instagram']}" target="_blank" style="color:#0ff;">{socials['instagram'] if socials['instagram'] != 'Yox' else 'Yoxdur'}</a></div>
            <div class="led"><b>WhatsApp:</b> <a href="{socials['whatsapp']}" target="_blank" style="color:#0ff;">{socials['whatsapp'] if socials['whatsapp'] != 'Yox' else 'Yoxdur'}</a></div>
        </div>
    """

    # --- Final HTML Structure ---
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Plaka Axtarışı | CekaMods</title>
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
                text-decoration: none; /* For links inside .led */
            }}
            .led a {{
                color: #0ff; /* Maintain neon color for links */
                text-decoration: none;
            }}
            input, button {{
                padding: 10px;
                font-size: 16px;
                margin: 5px;
                border-radius: 6px;
                border: none;
            }}
            button {{
                cursor: pointer;
                background-color: #0ff;
                color: #111;
                font-weight: bold;
            }}
            .message {{
                margin-top: 20px;
                color: #f66;
                font-weight: bold;
            }}
            /* Table specific styles moved into info_html for simplicity, 
               but added a new style for the image/video containers for better layout */
            .media-container {{
                margin-top: 30px;
                padding: 10px;
                border-top: 1px dashed #555;
            }}
        </style>
    </head>
    <body>
        <h1>🚗 CekaMods Maşın Axtarış Sistemi</h1>
        <form method="get">
            <input class="led" name="plaka" placeholder="Məs: 10FF110" required value="{plaka or ''}">
            <button type="submit">Axtar</button>
        </form>

        <div class="message">{message}</div>

        <div class="media-container">
            {images_html}
            {videos_html}
        </div>

        {info_html}
        {social_html}
        
    </body>
    </html>
    """

if __name__ == "__main__":
    # Render'da PORT gelir, yoksa 1111 olarak ayarlanır.
    port = int(os.environ.get("PORT", 1111))  
    # host="0.0.0.0" allows external access in deployment environments like Render.
    app.run(host="0.0.0.0", port=port)
        
