import os
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

def log_action(author: str, post_url: str, post_snippet: str, post_type: str, drafted_comment: str, final_comment: str, status: str):
    creds_json_str = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    
    if not creds_json_str or not sheet_id:
        print("Missing Google Sheets credentials or Sheet ID. Skipping logging.")
        return

    try:
        creds_dict = json.loads(creds_json_str)
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(sheet_id).sheet1
        
        timestamp = datetime.now().isoformat()
        
        row = [
            timestamp,
            author,
            post_url,
            post_snippet,
            post_type,
            drafted_comment,
            final_comment,
            status
        ]
        
        sheet.append_row(row)
        print("Successfully logged action to Google Sheets.")
    except Exception as e:
        print(f"Error logging to Google Sheets: {e}")
