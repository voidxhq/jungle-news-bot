import requests
import feedparser
from newspaper import Article as NewsScraper, Config
from groq import Groq
import json
import os
import random
from datetime import datetime
import re  # Added for strict whole-word keyword matching

# ==========================================
# ⚙️ CLOUD CONFIGURATION & GLOBALS
# ==========================================
# Added www. to prevent silent redirects dropping the API keys
RENDER_API_URL = "https://www.junglenews.online/api/bot/post-article"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

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
    'sports': [
        # Ghana football
        'black stars', 'gfa', 'ghana fa', 'afcon', 'ghana premier league',
        'hearts of oak', 'asante kotoko', 'accra lions', 'dreams fc',
        # General football
        'football', 'soccer', 'match', 'league', 'goal', 'goals', 'coach',
        'stadium', 'referee', 'transfer', 'kickoff', 'midfielder', 'striker',
        'defender', 'goalkeeper', 'friendly match', 'qualifier', 'world cup',
        'champions league', 'premier league', 'la liga', 'serie a', 'bundesliga',
        'europa league', 'fifa', 'uefa', 'cap', 'hat trick', 'penalty',
        # Clubs
        'chelsea', 'arsenal', 'manchester united', 'manchester city', 'liverpool',
        'real madrid', 'barcelona', 'atletico', 'psg', 'bayern',
        # Other sports
        'athletics', 'basketball', 'boxing', 'tennis', 'cricket', 'rugby',
        'olympics', 'commonwealth games', 'sports ministry', 'nsa',
        'sprinter', 'marathon', 'swimmer', 'cyclist', 'medal', 'trophy',
        'tournament', 'championship', 'sports news',
    ],

    'entertainment': [
        # Ghanaian artists
        'shatta wale', 'stonebwoy', 'sarkodie', 'medikal', 'efya', 'wendy shay',
        'kuami eugene', 'kidi', 'king promise', 'gyakie', 'amaarae', 'black sherif',
        'olamide', 'burna boy', 'wizkid', 'davido', 'tems', 'ayra starr',
        # Music
        'music', 'album', 'single', 'song', 'track', 'EP', 'mixtape',
        'afrobeats', 'afropop', 'dancehall', 'hiplife', 'highlife', 'drill',
        'rap', 'rapper', 'singer', 'artist', 'producer', 'beat', 'lyrics',
        'music video', 'bpm', 'vgma', 'grammy', 'bet awards', 'headies',
        # Film & TV
        'movie', 'film', 'series', 'nollywood', 'ghallywood', 'netflix',
        'showmax', 'amazon prime', 'actor', 'actress', 'director', 'premiere',
        'box office', 'trailer', 'tv show', 'reality show',
        # General entertainment
        'concert', 'show', 'performance', 'tour', 'festival', 'event',
        'celebrity', 'showbiz', 'comedian', 'comedy', 'skit', 'influencer',
        'tiktok', 'viral video', 'social media star', 'entertainment news',
        'red carpet', 'fashion', 'style', 'award', 'nomination',
    ],

    'campusinsider': [
        # Universities — Ghana
        'ucc', 'knust', 'legon', 'university of ghana', 'uew', 'umat',
        'upsa', 'gimpa', 'ttu', 'takoradi technical', 'ho technical',
        'accra technical', 'central university', 'ashesi', 'regent university',
        'valley view university', 'kaaf university', 'presbyterian university',
        'wisconsin university', 'uhas', 'uds', 'university for development',
        # Student governance
        'student', 'students', 'campus', 'src', 'nugs', 'jcr',
        'src president', 'nugs president', 'hall president', 'src election',
        'src manifesto', 'campus campaign', 'handover', 'src executives',
        # Academics
        'lecture', 'lecturer', 'midsem', 'end of semester', 'graduation',
        'matriculation', 'orientation', 'dean of students', 'vice chancellor',
        'academic calendar', 'resit', 'supplementary exams', 'cgpa', 'gpa',
        'level 100', 'level 200', 'level 300', 'level 400', 'freshers',
        'national service', 'nyep', 'national youth', 'wassce', 'bece', 'waec',
        'credit hour', 'deferred course', 'academic stress', 'ghana education',
        'nsmq', 'national science and maths quiz',
        # Hostels & halls
        'hostel', 'traditional hall', 'casford', 'mensah sarbah',
        'commonwealth hall', 'room allocation', 'campus accommodation',
        'hall master', 'hall mistress', 'porter',
        # Events
        'hall week', 'artiste night', 'artists night', 'jama night',
        'hall dinner', 'freshers night', 'welcome bash', 'campus rave',
        'campus concert', 'hall week celebration', 'awards night',
        # Campus life
        'campus vibes', 'academic stress', 'lecturer wahala',
        'campus wifi', 'eduroam', 'campus water', 'campus power',
        'campus fellowship', 'campus ministry', 'scripture union', 'pensa',
        'campus police', 'campus security', 'campus theft', 'hostel robbery',
        'campus drama', 'student protest', 'campus demonstration',
    ],

    'tech': [
        # AI & ML — specific terms only (NOT bare 'ai')
        'artificial intelligence', 'machine learning', 'deep learning',
        'chatgpt', 'openai', 'gemini', 'claude ai', 'llama', 'grok ai',
        'generative ai', 'large language model', 'llm', 'neural network',
        # Devices & hardware
        'iphone', 'ipad', 'macbook', 'android', 'samsung galaxy', 'pixel phone',
        'laptop', 'smartwatch', 'smart glasses', 'wearable', 'gadget',
        'headset', 'earbuds', 'airpods', 'tablet', 'smart tv', 'drone',
        # Companies (tech context)
        'google', 'apple', 'microsoft', 'meta', 'amazon', 'tesla',
        'nvidia', 'qualcomm', 'intel', 'openai', 'anthropic', 'samsung',
        'huawei', 'xiaomi', 'zipline', 'flutterwave', 'paystack', 'hubtel',
        'zeepay', 'mtn momo', 'mobile money', 'momo',
        # Software & development
        'software', 'hardware', 'app', 'application', 'coding', 'developer',
        'programming', 'python', 'javascript', 'web app', 'mobile app',
        'saas', 'cloud computing', 'cybersecurity', 'data breach', 'hacking',
        'startup', 'tech startup', 'fintech', 'edtech', 'healthtech',
        # Crypto & web3
        'crypto', 'bitcoin', 'ethereum', 'blockchain', 'nft', 'web3',
        # Ghana tech scene
        'silicon accra', 'ghana tech', 'accra tech', 'data bundle',
        'mtn ghana', 'vodafone ghana', 'airteltigo', 'e-levy', 'digitization',
        'tech news', 'technology',
    ],

    'ghana': [
        # Politics & government
        'mahama', 'bawumia', 'akufo-addo', 'npp', 'ndc', 'parliament',
        'mp', 'minister', 'vice president', 'president of ghana',
        'electoral commission', 'election commission', 'ec ghana',
        'supreme court ghana', 'high court ghana', 'attorney general',
        'ghana government', 'government of ghana',
        # Economy
        'cedi', 'ghana cedi', 'bank of ghana', 'bog', 'inflation ghana',
        'economy ghana', 'fuel price ghana', 'petroleum', 'cocoa ghana',
        'gold ghana', 'galamsey', 'ghana revenue', 'gra', 'imo',
        'imf ghana', 'world bank ghana', 'economic crisis', 'budget ghana',
        # Places & identity
        'accra', 'kumasi', 'tamale', 'takoradi', 'cape coast', 'sunyani',
        'ghanaian', 'ghana', 'greater accra', 'ashanti region', 'northern region',
        # Utilities & infrastructure
        'ecg', 'gridco', 'dumsor', 'load shedding', 'ghana water',
        'gwcl', 'ghana roads', 'highway ghana',
        # Culture & institutions
        'chieftaincy', 'paramount chief', 'nana', 'ghana police service',
        'ghana army', 'ghana navy', 'ghana immigration', 'ghana health service',
        'ges', 'ghana education service', 'nahco', 'kia airport',
        # Daily life
        'trotro', 'okada', 'ghana news', 'ghana today',
    ],

    'news': [
        # Crime & safety
        'killed', 'dead', 'murder', 'shooting', 'stabbing', 'robbery',
        'armed robbery', 'kidnapping', 'kidnapped', 'missing person',
        'accident', 'crash', 'fire outbreak', 'explosion', 'flood',
        'disaster', 'emergency', 'rescue', 'victim', 'crime', 'suspect',
        # Legal
        'court', 'arrested', 'charged', 'sentenced', 'bail', 'hearing',
        'judgment', 'verdict', 'lawsuit', 'prosecution', 'acquitted',
        'detained', 'remanded', 'investigation', 'case',
        # Health
        'hospital', 'disease', 'outbreak', 'health alert', 'epidemic',
        'pandemic', 'vaccine', 'doctor', 'patient', 'medical',
        # General news
        'press release', 'statement', 'announcement', 'breaking news',
        'developing story', 'update', 'confirmed', 'official',
    ],
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
    if not keyword or keyword == "USE_ORIGINAL":
        return None
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={keyword} Ghana&per_page=1"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'):
                return data['photos'][0]['src']['large2x']
    except Exception as e:
        print(f"⚠️ Pexels Image Error: {e}")
    return None


