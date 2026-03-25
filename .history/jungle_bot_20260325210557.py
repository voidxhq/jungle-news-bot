import requests
import feedparser
from newspaper import Article as NewsScraper
import google.generativeai as genai
import json

# ==========================================
# ⚙️ BOT CONFIGURATION (FILL THESE IN!)
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = "YOUR_RENDER_BOT_API_KEY_HERE"  # The one you set in Render
GEMINI_API_KEY = "AIzaSyCE2zLpEmTtI5We3R6R2mAevuDsgGkW2KQ" # From Google AI Studio

# Which RSS feed are we pulling from today?
RSS_FEED_URL = "https://feeds.bbci.co.uk/news/world/africa/rss.xml" 

# Initialize the AI
genai.configure(api_key=GEMINI_API_KEY)
# We use the fast, free tier model
model = genai.GenerativeModel('gemini-1.5-flash') 

def rewrite_article_with_ai(raw_text):
    """Sends the raw scraped text to Gemini to be rewritten for AdSense."""
    prompt = f"""
    You are an expert journalist for 'Jungle News', a Ghanaian digital news platform for university students.
    Read the following facts/article and write a completely original, engaging, plagiarism-free news article.
    
    Rules:
    1. Do NOT copy sentences from the original. 
    2. Format the content in clean HTML (use <p> tags, and <h2> tags for subheadings).
    3. Write a catchy Title.
    4. Write a 2-sentence excerpt.
    5. Decide if this is 'breaking' news (true/false).
    6. Return ONLY a valid JSON object with these exact keys: "title", "content", "excerpt", "is_breaking".
    
    Original Text:
    {raw_text}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's pure JSON
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"❌ AI Rewrite failed: {e}")
        return None

def run_bot():
    print(f"📡 Scanning for news at {RSS_FEED_URL}...")
    feed = feedparser.parse(RSS_FEED_URL)
    
    # Process the top 2 latest articles
    for entry in feed.entries[:2]:
        print(f"\n📰 Found Story: {entry.title}")
        
        # 1. Scrape the original article and image
        scraper = NewsScraper(entry.link)
        try:
            scraper.download()
            scraper.parse()
        except:
            print("⚠️ Could not download article. Skipping.")
            continue
            
        raw_text = scraper.text
        cover_image = scraper.top_image # Grabs the original cover image!
        
        if not raw_text or len(raw_text) < 100:
            print("⚠️ Article too short to rewrite. Skipping.")
            continue
            
        # 2. Rewrite with AI
        print("🧠 Sending to AI for rewriting...")
        ai_data = rewrite_article_with_ai(raw_text)
        
        if not ai_data:
            continue
            
        # 3. Package for Jungle News
        payload = {
            "title": ai_data.get("title"),
            "content": ai_data.get("content"),
            "excerpt": ai_data.get("excerpt"),
            "cover_image": cover_image,
            "category_slug": "news", # You can change this or ask AI to guess it!
            "is_breaking": ai_data.get("is_breaking", False),
            "is_trending": False,
            "is_featured": False
        }
        
        # 4. Post to your live Render app
        print(f"🚀 Publishing '{payload['title']}' to Jungle News...")
        headers = {"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}
        
        res = requests.post(RENDER_API_URL, headers=headers, json=payload)
        
        if res.status_code == 201:
            print(f"✅ SUCCESS! Live at: {res.json().get('url')}")
        else:
            print(f"❌ FAILED to publish: {res.text}")

if __name__ == "__main__":
    run_bot()