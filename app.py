from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest,
    TextMessage, TemplateMessage, ButtonsTemplate, URIAction, MessageAction
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
from bs4 import BeautifulSoup
import random
import os
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Line Bot credentials - loaded from .env file
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

# Check if environment variables are set
if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("❌ Missing Line Bot credentials in .env file")
    exit(1)

# Initialize Line Bot API v3
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

print("✅ Dynamic Article Bot loaded successfully!")

class ArticleScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.cache = {}
        self.cache_duration = timedelta(hours=2)  # Cache articles for 2 hours
    
    def get_cached_articles(self, website_key):
        """Check if we have cached articles that are still fresh"""
        if website_key in self.cache:
            cached_time, articles = self.cache[website_key]
            if datetime.now() - cached_time < self.cache_duration:
                print(f"📁 Using cached articles for {website_key}")
                return articles
        return None
    
    def cache_articles(self, website_key, articles):
        """Cache articles with timestamp"""
        self.cache[website_key] = (datetime.now(), articles)
        print(f"💾 Cached {len(articles)} articles for {website_key}")
    
    def scrape_national_geographic(self):
        """Scrape articles from National Geographic"""
        cached = self.get_cached_articles('natgeo')
        if cached:
            return cached
        
        try:
            print("🔍 Scraping National Geographic...")
            url = "https://www.nationalgeographic.com/science"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = []
            # Find article containers (National Geographic structure)
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href')
                if href and '/article/' in href and href.startswith('/'):
                    title_elem = link.find(['h2', 'h3', 'span'])
                    if title_elem:
                        title = title_elem.get_text().strip()
                        if len(title) > 20 and len(title) < 100:  # Filter reasonable titles
                            full_url = f"https://www.nationalgeographic.com{href}"
                            
                            article = {
                                'title': title,
                                'url': full_url,
                                'source': 'National Geographic',
                                'category': 'Science & Nature',
                                'difficulty': 'Intermediate to Advanced'
                            }
                            articles.append(article)
            
            # Remove duplicates
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            self.cache_articles('natgeo', unique_articles[:10])  # Cache top 10
            return unique_articles[:10]
            
        except Exception as e:
            print(f"❌ Error scraping National Geographic: {e}")
            return self.get_fallback_articles('natgeo')
    
    def scrape_bbc_science(self):
        """Scrape articles from BBC Science Focus"""
        cached = self.get_cached_articles('bbc_science')
        if cached:
            return cached
        
        try:
            print("🔍 Scraping BBC Science Focus...")
            url = "https://www.sciencefocus.com"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = []
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href')
                if href and ('/future-technology/' in href or '/planet-earth/' in href or '/science/' in href):
                    title_elem = link.find(['h2', 'h3', 'span'])
                    if title_elem:
                        title = title_elem.get_text().strip()
                        if len(title) > 15 and len(title) < 80:
                            full_url = href if href.startswith('http') else f"https://www.sciencefocus.com{href}"
                            
                            article = {
                                'title': title,
                                'url': full_url,
                                'source': 'BBC Science Focus',
                                'category': 'Science & Technology',
                                'difficulty': 'Intermediate'
                            }
                            articles.append(article)
            
            # Remove duplicates
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            self.cache_articles('bbc_science', unique_articles[:10])
            return unique_articles[:10]
            
        except Exception as e:
            print(f"❌ Error scraping BBC Science Focus: {e}")
            return self.get_fallback_articles('bbc_science')
    
    def scrape_scientific_american(self):
        """Scrape articles from Scientific American"""
        cached = self.get_cached_articles('sci_am')
        if cached:
            return cached
        
        try:
            print("🔍 Scraping Scientific American...")
            # Use their article listing page
            url = "https://www.scientificamerican.com/artificial-intelligence/"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = []
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href')
                if href and '/article/' in href:
                    title_elem = link.find(['h2', 'h3', 'span'])
                    if title_elem:
                        title = title_elem.get_text().strip()
                        if len(title) > 20 and len(title) < 100:
                            full_url = href if href.startswith('http') else f"https://www.scientificamerican.com{href}"
                            
                            article = {
                                'title': title,
                                'url': full_url,
                                'source': 'Scientific American',
                                'category': 'Science & AI',
                                'difficulty': 'Advanced'
                            }
                            articles.append(article)
            
            # Remove duplicates
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)
            
            self.cache_articles('sci_am', unique_articles[:8])
            return unique_articles[:8]
            
        except Exception as e:
            print(f"❌ Error scraping Scientific American: {e}")
            return self.get_fallback_articles('sci_am')
    
    def get_fallback_articles(self, source):
        """Fallback articles when scraping fails"""
        fallbacks = {
            'natgeo': [
                {
                    'title': 'Climate Change and Wildlife Conservation',
                    'url': 'https://www.nationalgeographic.com/environment/article/climate-change-wildlife',
                    'source': 'National Geographic',
                    'category': 'Environment',
                    'difficulty': 'Intermediate'
                }
            ],
            'bbc_science': [
                {
                    'title': 'Future Technology Innovations',
                    'url': 'https://www.sciencefocus.com/future-technology',
                    'source': 'BBC Science Focus',
                    'category': 'Technology',
                    'difficulty': 'Intermediate'
                }
            ],
            'sci_am': [
                {
                    'title': 'The Future of Artificial Intelligence',
                    'url': 'https://www.scientificamerican.com/artificial-intelligence/',
                    'source': 'Scientific American',
                    'category': 'AI',
                    'difficulty': 'Advanced'
                }
            ]
        }
        return fallbacks.get(source, [])
    
    def get_random_article(self, preferred_source=None):
        """Get a random article from available sources"""
        all_articles = []
        
        if preferred_source == 'natgeo' or not preferred_source:
            all_articles.extend(self.scrape_national_geographic())
        
        if preferred_source == 'bbc' or not preferred_source:
            all_articles.extend(self.scrape_bbc_science())
        
        if preferred_source == 'sciam' or not preferred_source:
            all_articles.extend(self.scrape_scientific_american())
        
        if not all_articles:
            # Ultimate fallback
            return {
                'title': 'The Science of Learning English',
                'url': 'https://learnenglish.britishcouncil.org',
                'source': 'British Council',
                'category': 'Education',
                'difficulty': 'Intermediate'
            }
        
        return random.choice(all_articles)

