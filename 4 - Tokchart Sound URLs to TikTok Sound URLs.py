# 4. Retrieve TikTok Sound URLs from Tokchart Sound URLs

import requests
from bs4 import BeautifulSoup
import pandas as pd

# Define the paths to the input and output Excel files
input_excel_path = # path to 'Tokchart Sound URLs.csv''
output_excel_path = # path to 'TikTok Sound URLs.xlsx'
log_file_path = # path to 'Tokchart_skipped_sounds.log'

def get_tiktok_url(tokchart_url):
    try:
        response = requests.get(tokchart_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')
        tiktok_anchor = soup.find('a', class_='t-btn bg-cadet bg-cadet hover:bg-cadet-900 active:bg-cadet-900')
        if tiktok_anchor:
            tiktok_url = tiktok_anchor['href']
            print(f"Found TikTok URL: {tiktok_url}")
            return tiktok_url
        else:
            print(f"No TikTok URL found for: {tokchart_url}")
            return None
    except Exception as e:
        print(f"Error fetching URL {tokchart_url}: {e}")
        with open(log_file_path, mode='a', encoding='utf-8') as log_file:
            log_file.write(f"Error fetching URL {tokchart_url}: {e}\n")
        return None

# Read the input Excel file
df = pd.read_excel(input_excel_path)

# Add a new column for the TikTok sound URL
df['TikTok Sound URL'] = ""

# Process each row in the DataFrame
for index, row in df.iterrows():
    print(f"Processing row {index + 1} of {len(df)}")
    tokchart_url = row['Sound Tokchart URL']
    tiktok_url = get_tiktok_url(tokchart_url)
    df.at[index, 'TikTok Sound URL'] = tiktok_url if tiktok_url else ""

# Save the results to a new Excel file
df.to_excel(output_excel_path, index=False)

print(f"Data successfully saved to {output_excel_path}")