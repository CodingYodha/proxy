import os
import requests
import json

def fetch_linkedin_posts():
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("LINKEDIN_ACCESS_TOKEN missing.")
        return

    url = "https://api.linkedin.com/v2/search?q=content&keywords=artificial+intelligence+LLM+deep+learning&count=20&sortBy=DATE_POSTED"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching posts from LinkedIn: {e}")
        return

    elements = data.get("elements", [])
    
    seen_posts_file = "data/seen_posts.json"
    seen_posts = []
    if os.path.exists(seen_posts_file):
        with open(seen_posts_file, "r") as f:
            try:
                seen_posts = json.load(f)
            except:
                pass
    
    new_posts = []
    new_urns = []
    
    for el in elements:
        urn = el.get("urn")
        if not urn or urn in seen_posts:
            continue
            
        author = el.get("author", "Unknown Author")
        text = el.get("text", "")
        post_url = el.get("url", f"https://www.linkedin.com/feed/update/{urn}")
        
        new_posts.append({
            "urn": urn,
            "author": author,
            "text": text,
            "url": post_url
        })
        new_urns.append(urn)

    if new_urns:
        seen_posts.extend(new_urns)
        os.makedirs(os.path.dirname(seen_posts_file), exist_ok=True)
        with open(seen_posts_file, "w") as f:
            json.dump(seen_posts, f, indent=4)
            
    candidate_file = "data/candidate_posts.json"
    os.makedirs(os.path.dirname(candidate_file), exist_ok=True)
    with open(candidate_file, "w") as f:
        json.dump(new_posts, f, indent=4)

    print(f"Fetched {len(new_posts)} new posts out of {len(elements)} total results.")

if __name__ == "__main__":
    from token_manager import check_token_expiry
    # Check token expiry at the start of the cron job
    check_token_expiry()
    fetch_linkedin_posts()
