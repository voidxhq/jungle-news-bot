import requests
import feedparser
from newspaper import Article as NewsScraper, Config
from groq import Groq
import json
import os
import base64
import random
from datetime import datetime
import re  # Added for strict whole-word keyword matching

# ==========================================
# ⚙️ CLOUD CONFIGURATION & GLOBALS
# ==========================================
RENDER_API_URL = "https://www.junglenews.online/api/bot/post-article"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")  # Add a free ImgBB API key to your environment variables

# 🎭 THE VIRTUAL NEWSROOM KEYS
AUTHOR_KEYS = {
    "nana":       os.environ.get("KEY_NANA_AMA"),    # entertainment, campusinsider
    "emmanuel":   os.environ.get("KEY_EMMANUEL"),    # tech
    "samuel":     os.environ.get("KEY_SAMUEL"),      # news, ghana
    "desmond":    os.environ.get("KEY_DESMOND"),     # sports
    "superadmin": os.environ.get("JUNGLE_BOT_KEY"),  # Prince Eshun — randomly assigned
}

# 🎲 SUPER ADMIN RANDOM CHANCE (0.0 - 1.0)
SUPER_ADMIN_CHANCE = 0.25

TRACKER_FILE = "daily_tracker.json"
POSTED_URLS_FILE = "posted_urls.txt"
REQUIRED_CATEGORIES = ['news', 'sports', 'entertainment', 'campusinsider', 'tech', 'ghana']

GHANA_RSS_FEEDS = [
    # ---- 📰 General News ----
    "https://myjoyonline.com/feed",
    "https://pulse.com.gh/rss",
    "https://adomonline.com/feed",
    "https://www.modernghana.com/rss/",
    "https://www.ghanaweb.com/GhanaHomePage/rss/",
    "https://peacefmonline.com/feed",
    "https://citinewsroom.com/feed",
    "https://aptnewsghana.com/index.php/feed",
    "https://ghanaiantimes.com.gh/feed",
    "https://theheraldghana.com/feed",
    "https://ghanasummary.com/feed",
    "https://impelnews.net/feed",
    "https://afiaghana.com/feed",
    "https://ghheadlines.com/rss",

    # ---- 🎓 Campus / Education ----
    "https://ghcampus.com/feed",
    "https://accramail.com/feed",
    "https://campusnewsofficial.blogspot.com/feeds/posts/default",
    "https://ghanacampus.blogspot.com/feeds/posts/default",

    # ---- 🎬 Entertainment / Showbiz ----
    "https://ghanamusic.com/feed",
    "https://3music.tv/feed",
    "https://eonlinegh.com/feed",
    "https://adomonline.com/category/entertainment/feed",

    # ---- ⚽ Sports ----
    "https://soccanews.com/feed",
    "https://pulse.com.gh/sports/rss",
    "https://citinewsroom.com/category/sports/feed",

    # ---- 📱 Tech / Trends ----
    "https://mfidie.com/feed",
    "https://fifty7tech.com/feed"
]

