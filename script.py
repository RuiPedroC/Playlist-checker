import urllib.request
import xml.etree.ElementTree as ET
import json
import os

# Configuração das playlists e das respetivas variáveis de ambiente do Discord
PLAYLISTS = [
    {"lane": "Top Lane", "id": "PLOoaS3fNpmkI", "env_var": "WEBHOOK_TOP"},
    {"lane": "Jungle",   "id": "PLLgMZW4S1TFY", "env_var": "WEBHOOK_JUNGLE"},
    {"lane": "Mid Lane", "id": "PLWVVe2y75Idc", "env_var": "WEBHOOK_MID"},
    {"lane": "ADC",      "id": "PLUJSB1435Otk", "env_var": "WEBHOOK_ADC"},
    {"lane": "Support",  "id": "PLfnM8GCc1ktg", "env_var": "WEBHOOK_SUPP"},
    {"lane": "Overall",  "id": "PLA13YOA8Fal8", "env_var": "WEBHOOK_OVERALL"},
]
STATE_FILE = "last_videos.json"

# Carrega o histórico de vídeos enviados
last_videos = {}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            last_videos = json.load(f)
    except Exception:
        last_videos = {}

# Processa cada uma das playlists
for item in PLAYLISTS:
    lane_name = item["lane"]
    playlist_id = item["id"]
    webhook_url = os.environ.get(item["env_var"])

    if not webhook_url or playlist_id.startswith("COLOCA_ID"):
        print(f"[{lane_name}] Ignorado (ID ou Webhook em falta).")
        continue

    rss_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})

    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        entries = root.findall('atom:entry', ns)

        if not entries:
            continue

        last_id = last_videos.get(playlist_id)

        # Guarda todos os vídeos novos ainda não enviados
        new_entries = []
        for entry in entries:
            v_id = entry.find('yt:videoId', ns).text
            if v_id == last_id:
                break  # Para assim que encontra o último vídeo registado
            new_entries.append(entry)

        # Inverte para enviar do vídeo mais antigo para o mais recente
        new_entries.reverse()

        # Envia uma notificação no Discord para cada vídeo novo
        for entry in new_entries:
            video_id = entry.find('yt:videoId', ns).text
            title = entry.find('atom:title', ns).text
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            payload = json.dumps({
                "content": f"🎥 **Novo vídeo de coaching ({lane_name})!**\n**{title}**\n{video_url}"
            }).encode('utf-8')

            disc_req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            )
            urllib.request.urlopen(disc_req)

            # Atualiza o registo para cada vídeo enviado
            last_videos[playlist_id] = video_id
            print(f"[{lane_name}] Novo aviso enviado: {title}")

    except Exception as e:
        print(f"[{lane_name}] Erro ao verificar: {e}")

# Guarda o ficheiro de histórico atualizado
with open(STATE_FILE, "w") as f:
    json.dump(last_videos, f, indent=2)
