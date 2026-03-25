import requests
import feedparser
from newspaper import Article as NewsScraper
from google import genai
from google.genai import types
import json
import random
import os
from datetime import datetime, timedelta
from time import mktime

# ==========================================
# ⚙️ CLOUD CONFIGURATION (Hidden Keys!)
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
# It now pulls your secret keys securely from GitHub's vault!
JUNGLE_BOT_KEY = os.environ.get("JUNGLE_BOT_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

GHANA_RSS_FEEDS = [
    "https://www.myjoyonline.com/feed/",          
    "https://citinewsroom.com/feed/",             
    "https://pulse.com.gh/news/rss",              
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml" 
]

feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Initialize the GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

def find_clean_image(keyword):
    search_query = f"{keyword} Africa"
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos') and len(data['photos']) > 0:
                return data['photos'][0]['src']['large2x']
    except Exception as e:
        print(f"⚠️ Pexels search failed: {e}")
    return None

def rewrite_article_with_ai(raw_text):
    prompt = f"""
    You are a senior investigative journalist for 'Jungle News', a premier Ghanaian digital news platform.
    Read the following facts and write a comprehensive, in-depth, and engaging long-form news article.
    
    Rules:
    1. The article 'content' MUST be strictly between 800 and 1200 words. 
    2. Expand on the story by adding relevant background context, explaining the broader implications, and discussing potential future impacts. Do not repeat yourself.
    3. Format the 'content' in clean HTML. Use at least 6-8 well-developed <p> paragraphs and multiple <h2> tags. Use single quotes inside HTML.
    4. Do NOT copy sentences from the original. 
    5. Write a catchy 'title' and a punchy 'excerpt' (THE EXCERPT MUST BE STRICTLY UNDER 250 CHARACTERS).
    6. IMAGE LOGIC: If the story is heavily focused on a specific politician, celebrity, or unique breaking event, set 'image_keywords' to EXACTLY "USE_ORIGINAL". If it is a general story, provide a SINGLE, simple visual search keyword.
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
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ AI Rewrite failed: {e}")
        return None

def run_bot():
    target_feed = random.choice(GHANA_RSS_FEEDS)
    print(f"📡 Scanning for news at {target_feed}...")
    feed = feedparser.parse(target_feed)
    
    if not feed.entries:
        print("⚠️ No articles found!")
        return
        
    posted_count = 0
    now = datetime.utcnow()
    
    for entry in feed.entries[:5]:
        if posted_count >= 2:
            break
            
        print(f"\n📰 Found Story: {entry.title}")
        
        # 👇 THE CLOUD MEMORY: Check if the article is too old
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            article_time = datetime.fromtimestamp(mktime(entry.published_parsed))
            if now - article_time > timedelta(hours=4):
                print("⏭️ Article is older than 4 hours. Skipping to avoid duplicates...")
                continue
            
        scraper = NewsScraper(entry.link)
        try:
            scraper.download()
            scraper.parse()
        except:
            print("⚠️ Could not download article. Skipping.")
            continue
            
        raw_text = scraper.text
        if not raw_text or len(raw_text) < 100:
            continue
            
        print("🧠 Sending to AI...")
        ai_data = rewrite_article_with_ai(raw_text)
        if not ai_data:
            continue
            
        keyword = ai_data.get("image_keywords", "news")
        if keyword == "USE_ORIGINAL":
            final_cover_image = scraper.top_image 
        else:
            clean_image = find_clean_image(keyword)
            final_cover_image = clean_image if clean_image else scraper.top_image 
            
        raw_excerpt = ai_data.get("excerpt", "")
        safe_excerpt = raw_excerpt[:290] + "..." if len(raw_excerpt) > 290 else raw_excerpt
            
        payload = {
            "title": ai_data.get("title"),
            "content": ai_data.get("content"),
            "excerpt": safe_excerpt,
            "cover_image": final_cover_image,
            "category_slug": ai_data.get("category_slug", "news"), 
            "is_breaking": ai_data.get("is_breaking", False)
        }
        
        headers = {"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}
        res = requests.post(RENDER_API_URL, headers=headers, json=payload)
        
        if res.status_code == 201:
            print(f"✅ SUCCESS! Live at: {res.json().get('url')}")
            posted_count += 1
        else:
            print(f"❌ FAILED to publish: {res.text}")

if __name__ == "__main__":
    run_bot()