# 7. Filter out videos over 30 seconds by placing them in a separate folder

!pip install --upgrade gspread google-auth google-auth-oauthlib google-auth-httplib2 pandas moviepy

from google.colab import auth
auth.authenticate_user()

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.colab import drive
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from google.auth import default
import os
from moviepy.editor import VideoFileClip
import numpy as np

# Mount Google Drive
drive.mount('/content/drive')
drive.mount("/content/drive", force_remount=True)

# Authenticate and initialize Google Sheets and Drive APIs
creds, _ = default()
gc = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# Function to move file to a new folder
def move_file(file_id, folder_id):
    try:
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        file = drive_service.files().update(fileId=file_id,
                                            addParents=folder_id,
                                            removeParents=previous_parents,
                                            fields='id, parents').execute()
        print(f"Moved file {file_id} to folder {folder_id}")
    except Exception as e:
        print(f"Error moving file {file_id}: {e}")

# Create a new folder
def create_folder(folder_name, parent_folder_id):
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        print(f"Created folder {folder_name} with ID {folder.get('id')}")
        return folder.get('id')
    except Exception as e:
        print(f"Error creating folder {folder_name}: {e}")
        return None

# Function to get the ID of a folder by name
def get_folder_id(folder_name, parent_folder_id='root'):
    try:
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        if not items:
            print(f'No folder found for {folder_name} in {parent_folder_id}')
            return None
        else:
            return items[0]['id']
    except Exception as e:
        print(f"Error getting folder ID for {folder_name}: {e}")
        return None

# Function to get file ID from file name
def get_file_id(file_name, parent_folder_id):
    try:
        query = f"name='{file_name}' and '{parent_folder_id}' in parents"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name, mimeType)').execute()
        items = results.get('files', [])
        if not items:
            print(f'No file found for {file_name}')
            return None, None
        else:
            return items[0]['id'], items[0]['mimeType']
    except Exception as e:
        print(f"Error getting file ID for {file_name}: {e}")
        return None, None

# Function to get the duration of a video file
def get_video_duration(file_path):
    try:
        clip = VideoFileClip(file_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"Error getting video duration for {file_path}: {e}")
        return None

# Specify the range of folder IDs to process
start_folder_id = 1
end_folder_id = 428

# Path to the TikTok Video Metadata folder
metadata_folder_name = 'TikTokVideoMetadata'
metadata_folder_path = f'/content/drive/My Drive/{metadata_folder_name}'

# Get the ID of the TikTokVideoMetadata folder
metadata_folder_id = get_folder_id(metadata_folder_name)
if not metadata_folder_id:
    raise ValueError(f"Folder {metadata_folder_name} not found.")

# Get the ID of the TikToks folder
tikToks_folder_id = get_folder_id('TikToks', 'root')
if not tikToks_folder_id:
    raise ValueError("TikToks folder not found in My Drive.")

# List all folders in TikToks within the specified range
folders = [str(f) for f in range(start_folder_id, end_folder_id + 1) if os.path.isdir(os.path.join(f'/content/drive/My Drive/TikToks', str(f)))]
print(f"Found {len(folders)} folders in TikToks within the range {start_folder_id} to {end_folder_id}.")

# Process each folder in TikToks
for folder in folders:
    print(f"Processing folder {folder}")

    folder_id = get_folder_id(folder, tikToks_folder_id)
    if not folder_id:
        print(f"Folder ID not found for {folder}")
        continue

    # Create 'Long Videos' folder
    long_videos_folder_id = create_folder('Long Videos', folder_id)
    if not long_videos_folder_id:
        print(f"Failed to create 'Long Videos' folder in {folder}")
        continue

    # Get the ID of the Google Sheets file (not the .xlsx file)
    metadata_file_name = f'TikTok_Video_URLs_with_metadata_{folder}'
    spreadsheet_id, mime_type = get_file_id(metadata_file_name, metadata_folder_id)
    if not (spreadsheet_id and mime_type == 'application/vnd.google-apps.spreadsheet'):
        print(f"Spreadsheet ID not found or not a Google Sheets file for {metadata_file_name}")
        continue

    print(f"Loading metadata spreadsheet with ID: {spreadsheet_id}")
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.get_worksheet(0)

    # Convert the sheet to a DataFrame
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Add Video Duration column if it doesn't exist
    if 'Video Duration' not in df.columns:
        df['Video Duration'] = ""

    # List all mp4 files in the folder
    video_files = [f for f in os.listdir(f'/content/drive/My Drive/TikToks/{folder}') if f.endswith('.mp4')]

    for video_file in video_files:
        video_path = f'/content/drive/My Drive/TikToks/{folder}/{video_file}'
        duration = get_video_duration(video_path)

        # Always add the video duration to the metadata
        print(f"Video {video_file} duration: {duration} seconds")
        file_id, _ = get_file_id(video_file, folder_id)

        # Move videos longer than 30 seconds to 'Long Videos'
        if duration and duration > 30:
            print(f"Video {video_file} is longer than 30 seconds, moving to 'Long Videos'")
            if file_id:
                move_file(file_id, long_videos_folder_id)

        # Find the row corresponding to the video
        video_id = video_file.split('-')[-1].split('.')[0]
        row_index = df.index[df['Video URL'].str.endswith(video_id)].tolist()
        if row_index:
            row_index = row_index[0]
            df.at[row_index, 'Video Duration'] = duration  # Add duration to the DataFrame

            # Highlight the row if the video is longer than 30 seconds
            if duration and duration > 30:
                cell_range = f'A{row_index+2}:H{row_index+2}'  # Adjust for header row and 0-based index
                print(f"Highlighting cells {cell_range} in darker red")
                format_darker_red = {"backgroundColor": {"red": 0.8, "green": 0.2, "blue": 0.2}}
                worksheet.format(cell_range, format_darker_red)

    # Handle NaN and infinite values before updating the Google Sheet
    df = df.replace([np.inf, -np.inf], np.nan).fillna('')

    # Update the Google Sheet with the new data
    set_with_dataframe(worksheet, df)
    print(f"Updated metadata spreadsheet for folder {folder}")
