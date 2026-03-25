import requests
import feedparser
from newspaper import Article as NewsScraper
from google import genai
from google.genai import types
import json
import random
import os

# ==========================================
# ⚙️ BOT CONFIGURATION
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = "jungle_super_secret_bot_key_2026"  
GEMINI_API_KEY = "AIzaSyCE2zLpEmTtI5We3R6R2mAevuDsgGkW2KQ" 
PEXELS_API_KEY = "PASTE_YOUR_FREE_PEXELS_KEY_HERE" # <--- PASTE PEXELS KEY HERE

# The memory file that stops duplicates!
MEMORY_FILE = "jungle_posted_links.txt"

# Array of Premium Ghanaian News Feeds
GHANA_RSS_FEEDS = [
    "https://www.myjoyonline.com/feed/",          
    "https://citinewsroom.com/feed/",             
    "https://pulse.com.gh/news/rss",              
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml" 
]

# Provide a User-Agent so news sites don't block us (The Disguise)
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Initialize the GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

# --- MEMORY FUNCTIONS ---
def is_already_posted(url):
    """Checks if we have already posted this exact article URL."""
    if not os.path.exists(MEMORY_FILE):
        return False
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return url in file.read()

def remember_url(url):
    """Saves the URL to our memory file so we never post it again."""
    with open(MEMORY_FILE, "a", encoding="utf-8") as file:
        file.write(url + "\n")
# ------------------------

def find_clean_image(keyword):
    """Searches Pexels for a real, high-quality, royalty-free stock photo."""
    search_query = f"{keyword} Africa"
    print(f"🔍 Hunting for clean stock photo on Pexels using: '{search_query}'")
    
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
    """Sends the raw scraped text to Gemini and forces a long-form, perfect JSON output."""
    prompt = f"""
    You are a senior investigative journalist for 'Jungle News', a premier Ghanaian digital news platform.
    Read the following facts and write a comprehensive, in-depth, and engaging long-form news article.
    
    Rules:
    1. The article 'content' MUST be strictly between 800 and 1200 words. 
    2. Expand on the story by adding relevant background context, explaining the broader implications, and discussing potential future impacts. Do not repeat yourself.
    3. Format the 'content' in clean HTML. Use at least 6-8 well-developed <p> paragraphs and multiple <h2> tags. Use single quotes inside HTML.
    4. Do NOT copy sentences from the original. 
    5. Write a catchy 'title' and a punchy 'excerpt' (THE EXCERPT MUST BE STRICTLY UNDER 250 CHARACTERS).
    6. IMAGE LOGIC: If the story is heavily focused on a specific politician, celebrity, or unique breaking event, set 'image_keywords' to EXACTLY "USE_ORIGINAL". If it is a general story (like tech, education, or lifestyle), provide a SINGLE, simple visual search keyword (e.g., "police", "university", "technology").
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
    
    if not feed.entries:
        print("⚠️ No articles found! The site might be blocking us, or the feed URL is broken.")
        return
        
    posted_count = 0
    
    # Check the top 5 articles, but stop after we successfully post 2 new ones
    for entry in feed.entries[:5]:
        if posted_count >= 2:
            break
            
        print(f"\n📰 Found Story: {entry.title}")
        
        # 👇 THE MEMORY CHECK 👇
        if is_already_posted(entry.link):
            print("⏭️ We already posted this story earlier today. Skipping to the next one...")
            continue
            
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
            
        # 👇 THE SMART IMAGE LOGIC 👇
        keyword = ai_data.get("image_keywords", "news")
        
        if keyword == "USE_ORIGINAL":
            final_cover_image = original_image
            print("📸 AI detected a specific person/event. Using the original source image for accuracy.")
        else:
            clean_image = find_clean_image(keyword)
            if clean_image:
                final_cover_image = clean_image
                print(f"✅ Successfully found a clean stock photo for '{keyword}'!")
            else:
                final_cover_image = original_image
                print("⚠️ Clean image search failed. Falling back to the original source image.")
            
        # 👇 THE EXCERPT DATABASE SAFETY SCISSORS 👇
        raw_excerpt = ai_data.get("excerpt", "")
        safe_excerpt = raw_excerpt[:290] + "..." if len(raw_excerpt) > 290 else raw_excerpt
            
        payload = {
            "title": ai_data.get("title"),
            "content": ai_data.get("content"),
            "excerpt": safe_excerpt,
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
            # Save it to memory so we never duplicate it!
            remember_url(entry.link)
            posted_count += 1
        else:
            print(f"❌ FAILED to publish: {res.text}")

if __name__ == "__main__":
    run_bot()