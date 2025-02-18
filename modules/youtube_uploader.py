from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from tqdm import tqdm
import config
import pickle
import os

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"

def authenticate():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            config.YOUTUBE_CLIENT_SECRET_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
    
    return build("youtube", "v3", credentials=credentials)

def upload_video(youtube, file, title, description, tags, privacy):
    media = MediaFileUpload(
        file,
        mimetype='video/mp4',
        resumable=True,
        chunksize=1024*1024
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": privacy
            }
        },
        media_body=media
    )
    
    # İlerleme çubuğu ile yükleme
    with tqdm(total=100, desc="Video yükleniyor") as pbar:
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pbar.update(int(status.progress() * 100))
    
    print(f"Video yüklendi: https://www.youtube.com/watch?v={response['id']}") 