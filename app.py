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
import json
from datetime import datetime, timedelta, timezone
import time

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

print("✅ Auto-Scraping Bot loaded successfully!")

class AutoArticleScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.cache = {}
        self.cache_duration = timedelta(hours=2)
        self.website_config = self.load_website_config()
        # Set timezone to UTC+8 (Asia/Taipei)
        self.local_timezone = timezone(timedelta(hours=8))
        
    def get_local_time(self):
        """Get current time in UTC+8"""
        return datetime.now(self.local_timezone)
        
    def format_time(self, dt):
        """Format datetime for display"""
        return dt.strftime('%Y-%m-%d %H:%M UTC+8')
        
    def load_website_config(self):
        """Load website scraping configuration from JSON"""
        try:
            with open('website_config.json', 'r', encoding='utf-8') as file:
                config = json.load(file)
                print(f"✅ Loaded {len(config['websites'])} website configurations")
                return config
        except FileNotFoundError:
            print("⚠️ website_config.json not found, using default config")
            return self.get_default_config()
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """Default configuration if JSON file is missing"""
        return {
            "websites": {
                "national_geographic": {
                    "name": "National Geographic",
                    "base_url": "https://www.nationalgeographic.com",
                    "section_urls": [
                        "https://www.nationalgeographic.com/science",
                        "https://www.nationalgeographic.com/environment"
                    ],
                    "article_selectors": {
                        "link_contains": "/article/",
                        "title_tags": ["h2", "h3", "h4"],
                        "min_title_length": 20,
                        "max_title_length": 100
                    },
                    "category": "Science & Nature",
                    "difficulty": "Intermediate",
                    "keywords": ["natgeo", "national geographic", "nature"]
                },
                "bbc_science": {
                    "name": "BBC Science Focus",
                    "base_url": "https://www.sciencefocus.com",
                    "section_urls": [
                        "https://www.sciencefocus.com/future-technology",
                        "https://www.sciencefocus.com/planet-earth"
                    ],
                    "article_selectors": {
                        "link_contains": ["/future-technology/", "/planet-earth/"],
                        "title_tags": ["h2", "h3"],
                        "min_title_length": 15,
                        "max_title_length": 80
                    },
                    "category": "Science & Technology",
                    "difficulty": "Intermediate",
                    "keywords": ["bbc", "science focus", "technology"]
                }
            }
        }
    
    def is_cache_fresh(self, key):
        """Check if cached data is still fresh"""
        if key in self.cache:
            timestamp, _ = self.cache[key]
            return self.get_local_time() - timestamp < self.cache_duration
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
        self.cache[key] = (self.get_local_time(), articles)
        print(f"💾 Cached {len(articles)} articles for {key}")
    
    def scrape_website(self, website_key, website_config):
        """Scrape articles from a specific website based on its config"""
        cached = self.get_cached_articles(website_key)
        if cached:
            return cached
        
        try:
            print(f"🔍 Scraping {website_config['name']}...")
            articles = []
            
            # Try each section URL
            for section_url in website_config['section_urls']:
                try:
                    response = requests.get(section_url, headers=self.headers, timeout=8)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find article links
                    links = soup.find_all('a', href=True)
                    
                    for link in links[:30]:  # Check first 30 links per section
                        href = link.get('href')
                        
                        # Check if link matches our criteria
                        link_contains = website_config['article_selectors']['link_contains']
                        if isinstance(link_contains, list):
                            link_match = any(pattern in href for pattern in link_contains if href)
                        else:
                            link_match = link_contains in href if href else False
                        
                        if link_match:
                            # Find title in the link
                            title_tags = website_config['article_selectors']['title_tags']
                            title_elem = link.find(title_tags)
                            
                            if title_elem:
                                title = title_elem.get_text().strip()
                                min_len = website_config['article_selectors']['min_title_length']
                                max_len = website_config['article_selectors']['max_title_length']
                                
                                # Check title length
                                if min_len <= len(title) <= max_len:
                                    # Build full URL
                                    if href.startswith('http'):
                                        full_url = href
                                    elif href.startswith('/'):
                                        full_url = website_config['base_url'] + href
                                    else:
                                        full_url = website_config['base_url'] + '/' + href
                                    
                                    article = {
                                        'title': title,
                                        'url': full_url,
                                        'source': website_config['name'],
                                        'category': website_config['category'],
                                        'difficulty': website_config['difficulty'],
                                        'scraped_at': self.format_time(self.get_local_time()),
                                        'type': 'scraped'
                                    }
                                    articles.append(article)
                        
                        # Limit articles per website
                        if len(articles) >= 8:
                            break
                    
                    # Small delay between sections
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"⚠️ Error scraping section {section_url}: {e}")
                    continue
            
            # Remove duplicates
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            if unique_articles:
                self.cache_articles(website_key, unique_articles)
                print(f"✅ Scraped {len(unique_articles)} articles from {website_config['name']}")
                return unique_articles
            
        except Exception as e:
            print(f"❌ Error scraping {website_config['name']}: {e}")
        
        return []
    
    def get_all_articles(self):
        """Get articles from all configured websites"""
        all_articles = []
        
        websites = self.website_config.get('websites', {})
        for website_key, website_config in websites.items():
            articles = self.scrape_website(website_key, website_config)
            all_articles.extend(articles)
            
            # Small delay between websites
            time.sleep(2)
        
        return all_articles
    
    def get_articles_by_source(self, preferred_source):
        """Get articles from a specific source"""
        websites = self.website_config.get('websites', {})
        
        # Find matching website
        for website_key, website_config in websites.items():
            keywords = website_config.get('keywords', [])
            if any(keyword in preferred_source.lower() for keyword in keywords):
                articles = self.scrape_website(website_key, website_config)
                return articles
        
        return []
    
    def get_random_article(self, preferred_source=None):
        """Get a random article, optionally from preferred source"""
        if preferred_source:
            articles = self.get_articles_by_source(preferred_source)
            if articles:
                return random.choice(articles)
        
        # Get from all sources
        all_articles = self.get_all_articles()
        
        if all_articles:
            return random.choice(all_articles)
        
        # Ultimate fallback
        return {
            'title': 'English Learning: The Science of Reading',
            'url': 'https://learnenglish.britishcouncil.org/skills/reading',
            'source': 'British Council',
            'category': 'Language Learning',
            'difficulty': 'All Levels',
            'type': 'fallback'
        }

