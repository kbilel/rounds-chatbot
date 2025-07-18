#!/usr/bin/env python3
"""
Simple test script to verify Slack tokens are properly configured.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_slack_tokens():
    """Test if Slack tokens are properly configured."""
    
    print("🔍 Testing Slack Token Configuration...")
    print("-" * 50)
    
    # Check required tokens
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    app_token = os.getenv('SLACK_APP_TOKEN')
    
    # Test Bot Token
    if bot_token and bot_token.startswith('xoxb-') and len(bot_token) > 20:
        print("✅ SLACK_BOT_TOKEN: Configured correctly")
    else:
        print("❌ SLACK_BOT_TOKEN: Missing or invalid")
        print(f"   Current value: {bot_token[:20] if bot_token else 'None'}...")
        
    # Test Signing Secret
    if signing_secret and len(signing_secret) > 20:
        print("✅ SLACK_SIGNING_SECRET: Configured correctly")
    else:
        print("❌ SLACK_SIGNING_SECRET: Missing or invalid")
        print(f"   Current value: {signing_secret[:10] if signing_secret else 'None'}...")
        
    # Test App Token
    if app_token and app_token.startswith('xapp-') and len(app_token) > 20:
        print("✅ SLACK_APP_TOKEN: Configured correctly")
    else:
        print("❌ SLACK_APP_TOKEN: Missing or invalid")
        print(f"   Current value: {app_token[:20] if app_token else 'None'}...")
    
    print("-" * 50)
    
    # Overall status
    all_configured = all([
        bot_token and bot_token.startswith('xoxb-'),
        signing_secret and len(signing_secret) > 20,
        app_token and app_token.startswith('xapp-')
    ])
    
    if all_configured:
        print("🎉 All tokens are properly configured!")
        print("✅ You can now run: python main.py start-bot")
    else:
        print("⚠️  Please update your .env file with actual Slack tokens")
        print("📖 Get them from: https://api.slack.com/apps")
    
    return all_configured

if __name__ == "__main__":
    test_slack_tokens() 