# ─── 🤖 AI REWRITE LOGIC ─────────────────────────────────────────────────────
def rewrite_article_with_ai(raw_text, forced_category):
    cat_logic = f"Set 'category_slug' to EXACTLY '{forced_category}'."

    prompt = f"""
    You are a senior journalist at Jungle News, Ghana's leading digital news platform covering campus life, entertainment, sports, tech, and national news.
    Your job is to transform the source material into a COMPLETE, ORIGINAL, deeply reported news article that passes Google AdSense's quality review.

    ⚠️ STRICT LENGTH REQUIREMENT: The 'content' field MUST contain at least 900 words of readable text (not counting HTML tags).
    This is non-negotiable. Count your words. If you are under 900 words, keep writing — add expert context, historical background, reader impact analysis, local relevance, and a forward-looking section.

    ══════════════════════════════════════════
    GOOGLE ADSENSE QUALITY STANDARDS (FOLLOW ALL):
    ══════════════════════════════════════════

    1. ORIGINALITY — Do NOT copy any sentence from the source. Every sentence must be written fresh in your own words. Restate facts, never reproduce them verbatim.

    2. DEPTH & VALUE — A reader who visits this article must learn MORE than the headline. Include:
       - Background: 2 paragraphs of history or context that explains the story's roots.
       - Impact: Who is affected and how? Be specific (students, traders, fans, government, etc.)
       - Expert angle: Introduce what analysts, officials, or community voices would say — paraphrased from the source or logically inferred from context.
       - Local relevance: Always tie the story back to Ghana, Ghanaian youth, or campus life where possible.

    3. STRUCTURE — Articles must be well-organised and easy to read. Use proper HTML:
       - Open with a <ul> of 4 key highlights (what happened, who is involved, why it matters, what comes next).
       - Follow with 2 engaging <p> intro paragraphs — hook the reader with the most compelling angle.
       - Use at least 4 <h2> subheadings to divide the article into clear, logical sections.
       - Write 2 to 4 full <p> paragraphs under EACH <h2> section. Each paragraph must be 3 to 5 sentences long.
       - Include a dedicated <h2> section titled "What This Means for Ghanaians" or "The Bigger Picture" with your editorial analysis.
       - End with a <h2> titled "What to Watch Next" or "Looking Ahead" describing what will happen next and why readers should follow the story.
       - Close with a confident <p> conclusion that summarises the story's importance.

    4. TONE & VOICE — Write like a real journalist, not a robot:
       - Use varied sentence lengths. Short punchy sentences. Then longer, more explanatory ones that build on what came before.
       - Be authoritative but approachable. This is news for young, educated Ghanaians.
       - No robotic repetition. Never start two consecutive paragraphs the same way.
       - No keyword stuffing. Write naturally as a human would.

    5. ACCURACY & CREDIBILITY — Stick to facts from the source material. Do not invent quotes or statistics. You may frame and expand upon facts, but never fabricate them.

    ══════════════════════════════════════════
    OTHER FIELDS:
    ══════════════════════════════════════════
    - HEADLINE (title): Specific, credible, and compelling. Must tell the reader exactly what happened. No vague clickbait. BAD: "Shocking News in Ghana". GOOD: "KNUST Students Protest Fee Hike as VC Promises Urgent Review".
    - EXCERPT: A single punchy sentence under 240 characters that summarises the full story and makes someone want to read it.
    - IMAGE: Set 'image_keywords' to "USE_ORIGINAL" if the story is about a specific named Ghanaian person or event with a real photo. Otherwise provide 2 to 3 descriptive generic search keywords (e.g. "university students Ghana campus").
    - CATEGORY: {cat_logic}
    - VISIBILITY (STRICT RULES): Choose EXACTLY ONE:
        "normal" for 85% of all articles (standard news, features, updates).
        "breaking" ONLY for urgent emergencies or major breaking news happening right now.
        "trending" ONLY for stories already viral on social media.
        "featured" ONLY for exclusive investigations or in-depth special reports.

    ══════════════════════════════════════════
    OUTPUT FORMAT:
    ══════════════════════════════════════════
    Return EXACTLY one JSON object. NO markdown. NO code fences. NO text before or after the JSON. Just the raw JSON:
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
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}, 
            temperature=0.7,
            max_tokens=5000  # Increased to support 900+ word AdSense-quality articles
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


# ─── 🚀 MAIN BOT LOGIC ───────────────────────────────────────────────────────
def run_bot():
    print("=========================================")
    print("🚀 BOT IS AWAKE: Starting Virtual Newsroom (Powered by Groq)")
    print("=========================================")

    # 🔑 Key audit
    print("🔑 Key audit:")
    for name, key in AUTHOR_KEYS.items():
        print(f"  {name}: {'✅ present' if key else '❌ MISSING'}")

    if not AUTHOR_KEYS.get("superadmin"):
        print("🛑 CRITICAL: JUNGLE_BOT_KEY (Prince Eshun / Super Admin) is missing. Check your GitHub Secrets.")
        return

    posted_urls = get_posted_urls()
    print(f"\n📁 Memory loaded: {len(posted_urls)} previously posted articles.")

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

    print(f"🔎 Found {len(all_entries)} fresh unposted articles across all feeds.")
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
            print("✅ Drip-feed quota reached (1 post). Shutting down until next cron cycle.")
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
            print("⚠️  Article text too short or blocked by paywall. Skipping.")
            continue
        
        safe_text = scr.text[:6000]  # Increased to give AI more source material for longer rewrites
        title_lower = entry.title.lower()

        # Helper function for strictly matching whole words via Regex
        def has_keyword(kw_list, text):
            for kw in kw_list:
                if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                    return True
            return False

        def count_keyword_hits(kw_list, text):
            """Count how many keywords from the list appear in the text."""
            return sum(
                1 for kw in kw_list
                if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)
            )

        # 🧠 SMART CATEGORY SCORING SYSTEM
        # Checks title (weighted 3x) + entry summary/description + article body
        # Picks the category with the most keyword hits — no more wrong defaults
        entry_summary = getattr(entry, 'summary', '') or ''
        combined_text = title_lower + ' ' + entry_summary.lower() + ' ' + safe_text.lower()

        DETECTION_CATEGORIES = ['tech', 'campusinsider', 'sports', 'entertainment', 'ghana', 'news']

        scores = {}
        for cat in DETECTION_CATEGORIES:
            kw_list = CATEGORY_KEYWORDS.get(cat, [])
            # Title matches are worth 3x — most reliable signal
            title_hits = count_keyword_hits(kw_list, title_lower) * 3
            # Body/summary hits add supporting evidence
            body_hits = count_keyword_hits(kw_list, combined_text)
            scores[cat] = title_hits + body_hits

        # Pick highest scoring category; fall back to 'news' only if all scores are 0
        best_cat = max(scores, key=scores.get)
        forced_cat = best_cat if scores[best_cat] > 0 else 'news'

        print(f"🧠 Category scores: { {k: v for k, v in sorted(scores.items(), key=lambda x: -x[1])} }")
        print(f"✅ Locked category: {forced_cat}")
        print(f"🤖 Sending to Groq AI for rewrite...")
        data = rewrite_article_with_ai(safe_text, forced_cat)

        if not data:
            print("❌ AI Failed to return valid JSON. Moving to next article.")
            continue

        # 🚦 PROCESS PAYLOAD
        img = (
            scr.top_image
            if data.get("image_keywords") == "USE_ORIGINAL"
            else (find_clean_image(data.get("image_keywords")) or scr.top_image)
        )
        vis_tag = data.get("visibility_tag", "normal").lower()
        cat_slug = data.get("category_slug", "news")

        payload = {
            "title":         data.get("title"),
            "content":       data.get("content"),
            "excerpt":       data.get("excerpt", "")[:280],
            "cover_image":   img,
            "category_slug": cat_slug,
            "is_breaking":   (vis_tag == "breaking"),
            "is_trending":   (vis_tag == "trending"),
            "is_featured":   (vis_tag == "featured")
        }

        # 🎭 ROUTE TO CORRECT WRITER KEY (with random super admin chance)
        current_key = get_writer_key(cat_slug)
        if not current_key:
            print(f"❌ CRITICAL: No API key available for '{cat_slug}'. Skipping.")
            continue

        print(f"🌐 Posting to Jungle News Backend (Category: {cat_slug}, Visibility: {vis_tag})...")
        res = requests.post(
            RENDER_API_URL,
            headers={"X-API-Key": current_key, "Content-Type": "application/json"},
            json=payload
        )

        if res.status_code == 201:
            print(f"🎉 SUCCESS! Published: '{data.get('title')}'")
            posted_count += 1
            save_posted_url(entry.link)

            if cat_slug not in tracker['posted_categories']:
                tracker['posted_categories'].append(cat_slug)
                save_daily_tracker(tracker)
        else:
            print(f"❌ SERVER ERROR {res.status_code}: {res.text}")
            failed_attempts += 1
            if failed_attempts >= 3:
                print("🛑 Too many server rejections. Shutting down to save Groq limits.")
                break


if __name__ == "__main__":
    run_bot()
