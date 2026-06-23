import os
import json
from linkedin_api import Linkedin
from token_manager import check_token_expiry

# Keywords to pre-filter posts locally before sending to Groq
AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'llm', 'large language model',
    'deep learning', 'machine learning', 'neural network', 'chatgpt',
    'gpt-4', 'claude', 'gemini', 'agentic', 'multi-agent'
]

def load_seen_posts():
    try:
        with open('data/seen_posts.json', 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_candidate_posts(candidates):
    os.makedirs('data', exist_ok=True)
    with open('data/candidate_posts.json', 'w') as f:
        json.dump(candidates, f, indent=2)

def fetch_feed_and_filter():
    check_token_expiry()

    li_at = os.environ.get('LINKEDIN_LI_AT')
    jsessionid = os.environ.get('LINKEDIN_JSESSIONID')
    
    if not li_at or not jsessionid:
        print('Missing LINKEDIN_LI_AT or LINKEDIN_JSESSIONID. Skipping fetch.')
        return

    try:
        api = Linkedin('', '', cookies={'li_at': li_at, 'JSESSIONID': jsessionid})
    except Exception as e:
        print(f'Failed to authenticate with linkedin-api: {e}')
        return

    seen_posts = load_seen_posts()
    
    print('Fetching home feed...')
    try:
        feed_posts = api.get_feed_posts(limit=30, exclude_promoted_posts=True)
    except Exception as e:
        print(f'Error fetching feed: {e}')
        return

    candidates = []
    new_urns = []
    
    for post in feed_posts:
        urn = post.get('urn')
        if urn and not urn.startswith('urn:li:activity:'):
            urn = f'urn:li:activity:{urn.split(":")[-1]}'
            
        if not urn or urn in seen_posts:
            continue
            
        content = post.get('content', '').lower()
        if not content:
            continue
            
        if any(keyword in content for keyword in AI_KEYWORDS):
            author = post.get('author_name', 'Unknown Author')
            if isinstance(author, dict):
                author = author.get('text', 'Unknown Author')
                
            post_url = post.get('url', f'https://www.linkedin.com/feed/update/{urn}')

            candidates.append({
                'urn': urn,
                'author': author,
                'text': post.get('content', ''),
                'url': post_url
            })
        
        new_urns.append(urn)

    print(f'Found {len(candidates)} new AI-related candidate posts from feed.')
    save_candidate_posts(candidates)

    if new_urns:
        seen_list = list(seen_posts)
        seen_list.extend(new_urns)
        os.makedirs('data', exist_ok=True)
        with open('data/seen_posts.json', 'w') as f:
            json.dump(seen_list, f, indent=4)

if __name__ == '__main__':
    fetch_feed_and_filter()

