# 1. Retrieve top artists from Tokchart

import requests
from bs4 import BeautifulSoup
import csv

base_url = "https://tokchart.com/dashboard/lists/artists/most-popular?page="
artist_urls = []

# Loop through pages 1 to 100
for page in range(1, 101):
    url = base_url + str(page)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for a_tag in soup.find_all('a', href=True):
        if a_tag['href'].startswith("https://tokchart.com/dashboard/artists"):
            artist_urls.append(a_tag['href'])

# Write the URLs to a CSV file
with open('Tokchart Artist URLs.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Artist URL"])
    for url in artist_urls:
        writer.writerow([url])

print(f"Collected {len(artist_urls)} artist URLs.")