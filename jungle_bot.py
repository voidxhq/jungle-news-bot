import requests
import feedparser
from newspaper import Article as NewsScraper
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
# ⚙️ CLOUD CONFIGURATION (GitHub Secrets)
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = os.environ.get("JUNGLE_BOT_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# 🌍 DIVERSE GHANA & CAMPUS FEEDS
GHANA_RSS_FEEDS = [
    "https://kuulpeeps.com/feed/",
    "https://yfmghana.com/feed/",
    "https://www.campusgh.com/feed/",
    "https://ucc.edu.gh/news/rss", 
    "https://ug.edu.gh/news/rss.xml", 
    "https://knust.edu.gh/news/rss",
    "https://yen.com.gh/rss/",
    "https://www.myjoyonline.com/feed/",          
    "https://citinewsroom.com/feed/",             
    "https://pulse.com.gh/news/rss",
    "https://www.ghanaweb.com/GhanaHomePage/NewsArchive/rss.xml",
    "https://graphic.com.gh/feed/"
]

feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
client = genai.Client(api_key=GEMINI_API_KEY)

# ─── 🔥 THE X TREND SNIPER ────────────────────────────────────────────────────
def get_trending_x_feed():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get("https://trends24.in/ghana/", headers=headers, timeout=10)
        match = re.search(r'class="trend-name"[^>]*><a[^>]*>([^<]+)</a>', res.text)
        if match:
            top_trend = match.group(1).strip()
            safe_trend = urllib.parse.quote(f"{top_trend} Ghana News")
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

def rewrite_article_with_ai(raw_text, forced_category=None):
    category_rule = f"Set 'category_slug' to EXACTLY '{forced_category}'." if forced_category else "Pick the most accurate 'category_slug' from: ['news', 'sports', 'entertainment', 'campusinsider', 'tech', 'ghana']."

    prompt = f"""
    You are the Editorial Director for Jungle News, a high-authority digital news organization in Ghana.
    Your task is to rewrite the following source material into a professional, objective, and deeply informative long-form news article.
    
    STRICT EDITORIAL GUIDELINES:
    1. PROFESSIONALISM: Avoid sensationalist clickbait. DO NOT use phrases like "Red Alert," "Jungle Justice," "Shocking," or "Unmasked." Use a sophisticated, neutral, and authoritative journalistic tone.
    2. HEADLINE: Write a strong, clear, and professional title that conveys the main fact. No all-caps shouting.
    3. LENGTH: The 'content' MUST be 800-1200 words. This is critical for AdSense and SEO. Provide deep context, historical background, and objective analysis of the situation.
    4. STRUCTURE: 
       - Start with a "Key Highlights" <ul> list of 3-4 professional bullet points.
       - Use clean HTML: <p> for paragraphs, <h2> for section headers.
       - Keep paragraphs short (3-4 sentences) for mobile readability.
    5. FORMATTING: Use <strong> tags sparingly for key names or figures. 
    6. EXCERPT: Write a concise, factual summary strictly under 240 characters.
    7. IMAGE LOGIC: Set 'image_keywords' to "USE_ORIGINAL" if the story is about a specific Ghanaian person, event, or institution (UCC, SRC, Gov, etc.). Only use search keywords for generic abstract topics.
    8. {category_rule}
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

def get_campus_prioritized_entries(feed):
    campus_keywords = ['ucc', 'legon', 'knust', 'student', 'campus', 'src', 'hostel', 'nugs', 'tertiary']
    campus, general = [], []
    for entry in feed.entries:
        if any(kw in entry.title.lower() for kw in campus_keywords):
            campus.append(entry)
        else:
            general.append(entry)
    return campus + general

def run_bot():
    random.shuffle(GHANA_RSS_FEEDS)
    trend_feed = get_trending_x_feed()
    if trend_feed:
        GHANA_RSS_FEEDS.insert(0, trend_feed)
    
    feed = None
    for target in GHANA_RSS_FEEDS:
        try:
            feed = feedparser.parse(target)
            if feed.entries: break
        except: continue
            
    if not feed or not feed.entries: return
        
    sorted_entries = get_campus_prioritized_entries(feed)
    posted_count = 0
    now = datetime.utcnow()
    
    for entry in sorted_entries:
        if posted_count >= 2: break
        
        # Check freshness (4 hour window)
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            if now - datetime.fromtimestamp(mktime(entry.published_parsed)) > timedelta(hours=4):
                continue
            
        scr = NewsScraper(entry.link)
        try:
            scr.download(); scr.parse()
        except: continue
            
        if not scr.text or len(scr.text) < 150: continue
            
        is_campus = any(u in entry.link for u in ['ucc.edu', 'knust.edu', 'ug.edu', 'kuulpeeps', 'campusgh'])
        
        data = rewrite_article_with_ai(scr.text, forced_category="campusinsider" if is_campus else None)
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
            print(f"✅ Published: {data.get('title')}")
            posted_count += 1

if __name__ == "__main__":
    run_bot()