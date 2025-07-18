#!/usr/bin/env python3
"""
Minimal test script to isolate Slack connection issues.
"""
import asyncio
import logging
import os
from dotenv import load_dotenv

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

async def test_slack_connection():
    """Test basic Slack connection without full bot functionality."""
    
    try:
        # Get tokens
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        app_token = os.getenv('SLACK_APP_TOKEN')
        
        print("🔍 Testing Slack Connection...")
        print(f"✅ Bot Token: {bot_token[:20]}...")
        print(f"✅ App Token: {app_token[:20]}...")
        
        # Create minimal app
        app = AsyncApp(
            token=bot_token,
            signing_secret=signing_secret
        )
        
        # Add a simple handler
        @app.message("hello")
        async def message_hello(message, say):
            await say(f"Hey there <@{message['user']}>!")
        
        print("🤖 Creating socket mode handler...")
        
        # Create handler
        handler = AsyncSocketModeHandler(app, app_token)
        
        print("🚀 Starting connection...")
        
        # Start with timeout
        await asyncio.wait_for(
            handler.start_async(),
            timeout=30.0
        )
        
    except asyncio.TimeoutError:
        print("⏰ Connection timeout - this might be normal for testing")
        print("✅ If no errors above, the connection setup is working!")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Running Slack Connection Test...")
    asyncio.run(test_slack_connection()) 