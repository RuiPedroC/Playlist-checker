import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import time


PLAYLISTS = [
    {"lane": "Top Lane", "id": "PLOoaS3fNpmkI...", "env_var": "WEBHOOK_TOP"},
    {"lane": "Jungle",   "id": "PLLgMZW4S1TFY...", "env_var": "WEBHOOK_JUNGLE"},
    {"lane": "Mid Lane", "id": "PLWVVe2y75Idc...", "env_var": "WEBHOOK_MID"},
    {"lane": "ADC",      "id": "PLUJSB1435Otk...", "env_var": "WEBHOOK_ADC"},
    {"lane": "Support",  "id": "PLfnM8GCc1ktg...", "env_var": "WEBHOOK_SUPP"},
    {"lane": "Overall",  "id": "PLA13YOA8Fal8...", "env_var": "WEBHOOK_OVERALL"},
]
STATE_FILE = "last_videos.json"

# Carrega o histórico de vídeos enviados
sent_videos = {}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Compatibilidade caso o ficheiro antigo tenha strings em vez de listas
            for k, v in data.items():
                sent_videos[k] = v if isinstance(v, list) else [v]
    except Exception as e:
        print(f"Erro ao ler {STATE_FILE}: {e}")
        sent_videos = {}

for item in PLAYLISTS:
    lane_name = item["lane"]
    playlist_id = item["id"]
    webhook_url = os.environ.get(item["env_var"])

    if not webhook_url or len(playlist_id) < 20:
        print(f"[{lane_name}] Ignorado (Webhook em falta ou ID de playlist incompleto: {playlist_id}).")
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
            print(f"[{lane_name}] Playlist vazia no RSS.")
            continue

        known_ids = sent_videos.get(playlist_id, [])

        # Filtra todos os vídeos que ainda não estão na lista de conhecidos
        new_entries = []
        for entry in entries:
            v_id = entry.find('yt:videoId', ns).text
            if v_id not in known_ids:
                new_entries.append(entry)

        if not new_entries:
            print(f"[{lane_name}] Sem vídeos novos.")
            continue

        # Inverte para enviar do mais antigo para o mais recente
        new_entries.reverse()

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

            # Regista o vídeo como enviado
            known_ids.append(video_id)
            sent_videos[playlist_id] = known_ids[-100:]  # Mantém os últimos 100 IDs
            print(f"[{lane_name}] Novo aviso enviado: {title}")
            time.sleep(1)  # Pausa de 1s para evitar Rate Limit do Discord

    except Exception as e:
        print(f"[{lane_name}] Erro ao verificar: {e}")

# Guarda o ficheiro de histórico atualizado
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_videos, f, indent=2)
