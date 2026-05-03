import requests
import os
from dotenv import load_dotenv

load_dotenv()

def send_google_email(recipient_emails, subject, html_body):
    """
    Sends email via Google Apps Script.
    attachments: List of file paths (e.g., ["*.pdf", "*.png"])
    """
    
    # 1. Load Variables
    GOOGLE_SCRIPT_URL = os.environ.get("GOOGLE_SCRIPT_URL")
    EMAIL_TOKEN = os.environ.get("EMAIL_TOKEN") 
    sender_name = os.environ.get("EMAIL_NAME")
    
    # 2. Handle Recipients
    if isinstance(recipient_emails, list):
        recipient_emails = ",".join(recipient_emails)

    # 3. Build Payload
    payload = {
        "token": EMAIL_TOKEN,
        "to": recipient_emails,
        "subject": subject,
        "body": html_body,     # This is your HTML content
        "name": sender_name,   # This is your "From" name
        "attachments": []
    }

    # 4. Send Request
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=20)
        # 5. Process Response
        
        # Check response for success    
        if "Success" in response.text:
            return {
                'success': True,
                'message': f'Email sent successfully to {len(recipient_emails.split(","))} recipient(s)',
                'recipients': recipient_emails,
            }
        else:
            return {"success": False, "message": f"Script Error: {response.text}"}
            
    except Exception as e:
        return {"success": False, "message": str(e)}