import os
from datetime import datetime
from src.gmail_sender import send_token_warning_email

def check_token_expiry():
    issue_date_str = os.environ.get("LINKEDIN_TOKEN_ISSUE_DATE")
    if not issue_date_str:
        print("No LINKEDIN_TOKEN_ISSUE_DATE set. Skipping expiry check.")
        return

    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
        delta = datetime.now() - issue_date
        days_passed = delta.days
        
        # 60 days total, if we are within 5 days (i.e. >= 55 days passed)
        if days_passed >= 55:
            days_left = max(0, 60 - days_passed)
            print(f"Token is expiring in {days_left} days. Sending warning email...")
            send_token_warning_email(days_left)
        else:
            print(f"Token is valid. {60 - days_passed} days remaining.")
    except Exception as e:
        print(f"Error checking token expiry: {e}")

if __name__ == "__main__":
    check_token_expiry()
