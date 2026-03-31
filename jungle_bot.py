import requests
import feedparser
from newspaper import Article as NewsScraper, Config
from google import genai
from google.genai import types
import json
import random
import os
import urllib.parse
import re
from datetime import datetime, timedelta
from time import mktime

# ==========================================
# ⚙️ CLOUD CONFIGURATION & GLOBALS
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = os.environ.get("JUNGLE_BOT_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

TRACKER_FILE = "daily_tracker.json"
POSTED_URLS_FILE = "posted_urls.txt"
REQUIRED_CATEGORIES = ['news', 'sports', 'entertainment', 'campusinsider', 'tech', 'ghana']

# 🌍 DIVERSE GHANA & CAMPUS FEEDS
GHANA_RSS_FEEDS = [
    # 🎓 Campus / Youth
    "https://kuulpeeps.com/feed/",
    "https://www.campusgh.com/feed/",
    "https://yfmghana.com/feed/",
    
    # 🇬🇭 Ghana News
    "https://yen.com.gh/rss/",
    "https://www.myjoyonline.com/feed/",
    "https://citinewsroom.com/feed/",
    "https://pulse.com.gh/news/rss",
    "https://www.ghanaweb.com/GhanaHomePage/NewsArchive/rss.xml",
    "https://graphic.com.gh/feed/",
    "https://www.adomonline.com/feed/",
    "https://starrfm.com.gh/feed/",
    
    # 💻 STUDENT TECH (🔥 IMPORTANT ADD)
    "https://techcrunch.com/feed/",
    "https://thenextweb.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.engadget.com/rss.xml",
    "https://techcabal.com/feed/",
    "https://www.itnewsafrica.com/feed/",
    "https://www.gadgetsafrica.com/feed/",
    "https://dev.to/feed",
    
    # 🔥 Trends
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo=GH"
]

CATEGORY_KEYWORDS = {
    'sports': ['football', 'match', 'coach', 'black stars', 'league', 'goals', 'stadium', 'tournament', 'medals', 'games','fifa', 'world cup', 'afcon', 'sports fest', 'athletics', 'basketball', 'volleyball','champions league', 'premier league', 'la liga', 'serie a', 'uefa'],
    'entertainment': ['shatta', 'stonebwoy', 'sarkodie', 'music', 'movie', 'actor', 'actress', 'concert', 'album', 'artist', 'afrobeats'],
    'campusinsider': [
    'ucc', 'knust', 'legon', 'ug',"traditional halls",
    'student', 'campus', 'src',"casford", "campus clash", "campus tradition",
    'hostel', 'hall week',"first semester", "second semester","conti", "katanga", "atl",
    'nugs', 'tertiary', 'src election','freshers',"finals","results"
    'lecture', 'exam', 'morale',
    'admission', 'graduation', 'artistes night','sports fest', 'interhall', 'intervarsity', 'student union'
],
    'tech': [
    'ai', 'chatgpt', 'openai','claude', 'gemini', 'midjourney', 'dall-e',
    'app', 'mobile app',
    'iphone', 'android', 'phone',
    'laptop', 'macbook',
    'startup', 'side hustle', 'online money',
    'coding', 'developer', 'programming',
    'software', 'tech', 'internet',
    'crypto', 'fintech', 'blockchain', 'nft', 'web3', 'gadgets', 'innovation', 'silicon', 'valley', 'elon musk', 'tesla', 'spacex', 'jeff bezos'
],
    'ghana': ['mahama', 'bawumia', 'npp', 'ndc', 'accra', 'kumasi', 'ghanaian', 'cedi', 'parliament'],
    'news': ['police', 'court', 'killed', 'accident', 'hospital', 'government', 'minister']
}

feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
client = genai.Client(api_key=GEMINI_API_KEY)

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
        except: pass
    return {'date': today, 'posted_categories': []}

def save_daily_tracker(data):
    with open(TRACKER_FILE, 'w') as f:
        json.dump(data, f)

# ─── 🔥 THE X TREND SNIPER ────────────────────────────────────────────────────
def get_trending_x_feed():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get("https://trends24.in/ghana/", headers=headers, timeout=10)
        match = re.search(r'class="trend-name"[^>]*><a[^>]*>([^<]+)</a>', res.text)
        if match:
            top_trend = match.group(1).strip()
            safe_trend = urllib.parse.quote(f"{top_trend} Ghana")
            return f"https://news.google.com/rss/search?q={safe_trend}&hl=en-NG&gl=GH&ceid=GH:en"
    except Exception:
        pass
    return None

def find_clean_image(keyword):
    search_query = f"{keyword} Ghana"
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'):
                return data['photos'][0]['src']['large2x']
    except Exception:
        pass
    return None

def rewrite_article_with_ai(raw_text, forced_category, missing_categories):
    missing_str = ", ".join(missing_categories)
    
    if forced_category:
        cat_logic = f"Set 'category_slug' to EXACTLY '{forced_category}'."
    else:
        cat_logic = f"Pick the most accurate 'category_slug' from: {REQUIRED_CATEGORIES}. URGENT PRIORITY: We urgently need articles for these categories today: [{missing_str}]. If the content matches one of these missing categories, assign it to that category!"

    prompt = f"""
    You are the Editorial Director for Jungle News, a high-authority digital news organization in Ghana.
    Your task is to rewrite the following source material into a professional, objective, and deeply informative long-form news article.
    
    STRICT EDITORIAL GUIDELINES:
    1. PROFESSIONALISM: Avoid sensationalist clickbait. DO NOT use phrases like "Red Alert," "Jungle Justice," or "Shocking." Use a sophisticated, neutral, and authoritative journalistic tone.
    2. HEADLINE: Write a strong, clear, and professional title that conveys the main fact.
    3. LENGTH: The 'content' MUST be 800-1200 words. Provide deep context, historical background, and objective analysis.
    4. STRUCTURE: 
       - Start with a "Key Highlights" <ul> list of 3-4 professional bullet points.
       - Use clean HTML: <p> for paragraphs, <h2> for section headers.
       - Keep paragraphs short (3-4 sentences).
    5. FORMATTING: Use <strong> tags sparingly for key names or figures. 
    6. EXCERPT: Write a concise, factual summary strictly under 240 characters.
    7. IMAGE LOGIC: Set 'image_keywords' to "USE_ORIGINAL" if the story is about a specific Ghanaian person, event, or institution. Only use keywords for generic abstract topics.
    8. {cat_logic}
    9. Decide if this is 'is_breaking' news (true or false).
    
    Return a JSON object: "title", "content", "excerpt", "image_keywords", "category_slug", "is_breaking".
    
    Source Material:
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
        print(f"❌ AI Error: {e}")
        return None

def score_entry_for_hunting(entry, missing_categories):
    score = 0
    title = entry.title.lower()
    
    # Check if this article matches a category we are desperately looking for
    for cat in missing_categories:
        keywords = CATEGORY_KEYWORDS.get(cat, [])
        if any(kw in title for kw in keywords):
            score += 50 # High priority boost!
            break
            
    # Freshness boost
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        hours_old = (datetime.utcnow() - datetime.fromtimestamp(mktime(entry.published_parsed))).total_seconds() / 3600
        if hours_old < 2:
            score += 10
            
    return score

def run_bot():
    print("🚀 Starting Jungle News Bot...")
    posted_urls = get_posted_urls()
    tracker = get_daily_tracker()
    
    # Figure out what categories we haven't posted today
    missing_categories = [c for c in REQUIRED_CATEGORIES if c not in tracker['posted_categories']]
    print(f"📊 Missing categories today: {missing_categories}")

    # Add trend feed dynamically
    trend_feed = get_trending_x_feed()
    if trend_feed:
        GHANA_RSS_FEEDS.insert(0, trend_feed)
    
    all_entries = []
    
    # Gather a massive pool of news from ALL feeds instead of stopping at the first one
    for target in GHANA_RSS_FEEDS:
        try:
            feed = feedparser.parse(target)
            if hasattr(feed, 'entries') and feed.entries:
                for e in feed.entries[:5]: # Take top 5 from each feed
                    if e.link not in posted_urls:
                        all_entries.append(e)
        except: continue
            
    if not all_entries: 
        print("❌ No fresh news found.")
        return
        
    # Sort the entries. The "Hunting Logic" pushes missing category topics to the top!
    all_entries.sort(key=lambda x: score_entry_for_hunting(x, missing_categories), reverse=True)
    
    posted_count = 0
    now = datetime.utcnow()
    
    # 🛡️ THE SCRAPER DISGUISE
    user_config = Config()
    user_config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
    user_config.request_timeout = 15 
    
    for entry in all_entries:
        if posted_count >= 4: # EXACTLY 4 POSTS PER RUN
            break
            
        # Hard freshness check (Skip if older than 4 hours)
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            if now - datetime.fromtimestamp(mktime(entry.published_parsed)) > timedelta(hours=4):
                continue
            
        scr = NewsScraper(entry.link, config=user_config)
        try:
            scr.download(); scr.parse()
        except Exception as e: 
            print(f"⚠️ Blocked: {entry.link}")
            continue
            
        if not scr.text or len(scr.text) < 150: continue
            
        is_campus = any(u in entry.link for u in ['ucc.edu', 'knust.edu', 'ug.edu', 'kuulpeeps', 'campusgh'])
        
        print(f"✍️ Writing: {entry.title[:50]}...")
        data = rewrite_article_with_ai(scr.text, "campusinsider" if is_campus else None, missing_categories)
        if not data: continue
            
        img = scr.top_image if data.get("image_keywords") == "USE_ORIGINAL" else (find_clean_image(data.get("image_keywords")) or scr.top_image)
            
        payload = {
            "title": data.get("title"),
            "content": data.get("content"),
            "excerpt": data.get("excerpt")[:280],
            "cover_image": img,
            "category_slug": data.get("category_slug", "news"), 
            "is_breaking": data.get("is_breaking", False)
        }
        
        res = requests.post(RENDER_API_URL, headers={"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}, json=payload)
        if res.status_code == 201:
            print(f"✅ Published [{data.get('category_slug')}]: {data.get('title')}")
            posted_count += 1
            save_posted_url(entry.link)
            
            # Update the daily tracker memory
            cat = data.get('category_slug')
            if cat not in tracker['posted_categories']:
                tracker['posted_categories'].append(cat)
                save_daily_tracker(tracker)
                missing_categories = [c for c in REQUIRED_CATEGORIES if c not in tracker['posted_categories']]

if __name__ == "__main__":
    run_bot()