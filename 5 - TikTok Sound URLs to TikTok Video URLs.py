# 5. Run simulated browser requests to retrieve TikTok videos from TikTok Sound URLs

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup Chrome options for headless mode
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Initialize WebDriver with the ChromeDriverManager to handle driver installation
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Read the input Excel file
input_excel_path = # path to 'TikTok Sound URLs.xlsx'
df = pd.read_excel(input_excel_path)

# Create a new Excel writer object
output_excel_path = # path to 'TikTok Video URLs.xlsx'
writer = pd.ExcelWriter(output_excel_path, engine='xlsxwriter')

# Process each row in the DataFrame
for index, row in df.iterrows():
    number = row['Number']
    tiktok_url = row['TikTok Sound URL']
    print(f"Processing row {index + 1} of {len(df)}: {tiktok_url}")

    try:
        # Open TikTok Sound URL
        driver.get(tiktok_url)

        # Allow the page to load
        time.sleep(5)

        # Scroll to load more content three times
        scroll_pause_time = 2

        for _ in range(8):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)

        # Get all URLs on the page containing '/video/'
        all_urls = driver.find_elements(By.TAG_NAME, 'a')
        video_urls = {url.get_attribute('href') for url in all_urls if '/video/' in (url.get_attribute('href') or '')}

        # Print the collected URLs for the current TikTok Sound URL
        print(f"Found {len(video_urls)} unique video URLs for {tiktok_url}")
        for url in video_urls:
            print(url)

        # Create a DataFrame for the video URLs and write to a new sheet in the Excel file
        video_urls_df = pd.DataFrame(list(video_urls), columns=['Video URL'])
        video_urls_df.to_excel(writer, sheet_name=str(number), index=False)
    except Exception as e:
        print(f"Error processing URL {tiktok_url}: {e}")

# Save and close the Excel file
writer.close()

# Close WebDriver
driver.quit()

print(f"Data successfully saved to {output_excel_path}")