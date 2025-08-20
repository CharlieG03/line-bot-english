from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
from dotenv import load_dotenv
import random
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Line Bot credentials
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("❌ Missing Line Bot credentials")
    exit(1)

# Initialize Line Bot API
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

print("✅ Smart Dynamic Bot loaded successfully!")

# RELIABLE FALLBACK ARTICLES (always work)
FALLBACK_ARTICLES = [
    {
        'title': 'Climate Change and Wildlife Conservation',
        'url': 'https://www.nationalgeographic.com/environment',
        'source': 'National Geographic',
        'category': 'Environment',
        'type': 'fallback'
    },
    {
        'title': 'The Future of Artificial Intelligence',
        'url': 'https://www.scientificamerican.com/artificial-intelligence/',
        'source': 'Scientific American',
        'category': 'Technology',
        'type': 'fallback'
    },
    {
        'title': 'Space Exploration Breakthroughs',
        'url': 'https://www.nationalgeographic.com/science/space',
        'source': 'National Geographic',
        'category': 'Science',
        'type': 'fallback'
    },
    {
        'title': 'Ocean Conservation Efforts',
        'url': 'https://www.nationalgeographic.com/environment/article/oceans',
        'source': 'National Geographic',
        'category': 'Environment',
        'type': 'fallback'
    },
    {
        'title': 'Renewable Energy Innovations',
        'url': 'https://www.sciencefocus.com/future-technology',
        'source': 'BBC Science Focus',
        'category': 'Technology',
        'type': 'fallback'
    }
]

class SmartArticleScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cache = {}
        self.cache_duration = timedelta(hours=3)  # Cache for 3 hours
    
    def is_cache_fresh(self, key):
        """Check if cached data is still fresh"""
        if key in self.cache:
            timestamp, _ = self.cache[key]
            return datetime.now() - timestamp < self.cache_duration
        return False
    
    def get_cached_articles(self, key):
        """Get cached articles if fresh"""
        if self.is_cache_fresh(key):
            _, articles = self.cache[key]
            print(f"📁 Using cached articles for {key}")
            return articles
        return None
    
    def cache_articles(self, key, articles):
        """Cache articles with timestamp"""
        self.cache[key] = (datetime.now(), articles)
        print(f"💾 Cached {len(articles)} articles for {key}")
    
    def try_scrape_natgeo(self):
        """Try to scrape National Geographic (with timeout)"""
        cached = self.get_cached_articles('natgeo')
        if cached:
            return cached
        
        try:
            print("🔍 Trying to scrape National Geographic...")
            url = "https://www.nationalgeographic.com/science"
            
            # Quick timeout to avoid hanging
            response = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = []
            links = soup.find_all('a', href=True)
            
            for link in links[:20]:  # Only check first 20 links
                href = link.get('href')
                if href and '/article/' in href and href.startswith('/'):
                    title_elem = link.find(['h2', 'h3', 'span', 'div'])
                    if title_elem:
                        title = title_elem.get_text().strip()
                        if 20 <= len(title) <= 80:  # Reasonable title length
                            full_url = f"https://www.nationalgeographic.com{href}"
                            
                            article = {
                                'title': title,
                                'url': full_url,
                                'source': 'National Geographic',
                                'category': 'Science & Nature',
                                'type': 'scraped'
                            }
                            articles.append(article)
                            
                            if len(articles) >= 5:  # Limit to 5 articles
                                break
            
            if articles:
                # Remove duplicates
                seen_urls = set()
                unique_articles = []
                for article in articles:
                    if article['url'] not in seen_urls:
                        seen_urls.add(article['url'])
                        unique_articles.append(article)
                
                self.cache_articles('natgeo', unique_articles)
                print(f"✅ Scraped {len(unique_articles)} new articles from National Geographic")
                return unique_articles
            
        except Exception as e:
            print(f"⚠️ Could not scrape National Geographic: {e}")
        
        return None
    
    def get_smart_article(self, preferred_source=None):
        """Get article with smart fallback strategy"""
        
        # Try dynamic scraping first (if user wants it)
        if preferred_source == 'natgeo' or random.random() < 0.7:  # 70% chance to try scraping
            scraped_articles = self.try_scrape_natgeo()
            if scraped_articles:
                article = random.choice(scraped_articles)
                print(f"📰 Returning fresh scraped article: {article['title']}")
                return article
        
        # Fallback to reliable articles
        article = random.choice(FALLBACK_ARTICLES)
        print(f"📚 Returning reliable fallback article: {article['title']}")
        return article