# Initialize article scraper
article_scraper = ArticleScraper()

def load_articles():
    """Get articles dynamically from web sources"""
    return article_scraper.get_random_article()

def get_random_article():
    """Get a random article from dynamic sources"""
    return article_scraper.get_random_article()

@app.route("/callback", methods=['POST'])
def callback():
    """Line webhook callback"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """Handle incoming text messages"""
    user_message = event.message.text.lower().strip()
    
    # Commands that trigger article recommendation
    recommend_keywords = ['recommend', 'article', 'read', 'suggest', 'help', 'start']
    source_keywords = {
        'natgeo': ['national geographic', 'natgeo', 'geography', 'nature'],
        'bbc': ['bbc', 'science focus', 'technology'],
        'sciam': ['scientific american', 'science', 'ai', 'artificial intelligence']
    }
    
    # Check for source preference
    preferred_source = None
    for source, keywords in source_keywords.items():
        if any(keyword in user_message for keyword in keywords):
            preferred_source = source
            break
    
    if any(keyword in user_message for keyword in recommend_keywords):
        send_article_recommendation(event, preferred_source)
    else:
        # Default response
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="👋 Hi! I'm your dynamic English learning assistant!\n\n"
                                 "🔍 I can recommend fresh articles from:\n"
                                 "• National Geographic (nature & science)\n"
                                 "• BBC Science Focus (technology)\n" 
                                 "• Scientific American (advanced science)\n\n"
                                 "📚 Type 'recommend' for a random article\n"
                                 "🎯 Or try: 'recommend natgeo' for specific sources!"
                        )
                    ]
                )
            )

def send_article_recommendation(event, preferred_source=None):
    """Send a dynamically scraped article recommendation"""
    try:
        print(f"🎯 Getting article (source: {preferred_source})...")
        article = article_scraper.get_random_article(preferred_source)
        
        if not article:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="😔 Sorry, I couldn't find any articles right now.\n"
                                           "Please try again in a moment!")
                        ]
                    )
                )
            return
        
        # Estimate reading time based on title length and source
        if article['source'] == 'Scientific American':
            reading_time = "12-18 minutes"
        elif article['source'] == 'National Geographic':
            reading_time = "8-15 minutes"
        else:
            reading_time = "6-12 minutes"
        
        # Create buttons template message
        buttons_template = ButtonsTemplate(
            title=article['title'][:40] + "..." if len(article['title']) > 40 else article['title'],
            text=f"📰 Source: {article['source']}\n"
                 f"📂 Category: {article['category']}\n"
                 f"🎯 Level: {article['difficulty']}\n"
                 f"⏱️ Est. reading: {reading_time}",
            actions=[
                URIAction(
                    label='📖 Read Article',
                    uri=article['url']
                ),
                MessageAction(
                    label='🔄 Get Another',
                    text='recommend'
                )
            ]
        )
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TemplateMessage(
                            alt_text=f"📚 Fresh Article: {article['title']} | {article['source']}",
                            template=buttons_template
                        )
                    ]
                )
            )
        
        print(f"✅ Sent article: {article['title']} from {article['source']}")
        
    except Exception as e:
        print(f"❌ Error in send_article_recommendation: {e}")
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="🔧 Sorry, there was a technical issue.\n"
                                       "Please try again!")
                    ]
                )
            )

@app.route("/")
def index():
    """Health check endpoint"""
    return "🤖 Dynamic Article Bot is running! Ready to scrape fresh content!"

@app.route("/test-scraping")
def test_scraping():
    """Test endpoint to check scraping functionality"""
    try:
        natgeo_articles = article_scraper.scrape_national_geographic()
        bbc_articles = article_scraper.scrape_bbc_science()
        sciam_articles = article_scraper.scrape_scientific_american()
        
        return {
            "status": "success",
            "natgeo_count": len(natgeo_articles),
            "bbc_count": len(bbc_articles),
            "sciam_count": len(sciam_articles),
            "sample_articles": {
                "natgeo": natgeo_articles[:2] if natgeo_articles else [],
                "bbc": bbc_articles[:2] if bbc_articles else [],
                "sciam": sciam_articles[:2] if sciam_articles else []
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)