CATEGORY_KEYWORDS = {
    'sports': [
        'football', 'match', 'coach', 'black stars', 'league', 'goals',
        'stadium', 'afcon', 'premier league', 'champions league',
        'fifa', 'referee', 'transfer', 'injury', 'kickoff', 'midfielder',
        'striker', 'defender', 'goalkeeper', 'sports ministry',
        'gfa', 'ghana fa', 'friendly match', 'qualifier', 'world cup',
        'chelsea', 'arsenal', 'manchester', 'real madrid', 'barcelona'
    ],

    'entertainment': [
        'shatta', 'stonebwoy', 'sarkodie', 'music', 'movie', 'concert',
        'album', 'artist', 'afrobeats', 'dancehall', 'rapper', 'actor', 
        'actress', 'celebrity', 'showbiz', 'performance', 'event', 'tour', 
        'festival', 'release', 'single', 'video', 'entertainment news'
    ],

    'campusinsider': [
        'ucc', 'knust', 'legon', 'university of ghana', 'uew', 'umat', 'upsa', 'gimpa', 'ttu', 'uds',
        'student', 'campus', 'src', 'nugs', 'jcr', 'src executives',
        'src president', 'nugs president', 'hall president', 'src election',
        'src manifesto', 'campus campaign', 'handover',
        'lecture','lecturers','midsem', 'end of semester', 'graduation', 'matriculation', 
        'orientation', 'dean of students', 'vice chancellor', 'academic calendar', 
        'resit', 'supplementary exams', 'deferred course', 'credit hour', 'cgpa', 'gpa',
        'level 100', 'level 200', 'level 300', 'level 400', 'freshers',
        'hostel', 'traditional hall', 'casford', 'mensah sarbah', 'commonwealth hall',
        'room allocation', 'campus accommodation', 'hall master', 'hall mistress', 'porter',
        'hall week', 'artists night', 'artiste night', 'jama night', 'hall dinner', 
        'awards night', 'freshers night', 'welcome bash', 'campus rave', 
        'campus concert', 'hall week celebration',
        'campus vibes', 'boys boys', 'slay queen', 'academic stress', 'lecturer wahala',
        'lecture hall', 'library', 'science market', 'campus wifi', 
        'eduroam', 'campus water shortage', 'campus power outage', 'dumsor on campus',
        'campus fellowship', 'campus ministry', 'scripture union', 'pensa',
        'campus police', 'campus security', 'student robbed', 'campus theft', 'hostel robbery',
        'trending on campus', 'viral on campus', 'campus drama', 'student protest', 'campus demonstration'
    ],

    'tech': [
        'ai', 'chatgpt', 'openai', 'app', 'iphone', 'android',
        'laptop', 'startup', 'coding', 'developer', 'crypto', 'fintech',
        'blockchain', 'software', 'hardware', 'programming',
        'python', 'javascript', 'web app', 'mobile app',
        'saas', 'cloud', 'cybersecurity', 'data', 'machine learning'
    ],

    'ghana': [
        'mahama', 'bawumia', 'npp', 'ndc', 'accra', 'kumasi',
        'ghanaian', 'cedi', 'parliament', 'ghana police', 'ecg', 'gridco', 
        'ec', 'election', 'president', 'vice president', 'minister', 'mp',
        'district', 'assembly', 'governor', 'policy', 'inflation', 'economy', 'fuel price'
    ],

    'news': [
        'police', 'court', 'killed', 'accident', 'hospital',
        'government', 'minister', 'arrest', 'investigation', 'fire outbreak', 
        'robbery', 'breaking', 'update', 'incident', 'crime', 'victim',
        'security', 'press release', 'statement', 'case', 'hearing', 'judgment', 'law'
    ]
}

feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)


# ─── 🎭 WRITER ROUTING LOGIC ──────────────────────────────────────────────────
def get_writer_key(category_slug):
    if random.random() < SUPER_ADMIN_CHANCE:
        superadmin_key = AUTHOR_KEYS.get("superadmin")
        if superadmin_key:
            print(f"  🎲 Random pick! This post goes to Prince Eshun (Super Admin).")
            return superadmin_key

    key_map = {
        'entertainment': AUTHOR_KEYS.get("nana"),
        'campusinsider': AUTHOR_KEYS.get("nana"),
        'tech':          AUTHOR_KEYS.get("emmanuel"),
        'news':          AUTHOR_KEYS.get("samuel"),
        'ghana':         AUTHOR_KEYS.get("samuel"),
        'sports':        AUTHOR_KEYS.get("desmond"),
        'trending':      AUTHOR_KEYS.get("desmond"),
    }

    intended_key = key_map.get(category_slug)
    if intended_key:
        return intended_key

    superadmin_key = AUTHOR_KEYS.get("superadmin")
    if superadmin_key:
        print(f"  ↳ No specific author key for '{category_slug}', routing to Prince Eshun (Super Admin).")
        return superadmin_key
    return None


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


# ─── 🔥 IMAGE LOGIC ──────────────────────────────────────────────────────────
def find_clean_image(keyword):
    if not keyword or str(keyword).strip().upper() == "USE_ORIGINAL":
        return None
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'):
                return data['photos'][0]['src']['large2x']
    except Exception as e:
        print(f"⚠️ Pexels Image Error: {e}")
    return None


