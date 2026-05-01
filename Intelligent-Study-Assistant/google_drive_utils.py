import io
import json
import PyPDF2
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

scopes_list = ['https://www.googleapis.com/auth/drive.readonly']

url_redirect = "http://localhost:5173/oauth/google/callback"

_pending_oauth = {}

def get_oauth_url(user_id: int) -> str:
    google_auth_flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=scopes_list,
        redirect_uri=url_redirect
    )

    authentication_url, state = google_auth_flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=str(user_id)
    )

    if hasattr(google_auth_flow, 'code_verifier') and google_auth_flow.code_verifier:
        _pending_oauth[state] = google_auth_flow.code_verifier

    return authentication_url

def exchange_code_for_tokens(code: str, state: str = None):
    
    google_auth_flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=scopes_list,
        redirect_uri=url_redirect
    )

    if state and state in _pending_oauth:
        google_auth_flow.code_verifier = _pending_oauth.pop(state)

    google_auth_flow.fetch_token(code=code)
    google_credentials = google_auth_flow.credentials

    return {
        "access_token": google_credentials.token,
        "refresh_token": google_credentials.refresh_token,
        "token_uri": google_credentials.token_uri,
        "client_id": google_credentials.client_id,
        "client_secret": google_credentials.client_secret,
        "scopes": list(google_credentials.scopes) if google_credentials.scopes else scopes_list
    }

def get_drive_service_from_tokens(token_data):

    if isinstance(token_data, str):
        token_data = json.loads(token_data)

    google_credentials = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", scopes_list)
    )

    if google_credentials.expired and google_credentials.refresh_token:
        google_credentials.refresh(Request())

        updated_tokens = {
            "access_token": google_credentials.token,
            "refresh_token": google_credentials.refresh_token,
            "token_uri": google_credentials.token_uri,
            "client_id": google_credentials.client_id,
            "client_secret": google_credentials.client_secret,
            "scopes": list(google_credentials.scopes) if google_credentials.scopes else scopes_list
        }
        return build('drive', 'v3', credentials=google_credentials), updated_tokens

    return build('drive', 'v3', credentials=google_credentials), None

def get_file_content_with_service(google_service, file_id: str):

    file_info = google_service.files().get(fileId=file_id).execute()
    file_type = file_info.get('mimeType')

    if file_type == 'application/vnd.google-apps.document':
        download_request = google_service.files().export_media(
            fileId=file_id, 
            mimeType='text/plain'
        )
    else:
        download_request = google_service.files().get_media(fileId=file_id)

    file_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(file_buffer, download_request)
    download_finished = False
    while not download_finished:
        _, download_finished = downloader.next_chunk()

    if file_type == 'application/pdf':
        file_buffer.seek(0)
        pdf_reader = PyPDF2.PdfReader(file_buffer)
        information_from_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                information_from_text += page_text + "\n"
        return information_from_text

    return file_buffer.getvalue().decode('utf-8', errors='ignore')
