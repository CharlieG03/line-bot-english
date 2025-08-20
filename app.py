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

print("✅ Ultra Simple Bot loaded successfully!")

# Sample articles for recommendations
SAMPLE_ARTICLES = [
    {
        'title': 'Climate Change and Wildlife Conservation',
        'url': 'https://www.nationalgeographic.com/environment',
        'source': 'National Geographic'
    },
    {
        'title': 'The Future of Artificial Intelligence',
        'url': 'https://www.scientificamerican.com/artificial-intelligence/',
        'source': 'Scientific American'
    },
    {
        'title': 'Renewable Energy Innovations', 
        'url': 'https://www.sciencefocus.com/future-technology',
        'source': 'BBC Science Focus'
    }
]

@app.route("/")
def index():
    return "🤖 Ultra Simple Bot is running!"

@app.route("/test")
def test():
    return {
        "status": "ok",
        "bot_loaded": True,
        "articles_count": len(SAMPLE_ARTICLES)
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
    """Handle incoming messages with simple text responses"""
    try:
        user_message = event.message.text.lower().strip()
        print(f"💬 User: {user_message}")
        
        # Simple keyword detection
        if any(word in user_message for word in ['recommend', 'article', 'read', 'help']):
            # Pick random article
            article = random.choice(SAMPLE_ARTICLES)
            
            reply_text = f"📚 Here's an article for you!\n\n" \
                        f"📰 {article['title']}\n" \
                        f"🔗 {article['url']}\n" \
                        f"📝 Source: {article['source']}\n\n" \
                        f"Type 'recommend' for another article!"
        
        elif 'hello' in user_message or 'hi' in user_message:
            reply_text = "👋 Hello! I'm your English learning bot!\n\n" \
                        "Type 'recommend' to get an article suggestion! 📚"
        
        else:
            reply_text = f"You said: '{user_message}'\n\n" \
                        "Try typing:\n" \
                        "• 'recommend' - for an article\n" \
                        "• 'hello' - to say hi\n\n" \
                        "I'm working! 🤖"
        
        # Send simple text message
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # Use the simplest possible message format
            request_body = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
            
            line_bot_api.reply_message(request_body)
        
        print("✅ Message sent successfully")
        
    except Exception as e:
        print(f"❌ Handler error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        
        # Try to send a super simple error message
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                error_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Bot error! But I'm alive! 🤖")]
                )
                line_bot_api.reply_message(error_request)
        except:
            print("❌ Could not send error message")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)