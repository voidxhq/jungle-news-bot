import requests
import feedparser
from newspaper import Article as NewsScraper
from google import genai
from google.genai import types
import json
import random

# ==========================================
# ⚙️ BOT CONFIGURATION
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = "jungle_super_secret_bot_key_2026"  
GEMINI_API_KEY = "AIzaSyCE2zLpEmTtI5We3R6R2mAevuDsgGkW2KQ" 
PEXELS_API_KEY = "JFtumHR8FAE3sOWQFOhFRkk5ryQE9wrljE2REfqcd4LW9mRdS8DzzAiP" # <--- NEW!

# Array of Premium Ghanaian News Feeds
GHANA_RSS_FEEDS = [
    "https://www.myjoyonline.com/feed/",          
    "https://citinewsroom.com/feed/",             
    "https://pulse.com.gh/news/rss",              
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml" 
]

# Initialize the GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

def find_clean_image(keyword):
    """Searches Pexels for a real, high-quality, royalty-free stock photo."""
    # We add 'Africa' to the search to try and keep the faces/locations localized
    search_query = f"{keyword} Africa"
    print(f"🔍 Hunting for clean image on Pexels using: '{search_query}'")
    
    headers = {
        "Authorization": PEXELS_API_KEY
    }
    url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=1"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos') and len(data['photos']) > 0:
                # Return the gorgeous, high-resolution version of the photo
                return data['photos'][0]['src']['large2x']
    except Exception as e:
        print(f"⚠️ Pexels search failed: {e}")
        
    return None

def rewrite_article_with_ai(raw_text):
    """Sends the raw scraped text to Gemini and forces a long-form, perfect JSON output."""
    prompt = f"""
    You are a senior investigative journalist for 'Jungle News', a premier Ghanaian digital news platform.
    Read the following facts and write a comprehensive, in-depth, and engaging long-form news article.
    
    Rules:
    1. The article 'content' MUST be strictly between 800 and 1200 words. 
    2. To reach this length, do not repeat yourself. Instead, expand on the story by adding relevant background context, explaining the broader implications of the event, and discussing potential future impacts.
    3. Format the 'content' in clean HTML. Use at least 6-8 well-developed <p> paragraphs. Use multiple <h2> tags to break the story into logical sections. Use single quotes inside HTML.
    4. Do NOT copy sentences from the original. 
    5. Write a catchy 'title' and a punchy 2-sentence 'excerpt'.
    6. Provide a SINGLE, simple visual search keyword to find a stock photo for this story (e.g., "police", "university", "technology", "soccer"). Name the key 'image_keywords'.
    7. Pick the most accurate 'category_slug' for this story from this exact list: ["news", "sports", "entertainment", "campusinsider", "tech", "ghana"].
    8. Decide if this is 'is_breaking' news (true or false).
    
    Return a JSON object with exactly these keys: "title", "content", "excerpt", "image_keywords", "category_slug", "is_breaking".
    
    Original Text:
    {raw_text}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ AI Rewrite failed: {e}")
        return None

def run_bot():
    target_feed = random.choice(GHANA_RSS_FEEDS)
    print(f"📡 Scanning for news at {target_feed}...")
    
    feed = feedparser.parse(target_feed)
    
    for entry in feed.entries[:2]:
        print(f"\n📰 Found Story: {entry.title}")
        
        scraper = NewsScraper(entry.link)
        try:
            scraper.download()
            scraper.parse()
        except:
            print("⚠️ Could not download article. Skipping.")
            continue
            
        raw_text = scraper.text
        original_image = scraper.top_image 
        
        if not raw_text or len(raw_text) < 100:
            print("⚠️ Article too short to rewrite. Skipping.")
            continue
            
        print("🧠 Sending to AI for rewriting and categorization...")
        ai_data = rewrite_article_with_ai(raw_text)
        
        if not ai_data:
            continue
            
        # Call our new Pexels function!
        clean_image = find_clean_image(ai_data.get("image_keywords", "news"))
        
        if clean_image:
            final_cover_image = clean_image
            print("✅ Successfully found a clean, unique cover image!")
        else:
            final_cover_image = original_image
            print("⚠️ Clean image search failed. Falling back to the original source image.")
            
        payload = {
            "title": ai_data.get("title"),
            "content": ai_data.get("content"),
            "excerpt": ai_data.get("excerpt"),
            "cover_image": final_cover_image,
            "category_slug": ai_data.get("category_slug", "news"), 
            "is_breaking": ai_data.get("is_breaking", False),
            "is_trending": False,
            "is_featured": False
        }
        
        print(f"🚀 Publishing '{payload['title']}' to the '{payload['category_slug']}' category...")
        headers = {"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}
        
        res = requests.post(RENDER_API_URL, headers=headers, json=payload)
        
        if res.status_code == 201:
            print(f"✅ SUCCESS! Live at: {res.json().get('url')}")
        else:
            print(f"❌ FAILED to publish: {res.text}")

if __name__ == "__main__":
    run_bot()