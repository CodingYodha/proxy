import os
import imaplib
import email
from email.header import decode_header
import json
import re
import smtplib
from email.message import EmailMessage

def send_success_email(receiver_email, sender_email, sender_password, author, post_url, comment_text):
    if not receiver_email or not sender_email or not sender_password:
        return
    try:
        msg = EmailMessage()
        msg['Subject'] = f"✅ SUCCESS: Comment posted on {author}'s post"
        msg['From'] = sender_email
        msg['To'] = receiver_email
        body = f"Your comment was successfully posted to LinkedIn!\n\n"
        body += f"Author: {author}\n"
        body += f"Post URL: {post_url}\n\n"
        body += f"--- YOUR COMMENT ---\n{comment_text}\n--------------------\n"
        msg.set_content(body)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Success email sent to {receiver_email}")
    except Exception as e:
        print(f"Failed to send success email: {e}")

# Project root (one level up from src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" not in content_disposition:
                if content_type == "text/plain":
                    return part.get_payload(decode=True).decode()
    else:
        return msg.get_payload(decode=True).decode()
    return ""

def poll_gmail_approvals():
    sender_email = os.environ.get("GMAIL_SENDER_ADDRESS")
    sender_password = os.environ.get("GMAIL_SENDER_APP_PASSWORD")
    receiver_email = os.environ.get("GMAIL_RECEIVER_ADDRESS")

    if not sender_email or not sender_password:
        print("Missing GMAIL credentials for poller.")
        return

    pending_file = os.path.join(DATA_DIR, "pending_approvals.json")
    if not os.path.exists(pending_file):
        print("No pending approvals file found.")
        return

    with open(pending_file, "r") as f:
        try:
            pending_approvals = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return

    if not pending_approvals:
        print("No pending approvals.")
        return

    from datetime import datetime, timedelta
    current_time = datetime.now()
    
    # Discard any pending approvals older than 24 hours
    for urn, data in pending_approvals.items():
        if data.get("status") == "pending" and "sent_at" in data:
            try:
                sent_at = datetime.fromisoformat(data["sent_at"])
                if current_time - sent_at > timedelta(hours=24):
                    data["status"] = "expired"
                    print(f"Expired approval for {urn} (sent > 24h ago).")
            except (ValueError, TypeError):
                pass

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(sender_email, sender_password)
        mail.select("inbox")
        
        # Search ALL emails instead of just UNSEEN.
        # We rely on pending_approvals["status"] == "pending" to prevent double-processing.
        status, messages = mail.search(None, 'ALL')
        if status != "OK":
            return
            
        from linkedin_poster import post_to_linkedin
        from sheets_logger import log_action
        
        message_ids = messages[0].split()
        for mail_id in message_ids:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = get_body(msg)
                    
                    if not body:
                        continue
                        
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors="ignore")
                        
                    urn = None
                    # Most robust: Regex extract URN from body
                    match = re.search(r'(urn:li:activity:\d+)', body)
                    if match:
                        urn = match.group(1)
                    else:
                        # Fallback: Extract from Subject if body was stripped
                        match = re.search(r'\[(\d+)\]', subject)
                        if match:
                            urn = f"urn:li:activity:{match.group(1)}"
                            
                    if urn and urn in pending_approvals and pending_approvals[urn]["status"] == "pending":
                        lines = body.splitlines()
                        reply_text = ""
                        for line in lines:
                            if line.startswith("On ") and "wrote:" in line:
                                break
                            if line.startswith(">"):
                                break
                            if line.strip():
                                reply_text += line.strip() + " "
                                
                        reply_text = reply_text.strip()
                        print(f"Found pending reply for URN {urn}. Extracted text: '{reply_text}'")
                        
                        action_taken = False
                        final_comment = ""
                        success = False
                        if reply_text.upper() == "YES":
                            final_comment = pending_approvals[urn]["drafted_comment"]
                            success = post_to_linkedin(urn, final_comment)
                            pending_approvals[urn]["status"] = "posted" if success else "failed"
                            action_taken = True
                        elif reply_text.upper() == "NO":
                            pending_approvals[urn]["status"] = "rejected"
                            final_comment = "REJECTED"
                            action_taken = True
                        elif reply_text:
                            final_comment = reply_text
                            success = post_to_linkedin(urn, final_comment)
                            pending_approvals[urn]["status"] = "posted" if success else "failed"
                            action_taken = True
                            
                        if success and receiver_email:
                            send_success_email(
                                receiver_email, sender_email, sender_password,
                                pending_approvals[urn].get("author", "Unknown"),
                                pending_approvals[urn].get("url", ""),
                                final_comment
                            )
                            
                        if action_taken:
                            log_action(
                                author=pending_approvals[urn].get("author", ""),
                                post_url=pending_approvals[urn].get("url", ""),
                                post_snippet=pending_approvals[urn].get("text", "")[:100],
                                post_type=pending_approvals[urn].get("post_type", ""),
                                drafted_comment=pending_approvals[urn]["drafted_comment"],
                                final_comment=final_comment,
                                status=pending_approvals[urn]["status"]
                            )

        mail.logout()

    except Exception as e:
        print(f"Error polling gmail: {e}")
    finally:
        # Always save pending_approvals so expiry updates are persisted
        # even if the IMAP connection fails
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(pending_file, "w") as f:
                json.dump(pending_approvals, f, indent=4)
        except Exception as e:
            print(f"Error saving pending approvals: {e}")

if __name__ == "__main__":
    poll_gmail_approvals()