# Initialize scraper
article_scraper = AutoArticleScraper()

@app.route("/")
def index():
    return "🤖 Auto-Scraping Bot is running! 🔄 Articles auto-updated every 2 hours!"

@app.route("/test")
def test():
    """Test endpoint with scraping status"""
    websites = article_scraper.website_config.get('websites', {})
    cache_status = {}
    
    for website_key in websites.keys():
        cache_status[website_key] = article_scraper.is_cache_fresh(website_key)
    
    return {
        "status": "ok",
        "bot_type": "auto_scraping",
        "websites_configured": len(websites),
        "cache_status": cache_status,
        "cache_duration_hours": article_scraper.cache_duration.total_seconds() / 3600
    }

@app.route("/scrape-status")
def scrape_status():
    """Check current scraping status and cached articles"""
    websites = article_scraper.website_config.get('websites', {})
    status = {}
    
    for website_key, website_config in websites.items():
        cached_articles = article_scraper.get_cached_articles(website_key)
        status[website_key] = {
            "name": website_config['name'],
            "cache_fresh": article_scraper.is_cache_fresh(website_key),
            "cached_articles": len(cached_articles) if cached_articles else 0,
            "sample_titles": [a['title'] for a in (cached_articles or [])[:3]]
        }
    
    current_time = article_scraper.format_time(article_scraper.get_local_time())
    
    return {
        "scraping_status": status,
        "current_time_utc8": current_time,
        "timezone": "UTC+8 (Asia/Taipei)"
    }

