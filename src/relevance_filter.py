import os
import json
from groq import Groq

def filter_posts():
    candidate_file = "data/candidate_posts.json"
    if not os.path.exists(candidate_file):
        print("No candidate posts to filter.")
        return

    with open(candidate_file, "r") as f:
        try:
            posts = json.load(f)
        except:
            posts = []

    if not posts:
        return

    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        print("GROQ_API_KEY missing.")
        return
        
    client = Groq(api_key=groq_api_key)
    
    relevant_posts = []
    
    for post in posts:
        text = post.get("text", "")
        if not text:
            continue
            
        prompt = (
            "You are a relevance classifier for LinkedIn posts. "
            "Your job is to determine if a post is genuinely about AI/ML topics "
            "(LLMs, deep learning, computer vision, AI agents, NLP, model training, "
            "AI research, AI tools, AI ethics, AI in industry).\n"
            "Respond ONLY with a JSON object. No explanation. No markdown. Example:\n"
            '{"relevant": true, "post_type": "insight"}\n'
            'post_type must be one of: "insight", "question", "announcement", "opinion"\n'
            "A post is NOT relevant if AI is mentioned only casually or tangentially.\n\n"
            f"Post text:\n{text}"
        )
        
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a JSON-only response bot."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-8b-8192",
                temperature=0.0
            )
            
            output = response.choices[0].message.content.strip()
            # Clean up markdown if model incorrectly outputs it
            if output.startswith("```json"):
                output = output[7:-3]
            elif output.startswith("```"):
                output = output[3:-3]
                
            result = json.loads(output)
            if result.get("relevant"):
                post["post_type"] = result.get("post_type", "insight")
                relevant_posts.append(post)
                
        except Exception as e:
            print(f"Error calling Groq for post {post.get('urn')}: {e}")

    with open(candidate_file, "w") as f:
        json.dump(relevant_posts, f, indent=4)
        
    print(f"{len(relevant_posts)} out of {len(posts)} posts are relevant.")

if __name__ == "__main__":
    filter_posts()
