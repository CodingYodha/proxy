import os
import json
import anthropic

# Project root (one level up from src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

def generate_comments():
    candidate_file = os.path.join(DATA_DIR, "candidate_posts.json")
    if not os.path.exists(candidate_file):
        print("No candidate posts.")
        return

    with open(candidate_file, "r") as f:
        try:
            posts = json.load(f)
        except (json.JSONDecodeError, ValueError):
            posts = []

    if not posts:
        return

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("ANTHROPIC_API_KEY missing.")
        return
        
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    system_prompt = (
        "You are helping Shivaprasad Gowda, a second-year undergrad at IIIT Nagpur, "
        "currently a Research Intern at IIT Roorkee working on deep learning and "
        "3D perception (LiDAR-based BEVWaveFormer), multi-agent AI systems, and "
        "representation learning. He is building his personal brand on LinkedIn "
        "as a young AI researcher.\n"
        "Your job is to write a LinkedIn comment that:\n"
        "- Sounds like a sharp, intellectually curious young researcher, NOT a corporate professional\n"
        "- Is 2–4 sentences maximum\n"
        "- Has ZERO hashtags, ZERO emojis, ZERO phrases like \"Great post!\" or \"Totally agree!\"\n"
        "- NEVER uses em-dashes (—) or en-dashes (–) anywhere in the text\n"
        "- Either asks a genuinely interesting follow-up question OR gives a nuanced/contrarian perspective\n"
        "- References a real concept, paper, or idea where relevant (don't fabricate citations)\n"
        "- Feels like it came from someone who has thought deeply about this topic\n"
        "Comment style rules by post_type:\n"
        "- \"insight\" or \"announcement\" → Give a nuanced take, add missing context, or push back respectfully\n"
        "- \"question\" or \"opinion\" → Ask a sharp follow-up that reframes or deepens the question"
    )

    processed_posts = []
    
    for post in posts:
        text = post.get("text", "")
        post_type = post.get("post_type", "insight")
        
        if not text:
            continue
        
        user_message = f"Post text: {text}\nPost type: {post_type}\nWrite the comment now."
        
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=200,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            comment = response.content[0].text.strip()
            post["drafted_comment"] = comment
            processed_posts.append(post)
        except Exception as e:
            print(f"Error calling Claude for post {post.get('urn')}: {e}")

    with open(candidate_file, "w") as f:
        json.dump(processed_posts, f, indent=4)
        
    print(f"Generated comments for {len(processed_posts)} posts.")

if __name__ == "__main__":
    generate_comments()
