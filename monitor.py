import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import os
import json
from datetime import datetime, date

def get_current_releases_url():
    """Generate the current month's San-X releases URL"""
    current_date = date.today()
    year = current_date.year
    month = current_date.month
    
    # Format: YYYYMM_new
    month_str = f"{year}{month:02d}_new"
    url = f"https://shop.san-x.co.jp/feature/index/{month_str}"
    
    return url, month_str

def check_page_exists(url):
    """Check if the releases page exists for current month"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.head(url, headers=headers, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error checking if page exists: {str(e)}")
        return False

def get_fallback_url():
    """Get fallback URL if current month's page doesn't exist"""
    current_date = date.today()
    
    # Try previous month first
    if current_date.month == 1:
        prev_year = current_date.year - 1
        prev_month = 12
    else:
        prev_year = current_date.year
        prev_month = current_date.month - 1
    
    prev_month_str = f"{prev_year}{prev_month:02d}_new"
    prev_url = f"https://shop.san-x.co.jp/feature/index/{prev_month_str}"
    
    if check_page_exists(prev_url):
        return prev_url, prev_month_str
    
    # If previous month doesn't exist, try next month
    if current_date.month == 12:
        next_year = current_date.year + 1
        next_month = 1
    else:
        next_year = current_date.year
        next_month = current_date.month + 1
    
    next_month_str = f"{next_year}{next_month:02d}_new"
    next_url = f"https://shop.san-x.co.jp/feature/index/{next_month_str}"
    
    if check_page_exists(next_url):
        return next_url, next_month_str
    
    # If neither works, fall back to general new arrivals or shop
    return "https://shop.san-x.co.jp/category/new", "general_new"
    """Send email notification"""
    try:
        # Email configuration from environment variables
        smtp_server = "smtp.gmail.com"  # Change if not using Gmail
        smtp_port = 587
        sender_email = os.environ['SENDER_EMAIL']
        sender_password = os.environ['EMAIL_PASSWORD']  # Use app password for Gmail
        recipient_email = os.environ['RECIPIENT_EMAIL']
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Email body
        email_body = f"""
        {body}
        
        {month_info}
        URL: {url}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        Check it out: {url}
        """
        
        msg.attach(MIMEText(email_body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"Email sent successfully to {recipient_email}")
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def get_page_content(url):
    """Fetch and parse the San-X shop page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements to focus on content
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find product listings or main content area
        # Specific selectors that might be used on San-X feature pages
        content_selectors = [
            '.feature-products',
            '.product-list',
            '.new-items',
            '.items-grid',
            '.products',
            '.main-content',
            '#main',
            '.container',
            'main'
        ]
        
        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break
        
        # If no specific selector found, use body content
        if not content:
            content = soup.find('body')
        
        # Get text content and clean it up
        text_content = content.get_text(separator=' ', strip=True) if content else ""
        
        return text_content
        
    except Exception as e:
        print(f"Error fetching page: {str(e)}")
        return None

def load_previous_hash():
    """Load the previous content hash and URL"""
    hash_file = 'sanx_hash.json'
    if os.path.exists(hash_file):
        try:
            with open(hash_file, 'r') as f:
                data = json.load(f)
                return data.get('hash'), data.get('last_check'), data.get('url'), data.get('month_str')
        except:
            pass
    return None, None, None, None

def save_current_hash(content_hash, url, month_str):
    """Save the current content hash and URL"""
    hash_file = 'sanx_hash.json'
    data = {
        'hash': content_hash,
        'url': url,
        'month_str': month_str,
        'last_check': datetime.now().isoformat()
    }
    with open(hash_file, 'w') as f:
        json.dump(data, f)

def check_sanx_updates():
    """Main function to check for San-X monthly releases updates"""
    # Get current month's releases URL
    url, month_str = get_current_releases_url()
    
    print(f"Checking San-X releases for {month_str} at {datetime.now()}")
    print(f"Target URL: {url}")
    
    # Check if current month's page exists
    if not check_page_exists(url):
        print(f"Current month's page ({month_str}) doesn't exist, trying fallback...")
        url, month_str = get_fallback_url()
        print(f"Using fallback URL: {url} ({month_str})")
    
    # Get current page content
    current_content = get_page_content(url)
    if not current_content:
        print("Failed to fetch page content")
        return
    
    # Create hash of current content
    current_hash = hashlib.md5(current_content.encode('utf-8')).hexdigest()
    
    # Load previous hash and URL
    previous_hash, last_check, previous_url, previous_month = load_previous_hash()
    
    print(f"Current hash: {current_hash}")
    print(f"Previous hash: {previous_hash}")
    print(f"Current URL: {url}")
    print(f"Previous URL: {previous_url}")
    
    # Determine if we should send notification
    should_notify = False
    notification_reason = ""
    
    if not previous_hash:
        # First run
        print("First run - storing initial hash")
        notification_reason = "Initial setup"
    elif url != previous_url:
        # URL changed (new month)
        print(f"Switched from {previous_month} to {month_str} - sending notification")
        should_notify = True
        notification_reason = f"Switched to monitoring {month_str} releases"
    elif current_hash != previous_hash:
        # Content changed on same URL
        print("Content has changed! Sending notification...")
        should_notify = True
        notification_reason = f"Content updated on {month_str} releases page"
    else:
        print("No changes detected")
    
    # Send notification if needed
    if should_notify:
        month_name = datetime.strptime(month_str.split('_')[0], '%Y%m').strftime('%B %Y')
        send_email(
            f"🎉 San-X {month_name} Releases Updated!",
            f"The San-X {month_name} releases page has been updated!",
            url,
            f"Monitoring: {month_name} releases ({month_str})\nReason: {notification_reason}"
        )
    
    # Save current state
    save_current_hash(current_hash, url, month_str)
    print("Check completed")

if __name__ == "__main__":
    check_sanx_updates()
