# NB: At this point, operations were moved onto Google Colab for efficiency purposes
# 6. Download videos and create video metadata spreadsheets

from google.colab import drive
drive.mount('/content/drive')

!pip install yt-dlp
!pip install pandas
!pip install openpyxl
!pip install beautifulsoup4
!pip install requests
!pip install xlsxwriter

import os
import json
import requests
import yt_dlp
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time

def download_tiktok_video(url, folder_name, tab_number, video_id, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            break
        except (requests.RequestException, requests.Timeout) as e:
            print(f"Attempt {attempt + 1} failed for URL {url}: {e}")
            if attempt + 1 == retries:
                print(f"Giving up on URL {url} after {retries} attempts")
                return "N/A", [], "N/A", [], "N/A", "N/A", "N/A", "N/A"
            time.sleep(5)

    script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
    if script_tag:
        try:
            data = json.loads(script_tag.string)
            video_info = data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']

            captions_text = video_info.get('desc', 'N/A')
            hashtags_text = [tag for tag in captions_text.split() if tag.startswith('#')]
            create_time = video_info.get('createTime', 'N/A')
            date = datetime.utcfromtimestamp(int(create_time)).strftime('%Y-%m-%d %H:%M:%S') if create_time != 'N/A' else 'N/A'
            diversification_labels = video_info.get('diversificationLabels', [])
            music_info = video_info.get('music', {})
            music_id = music_info.get('id', 'N/A')
            music_title = music_info.get('title', 'N/A')
            location_created = video_info.get('locationCreated', 'N/A')
        except (KeyError, TypeError, ValueError) as e:
            print(f"Error parsing video info for URL {url}: {e}")
            captions_text = "N/A"
            hashtags_text = []
            date = "N/A"
            diversification_labels = []
            music_id = "N/A"
            music_title = "N/A"
            location_created = "N/A"
    else:
        captions_text = "N/A"
        hashtags_text = []
        date = "N/A"
        diversification_labels = []
        music_id = "N/A"
        music_title = "N/A"
        location_created = "N/A"

    print("Captions:", captions_text)
    print("Hashtags:", hashtags_text)
    print("Date:", date)
    print("Diversification Labels:", diversification_labels)
    print("Music ID:", music_id)
    print("Music Title:", music_title)
    print("Location Created:", location_created)

    ydl_opts = {
        'outtmpl': os.path.join(folder_name, f"{tab_number}-{video_id}.mp4"),
    }

    for attempt in range(retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to download video for URL {url}: {e}")
            if attempt + 1 == retries:
                print(f"Giving up on video download for URL {url} after {retries} attempts")
                break
            time.sleep(5)

    return captions_text, hashtags_text, date, diversification_labels, music_id, music_title, location_created

def process_tiktok_urls(input_file, output_file_base):
    data = pd.read_excel(input_file, sheet_name=None)
    tabs = list(data.items())

    for tab, df in tabs:
        output_file = f"{output_file_base}_{tab}.xlsx"
        writer = pd.ExcelWriter(output_file, engine='xlsxwriter')

        folder_name = os.path.join('/content/drive/My Drive/TikToks', str(tab))
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        urls_data = []

        for url in df['Video URL'].dropna():
            try:
                video_id = url.split('/')[-1]
                captions, hashtags, date, diversification_labels, music_id, music_title, location_created = download_tiktok_video(url, folder_name, tab, video_id)
                urls_data.append([url, captions, "; ".join(hashtags), date, "; ".join(diversification_labels), music_id, music_title, location_created])
            except Exception as e:
                print(f"Failed to process URL {url}: {e}")
                urls_data.append([url, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])

        output_df = pd.DataFrame(urls_data, columns=["Video URL", "Captions", "Hashtags", "Date", "Diversification Labels", "Music ID", "Music Title", "Location Created"])
        output_df.to_excel(writer, sheet_name=tab, index=False)

        writer.close()
        print(f"Metadata saved to {output_file}")

# File paths
input_file = '/content/drive/My Drive/TikTok Video URLs.xlsx'
output_file_base = '/content/drive/My Drive/TikTok Video Metadata/TikTok_Video_URLs_with_metadata'
process_tiktok_urls(input_file, output_file_base)