import requests
import feedparser
from newspaper import Article as NewsScraper
from google import genai
from google.genai import types
import json
import random
import os

# ==========================================
# ⚙️ CLOUD CONFIGURATION (GitHub Secrets)
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = os.environ.get("JUNGLE_BOT_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

MEMORY_FILE = "posted_urls.txt"

# 🔥 YEN-STYLE VIRAL & ENTERTAINMENT FEEDS 🔥
GHANA_RSS_FEEDS = [
    "https://pulse.com.gh/entertainment/rss",     
    "https://ameyawdebrah.com/feed/",             
    "https://www.ghanaweb.com/GhanaHomePage/entertainment/rss2.xml", 
    "https://yfmghana.com/feed/",                 
    "https://www.myjoyonline.com/feed/",          
    "https://citinewsroom.com/feed/",
    "https://dailyguidenetwork.com/category/entertainment/feed/"
]

# Provide a User-Agent disguise
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Initialize the GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

# --- CLOUD MEMORY FUNCTIONS ---
def is_already_posted(url):
    if not os.path.exists(MEMORY_FILE): return False
    with open(MEMORY_FILE, "r", encoding="utf-8") as file: 
        return url in file.read()

def remember_url(url):
    with open(MEMORY_FILE, "a", encoding="utf-8") as file: 
        file.write(url + "\n")

# --- IMAGE SEARCH ---
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
    except:
        pass
    return None

# --- AI REWRITER (YEN.COM.GH STYLE) ---
def rewrite_article_with_ai(raw_text):
    prompt = f"""
    You are a highly engaging digital editor for 'Jungle News', a trendy Ghanaian news and entertainment platform similar to YEN.com.gh.
    Read the following facts and write a highly shareable, engaging, and conversational news article.
    
    Rules:
    1. The article 'content' MUST be strictly between 600 and 1000 words. Keep paragraphs short and punchy for mobile users.
    2. Expand on the story by adding context, explaining why Ghanaians care, and discussing the social media vibe or broader implications.
    3. Format the 'content' in clean HTML. Use multiple <p> tags and <h2> tags with exciting, clickable subheadings. Use single quotes inside HTML.
    4. Do NOT copy sentences from the original. Write in a relatable, slightly informal, but professional Ghanaian digital tone.
    5. Write a highly clickable, dramatic, and catchy 'title' (viral blog style) and a punchy 'excerpt' (STRICTLY UNDER 250 CHARACTERS).
    6. IMAGE LOGIC: If the story involves a specific celebrity, politician, or viral person, set 'image_keywords' to EXACTLY "USE_ORIGINAL". If generic, provide a SINGLE visual search keyword.
    7. Pick the most accurate 'category_slug' from: ["entertainment", "news", "sports", "campusinsider", "tech", "ghana"].
    8. Decide if this is 'is_breaking' news (true or false).
    
    Return a JSON object with keys: "title", "content", "excerpt", "image_keywords", "category_slug", "is_breaking".
    
    Original Text: {raw_text}
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

# --- MAIN ENGINE ---
def run_bot():
    random.shuffle(GHANA_RSS_FEEDS)
    
    feed = None
    for target_feed in GHANA_RSS_FEEDS:
        print(f"📡 Scanning for trending stories at {target_feed}...")
        feed = feedparser.parse(target_feed)
        if feed.entries:
            print(f"✅ Success! Grabbed {len(feed.entries)} articles.")
            break 
            
    if not feed or not feed.entries:
        print("❌ All feeds blocked by security. Ending session.")
        return
        
    posted_count = 0
    # Process top 5 entries, publish up to 2 new ones per run
    for entry in feed.entries[:5]:
        if posted_count >= 2: break
        
        print(f"\n📰 Checking: {entry.title}")
        
        if is_already_posted(entry.link):
            print("⏭️ Already posted. Skipping...")
            continue
            
        scraper = NewsScraper(entry.link)
        try:
            scraper.download()
            scraper.parse()
        except:
            continue
            
        raw_text = scraper.text
        if not raw_text or len(raw_text) < 150: continue
            
        print("🧠 Creating viral content with AI...")
        ai_data = rewrite_article_with_ai(raw_text)
        if not ai_data: continue
            
        # Image Selection logic
        keyword = ai_data.get("image_keywords", "trending")
        if keyword == "USE_ORIGINAL":
            final_cover_image = scraper.top_image 
            print("📸 Using original photo for celebrity/person accuracy.")
        else:
            clean_image = find_clean_image(keyword)
            final_cover_image = clean_image if clean_image else scraper.top_image 
            print(f"✅ Found clean stock photo for '{keyword}'.")
            
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
        
        print(f"🚀 Publishing: '{payload['title']}'")
        headers = {"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}
        res = requests.post(RENDER_API_URL, headers=headers, json=payload)
        
        if res.status_code == 201:
            print(f"✅ SUCCESS! Live now.")
            remember_url(entry.link)
            posted_count += 1
        else:
            print(f"❌ FAILED: {res.text}")

if __name__ == "__main__":
    run_bot()
