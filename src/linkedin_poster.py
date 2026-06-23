import os
import requests
import json
from datetime import datetime
from urllib.parse import quote

# Project root (one level up from src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

def post_to_linkedin(urn: str, comment_text: str) -> bool:
    count_file = os.path.join(DATA_DIR, "daily_count.json")
    daily_data = {"date": "", "count": 0}
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(count_file):
        with open(count_file, "r") as f:
            try:
                daily_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                pass
                
    if daily_data.get("date") != today:
        daily_data = {"date": today, "count": 0}
        
    if daily_data["count"] >= 10:
        print("Daily comment limit of 10 reached. Skipping.")
        return False

    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.environ.get("LINKEDIN_PERSON_URN")
    
    if not access_token or not person_urn:
        print("LINKEDIN credentials missing for posting.")
        return False
    
    # Fix: Strip existing "urn:li:person:" prefix if present to avoid double-wrapping
    if person_urn.startswith("urn:li:person:"):
        actor_urn = person_urn
    else:
        actor_urn = f"urn:li:person:{person_urn}"
    
    # Fix: URL-encode the URN in the path (colons must be encoded)
    encoded_urn = quote(urn, safe='')
    url = f"https://api.linkedin.com/v2/socialActions/{encoded_urn}/comments"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    payload = {
        "actor": actor_urn,
        "message": {
            "text": comment_text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 401:
            print("401 Unauthorized: Access token is invalid or expired. Failing gracefully.")
            return False
            
        if response.status_code == 429:
            print("429 Too Many Requests: Rate limit hit. Skipping.")
            return False
            
        response.raise_for_status()
        
        daily_data["count"] += 1
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(count_file, "w") as f:
            json.dump(daily_data, f, indent=4)
            
        print(f"Successfully posted comment on {urn}.")
        return True
    except Exception as e:
        print(f"Error posting comment to LinkedIn: {e}")
        return False