# ─── 🛡️ IMAGE RE-HOSTING LOGIC ────────────────────────────────────────────────
def rehost_image(image_url):
    """Downloads an image from the source and re-hosts it on ImgBB to prevent broken images."""
    if not image_url or not IMGBB_API_KEY:
        return image_url  # Fallback to the original URL if no API key is set
        
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            image_b64 = base64.b64encode(response.content).decode('utf-8')
            
            res = requests.post("https://api.imgbb.com/1/upload", data={
                "key": IMGBB_API_KEY,
                "image": image_b64
            }, timeout=15)
            
            if res.status_code == 200:
                return res.json()["data"]["url"]  # Return the new permanent URL
    except Exception as e:
        print(f"⚠️ Re-hosting failed, using original URL. Error: {e}")
    
    return image_url


# ─── 🤖 AI REWRITE LOGIC ─────────────────────────────────────────────────────
def rewrite_article_with_ai(raw_text):
    prompt = f"""
    You are a professional journalist for Jungle News, writing in the authoritative style of top Ghanaian news outlets like JoyNews, Citi News, or Yen.com.gh.
    Rewrite the source material into a FULL, ORIGINAL, high-quality news article.

    ⚠️ LENGTH REQUIREMENT: The 'content' field MUST be at least 600 words. Expand with real analysis and background context.

    CONTENT QUALITY RULES:
    - Write objectively like a hard-news reporter. Do NOT ask the reader rhetorical questions.
    - If the story is international (e.g., US tech, global finance), just report the facts objectively. DO NOT force a fake connection to Ghana or campus life if none exists in the source.
    - If the story is actually about Ghana or Africa, provide the relevant local context.
    - Never copy sentences directly from the source. 
    - Add BACKGROUND: 1-2 paragraphs of relevant history about the topic.
    - Use VARIED sentence lengths. Keep it professional.

    REQUIRED HTML STRUCTURE for 'content':
    1. Open with a <ul> containing 3-4 key highlight bullet points.
    2. Write the intro in 2 <p> tags.
    3. Use at least 3 <h2> subheadings.
    4. Each section should have 2-3 full <p> paragraphs underneath it.
    5. End with an objective <h2> section (e.g., "Looking Ahead" or "Market Impact").

    OTHER FIELDS:
    - HEADLINE: Catchy, specific, and credible. No clickbait.
    - EXCERPT: A compelling 1-sentence summary under 240 characters.
    - IMAGE: ALWAYS set 'image_keywords' to "USE_ORIGINAL" to use the real news photo. Only provide generic 1-2 word search keywords if the story has absolutely no specific people/events.
    - VISIBILITY: Choose EXACTLY ONE word: "normal", "breaking", "trending", or "featured".

    Return EXACTLY a JSON object:
    {{"title": "...", "content": "...", "excerpt": "...", "image_keywords": "...", "visibility_tag": "..."}}

    Source Material:
    {raw_text}
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant", 
            response_format={"type": "json_object"}, 
            temperature=0.7,
            max_tokens=3500 
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
        if any(re.search(r'\b' + re.escape(kw) + r'\b', title) for kw in CATEGORY_KEYWORDS.get(cat, [])):
            score += 50
            break
    if any(re.search(r'\b' + re.escape(kw) + r'\b', title) for kw in CATEGORY_KEYWORDS['campusinsider']):
        score += 30
    return score


# ─── 🚀 MAIN BOT LOGIC ───────────────────────────────────────────────────────
def run_bot():
    print("=========================================")
    print("🚀 BOT IS AWAKE: Starting Virtual Newsroom (Powered by Groq)")
    print("=========================================")

    if not AUTHOR_KEYS.get("superadmin"):
        print("🛑 CRITICAL: JUNGLE_BOT_KEY is missing.")
        return

    posted_urls = get_posted_urls()
    tracker = get_daily_tracker()
    missing_categories = [c for c in REQUIRED_CATEGORIES if c not in tracker['posted_categories']]
    print(f"🎯 Target Categories for today: {missing_categories}")

    all_entries = []
    print("📡 Scanning RSS Feeds...")
    for target in GHANA_RSS_FEEDS:
        try:
            feed = feedparser.parse(target)
            for e in feed.entries[:3]:
                if e.link not in posted_urls:
                    all_entries.append(e)
        except:
            pass

    if not all_entries:
        print("💤 No fresh news found. Going back to sleep.")
        return

    all_entries.sort(key=lambda x: score_entry_for_hunting(x, missing_categories), reverse=True)

    posted_count = 0
    failed_attempts = 0
    user_config = Config()
    user_config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'

    for entry in all_entries:
        if posted_count >= 1:
            print("✅ Drip-feed quota reached (1 post). Shutting down.")
            break

        print(f"\n🗞️  Attempting to process: {entry.title[:60]}...")

        scr = NewsScraper(entry.link, config=user_config)
        try:
            scr.download()
            scr.parse()
        except:
            print("⚠️  Failed to scrape article text. Skipping.")
            continue

        if not scr.text or len(scr.text) < 400:
            print("⚠️  Article text too short. Skipping.")
            continue
        
        safe_text = scr.text[:4000]
        title_lower = entry.title.lower()

        # 🧠 INTELLIGENT PYTHON CATEGORY SCORING
        def get_best_category(title, content):
            scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
            title_lower = title.lower()
            content_lower = content.lower()
            
            for cat, kw_list in CATEGORY_KEYWORDS.items():
                for kw in kw_list:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    # 3 points for a title match
                    if re.search(pattern, title_lower):
                        scores[cat] += 3
                    # 1 point for each occurrence in the body content
                    scores[cat] += len(re.findall(pattern, content_lower))
                    
            best_cat = "news" # Default fallback
            max_score = 0
            for cat, score in scores.items():
                if score > max_score:
                    max_score = score
                    best_cat = cat
            return best_cat, scores

        forced_cat, cat_scores = get_best_category(entry.title, safe_text)
        print(f"🧠 Category Scores: {cat_scores}")
        print(f"🧠 Sending to Groq AI (Locked Category: {forced_cat})...")
        # Notice we don't pass forced_cat to the AI anymore!
        data = rewrite_article_with_ai(safe_text)

        if not data:
            print("❌ AI Failed to return valid JSON.")
            continue

        # 🚦 ROBUST IMAGE HANDLING
        original_img = scr.top_image if isinstance(scr.top_image, str) and scr.top_image else ""
        img_keywords = str(data.get("image_keywords", "USE_ORIGINAL")).strip()
        
        # Prefer the original scraped image as it's the most accurate representation of the news.
        # Only fallback to Pexels if the original image is missing.
        if original_img:
            print("🛡️ Re-hosting original image to prevent broken links...")
            final_img = rehost_image(original_img)
        else:
            final_img = find_clean_image(img_keywords) if img_keywords.upper() != "USE_ORIGINAL" else ""

        # 🚦 FUZZY VISIBILITY HANDLING
        vis_tag = str(data.get("visibility_tag", "normal")).lower()
        is_breaking = "breaking" in vis_tag
        is_trending = "trending" in vis_tag
        is_featured = "featured" in vis_tag

        # 🚦 STRICT PAYLOAD (Category is hardcoded by Python)
        payload = {
            "title":         data.get("title"),
            "content":       data.get("content"),
            "excerpt":       data.get("excerpt", "")[:280],
            "cover_image":   final_img,
            "category_slug": forced_cat,  # <--- ABSOLUTE DICTATOR
            "is_breaking":   is_breaking,
            "is_trending":   is_trending,
            "is_featured":   is_featured
        }

        # 🎭 ROUTE TO CORRECT WRITER KEY 
        current_key = get_writer_key(forced_cat)
        if not current_key:
            print(f"❌ CRITICAL: No API key available for '{forced_cat}'.")
            continue

        # Determine tag for terminal print
        print_tag = "normal"
        if is_breaking: print_tag = "breaking"
        elif is_trending: print_tag = "trending"
        elif is_featured: print_tag = "featured"

        print(f"🌐 Posting to Jungle News Backend (Category: {forced_cat}, Visibility: {print_tag})...")
        res = requests.post(
            RENDER_API_URL,
            headers={"X-API-Key": current_key, "Content-Type": "application/json"},
            json=payload
        )

        if res.status_code == 201:
            print(f"🎉 SUCCESS! Published: '{data.get('title')}'")
            posted_count += 1
            save_posted_url(entry.link)

            if forced_cat not in tracker['posted_categories']:
                tracker['posted_categories'].append(forced_cat)
                save_daily_tracker(tracker)
        else:
            print(f"❌ SERVER ERROR {res.status_code}: {res.text}")
            failed_attempts += 1
            if failed_attempts >= 3:
                print("🛑 Too many server rejections. Shutting down.")
                break


if __name__ == "__main__":
    run_bot()