# 9. Create strip-views and visual profiles for each Sound

!pip install opencv-python-headless pydub

from google.colab import drive
drive.mount('/content/drive')

import cv2
import os
import glob
import pandas as pd
from pydub import AudioSegment
from PIL import Image as PILImage

# Authenticate and initialize the Google Sheets client.
import gspread
from google.colab import auth
import google.auth

auth.authenticate_user()
creds, _ = google.auth.default()
gc_client = gspread.authorize(creds)

def load_metadata(sheet_name):
    try:
        sheet = gc_client.open(sheet_name).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error loading metadata for sheet {sheet_name}: {e}")
        return pd.DataFrame()

def extract_frames(video_path, time_interval):
    try:
        video_cap = cv2.VideoCapture(video_path)
        fps = video_cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            print(f"Error: FPS value not valid for video {video_path}")
            return []

        interval_frames = int(fps * time_interval)
        if interval_frames <= 0:
            print(f"Error: Interval frames value not valid for video {video_path}")
            return []

        frames = []
        success, image = video_cap.read()
        count = 0

        while success:
            if count % interval_frames == 0:
                # Convert BGR image to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                frames.append(image_rgb)
            success, image = video_cap.read()
            count += 1

        video_cap.release()
        return frames
    except Exception as e:
        print(f"Error extracting frames from video {video_path}: {e}")
        return []

def create_horizontal_strip(frames, frame_width=240):
    try:
        thumbnails = []
        for frame in frames:
            img_pil = PILImage.fromarray(frame)
            img_pil.thumbnail((frame_width, frame_width))
            thumbnails.append(img_pil)

        # Concatenate images horizontally
        strip_width = sum(thumbnail.width for thumbnail in thumbnails)
        strip_height = max(thumbnail.height for thumbnail in thumbnails)
        strip_image = PILImage.new('RGB', (strip_width, strip_height))

        x_offset = 0
        for thumbnail in thumbnails:
            strip_image.paste(thumbnail, (x_offset, 0))
            x_offset += thumbnail.width

        return strip_image
    except Exception as e:
        print(f"Error creating horizontal strip: {e}")
        return None

def save_strip(strip_image, output_path, video_file):
    try:
        base_name = os.path.basename(video_file).split('.')[0]
        file_name = f'{base_name}_strip.png'
        strip_image.save(os.path.join(output_path, file_name))
    except Exception as e:
        print(f"Error saving strip image for video {video_file}: {e}")

def process_videos(range_start, range_end, video_base_path, metadata_base_path):
    for folder_number in range(range_start, range_end + 1):
        # Load metadata
        sheet_name = f'TikTok_Video_URLs_with_metadata_{folder_number}'
        metadata = load_metadata(sheet_name)

        if metadata.empty:
            print(f"Skipping folder {folder_number} due to empty or missing metadata")
            continue

        # Check for expected columns
        if 'Start Time' not in metadata.columns or 'End Time' not in metadata.columns:
            print(f"Skipping folder {folder_number} due to missing 'Start Time' or 'End Time' columns")
            continue

        # Convert 'Start Time' and 'End Time' to numeric, coercing errors to NaN
        metadata['Start Time'] = pd.to_numeric(metadata['Start Time'], errors='coerce')
        metadata['End Time'] = pd.to_numeric(metadata['End Time'], errors='coerce')

        # Drop rows with NaN values in 'Start Time' and 'End Time'
        metadata = metadata.dropna(subset=['Start Time', 'End Time'])

        # Round start and end times to one significant figure
        metadata['Start Time'] = metadata['Start Time'].round(1)
        metadata['End Time'] = metadata['End Time'].round(1)

        # Find the modal start time and end time
        if metadata['Start Time'].empty or metadata['End Time'].empty:
            print(f"Skipping folder {folder_number} due to empty 'Start Time' or 'End Time' columns")
            continue

        modal_start_time = metadata['Start Time'].mode().iloc[0]
        modal_end_time = metadata['End Time'].mode().iloc[0]

        # Debug print statements
        print(f"Folder number: {folder_number}")
        print(f"Modal start time: {modal_start_time}")
        print(f"Modal end time: {modal_end_time}")

        # Compute the length of the longest video
        try:
            audio_file = glob.glob(os.path.join('/content/drive/My Drive/Sound MP3s', f'{folder_number} - *.mp3'))[0]
            audio_segment = AudioSegment.from_file(audio_file)
            audio_duration = len(audio_segment) / 1000  # duration in seconds
        except Exception as e:
            print(f"Error processing audio file for folder {folder_number}: {e}")
            continue

        # Debug print statement
        print(f"Audio duration: {audio_duration}")

        if modal_start_time is None or modal_end_time is None or audio_duration <= 0:
            print(f"Skipping folder {folder_number} due to invalid start time, end time, or audio duration")
            continue

        longest_video_duration = audio_duration * (modal_end_time - modal_start_time)
        time_interval = longest_video_duration / 10

        # Debug print statement
        print(f"Longest video duration: {longest_video_duration}")
        print(f"Time interval: {time_interval}")

        if time_interval <= 0:
            print(f"Skipping folder {folder_number} due to invalid calculated time interval")
            continue

        # Get all video files in the directory
        video_folder_path = os.path.join(video_base_path, str(folder_number))
        if not os.path.exists(video_folder_path):
            print(f"Skipping folder {folder_number} as it does not exist in the main folder")
            continue

        video_files = glob.glob(os.path.join(video_folder_path, '*.mp4'))[:50]  # Process only the first 50 videos

        if not video_files:
            print(f"Skipping folder {folder_number} as it contains no videos")
            continue

        # Create output folder if it doesn't exist
        output_folder_path = os.path.join('/content/drive/My Drive/Frames', str(folder_number))
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)

        # List to hold all strips for the final consolidated image
        all_strips = []

        for video_file in video_files:
            print(f'Processing video: {video_file}')
            frames = extract_frames(video_file, time_interval)
            if not frames:
                print(f"Skipping video {video_file} due to invalid FPS.")
                continue
            strip_image = create_horizontal_strip(frames)
            if strip_image is not None:
                all_strips.append(strip_image)
                save_strip(strip_image, output_folder_path, video_file)

        # Create the consolidated image
        if all_strips:
            try:
                max_width = max(strip.width for strip in all_strips)
                total_height = sum(strip.height for strip in all_strips)
                consolidated_image = PILImage.new('RGB', (max_width, total_height), color=(0, 0, 0))

                y_offset = 0
                for strip in all_strips:
                    consolidated_image.paste(strip, (0, y_offset))
                    y_offset += strip.height

                consolidated_image.save(os.path.join(output_folder_path, 'consolidated_image.png'))
                print(f"Consolidated image saved for folder {folder_number}")
            except Exception as e:
                print(f"Error creating consolidated image for folder {folder_number}: {e}")

# Example usage
video_base_path = '/content/drive/My Drive/TikToks'
metadata_base_path = '/content/drive/My Drive/TikTokVideoMetadata'

process_videos(1, 428, video_base_path, metadata_base_path)