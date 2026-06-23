import os
import json
import requests
import time
import random
from linkedin_api import Linkedin
from token_manager import check_token_expiry

# Project root (one level up from src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Keywords to pre-filter posts locally before sending to Groq
AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'llm', 'large language model',
    'deep learning', 'machine learning', 'neural network', 'chatgpt',
    'gpt-4', 'claude', 'gemini', 'agentic', 'multi-agent',
    'transformer', 'diffusion', 'reinforcement learning', 'nlp',
    'computer vision', 'generative ai', 'foundation model',
]

def extract_urn_from_url(url: str) -> str:
    """Extract the full activity URN from a linkedin feed URL.
    
    The linkedin-api library returns URLs like:
      https://www.linkedin.com/feed/update/urn:li:activity:7318592837465
    We extract: urn:li:activity:7318592837465
    """
    if not url:
        return ""
    marker = "/feed/update/"
    idx = url.find(marker)
    if idx != -1:
        return url[idx + len(marker):]
    return ""

def load_seen_posts():
    seen_file = os.path.join(DATA_DIR, 'seen_posts.json')
    try:
        with open(seen_file, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_candidate_posts(candidates):
    os.makedirs(DATA_DIR, exist_ok=True)
    candidate_file = os.path.join(DATA_DIR, 'candidate_posts.json')
    with open(candidate_file, 'w') as f:
        json.dump(candidates, f, indent=2)

def fetch_feed_and_filter():
    check_token_expiry()

    li_at = os.environ.get('LINKEDIN_LI_AT')
    jsessionid = os.environ.get('LINKEDIN_JSESSIONID')
    
    if not li_at or not jsessionid:
        print('Missing LINKEDIN_LI_AT or LINKEDIN_JSESSIONID. Skipping fetch.')
        return

    # Authenticate using cookies
    cookie_dict = {"li_at": li_at, "JSESSIONID": jsessionid}
    jar = requests.cookies.RequestsCookieJar()
    for name, value in cookie_dict.items():
        jar.set(name, value)
    
    try:
        api = Linkedin('', '', cookies=jar)
    except Exception as e:
        print(f'Failed to authenticate with linkedin-api: {e}')
        return

    seen_posts = load_seen_posts()
    
    # Random small delay before fetching to appear more human-like
    delay = random.uniform(2, 8)
    print(f'Waiting {delay:.1f}s before fetching feed...')
    time.sleep(delay)
    
    print('Fetching home feed...')
    try:
        feed_posts = api.get_feed_posts(limit=30, exclude_promoted_posts=True)
    except Exception as e:
        print(f'Error fetching feed: {e}')
        return

    candidates = []
    new_urns = []
    
    for post in feed_posts:
        # The linkedin-api library returns dicts with these keys:
        #   'author_name'    -> str (author's display name)
        #   'author_profile' -> str (author's profile URL)
        #   'content'        -> str (post text from commentary.text.text)
        #   'url'            -> str (post URL like .../feed/update/urn:li:activity:XXX)
        #   'old'            -> str (age string like '2 mo', also used for 'Promoted' check)
        
        post_url = post.get('url', '')
        urn = extract_urn_from_url(post_url)
            
        if not urn or urn in seen_posts:
            continue
            
        content = post.get('content', '')
        if not content:
            continue
        
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in AI_KEYWORDS):
            author = post.get('author_name', 'Unknown Author')
            if isinstance(author, dict):
                author = author.get('text', 'Unknown Author')

            candidates.append({
                'urn': urn,
                'author': author,
                'text': content,  # Store actual content under 'text' for downstream use
                'url': post_url
            })
        
        new_urns.append(urn)

    print(f'Found {len(candidates)} new AI-related candidate posts from feed.')
    save_candidate_posts(candidates)

    if new_urns:
        seen_list = list(seen_posts)
        seen_list.extend(new_urns)
        os.makedirs(DATA_DIR, exist_ok=True)
        seen_file = os.path.join(DATA_DIR, 'seen_posts.json')
        with open(seen_file, 'w') as f:
            json.dump(seen_list, f, indent=4)

if __name__ == '__main__':
    fetch_feed_and_filter()
