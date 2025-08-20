#!/usr/bin/env python3
"""
Test script to verify Line Bot setup
"""
import os
import json

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("🔍 Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, checking system environment variables only")

def test_environment_variables():
    """Test if environment variables are set"""
    print("🔍 Checking environment variables...")
    
    access_token = os.getenv('CHANNEL_ACCESS_TOKEN')
    secret = os.getenv('CHANNEL_SECRET')
    
    if access_token:
        print(f"✅ CHANNEL_ACCESS_TOKEN: {access_token[:10]}...{access_token[-4:]}")
    else:
        print("❌ CHANNEL_ACCESS_TOKEN not found!")
        return False
    
    if secret:
        print(f"✅ CHANNEL_SECRET: {secret[:10]}...{secret[-4:]}")
    else:
        print("❌ CHANNEL_SECRET not found!")
        return False
    
    return True

def test_articles_file():
    """Test if articles.json exists and is valid"""
    print("\n📚 Checking articles.json...")
    
    try:
        with open('articles.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            articles = data.get('articles', [])
            
            if not articles:
                print("❌ No articles found in articles.json!")
                return False
            
            print(f"✅ Found {len(articles)} articles:")
            for i, article in enumerate(articles, 1):
                print(f"   {i}. {article.get('title', 'No title')}")
                if not article.get('url'):
                    print(f"      ⚠️  Warning: No URL for article {i}")
            
            return True
            
    except FileNotFoundError:
        print("❌ articles.json not found!")
        return False
    except json.JSONDecodeError:
        print("❌ Invalid JSON in articles.json!")
        return False

def test_imports():
    """Test if required packages can be imported"""
    print("\n📦 Testing imports...")
    
    try:
        from linebot.v3 import WebhookHandler
        from linebot.v3.messaging import Configuration, MessagingApi
        print("✅ Line Bot SDK v3 imported successfully")
        
        from flask import Flask
        print("✅ Flask imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("🤖 LINE BOT SETUP VERIFICATION")
    print("=" * 50)
    
    tests = [
        test_imports(),
        test_environment_variables(),
        test_articles_file()
    ]
    
    print("\n" + "=" * 50)
    if all(tests):
        print("🎉 ALL TESTS PASSED! Your bot is ready to run!")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Use ngrok to expose your local server")
        print("3. Set webhook URL in Line Developer Console")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    print("=" * 50)

if __name__ == "__main__":
    main()