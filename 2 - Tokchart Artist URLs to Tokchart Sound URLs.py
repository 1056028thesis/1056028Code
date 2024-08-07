# 2. Retrieve top Sounds from top Artists

import csv
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Define the paths to the input and output CSV files
input_csv_path = # path to 'Tokchart Artist URLs.csv'
output_csv_path = # path to 'Tokchart Sound URLs.csv'
log_file_path = # path to 'Tokchart_skipped_artists.log'

def get_sounds_info(artist, url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL for artist {artist}: {e}")
        with open(log_file_path, mode='a', encoding='utf-8') as log_file:
            log_file.write(f"Error fetching URL for artist {artist}: {e}\n")
        return []

    sounds_info = []

    # Find all rows in the table body
    sound_rows = soup.select('tbody > tr')

    for row in sound_rows:
        try:
            # Find the sound URL
            sound_anchor = row.find('a', class_='block shrink-0 w-12 h-12 rounded-full mr-2 sm:mr-3 bg-indigo-500 overflow-hidden')
            if not sound_anchor:
                continue
            sound_url = sound_anchor['href']
            print(f"Found sound URL: {sound_url}")
            
            # Find the sound title
            title_element = row.find('a', class_='hover:underline font-medium text-gray-800')
            if not title_element:
                print(f"Title element not found for sound URL: {sound_url}")
                continue
            sound_title = title_element.text.strip()
            print(f"Found sound title: {sound_title}")

            # Find all <td> elements
            td_elements = row.find_all('td')
            if len(td_elements) < 3:
                print(f"Not enough <td> elements found for sound URL: {sound_url}")
                continue

            # Find the views in the third <td> element
            views_div = td_elements[2].find('div', class_='text-center')
            if not views_div:
                print(f"Views element not found for sound URL: {sound_url}")
                continue
            views = views_div.text.strip()
            print(f"Found views: {views}")

            sounds_info.append((artist, sound_title, sound_url, views))
        except Exception as e:
            print(f"Error processing sound for artist {artist}: {e}")
            with open(log_file_path, mode='a', encoding='utf-8') as log_file:
                log_file.write(f"Error processing sound for artist {artist} at URL {url}: {e}\n")

    return sounds_info

# Read the input CSV file
artists = []
with open(input_csv_path, mode='r', encoding='latin1') as file:
    reader = csv.reader(file)
    next(reader)  # Skip the header
    for row in reader:
        try:
            artists.append((row[0], row[1]))
        except Exception as e:
            print(f"Error reading row {row}: {e}")
            with open(log_file_path, mode='a', encoding='utf-8') as log_file:
                log_file.write(f"Error reading row {row}: {e}\n")

# Scrape the data for each artist
all_sounds_info = []
for artist, url in artists:
    print(f"Processing artist: {artist}, URL: {url}")
    sounds_info = get_sounds_info(artist, url)
    if sounds_info:
        all_sounds_info.extend(sounds_info)
    else:
        print(f"No sounds found for artist {artist}")

# Create a DataFrame and save to a new CSV file
df = pd.DataFrame(all_sounds_info, columns=['Artist', 'Title', 'Sound URL', 'Total Views'])
df.to_csv(output_csv_path, index=False)

print(f"Data successfully saved to {output_csv_path}")
