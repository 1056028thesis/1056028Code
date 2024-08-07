# 8. Filter out Sounds using audio fingerprinting

!pip install gspread gspread-formatting pydub librosa fastdtw
!apt-get install -y ffmpeg

from google.colab import auth
auth.authenticate_user()

from googleapiclient.discovery import build
from google.colab import drive
import gspread
from google.auth import default
from gspread_formatting import CellFormat, format_cell_range, Color
import os
import subprocess
import shutil
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pydub import AudioSegment
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
import pandas as pd

# Mount Google Drive
drive.mount('/content/drive')

# Authenticate and initialize Google Sheets and Drive APIs
creds, _ = default()
gc = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# Function to extract audio from video using subprocess
def extract_audio(video_path, audio_path):
    try:
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path, '-y']
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio from {video_path}: {e}")
        raise

# Function to load audio and convert to a numpy array
def load_audio(file_path, target_sr=11025):
    audio = AudioSegment.from_file(file_path)
    samples = np.array(audio.get_array_of_samples())
    frame_rate = audio.frame_rate
    # Downsample the audio
    samples = librosa.resample(samples.astype(float), orig_sr=frame_rate, target_sr=target_sr)
    duration = len(samples) / target_sr
    return samples, target_sr

# Function to compute MFCC features with retry mechanism
def compute_mfcc_with_retry(audio, sr, n_mfcc=13, retries=1):
    for attempt in range(retries + 1):
        mfccs = compute_mfcc(audio, sr, n_mfcc)
        if mfccs is not None:
            return mfccs
    return None

# Function to compute MFCC features
def compute_mfcc(audio, sr, n_mfcc=13):
    max_val = np.max(np.abs(audio))
    if max_val == 0:
        return None
    y = audio.astype(float) / max_val
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    return mfccs

# Function to check if two audio segments match and return the match score using rolling window
def audio_match_with_rolling_window(audio1, sr1, audio2, sr2, step=50, n_mfcc=13):
    mfcc1 = compute_mfcc_with_retry(audio1, sr1, n_mfcc)
    mfcc2 = compute_mfcc_with_retry(audio2, sr2, n_mfcc)

    if mfcc1 is None or mfcc2 is None:
        return None, None, None

    best_match_score = float('-inf')
    best_match_position = None

    # Use a rolling window over MFCC1 to find the best matching segment
    for i in range(0, mfcc1.shape[1] - mfcc2.shape[1] + 1, step):
        mfcc1_segment = mfcc1[:, i:i + mfcc2.shape[1]]
        distance, _ = fastdtw(mfcc1_segment.T, mfcc2.T, dist=euclidean)
        match_score = -distance  # Invert distance to match similarity
        if match_score > best_match_score:
            best_match_score = match_score
            best_match_position = i

    # Calculate start and end times based on the best matching position
    if best_match_position is not None:
        start_time = best_match_position / mfcc1.shape[1]
        end_time = (best_match_position + mfcc2.shape[1]) / mfcc1.shape[1]
    else:
        start_time = None
        end_time = None

    return best_match_score, start_time, end_time

# Function to add columns to the Google Sheet if they don't exist
def add_columns_if_not_exist(sheet, columns):
    existing_columns = sheet.row_values(1)
    for column in columns:
        if column not in existing_columns:
            existing_columns.append(column)
    sheet.update([existing_columns])

# Function to update Google Sheet for matched or mismatched videos
def update_sheet(sheet, video_id, start_time=None, end_time=None, highlight=False):
    cell = None
    try:
        # Load the sheet data into a DataFrame
        df = pd.DataFrame(sheet.get_all_records())
        row_index = df.index[df['Video URL'].str.endswith(video_id)].tolist()
        if row_index:
            row_index = row_index[0]
            cell = sheet.cell(row_index + 2, 1)  # Adjust for header row
    except Exception as e:
        pass

    if cell:
        cell_range = f'A{cell.row}:I{cell.row}'

        if highlight:
            format_orange = CellFormat(
                backgroundColor=Color(1, 0.65, 0)
            )
            format_cell_range(sheet, cell_range, format_orange)

        # Update start and end times if provided
        if start_time is not None and end_time is not None:
            add_columns_if_not_exist(sheet, ['Start Time', 'End Time'])
            start_time_col = sheet.row_values(1).index('Start Time') + 1
            end_time_col = sheet.row_values(1).index('End Time') + 1
            sheet.update_cell(row_index + 2, start_time_col, start_time)
            sheet.update_cell(row_index + 2, end_time_col, end_time)

