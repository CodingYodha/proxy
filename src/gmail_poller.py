import os
import imaplib
import email
from email.header import decode_header
import json

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

    if not sender_email or not sender_password:
        print("Missing GMAIL credentials for poller.")
        return

    pending_file = "data/pending_approvals.json"
    if not os.path.exists(pending_file):
        print("No pending approvals.")
        return

    with open(pending_file, "r") as f:
        try:
            pending_approvals = json.load(f)
        except:
            return

    from datetime import datetime, timedelta
    current_time = datetime.now()
    
    # Discard any pending approvals older than 24 hours
    for urn, data in pending_approvals.items():
        if data["status"] == "pending" and "sent_at" in data:
            try:
                sent_at = datetime.fromisoformat(data["sent_at"])
                if current_time - sent_at > timedelta(hours=24):
                    data["status"] = "expired"
            except:
                pass

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(sender_email, sender_password)
        mail.select("inbox")
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != "OK":
            return
            
        from src.linkedin_poster import post_to_linkedin
        from src.sheets_logger import log_action
        
        message_ids = messages[0].split()
        for mail_id in message_ids:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = get_body(msg)
                    
                    if not body:
                        continue
                        
                    urn = None
                    for line in body.splitlines():
                        if line.startswith("Post ID: urn:li:activity:"):
                            urn = line.split("Post ID: ")[1].strip()
                            break
                            
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
                        
                        action_taken = False
                        final_comment = ""
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

        with open(pending_file, "w") as f:
            json.dump(pending_approvals, f, indent=4)
            
    except Exception as e:
        print(f"Error polling gmail: {e}")

if __name__ == "__main__":
    poll_gmail_approvals()
