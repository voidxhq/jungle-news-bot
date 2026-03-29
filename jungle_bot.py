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

# 🌍 MASSIVE GHANA & CAMPUS RSS FEEDS
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

# ─── 🔥 THE X (TWITTER) TREND SNIPER ──────────────────────────────────────────
def get_trending_x_feed():
    print("🔍 Checking X (Twitter) for the top Ghana trend...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get("https://trends24.in/ghana/", headers=headers, timeout=10)
        
        # Regex to find the #1 trend
        match = re.search(r'class="trend-name"[^>]*><a[^>]*>([^<]+)</a>', res.text)
        if match:
            top_trend = match.group(1).strip()
            print(f"🔥 TOP TREND DETECTED: {top_trend}")
            
            # Turn the trend into a Google News RSS feed search!
            safe_trend = urllib.parse.quote(f"{top_trend} Ghana")
            trend_rss_url = f"https://news.google.com/rss/search?q={safe_trend}&hl=en-NG&gl=GH&ceid=GH:en"
            return trend_rss_url
    except Exception as e:
        print(f"⚠️ Could not fetch X trends: {e}")
    return None

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
        pass
    return None

def rewrite_article_with_ai(raw_text, forced_category=None):
    category_rule = f"Set 'category_slug' to EXACTLY '{forced_category}'." if forced_category else "Pick the most accurate 'category_slug' from this list: ['news', 'sports', 'entertainment', 'campusinsider', 'tech', 'ghana']."

    prompt = f"""
    You are the lead content writer for a viral, highly engaging Ghanaian news and campus blog.
    Read the following raw facts and write a highly clickable, engaging, long-form news article.
    
    STRICT WRITING RULES:
    1. LENGTH (CRITICAL): The article 'content' MUST be strictly between 800 and 1200 words to qualify for Google AdSense. Expand on the background and implications.
    2. Tone: Sensational but accurate, highly engaging, relatable to Ghanaian youth.
    3. Headline: Write a very catchy, curiosity-inducing 'title'.
    4. Structure: Start with a <ul> list of 3-4 bullet points ("What you need to know"). Follow with short, punchy paragraphs (max 2-3 sentences).
    5. Formatting: Heavily use HTML <strong> tags to bold important names. Use multiple <h2> tags.
    6. Excerpt: Write a punchy 'excerpt' strictly under 200 characters.
    
    META RULES:
    7. IMAGE LOGIC: If it's a specific person/event, set 'image_keywords' to "USE_ORIGINAL". Otherwise, give a 1-2 word search keyword.
    8. {category_rule}
    9. Decide if this is 'is_breaking' news (true or false).
    
    Return a JSON object with EXACTLY these keys: "title", "content", "excerpt", "image_keywords", "category_slug", "is_breaking".
    
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

def get_campus_prioritized_entries(feed):
    campus_keywords = ['ucc', 'legon', 'knust', 'student', 'campus', 'src', 'vice chancellor', 'hostel', 'nugs']
    campus_entries, general_entries = [], []
    for entry in feed.entries:
        title_lower = entry.title.lower()
        if any(keyword in title_lower for keyword in campus_keywords):
            campus_entries.append(entry)
        else:
            general_entries.append(entry)
    return campus_entries + general_entries

def run_bot():
    random.shuffle(GHANA_RSS_FEEDS)
    
    # 🔥 Try to snipe the top X Trend first!
    trend_feed = get_trending_x_feed()
    if trend_feed:
        GHANA_RSS_FEEDS.insert(0, trend_feed) # Put it at the very front of the line
    
    feed = None
    for target_feed in GHANA_RSS_FEEDS:
        print(f"📡 Scanning for news at {target_feed[:50]}...")
        try:
            feed = feedparser.parse(target_feed)
            if feed.entries:
                print(f"✅ Success! Grabbed {len(feed.entries)} articles from this feed.")
                break
        except Exception as e:
            print(f"⚠️ Feed error: {e}")
            
    if not feed or not feed.entries:
        print("❌ All feeds were blocked or empty! The bot will try again later.")
        return
        
    sorted_entries = get_campus_prioritized_entries(feed)
    posted_count = 0
    now = datetime.utcnow()
    
    for entry in sorted_entries:
        if posted_count >= 2:
            break
            
        print(f"\n📰 Found Story: {entry.title}")
        
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
            print("⚠️ Article too short to rewrite. Skipping.")
            continue
            
        # Route to Campus Insider if from a uni site
        is_campus_source = any(campus_url in entry.link for campus_url in ['ucc.edu', 'knust.edu', 'ug.edu', 'kuulpeeps', 'campusgh'])
        
        print("🧠 Sending to AI for Yen.com.gh Style + AdSense Rewrite...")
        ai_data = rewrite_article_with_ai(raw_text, forced_category="campusinsider" if is_campus_source else None)
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