# Function to get folder ID by name
def get_folder_id(folder_name, parent_id='root'):
    results = drive_service.files().list(
        q=f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    folders = results.get('files', [])
    if not folders:
        return None
    return folders[0]['id']

# Function to get file ID by name and type
def get_file_id(file_name, parent_id='root'):
    results = drive_service.files().list(
        q=f"'{parent_id}' in parents and name='{file_name}' and trashed=false",
        fields="files(id, mimeType)"
    ).execute()
    files = results.get('files', [])
    if not files:
        return None, None
    return files[0]['id'], files[0]['mimeType']

# Path settings
sound_folder = "/content/drive/My Drive/Sound MP3s"
tiktok_folder = "/content/drive/My Drive/TikToks"
metadata_folder_path = "/content/drive/My Drive/TikTokVideoMetadata"
output_folder = "/content/drive/My Drive/Extracted Audio"

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Range of numbers to process
start_range = 1
end_range = 428

# Threshold for considering a match
threshold = -25000

# Dictionary to store fingerprinted sounds
sound_fingerprints = {}

# Fingerprint sound files within the specified range
for file_name in os.listdir(sound_folder):
    if file_name.endswith(".mp3"):
        try:
            sound_id = int(file_name.split(" - ")[0])
            if start_range <= sound_id <= end_range:
                sound_path = os.path.join(sound_folder, file_name)
                samples, sr = load_audio(sound_path)
                sound_fingerprints[sound_id] = (samples, sr)
        except ValueError:
            pass

# Load metadata spreadsheet once
metadata_spreadsheets = {}

for sound_id in range(start_range, end_range + 1):
    try:
        tiktok_path = os.path.join(tiktok_folder, str(sound_id))
        if os.path.isdir(tiktok_path):
            mismatch_folder = os.path.join(tiktok_path, "Wrong Fingerprinting")
            os.makedirs(mismatch_folder, exist_ok=True)
            for video_file in sorted(os.listdir(tiktok_path)):
                if video_file.endswith(".mp4"):
                    video_path = os.path.join(tiktok_path, video_file)
                    audio_path = os.path.join(output_folder, f"{sound_id}_audio_{video_file}.mp3")
                    try:
                        extract_audio(video_path, audio_path)
                        video_samples, video_sr = load_audio(audio_path)
                        original_samples, original_sr = sound_fingerprints[sound_id]
                        match_score, start_time, end_time = audio_match_with_rolling_window(original_samples, original_sr, video_samples, video_sr)
                        if match_score is not None and match_score >= threshold:
                            print(f"Match - {video_file} - {match_score}")
                            # Update sheet with match details
                            metadata_file_name = f'TikTok_Video_URLs_with_metadata_{sound_id}'
                            if metadata_file_name not in metadata_spreadsheets:
                                spreadsheet_id, mime_type = get_file_id(metadata_file_name, get_folder_id('TikTokVideoMetadata'))
                                if spreadsheet_id and mime_type == 'application/vnd.google-apps.spreadsheet':
                                    metadata_spreadsheets[metadata_file_name] = gc.open_by_key(spreadsheet_id).sheet1
                                else:
                                    continue
                            sheet = metadata_spreadsheets[metadata_file_name]
                            update_sheet(sheet, video_file.split('-')[-1].split('.')[0], start_time, end_time, highlight=False)
                        else:
                            print(f"Non Match - {video_file} - {match_score}")
                            shutil.move(video_path, os.path.join(mismatch_folder, video_file))
                            mismatched_video_id = video_file.split('-')[-1].split('.')[0]
                            metadata_file_name = f'TikTok_Video_URLs_with_metadata_{sound_id}'
                            if metadata_file_name not in metadata_spreadsheets:
                                spreadsheet_id, mime_type = get_file_id(metadata_file_name, get_folder_id('TikTokVideoMetadata'))
                                if spreadsheet_id and mime_type == 'application/vnd.google-apps.spreadsheet':
                                    metadata_spreadsheets[metadata_file_name] = gc.open_by_key(spreadsheet_id).sheet1
                                else:
                                    continue
                            sheet = metadata_spreadsheets[metadata_file_name]
                            update_sheet(sheet, mismatched_video_id, highlight=True)

                    except Exception as e:
                        print(f"Error processing {video_path}: {e}")
                        shutil.move(video_path, os.path.join(mismatch_folder, video_file))
                        mismatched_video_id = video_file.split('-')[-1].split('.')[0]
                        metadata_file_name = f'TikTok_Video_URLs_with_metadata_{sound_id}'
                        if metadata_file_name not in metadata_spreadsheets:
                            spreadsheet_id, mime_type = get_file_id(metadata_file_name, get_folder_id('TikTokVideoMetadata'))
                            if spreadsheet_id and mime_type == 'application/vnd.google-apps.spreadsheet':
                                metadata_spreadsheets[metadata_file_name] = gc.open_by_key(spreadsheet_id).sheet1
                            else:
                                continue
                        sheet = metadata_spreadsheets[metadata_file_name]
                        update_sheet(sheet, mismatched_video_id, highlight=True)

    except ValueError:
        pass