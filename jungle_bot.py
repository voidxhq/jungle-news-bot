import requests
import feedparser
from newspaper import Article as NewsScraper, Config
from google import genai
from google.genai import types
import json
import os
import urllib.parse
import re
import time
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
    "https://www.itnewsafrica.com/feed/",
    "https://www.gadgetsafrica.com/feed/",
    "https://dev.to/feed",
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo=GH"
]

CATEGORY_KEYWORDS = {
    'sports': ['football', 'match', 'coach', 'black stars', 'league', 'goals', 'stadium', 'tournament', 'medals', 'games','fifa', 'world cup', 'afcon', 'sports fest', 'athletics', 'basketball', 'volleyball','champions league', 'premier league', 'la liga', 'serie a', 'uefa'],
    'entertainment': ['shatta', 'stonebwoy', 'sarkodie', 'music', 'movie', 'actor', 'actress', 'concert', 'album', 'artist', 'afrobeats'],
    'campusinsider': [
        'ucc', 'knust', 'legon', 'ug', "traditional halls",
        'student', 'campus', 'src', "casford", "campus clash", "campus tradition",
        'hostel', 'hall week', "first semester", "second semester", "conti", "katanga", "atl",
        'nugs', 'tertiary', 'src election', 'freshers', "finals", "results",
        'lecture', 'exam', 'morale',
        'admission', 'graduation', 'artistes night', 'sports fest', 'interhall', 'intervarsity', 'student union'
    ],
    'tech': [
        'ai', 'chatgpt', 'openai', 'claude', 'gemini', 'midjourney', 'dall-e',
        'app', 'mobile app', 'iphone', 'android', 'phone', 'laptop', 'macbook',
        'startup', 'side hustle', 'online money', 'coding', 'developer', 'programming',
        'software', 'tech', 'internet', 'crypto', 'fintech', 'blockchain', 'nft', 'web3', 
        'gadgets', 'innovation', 'silicon', 'valley', 'elon musk', 'tesla', 'spacex', 'jeff bezos'
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
        cat_logic = f"Pick the most accurate 'category_slug' from: {REQUIRED_CATEGORIES}. URGENT PRIORITY: We urgently need articles for these categories today: [{missing_str}]."

    prompt = f"""
    You are the Editorial Director for Jungle News (UCC's leading news site) and VoidX.
    Your task is to rewrite the following source material into a professional, deeply informative, yet highly engaging long-form news article.
    
    STRICT EDITORIAL GUIDELINES:
    1. PROFESSIONAL BUT RELATABLE: Avoid cheap clickbait, but frame the story so it appeals to university students and Gen-Z tech enthusiasts. 
    2. HEADLINE: Write a strong, engaging headline. It must remain credible but be catchy.
    3. LENGTH: The 'content' MUST be 800-1200 words. Provide deep context and objective analysis.
    4. STRUCTURE: 
       - Start with a "Key Highlights" <ul> list of 3-4 professional bullet points.
       - Use clean HTML: <p> for paragraphs, <h2> for section headers.
       - Keep paragraphs short (3-4 sentences).
    5. EXCERPT: Write a concise, factual summary strictly under 240 characters.
    6. IMAGE LOGIC: Set 'image_keywords' to "USE_ORIGINAL" if the story is about a specific Ghanaian person/event. Otherwise use generic keywords.
    7. {cat_logic}
    
    8. VISIBILITY TAGS (CRITICAL): Analyze the story's impact and set boolean (true/false) values for:
       - 'is_breaking' (Only for urgent, unfolding, time-sensitive news)
       - 'is_trending' (For highly viral, pop culture, or heavily talked about topics)
       - 'is_featured' (For major headlines, high-quality deep dives, or front-page worthy news)
       (An article can have multiple tags set to true if it fits).
    
    Return EXACTLY a JSON object with these keys: 
    "title", "content", "excerpt", "image_keywords", "category_slug", "is_breaking", "is_trending", "is_featured".
    
    Source Material:
    {raw_text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
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
    
    for cat in missing_categories:
        keywords = CATEGORY_KEYWORDS.get(cat, [])
        if any(kw in title for kw in keywords):
            score += 50 
            break

    if any(kw in title for kw in CATEGORY_KEYWORDS['campusinsider']):
        score += 30

    if any(kw in title for kw in CATEGORY_KEYWORDS['tech']):
        score += 25
            
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        hours_old = (datetime.utcnow() - datetime.fromtimestamp(mktime(entry.published_parsed))).total_seconds() / 3600
        if hours_old < 2:
            score += 15
            
    return score

def run_bot():
    print("🚀 Starting Jungle News Bot...")
    posted_urls = get_posted_urls()
    tracker = get_daily_tracker()
    
    missing_categories = [c for c in REQUIRED_CATEGORIES if c not in tracker['posted_categories']]
    print(f"📊 Missing categories today: {missing_categories}")

    trend_feed = get_trending_x_feed()
    if trend_feed:
        GHANA_RSS_FEEDS.insert(0, trend_feed)
    
    all_entries = []
    for target in GHANA_RSS_FEEDS:
        try:
            feed = feedparser.parse(target)
            if hasattr(feed, 'entries') and feed.entries:
                for e in feed.entries[:8]: 
                    if e.link not in posted_urls:
                        all_entries.append(e)
        except: continue
            
    if not all_entries: 
        print("❌ No fresh news found.")
        return
        
    all_entries.sort(key=lambda x: score_entry_for_hunting(x, missing_categories), reverse=True)
    
    posted_count = 0
    now = datetime.utcnow()
    
    user_config = Config()
    user_config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
    user_config.request_timeout = 15 
    
    for entry in all_entries:
        if posted_count >= 4: 
            break
            
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            if now - datetime.fromtimestamp(mktime(entry.published_parsed)) > timedelta(hours=6):
                continue
            
        scr = NewsScraper(entry.link, config=user_config)
        try:
            scr.download(); scr.parse()
        except Exception as e: 
            print(f"⚠️ Blocked: {entry.link}")
            continue
            
        if not scr.text or len(scr.text) < 150: continue
            
        is_campus = (
            any(u in entry.link for u in ['ucc.edu', 'knust.edu', 'ug.edu', 'kuulpeeps', 'campusgh'])
            or any(kw in entry.title.lower() for kw in CATEGORY_KEYWORDS['campusinsider'])
        )
        
        print(f"✍️ Writing: {entry.title[:50]}...")
        data = rewrite_article_with_ai(scr.text, "campusinsider" if is_campus else None, missing_categories)
        
        if not data: 
            print("⏳ Cooling down for 5s after AI failure...")
            time.sleep(5)
            continue
            
        img = scr.top_image if data.get("image_keywords") == "USE_ORIGINAL" else (find_clean_image(data.get("image_keywords")) or scr.top_image)
        
        # 🛡️ THE SAFETY NET
        raw_excerpt = data.get("excerpt")
        safe_excerpt = raw_excerpt if raw_excerpt is not None else "Click to read the full story on Jungle News."
            
        # 🔥 UPGRADED PAYLOAD with all Visibility Tags
        payload = {
            "title": data.get("title"),
            "content": data.get("content"),
            "excerpt": safe_excerpt[:280],
            "cover_image": img,
            "category_slug": data.get("category_slug", "news"), 
            "is_breaking": data.get("is_breaking", False),
            "is_trending": data.get("is_trending", False),
            "is_featured": data.get("is_featured", False)
        }
        
        res = requests.post(RENDER_API_URL, headers={"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}, json=payload)
        
        if res.status_code == 201:
            print(f"✅ Published [{data.get('category_slug')}]: {data.get('title')}")
            posted_count += 1
            save_posted_url(entry.link)
            
            cat = data.get('category_slug')
            if cat not in tracker['posted_categories']:
                tracker['posted_categories'].append(cat)
                save_daily_tracker(tracker)
                missing_categories = [c for c in REQUIRED_CATEGORIES if c not in tracker['posted_categories']]
        
        # 🛑 THE COOL-DOWN to avoid 429 Errors
        print("⏳ Cooling down for 10 seconds to respect API limits...")
        time.sleep(10)

if __name__ == "__main__":
    run_bot()