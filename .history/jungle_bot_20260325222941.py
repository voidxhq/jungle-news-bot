import requests
import feedparser
from newspaper import Article as NewsScraper
from google import genai
from google.genai import types
import json
import random
from duckduckgo_search import DDGS

# ==========================================
# ⚙️ BOT CONFIGURATION
# ==========================================
RENDER_API_URL = "https://junglenews.online/api/bot/post-article"
JUNGLE_BOT_KEY = "jungle_super_secret_bot_key_2026"  
GEMINI_API_KEY = "AIzaSyCE2zLpEmTtI5We3R6R2mAevuDsgGkW2KQ" 

# Array of Premium Ghanaian News Feeds
GHANA_RSS_FEEDS = [
    "https://www.myjoyonline.com/feed/",          # JoyNews
    "https://citinewsroom.com/feed/",             # Citi News
    "https://pulse.com.gh/news/rss",              # Pulse Ghana
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml" # BBC Africa (Fallback)
]

# Initialize the NEW GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

def find_clean_image(keywords):
    """Searches the web for a real, unwatermarked image."""
    # We append 'Ghana' to force the search engine to find local-looking photos
    search_query = f"{keywords} Ghana news high resolution"
    print(f"🔍 Hunting for clean image using: '{search_query}'")
    
    try:
        results = DDGS().images(
            keywords=search_query,
            region="wt-wt",
            safesearch="moderate",
            size="Large",
            max_results=1
        )
        if results:
            return results[0].get("image") # Returns the direct image URL
    except Exception as e:
        print(f"⚠️ Image search failed: {e}")
        
    return None

def rewrite_article_with_ai(raw_text):
    """Sends the raw scraped text to Gemini and forces perfect JSON output using the new SDK."""
    prompt = f"""
    You are an expert journalist for 'Jungle News', a Ghanaian digital news platform.
    Read the following facts and write a completely original, engaging, plagiarism-free news article.
    
    Rules:
    1. Do NOT copy sentences from the original. 
    2. Format the 'content' in clean HTML (use <p> tags, and <h2> tags for subheadings). Use single quotes inside HTML.
    3. Write a catchy 'title' and a 2-sentence 'excerpt'.
    4. Provide a string of 3 specific 'image_keywords' to help a search engine find a real photo for this story (e.g., "university students laptops").
    5. Pick the most accurate 'category_slug' for this story from this exact list: ["news", "sports", "entertainment", "campusinsider", "tech", "ghana"].
    6. Decide if this is 'is_breaking' news (true or false).
    
    Return a JSON object with exactly these keys: "title", "content", "excerpt", "image_keywords", "category_slug", "is_breaking".
    
    Original Text:
    {raw_text}
    """
    
    try:
        # This is the new Google GenAI syntax!
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ AI Rewrite failed: {e}")
        return None

def run_bot():
    # 1. Pick a random feed from our list so the site gets varied content!
    target_feed = random.choice(GHANA_RSS_FEEDS)
    print(f"📡 Scanning for news at {target_feed}...")
    
    feed = feedparser.parse(target_feed)
    
    # Process the top 2 latest articles
    for entry in feed.entries[:2]:
        print(f"\n📰 Found Story: {entry.title}")
        
        # 2. Scrape the original article
        scraper = NewsScraper(entry.link)
        try:
            scraper.download()
            scraper.parse()
        except:
            print("⚠️ Could not download article. Skipping.")
            continue
            
        raw_text = scraper.text
        original_image = scraper.top_image 
        
        if not raw_text or len(raw_text) < 100:
            print("⚠️ Article too short to rewrite. Skipping.")
            continue
            
        # 3. Rewrite with AI and get Categories/Keywords
        print("🧠 Sending to AI for rewriting and categorization...")
        ai_data = rewrite_article_with_ai(raw_text)
        
        if not ai_data:
            continue
            
        # 4. Try to find a clean, non-watermarked image
        clean_image = find_clean_image(ai_data.get("image_keywords", "Ghana news"))
        
        if clean_image:
            final_cover_image = clean_image
            print("✅ Successfully found a clean, unique cover image!")
        else:
            final_cover_image = original_image
            print("⚠️ Clean image search failed. Falling back to the original source image.")
            
        # 5. Package for Jungle News
        payload = {
            "title": ai_data.get("title"),
            "content": ai_data.get("content"),
            "excerpt": ai_data.get("excerpt"),
            "cover_image": final_cover_image,
            "category_slug": ai_data.get("category_slug", "news"), 
            "is_breaking": ai_data.get("is_breaking", False),
            "is_trending": False,
            "is_featured": False
        }
        
        # 6. Post to your live Render app
        print(f"🚀 Publishing '{payload['title']}' to the '{payload['category_slug']}' category...")
        headers = {"X-API-Key": JUNGLE_BOT_KEY, "Content-Type": "application/json"}
        
        res = requests.post(RENDER_API_URL, headers=headers, json=payload)
        
        if res.status_code == 201:
            print(f"✅ SUCCESS! Live at: {res.json().get('url')}")
        else:
            print(f"❌ FAILED to publish: {res.text}")

if __name__ == "__main__":
    run_bot()