# Initialize smart scraper
smart_scraper = SmartArticleScraper()

@app.route("/")
def index():
    return "🤖 Smart Dynamic Bot is running! 🔄"

@app.route("/test")
def test():
    """Test endpoint with cache status"""
    natgeo_fresh = smart_scraper.is_cache_fresh('natgeo')
    return {
        "status": "ok",
        "bot_type": "smart_dynamic",
        "fallback_articles": len(FALLBACK_ARTICLES),
        "natgeo_cache_fresh": natgeo_fresh,
        "cache_duration_hours": smart_scraper.cache_duration.total_seconds() / 3600
    }

@app.route("/force-scrape")
def force_scrape():
    """Force scrape for testing"""
    articles = smart_scraper.try_scrape_natgeo()
    return {
        "status": "scrape_attempted",
        "articles_found": len(articles) if articles else 0,
        "sample_titles": [a['title'] for a in (articles or [])[:3]]
    }

@app.route("/callback", methods=['POST'])
def callback():
    """Line webhook callback"""
    try:
        signature = request.headers.get('X-Line-Signature')
        if not signature:
            abort(400)
        
        body = request.get_data(as_text=True)
        handler.handle(body, signature)
        return 'OK'
        
    except InvalidSignatureError:
        print("❌ Invalid signature")
        abort(400)
    except Exception as e:
        print(f"❌ Callback error: {e}")
        return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """Handle incoming messages with smart article recommendations"""
    try:
        user_message = event.message.text.lower().strip()
        print(f"💬 User: {user_message}")
        
        # Check for source preferences
        preferred_source = None
        if 'natgeo' in user_message or 'national geographic' in user_message:
            preferred_source = 'natgeo'
        
        # Handle different message types
        if any(word in user_message for word in ['Recommend', 'recommend', 'article', 'read', 'Help', 'help', 'suggest']):
            # Get smart article recommendation
            article = smart_scraper.get_smart_article(preferred_source)
            
            # Create response with article info
            freshness = "🆕 Fresh" if article.get('type') == 'scraped' else "📚 Curated"
            
            reply_text = f"{freshness} article for you!\n\n" \
                        f"📰 {article['title']}\n\n" \
                        f"🔗 {article['url']}\n\n" \
                        f"📝 Source: {article['source']}\n" \
                        f"📂 Category: {article['category']}\n\n" \
                        f"Type 'recommend' for another article! 🔄"
        
        elif any(word in user_message for word in ['hello', 'hi', 'hey', 'start']):
            reply_text = "👋 Hello! I'm your smart English learning assistant!\n\n" \
                        "I find articles from top sources:\n" \
                        "• National Geographic 🌍\n" \
                        "• Scientific American 🔬\n" \
                        "• BBC Science Focus 🚀\n\n" \
                        "I mix fresh content with reliable classics!\n\n" \
                        "Type 'recommend' to get started! 📚"
        
        elif 'fresh' in user_message or 'new' in user_message:
            reply_text = "🆕 I'll try to find you a fresh article!\n\n" \
                        "I scrape content from National Geographic and other sources every few hours.\n\n" \
                        "Type 'recommend natgeo' for fresh Nat Geo content! 🌍"
        
        elif 'thanks' in user_message or 'thank you' in user_message:
            reply_text = "You're very welcome! 😊\n\n" \
                        "Enjoy reading! The best way to improve English is through consistent practice.\n\n" \
                        "Type 'recommend' anytime for more articles! 📖"
        
        else:
            reply_text = f"I see you said: '{event.message.text}'\n\n" \
                        "Here's what I can do:\n" \
                        "• 'recommend' - smart article suggestion 🧠\n" \
                        "• 'recommend natgeo' - fresh Nat Geo content 🌍\n" \
                        "• 'hello' - friendly greeting 👋\n\n" \
                        "I'm your smart learning assistant! 🤖✨"
        
        # Send response using working format
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            request_body = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
            line_bot_api.reply_message(request_body)
        
        print("✅ Smart message sent successfully")
        
    except Exception as e:
        print(f"❌ Handler error: {e}")
        
        # Reliable error message
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                error_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Oops! Had a small hiccup, but I'm still here! 🤖\n\nTry 'recommend' again!")]
                )
                line_bot_api.reply_message(error_request)
        except:
            print("❌ Could not send error message")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)