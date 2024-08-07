# 3. Download Sound mp3s from Sound URLs

import os
import re
import pandas as pd
import requests
import mimetypes

# Define the input Excel file path
input_excel_path = # path to 'Tokchart Sound URLs.csv'

# Read the input Excel file
df = pd.read_excel(input_excel_path)

# Define the output directory
output_dir = # path to 'Downloaded Audio Files'
os.makedirs(output_dir, exist_ok=True)

# Function to clean the filename
def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

# Function to download the audio file
def download_audio_file(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Determine the file extension from the MIME type
        content_type = response.headers.get('content-type')
        extension = mimetypes.guess_extension(content_type.split(';')[0])
        if not extension:
            extension = ".mp3"  # Default extension if MIME type is not recognized
        
        # Save the file with the appropriate extension
        save_path = save_path + extension
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Downloaded: {save_path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

# Process each row in the DataFrame
for index, row in df.iterrows():
    number = row['Number']
    title = row['Title']
    source_url = row['Source sound URL']
    
    # Generate the filename
    filename = f"{number} - {clean_filename(title)}"
    save_path = os.path.join(output_dir, filename)
    
    # Download the audio file
    download_audio_file(source_url, save_path)

print("All files downloaded.")