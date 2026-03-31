import requests
import feedparser
from newspaper import Article as NewsScraper, Config
from groq import Groq
import json
import os
import urllib.parse
import time
from datetime import datetime, timedelta
from time import mktime

# ==========================================
# ⚙️ CLOUD CONFIGURATION & GLOBALS
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# 🎭 THE VIRTUAL NEWSROOM KEYS
AUTHOR_KEYS = {
    "nana": os.environ.get("KEY_NANA_AMA"),
    "emmanuel": os.environ.get("KEY_EMMANUEL"),
    "samuel": os.environ.get("KEY_SAMUEL"),
    "desmond": os.environ.get("KEY_DESMOND")
}
# Fallback key just in case a specific author's key is missing
FALLBACK_KEY = os.environ.get("JUNGLE_BOT_KEY") or AUTHOR_KEYS.get("samuel")

TRACKER_FILE = "daily_tracker.json"
POSTED_URLS_FILE = "posted_urls.txt"
REQUIRED_CATEGORIES = ['news', 'sports', 'entertainment', 'campusinsider', 'tech', 'ghana']

GHANA_RSS_FEEDS = [
    "https://kuulpeeps.com/feed/",
    "https://www.campusgh.com/feed/",
    "https://yfmghana.com/feed/",
    "https://yen.com.gh/rss/",
    "https://www.myjoyonline.com/feed/",
    "https://citinewsroom.com/feed/",
    "https://pulse.com.gh/news/rss",
    "https://www.ghanaweb.com/GhanaHomePage/NewsArchive/rss.xml",
    "https://graphic.com.gh/feed/",
    "https://www.adomonline.com/feed/",
    "https://starrfm.com.gh/feed/",
    "https://techcrunch.com/feed/",
    "https://thenextweb.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.engadget.com/rss.xml",
    "https://techcabal.com/feed/",
    "https://dev.to/feed"
]

CATEGORY_KEYWORDS = {
    'sports': ['football', 'match', 'coach', 'black stars', 'league', 'goals', 'stadium', 'afcon', 'premier league', 'champions league'],
    'entertainment': ['shatta', 'stonebwoy', 'sarkodie', 'music', 'movie', 'concert', 'album', 'artist', 'afrobeats'],
    'campusinsider': ['ucc', 'knust', 'legon', 'ug', 'student', 'campus', 'src', 'casford', 'hostel', 'hall week', 'nugs', 'tertiary'],
    'tech': ['ai', 'chatgpt', 'openai', 'app', 'iphone', 'android', 'laptop', 'startup', 'coding', 'developer', 'crypto', 'fintech'],
    'ghana': ['mahama', 'bawumia', 'npp', 'ndc', 'accra', 'kumasi', 'ghanaian', 'cedi', 'parliament'],
    'news': ['police', 'court', 'killed', 'accident', 'hospital', 'government', 'minister']
}

feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# ─── 🎭 WRITER ROUTING LOGIC ──────────────────────────────────────────────────
def get_writer_key(category_slug):
    """Assigns the correct Category Admin's API Key based on the story topic"""
    key = FALLBACK_KEY
    if category_slug in ['campusinsider', 'entertainment']:
        key = AUTHOR_KEYS.get("nana")
    elif category_slug in ['tech']:
        key = AUTHOR_KEYS.get("emmanuel")
    elif category_slug in ['news', 'ghana']:
        key = AUTHOR_KEYS.get("samuel")
    elif category_slug in ['sports', 'trending']:
        key = AUTHOR_KEYS.get("desmond")
    
    return key if key else FALLBACK_KEY

# ─── 🧠 MEMORY & TRACKING ──────────────────────────────────────────────────────
def get_posted_urls():
    if os.path.exists(POSTED_URLS_FILE):
        with open(POSTED_URLS_FILE, 'r') as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_posted_url(url):
    with open(POSTED_URLS_FILE, 'a') as f:
        f.write(url + '\n')

def get_daily_tracker():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, 'r') as f:
                data = json.load(f)
                if data.get('date') == today: 
                    return data
        except: 
            pass
    return {'date': today, 'posted_categories': []}

def save_daily_tracker(data):
    with open(TRACKER_FILE, 'w') as f:
        json.dump(data, f)

# ─── 🔥 IMAGE & AI REWRITE LOGIC ─────────────────────────────────────────────
def find_clean_image(keyword):
    if not keyword or keyword == "USE_ORIGINAL":
        return None
    search_query = f"{keyword} Ghana"
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'): 
                return data['photos'][0]['src']['large2x']
    except Exception as e: 
        print(f"⚠️ Pexels Image Error: {e}")
    return None

