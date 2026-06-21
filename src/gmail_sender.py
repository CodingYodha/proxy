import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
from datetime import datetime

def send_email(subject: str, body: str):
    sender_email = os.environ.get("GMAIL_SENDER_ADDRESS")
    sender_password = os.environ.get("GMAIL_SENDER_APP_PASSWORD")
    receiver_email = os.environ.get("GMAIL_RECEIVER_ADDRESS")

    if not sender_email or not sender_password or not receiver_email:
        print("Missing email credentials. Cannot send email.")
        return

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
    except Exception as e:
        print(f"Error sending email: {e}")

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
Reply NO to skip.
Reply with any other text to post your edited version instead.

Post ID: {urn}"""

    send_email(subject, body)
    return subject

def send_token_warning_email(days_left: int):
    subject = "[URGENT] LinkedIn Token Expiry Warning"
    body = f"LinkedIn token expires in {days_left} days — regenerate via Postman and update the GitHub Secret."
    send_email(subject, body)

def process_candidate_posts():
    candidate_file = "data/candidate_posts.json"
    pending_file = "data/pending_approvals.json"
    
    if not os.path.exists(candidate_file):
        print("No candidate posts to send approvals for.")
        return

    with open(candidate_file, "r") as f:
        try:
            posts = json.load(f)
        except:
            posts = []

    if not posts:
        return

    pending_approvals = {}
    if os.path.exists(pending_file):
        with open(pending_file, "r") as f:
            try:
                pending_approvals = json.load(f)
            except:
                pass
                
    sent_count = 0
    for post in posts:
        urn = post.get("urn")
        comment = post.get("drafted_comment")
        if not comment or urn in pending_approvals:
            continue
            
        subject = send_approval_email(
            author_name=post.get("author"),
            post_text=post.get("text"),
            url=post.get("url"),
            comment_text=comment,
            urn=urn
        )
        
        pending_approvals[urn] = {
            "drafted_comment": comment,
            "email_subject": subject,
            "status": "pending",
            "sent_at": datetime.now().isoformat(),
            "author": post.get("author"),
            "url": post.get("url"),
            "post_type": post.get("post_type", "insight"),
            "text": post.get("text")
        }
        sent_count += 1
        
    with open(pending_file, "w") as f:
        json.dump(pending_approvals, f, indent=4)
        
    os.remove(candidate_file)
    print(f"Sent {sent_count} approval emails.")

if __name__ == "__main__":
    process_candidate_posts()