@app.route("/force-refresh")
def force_refresh():
    """Force refresh all cached articles"""
    article_scraper.cache.clear()
    new_articles = article_scraper.get_all_articles()
    refresh_time = article_scraper.format_time(article_scraper.get_local_time())
    
    return {
        "status": "force_refreshed",
        "refresh_time_utc8": refresh_time,
        "articles_found": len(new_articles),
        "sample_titles": [a['title'] for a in new_articles[:5]]
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
    """Handle messages with auto-scraped articles"""
    try:
        user_message = event.message.text.lower().strip()
        print(f"💬 User: {user_message}")
        
        # Detect source preferences
        preferred_source = None
        if any(word in user_message for word in ['natgeo', 'national geographic', 'nature']):
            preferred_source = 'national geographic'
        elif any(word in user_message for word in ['bbc', 'science focus', 'technology']):
            preferred_source = 'bbc'
        
        # Handle different message types
        if any(word in user_message for word in ['Recommend', 'recommend', 'article', 'Read', 'read', 'suggest', 'Help', 'help']):
            # Get auto-scraped article
            article = article_scraper.get_random_article(preferred_source)
            
            # Determine freshness
            article_type = article.get('type', 'unknown')
            if article_type == 'scraped':
                freshness_icon = "🆕"
                freshness_text = "Fresh"
                scraped_time = article.get('scraped_at', 'recently')
                extra_info = f"Scraped: {scraped_time}"
            else:
                freshness_icon = "📚"
                freshness_text = "Reliable"
                extra_info = "Always available"
            
            reply_text = f"{freshness_icon} {freshness_text} article for you!\n\n" \
                        f"📰 {article['title']}\n\n" \
                        f"🔗 {article['url']}\n\n" \
                        f"📝 Source: {article['source']}\n" \
                        f"📂 Category: {article['category']}\n" \
                        f"🎯 Level: {article['difficulty']}\n" \
                        f"⏰ {extra_info}\n\n" \
                        f"Type 'recommend' for another! 🔄"
        
        elif any(word in user_message for word in ['hello', 'hi', 'hey', 'start']):
            websites = article_scraper.website_config.get('websites', {})
            website_names = [config['name'] for config in websites.values()]
            
            reply_text = f"👋 Hello! I'm your auto-scraping English bot!\n\n" \
                        f"🔄 I automatically find fresh articles from:\n"
            
            for name in website_names:
                reply_text += f"• {name} 🌐\n"
            
            reply_text += f"\n⏰ Articles refresh every 2 hours!\n\n" \
                         f"Type 'recommend' for a fresh article! 📚"
        
        elif 'status' in user_message or 'cache' in user_message:
            websites = article_scraper.website_config.get('websites', {})
            cache_info = []
            
            for website_key, website_config in websites.items():
                is_fresh = article_scraper.is_cache_fresh(website_key)
                status = "✅ Fresh" if is_fresh else "🔄 Updating"
                cache_info.append(f"• {website_config['name']}: {status}")
            
            current_time = article_scraper.format_time(article_scraper.get_local_time())
            
            reply_text = f"📊 Auto-Scraping Status:\n\n" + "\n".join(cache_info) + \
                        f"\n\n⏰ Cache refreshes every 2 hours\n" \
                        f"🔄 Always getting fresh content!\n" \
                        f"🕐 Current time: {current_time}\n\n" \
                        f"Type 'recommend' for an article!"
        
        elif 'thanks' in user_message or 'thank you' in user_message:
            reply_text = f"You're welcome! 😊\n\n" \
                        f"🔄 I'm constantly finding fresh articles for you!\n" \
                        f"📚 Perfect for improving your English reading skills.\n\n" \
                        f"Type 'recommend' anytime! 🤖"
        
        else:
            reply_text = f"I see: '{event.message.text}'\n\n" \
                        f"🔄 Auto-Scraping Commands:\n" \
                        f"• 'recommend' - fresh article 🆕\n" \
                        f"• 'recommend natgeo' - National Geographic 🌍\n" \
                        f"• 'status' - scraping status 📊\n" \
                        f"• 'hello' - greeting 👋\n\n" \
                        f"I auto-update content every 2 hours! 🤖"
        
        # Send response
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            request_body = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
            line_bot_api.reply_message(request_body)
        
        print("✅ Auto-scraping response sent")
        
    except Exception as e:
        print(f"❌ Handler error: {e}")
        
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                error_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔧 Small hiccup in auto-scraping, but I'm here!\n\nTry 'recommend' again! 🤖")]
                )
                line_bot_api.reply_message(error_request)
        except:
            print("❌ Could not send error message")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)