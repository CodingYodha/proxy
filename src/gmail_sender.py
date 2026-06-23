import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
from datetime import datetime

# Project root (one level up from src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

def send_email(subject: str, body: str) -> bool:
    """Send an email. Returns True on success, False on failure."""
    sender_email = os.environ.get("GMAIL_SENDER_ADDRESS")
    sender_password = os.environ.get("GMAIL_SENDER_APP_PASSWORD")
    receiver_email = os.environ.get("GMAIL_RECEIVER_ADDRESS")

    if not sender_email or not sender_password or not receiver_email:
        print("Missing email credentials. Cannot send email.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Successfully sent email to {receiver_email} with subject: {subject}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_approval_email(author_name: str, post_text: str, url: str, comment_text: str, urn: str):
    subject = f"[APPROVE?] Comment on post by {author_name}"
    
    snippet = post_text[:300] + "..." if len(post_text) > 300 else post_text

    body = f"""Post by: {author_name}
Post snippet: {snippet}
Post URL: {url}

---DRAFTED COMMENT---
{comment_text}
---------------------

Reply YES to post this comment.
Reply NO to reject it.
Reply with any other text to post your edited version instead.
(If you don't reply within 24 hours, this comment will be automatically discarded).

Post ID: {urn}"""

    success = send_email(subject, body)
    if success:
        return subject
    else:
        return None

def send_token_warning_email(days_left: int):
    subject = "[URGENT] LinkedIn Token Expiry Warning"
    body = f"LinkedIn token expires in {days_left} days — regenerate via Postman and update the GitHub Secret."
    send_email(subject, body)

def process_candidate_posts():
    candidate_file = os.path.join(DATA_DIR, "candidate_posts.json")
    pending_file = os.path.join(DATA_DIR, "pending_approvals.json")
    
    if not os.path.exists(candidate_file):
        print("No candidate posts to send approvals for.")
        return

    with open(candidate_file, "r") as f:
        try:
            posts = json.load(f)
        except (json.JSONDecodeError, ValueError):
            posts = []

    if not posts:
        return

    pending_approvals = {}
    if os.path.exists(pending_file):
        with open(pending_file, "r") as f:
            try:
                pending_approvals = json.load(f)
            except (json.JSONDecodeError, ValueError):
                pass
                
    sent_count = 0
    for post in posts:
        urn = post.get("urn")
        comment = post.get("drafted_comment")
        if not comment or not urn or urn in pending_approvals:
            continue
        
        # Provide safe defaults for missing fields
        author = post.get("author") or "Unknown Author"
        post_text = post.get("text") or ""
        post_url = post.get("url") or ""
        
        subject = send_approval_email(
            author_name=author,
            post_text=post_text,
            url=post_url,
            comment_text=comment,
            urn=urn
        )
        
        # Only record as pending if the email was actually sent
        if subject is None:
            print(f"Failed to send approval email for {urn}. Skipping.")
            continue
        
        pending_approvals[urn] = {
            "drafted_comment": comment,
            "email_subject": subject,
            "status": "pending",
            "sent_at": datetime.now().isoformat(),
            "author": author,
            "url": post_url,
            "post_type": post.get("post_type", "insight"),
            "text": post_text
        }
        sent_count += 1
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(pending_file, "w") as f:
        json.dump(pending_approvals, f, indent=4)
    
    # Only remove candidate file after everything is safely saved
    try:
        os.remove(candidate_file)
    except OSError as e:
        print(f"Warning: Could not remove candidate file: {e}")
        
    print(f"Sent {sent_count} approval emails.")

if __name__ == "__main__":
    process_candidate_posts()