def rewrite_article_with_ai(raw_text, forced_category, missing_categories):
    missing_str = ", ".join(missing_categories)
    cat_logic = f"Set 'category_slug' to EXACTLY '{forced_category}'." if forced_category else f"Pick the most accurate 'category_slug' from: {REQUIRED_CATEGORIES}. PRIORITY TODAY: [{missing_str}]."

    prompt = f"""
    You are the Editorial Director for Jungle News (UCC's leading news site) and VoidX.
    Rewrite this source material into a professional, engaging long-form news article (800-1200 words).
    
    GUIDELINES:
    1. HEADLINE: Catchy but credible.
    2. STRUCTURE: Start with 3-4 bullet points in a <ul>. Use <p> and <h2> for body text.
    3. EXCERPT: Concise summary under 240 chars.
    4. IMAGE: Set 'image_keywords' to "USE_ORIGINAL" for specific Ghanaian events, otherwise use generic keywords.
    5. {cat_logic}
    6. VISIBILITY (STRICT): Choose EXACTLY ONE: "normal" (90% of news), "breaking" (emergencies/firings), "trending" (viral social media), or "featured" (exclusive deep-dives).
    
    Return EXACTLY a JSON object with NO MARKDOWN formatting: 
    {{"title": "...", "content": "...", "excerpt": "...", "image_keywords": "...", "category_slug": "...", "visibility_tag": "..."}}
    
    Source Material: 
    {raw_text}
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant", # Lightning fast Llama 3.1
            response_format={"type": "json_object"}, # Forces Groq to return perfect JSON
            temperature=0.7,
            max_tokens=4000
        )
        
        clean_text = chat_completion.choices[0].message.content.strip()
        return json.loads(clean_text)
    except Exception as e: 
        print(f"❌ Groq AI Error: {e}")
        return None

# ─── 🐺 HUNTING LOGIC ────────────────────────────────────────────────────────
def score_entry_for_hunting(entry, missing_categories):
    score = 0
    title = entry.title.lower()
    for cat in missing_categories:
        if any(kw in title for kw in CATEGORY_KEYWORDS.get(cat, [])):
            score += 50
            break
    if any(kw in title for kw in CATEGORY_KEYWORDS['campusinsider']): 
        score += 30
    return score

def run_bot():
    print("=========================================")
    print("🚀 BOT IS AWAKE: Starting Virtual Newsroom (Powered by Groq)")
    print("=========================================")
    
    posted_urls = get_posted_urls()
    print(f"📁 Memory loaded: {len(posted_urls)} previously posted articles.")
    
    tracker = get_daily_tracker()
    missing_categories = [c for c in REQUIRED_CATEGORIES if c not in tracker['posted_categories']]
    print(f"🎯 Target Categories for today: {missing_categories}")
    
    all_entries = []
    print("📡 Scanning RSS Feeds...")
    for target in GHANA_RSS_FEEDS:
        try:
            feed = feedparser.parse(target)
            for e in feed.entries[:3]: # Limit to top 3 per feed to save memory
                if e.link not in posted_urls: 
                    all_entries.append(e)
        except Exception as e: 
            pass
            
    print(f"🔎 Found {len(all_entries)} fresh unposted articles across all feeds.")
    if not all_entries: 
        print("💤 No fresh news found. Going back to sleep.")
        return
        
    all_entries.sort(key=lambda x: score_entry_for_hunting(x, missing_categories), reverse=True)
    
    posted_count = 0
    user_config = Config()
    user_config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
    
    for entry in all_entries:
        if posted_count >= 1: 
            print("✅ Drip-feed quota reached (1 post). Shutting down until next cron cycle.")
            break 
            
        print(f"\n🗞️ Attempting to process: {entry.title[:60]}...")
        
        scr = NewsScraper(entry.link, config=user_config)
        try: 
            scr.download()
            scr.parse()
        except Exception as e: 
            print(f"⚠️ Failed to scrape article text. Skipping.")
            continue
            
        if not scr.text or len(scr.text) < 200: 
            print("⚠️ Article text too short or blocked by paywall. Skipping.")
            continue
            
        is_campus = any(kw in entry.title.lower() for kw in CATEGORY_KEYWORDS['campusinsider'])
        
        print("🧠 Sending to Groq AI for rewrite...")
        data = rewrite_article_with_ai(scr.text, "campusinsider" if is_campus else None, missing_categories)
        
        if not data: 
            print("❌ AI Failed to return valid JSON. Moving to next article.")
            continue
            
        # 🚦 PROCESS PAYLOAD
        img = scr.top_image if data.get("image_keywords") == "USE_ORIGINAL" else (find_clean_image(data.get("image_keywords")) or scr.top_image)
        vis_tag = data.get("visibility_tag", "normal").lower()
        cat_slug = data.get("category_slug", "news")
        
        payload = {
            "title": data.get("title"),
            "content": data.get("content"),
            "excerpt": data.get("excerpt", "")[:280],
            "cover_image": img,
            "category_slug": cat_slug, 
            "is_breaking": (vis_tag == "breaking"),
            "is_trending": (vis_tag == "trending"),
            "is_featured": (vis_tag == "featured")
        }
        
        # 🎭 ROUTE TO CORRECT WRITER KEY
        current_key = get_writer_key(cat_slug)
        if not current_key:
            print(f"❌ CRITICAL: No API key found for category '{cat_slug}' and no fallback key exists!")
            continue

        print(f"🌐 Posting to Jungle News Backend (Category: {cat_slug}, Visibility: {vis_tag})...")
        res = requests.post(RENDER_API_URL, headers={"X-API-Key": current_key, "Content-Type": "application/json"}, json=payload)
        
        if res.status_code == 201:
            print(f"🎉 SUCCESS! Published: '{data.get('title')}'")
            posted_count += 1
            save_posted_url(entry.link)
            
            if cat_slug not in tracker['posted_categories']:
                tracker['posted_categories'].append(cat_slug)
                save_daily_tracker(tracker)
        else:
            print(f"❌ SERVER ERROR {res.status_code}: {res.text}")

if __name__ == "__main__":
    run_bot()