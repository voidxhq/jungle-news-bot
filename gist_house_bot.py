import requests
import feedparser
from newspaper import Article as NewsScraper, Config
from groq import Groq
import json
import os
import base64
import random
import time
from datetime import datetime
import re  # Added for strict whole-word keyword matching
import cloudinary
import cloudinary.uploader
import socket

# Set global default timeout for socket operations to prevent hanging on network calls
socket.setdefaulttimeout(30)

# ==========================================
# ⚙️ CLOUD CONFIGURATION & GLOBALS
# ==========================================
RENDER_API_URL = "https://www.thegisthouse.com/api/bot/post-article"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# 🎭 THE VIRTUAL NEWSROOM KEYS
AUTHOR_KEYS = {
    "nana": os.environ.get("KEY_NANA_AMA"),  # entertainment, campuspulse
    "emmanuel": os.environ.get("KEY_EMMANUEL"),  # tech
    "samuel": os.environ.get("KEY_SAMUEL"),  # news, ghana
    "desmond": os.environ.get("KEY_DESMOND"),  # sports
    "superadmin": os.environ.get("JUNGLE_BOT_KEY"),  # Prince Eshun — randomly assigned
}

# 🎲 SUPER ADMIN RANDOM CHANCE (0.0 - 1.0)
SUPER_ADMIN_CHANCE = 0.25
DAILY_POST_LIMIT = 9  # Set the daily article limit (between 8-10 as requested)

TRACKER_FILE = "daily_tracker.json"
POSTED_URLS_FILE = "posted_urls.txt"
REQUIRED_CATEGORIES = [
    "news",
    "sports",
    "entertainment",
    "campuspulse",
    "tech",
    "ghana",
]

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
    "https://fifty7tech.com/feed",
]

CATEGORY_KEYWORDS = {
    "sports": [
        "football",
        "match",
        "coach",
        "black stars",
        "league",
        "goals",
        "stadium",
        "afcon",
        "premier league",
        "champions league",
        "fifa",
        "referee",
        "transfer",
        "injury",
        "kickoff",
        "midfielder",
        "striker",
        "defender",
        "goalkeeper",
        "sports ministry",
        "gfa",
        "ghana fa",
        "friendly match",
        "qualifier",
        "world cup",
        "chelsea",
        "arsenal",
        "manchester",
        "real madrid",
        "barcelona",
    ],
    "entertainment": [
        "shatta",
        "stonebwoy",
        "sarkodie",
        "music",
        "movie",
        "concert",
        "album",
        "artist",
        "afrobeats",
        "dancehall",
        "rapper",
        "actor",
        "actress",
        "celebrity",
        "showbiz",
        "performance",
        "event",
        "tour",
        "festival",
        "release",
        "single",
        "video",
        "entertainment news",
    ],
    "campuspulse": [
        "ucc",
        "knust",
        "legon",
        "university of ghana",
        "uew",
        "umat",
        "upsa",
        "gimpa",
        "ttu",
        "uds",
        "student",
        "campus",
        "src",
        "nugs",
        "jcr",
        "src executives",
        "src president",
        "nugs president",
        "hall president",
        "src election",
        "src manifesto",
        "campus campaign",
        "handover",
        "lecture",
        "lecturers",
        "midsem",
        "end of semester",
        "graduation",
        "matriculation",
        "orientation",
        "dean of students",
        "vice chancellor",
        "academic calendar",
        "resit",
        "supplementary exams",
        "deferred course",
        "credit hour",
        "cgpa",
        "gpa",
        "level 100",
        "level 200",
        "level 300",
        "level 400",
        "freshers",
        "hostel",
        "traditional hall",
        "casford",
        "mensah sarbah",
        "commonwealth hall",
        "room allocation",
        "campus accommodation",
        "hall master",
        "hall mistress",
        "porter",
        "hall week",
        "artists night",
        "artiste night",
        "jama night",
        "hall dinner",
        "awards night",
        "freshers night",
        "welcome bash",
        "campus rave",
        "campus concert",
        "hall week celebration",
        "campus vibes",
        "boys boys",
        "slay queen",
        "academic stress",
        "lecturer wahala",
        "lecture hall",
        "library",
        "science market",
        "campus wifi",
        "eduroam",
        "campus water shortage",
        "campus power outage",
        "dumsor on campus",
        "campus fellowship",
        "campus ministry",
        "scripture union",
        "pensa",
        "campus police",
        "campus security",
        "student robbed",
        "campus theft",
        "hostel robbery",
        "trending on campus",
        "viral on campus",
        "campus drama",
        "student protest",
        "campus demonstration",
    ],
    "tech": [
        "ai",
        "chatgpt",
        "openai",
        "app",
        "iphone",
        "android",
        "laptop",
        "startup",
        "coding",
        "developer",
        "crypto",
        "fintech",
        "blockchain",
        "software",
        "hardware",
        "programming",
        "python",
        "javascript",
        "web app",
        "mobile app",
        "saas",
        "cloud",
        "cybersecurity",
        "data",
        "machine learning",
    ],
    "ghana": [
        "mahama",
        "bawumia",
        "npp",
        "ndc",
        "accra",
        "kumasi",
        "ghanaian",
        "cedi",
        "parliament",
        "ghana police",
        "ecg",
        "gridco",
        "ec",
        "election",
        "president",
        "vice president",
        "minister",
        "mp",
        "district",
        "assembly",
        "governor",
        "policy",
        "inflation",
        "economy",
        "fuel price",
        "bill",
        "strike",
        "protest",
    ],
    "news": [
        "police",
        "court",
        "killed",
        "accident",
        "hospital",
        "government",
        "minister",
        "arrest",
        "investigation",
        "fire outbreak",
        "robbery",
        "breaking",
        "update",
        "incident",
        "crime",
        "victim",
        "security",
        "press release",
        "statement",
        "case",
        "hearing",
        "judgment",
        "law",
        "bill",
        "viral",
        "trending",
    ],
}

feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)


# ─── 🎭 WRITER ROUTING LOGIC ──────────────────────────────────────────────────
def get_writer_key(category_slug):
    # Rotate admins randomly so it looks like a real human newsroom
    available_authors = [
        AUTHOR_KEYS.get("nana"),
        AUTHOR_KEYS.get("emmanuel"),
        AUTHOR_KEYS.get("samuel"),
        AUTHOR_KEYS.get("desmond"),
        AUTHOR_KEYS.get("superadmin")
    ]
    valid_authors = [author for author in available_authors if author]
    
    if valid_authors:
        print("🎭 Randomly rotating admin to post this article...")
        return random.choice(valid_authors)

    print("❌ CRITICAL: No valid author keys found.")
    return None


# ─── 🧠 MEMORY & TRACKING ──────────────────────────────────────────────────────
def get_posted_urls():
    if os.path.exists(POSTED_URLS_FILE):
        with open(POSTED_URLS_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()


def save_posted_url(url):
    with open(POSTED_URLS_FILE, "a") as f:
        f.write(url + "\n")


def get_daily_tracker():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r") as f:
                data = json.load(f)
                if data.get("date") == today:
                    # Ensure post_count exists for older tracker files
                    if "post_count" not in data:
                        data["post_count"] = len(data.get("posted_categories", []))
                    return data
        except:
            pass # If file doesn't exist, is corrupt, or is for a previous day, reset it.
    return {"date": today, "posted_categories": [], "post_count": 0}


def save_daily_tracker(data):
    with open(TRACKER_FILE, "w") as f:
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
            if data.get("photos"):
                return data["photos"][0]["src"]["large2x"]
    except Exception as e:
        print(f"⚠️ Pexels Image Error: {e}")
    return None


# ─── 🛡️ IMAGE RE-HOSTING LOGIC ────────────────────────────────────────────────
def rehost_image(image_url):
    """Re-hosts a scraped image directly onto your Cloudinary account."""
    if not image_url:
        return image_url

    try:
        # Uploads directly from the external URL to your Cloudinary thegisthouse folder
        upload_result = cloudinary.uploader.upload(image_url, folder="thegisthouse/articles")
        return upload_result['secure_url']
    except Exception as e:
        print(f"⚠️ Cloudinary upload failed, using original URL. Error: {e}")
        return image_url


# ─── 🤖 AI REWRITE LOGIC ─────────────────────────────────────────────────────
def rewrite_article_with_ai(raw_text):
    prompt = f"""
    You are a professional journalist for The Gist House, writing in the authoritative style of top Ghanaian news outlets like JoyNews, Citi News, or Yen.com.gh.
    Rewrite the source material into a FULL, ORIGINAL, high-quality news article.

        ⚠️ GOOGLE ADSENSE "HIGH VALUE" REQUIREMENT: Do NOT generate fluff, repetitive text, or filler. Your goal is to create a deeply engaging, unique article that provides immense value to the reader. Ensure the content is brand-safe, objective, and strictly complies with AdSense policies.

    CONTENT QUALITY RULES:
    - Write objectively like a hard-news reporter. Do NOT ask the reader rhetorical questions.
        - DO NOT pad the article to reach a specific word count. If the source material is brief, add value by providing deep historical background, market implications, or broader context related to the topic.
    - If the story is international (e.g., US tech, global finance), just report the facts objectively. DO NOT force a fake connection to Ghana or campus life if none exists in the source.
    - If the story is actually about Ghana or Africa, provide the relevant local context.
    - Never copy sentences directly from the source to ensure originality. 
        - Add a dedicated "Background & Context" section to provide rich educational value.
        - Add a "Why This Matters" or "Broader Implications" section to give the reader analytical insights they wouldn't get from a standard news site.
    - Use VARIED sentence lengths. Keep it professional.

    REQUIRED HTML STRUCTURE for 'content':
        1. Open with a <h2> Key Takeaways </h2> followed by a <ul> containing 3-4 factual bullet points.
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
            max_tokens=2000,
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
        if any(
            re.search(r"\b" + re.escape(kw) + r"\b", title)
            for kw in CATEGORY_KEYWORDS.get(cat, [])
        ):
            score += 50
            break
    if any(
        re.search(r"\b" + re.escape(kw) + r"\b", title)
        for kw in CATEGORY_KEYWORDS["campuspulse"]
    ):
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
    post_count = tracker.get("post_count", 0)

    # Check if the daily post limit has been reached
    if post_count >= DAILY_POST_LIMIT:
        print(
            f"🛑 Daily post limit of {DAILY_POST_LIMIT} reached for {tracker['date']}. Going back to sleep."
        )
        return

    # 🎲 RANDOM HUMAN-LIKE POSTING LOGIC
    current_hour = datetime.utcnow().hour
    hours_left = 24 - current_hour
    posts_left = DAILY_POST_LIMIT - post_count

    # Dynamically calculate chance to post so we naturally hit the target by the end of the day
    run_probability = posts_left / hours_left if hours_left > 0 else 1.0
    run_probability = min(1.0, max(0.1, run_probability)) # Keep probability between 10% and 100%

    print(f"🎲 Random posting chance this hour: {run_probability * 100:.1f}% ({posts_left} posts left, {hours_left} hours left in day)")

    if random.random() > run_probability:
        print("💤 Bot decided to take a random nap this hour to look more human. Skipping!")
        return

    # Sleep for a random number of seconds (between 1 and 45 minutes) so the timestamp isn't exactly XX:00
    # If running in GitHub Actions, use a very short sleep (5 to 30 seconds) to avoid wasting billing minutes
    if os.environ.get("GITHUB_ACTIONS") == "true":
        sleep_time = random.randint(5, 30)
        print(f"⏳ Running in GitHub Actions. Short sleep of {sleep_time} seconds to prevent exact alignment...")
    else:
        sleep_time = random.randint(60, 2700)
        print(f"⏳ Sleeping for {sleep_time} seconds to randomize the exact posting minute...")
    time.sleep(sleep_time)

    missing_categories = [
        c for c in REQUIRED_CATEGORIES if c not in tracker["posted_categories"]
    ]
    print(f"🎯 Target Categories for today: {missing_categories}")

    all_entries = []
    print("📡 Scanning RSS Feeds...")
    for target in GHANA_RSS_FEEDS:
        try:
            feed = feedparser.parse(target)
            for e in feed.entries[:15]:
                if e.link not in posted_urls:
                    all_entries.append(e)
        except:
            pass

    if not all_entries:
        print("💤 No fresh news found. Going back to sleep.")
        return

    all_entries.sort(
        key=lambda x: score_entry_for_hunting(x, missing_categories), reverse=True
    )

    posted_count = 0
    failed_attempts = 0
    user_config = Config()
    user_config.browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    )
    user_config.request_timeout = 15  # Set a request timeout to prevent scraping from hanging

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

        if not scr.text or len(scr.text) < 1200:
            print("⚠️  Article text too short. Skipping.")
            continue

        safe_text = scr.text[:10000]
        title_lower = entry.title.lower()

        # 🧠 INTELLIGENT PYTHON CATEGORY SCORING
        def get_best_category(title, content):
            scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
            title_lower = title.lower()
            content_lower = content.lower()

            for cat, kw_list in CATEGORY_KEYWORDS.items():
                for kw in kw_list:
                    pattern = r"\b" + re.escape(kw) + r"\b"
                    # 3 points for a title match
                    if re.search(pattern, title_lower):
                        scores[cat] += 3
                    # 1 point for each occurrence in the body content
                    scores[cat] += len(re.findall(pattern, content_lower))

            best_cat = "news"  # Default fallback
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

        # 🚦 VALIDATE AI OUTPUT TO PREVENT EMPTY POSTS
        ai_content = str(data.get("content") or "").strip()
        ai_excerpt = str(data.get("excerpt") or "").strip()
        ai_title = str(data.get("title") or "").strip()

        if len(ai_content) < 100 or len(ai_excerpt) < 10 or not ai_title:
            print("❌ AI returned incomplete data (missing content, excerpt, or title). Skipping.")
            continue

        # 🚦 ROBUST IMAGE HANDLING
        original_img = (
            scr.top_image if isinstance(scr.top_image, str) and scr.top_image else ""
        )
        img_keywords = str(data.get("image_keywords", "USE_ORIGINAL")).strip()

        image_source_text = ""

        # Prefer the original scraped image as it's the most accurate representation of the news.
        # Only fallback to Pexels if the original image is missing.
        if original_img:
            print("🛡️ Re-hosting original image to prevent broken links...")
            final_img = rehost_image(original_img)
            image_source_text = original_img
        else:
            final_img = (
                find_clean_image(img_keywords)
                if img_keywords.upper() != "USE_ORIGINAL"
                else ""
            )
            if final_img:
                image_source_text = "Pexels"

        # Append image source to the generated content
        final_content = ai_content
        if image_source_text:
            if image_source_text.startswith("http"):
                final_content += f'\n<p><em>Image Source: <a href="{image_source_text}" target="_blank">{image_source_text}</a></em></p>'
            else:
                final_content += f"\n<p><em>Image Source: {image_source_text}</em></p>"

        # 🚦 FUZZY VISIBILITY HANDLING
        vis_tag = str(data.get("visibility_tag") or "normal").lower()
        is_breaking = "breaking" in vis_tag
        is_trending = "trending" in vis_tag
        is_featured = "featured" in vis_tag

        # 🚦 STRICT PAYLOAD (Category is hardcoded by Python)
        payload = {
            "title": ai_title,
            "content": final_content,
            "excerpt": ai_excerpt[:280],
            "cover_image": final_img,
            "category_slug": forced_cat,  # <--- ABSOLUTE DICTATOR
            "is_breaking": is_breaking,
            "is_trending": is_trending,
            "is_featured": is_featured,
        }

        # 🎭 ROUTE TO CORRECT WRITER KEY
        current_key = get_writer_key(forced_cat)
        if not current_key:
            print(f"❌ CRITICAL: No API key available for '{forced_cat}'.")
            continue

        # Determine tag for terminal print
        print_tag = "normal"
        if is_breaking:
            print_tag = "breaking"
        elif is_trending:
            print_tag = "trending"
        elif is_featured:
            print_tag = "featured"

        print(
            f"🌐 Posting to The Gist House Backend (Category: {forced_cat}, Visibility: {print_tag})..."
        )
        res = requests.post(
            RENDER_API_URL,
            headers={"X-API-Key": current_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,  # Set timeout to prevent hanging if Render API is sleeping or unresponsive
        )

        if res.status_code == 201:
            print(f"🎉 SUCCESS! Published: '{data.get('title')}'")
            posted_count += 1
            save_posted_url(entry.link)

            # Update the daily tracker
            tracker["post_count"] = tracker.get("post_count", 0) + 1
            if forced_cat not in tracker["posted_categories"]:
                tracker["posted_categories"].append(forced_cat)
            save_daily_tracker(tracker)
        else:
            print(f"❌ SERVER ERROR {res.status_code}: {res.text}")
            failed_attempts += 1
            if failed_attempts >= 3:
                print("🛑 Too many server rejections. Shutting down.")
                break


if __name__ == "__main__":
    run_bot()
