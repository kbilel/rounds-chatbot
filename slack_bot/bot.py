"""
Main Slack bot implementation.
Handles user interactions, processes queries, and manages bot responses.
"""
import logging
import asyncio
import re
from typing import Dict, Any, Optional
import json
import tempfile
import os
from datetime import datetime

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
import pandas as pd

from config import settings
from ai import sql_engine, response_formatter
from .user_session import UserSessionManager
from .csv_handler import CSVHandler

logger = logging.getLogger(__name__)


class RoundsAnalyticsBot:
    """
    Slack bot for Rounds analytics and business intelligence.
    
    Features:
    - Natural language query processing
    - Smart response formatting
    - CSV export functionality
    - SQL query sharing
    - User session management
    """
    
    def __init__(self):
        """Initialize the Slack bot."""
        self.app = AsyncApp(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret
        )
        
        self.session_manager = UserSessionManager()
        self.csv_handler = CSVHandler()
        
        # Set up event handlers
        self._setup_event_handlers()
        
        logger.info("Rounds Analytics Bot initialized")
    
    def _setup_event_handlers(self):
        """Set up Slack event handlers."""
        
        @self.app.event("app_mention")
        async def handle_app_mention(event, say, client):
            """Handle when the bot is mentioned."""
            await self._handle_message(event, say, client)
        
        @self.app.event("message")
        async def handle_direct_message(event, say, client):
            """Handle direct messages to the bot."""
            # Only respond to direct messages (DMs)
            if event.get("channel_type") == "im":
                await self._handle_message(event, say, client)
        
        @self.app.command("/analytics")
        async def handle_analytics_command(ack, body, say, client):
            """Handle the /analytics slash command."""
            await ack()
            
            # Extract the text from the command
            text = body.get("text", "").strip()
            
            if not text:
                try:
                    await say("👋 Hi! I'm the Rounds Analytics Bot. Ask me questions about our app portfolio!\n\n"
                             "Try asking:\n"
                             "• 'How many apps do we have?'\n"
                             "• 'Which country generates the most revenue?'\n"
                             "• 'Show me top iOS apps by popularity'")
                except Exception as e:
                    logger.error(f"Failed to send help message: {e}")
                    # Try responding directly to the user
                    try:
                        await client.chat_postMessage(
                            channel=body["user_id"],
                            text="👋 Hi! I'm here to help with analytics questions. Try asking 'How many apps do we have?'"
                        )
                    except Exception as e2:
                        logger.error(f"Failed to send DM: {e2}")
                return
            
            # Process the analytics question
            try:
                # Check if we can respond in the channel
                channel_id = body.get("channel_id")
                user_id = body.get("user_id")
                
                logger.info(f"Processing slash command from user {user_id} in channel {channel_id}: {text}")
                
                # Try to process the query
                query_result = sql_engine.process_query(text)
                formatted_response = response_formatter.format_response(query_result, text)
                
                # Try to send response
                try:
                    await say(formatted_response["response_text"])
                except Exception as channel_error:
                    logger.warning(f"Cannot respond in channel {channel_id}: {channel_error}")
                    # Fall back to DM
                    try:
                        await client.chat_postMessage(
                            channel=user_id,
                            text=f"Here's your analytics result:\n\n{formatted_response['response_text']}"
                        )
                    except Exception as dm_error:
                        logger.error(f"Failed to send DM: {dm_error}")
                        await say("❌ I encountered an issue sending the response. Please try again or contact an admin.")
                
            except Exception as e:
                logger.error(f"Error processing analytics command: {e}")
                try:
                    await say(f"❌ I encountered an issue processing your request: {str(e)}\n\n"
                             "Please try rephrasing your question or ask something like:\n"
                             "• 'List all apps sorted by popularity'\n"
                             "• 'What's our total revenue this month?'\n"
                             "• 'Compare iOS vs Android performance'")
                except Exception:
                    # If we can't respond at all, log it
                    logger.error(f"Cannot send error response for slash command")
        
        @self.app.action("export_csv")
        async def handle_csv_export(ack, body, client):
            """Handle CSV export button clicks."""
            await ack()
            await self._handle_csv_export(body, client)
        
        @self.app.action("show_sql")
        async def handle_show_sql(ack, body, client):
            """Handle SQL query display button clicks."""
            await ack()
            await self._handle_show_sql(body, client)
        
        @self.app.action("help_button")
        async def handle_help(ack, body, say):
            """Handle help button clicks."""
            await ack()
            await self._send_help_message(say)
    
    async def _handle_message(self, event: Dict[str, Any], say, client: AsyncWebClient):
        """
        Process incoming messages and generate responses.
        
        Args:
            event: Slack event data
            say: Slack say function for responses
            client: Slack web client
        """
        try:
            user_id = event["user"]
            text = event["text"]
            channel = event["channel"]
            message_ts = event["ts"]
            
            # Clean the text (remove bot mentions)
            text = re.sub(r'<@\w+>', '', text).strip()
            
            if not text:
                await self._send_help_message(say)
                return
            
            # Check for special commands
            if text.lower() in ["help", "?", "commands"]:
                await self._send_help_message(say)
                return
            
            # Show typing indicator
            await self._send_typing_indicator(client, channel)
            
            # Check for CSV export request
            if await self._handle_export_request(text, user_id, say, client):
                return
            
            # Check for SQL query request
            if await self._handle_sql_request(text, user_id, say, client):
                return
            
            # Process the analytics query
            await self._process_analytics_query(text, user_id, say, client, message_ts)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await say(f"❌ Sorry, I encountered an error processing your request: {str(e)}")
    
    async def _process_analytics_query(self, question: str, user_id: str, 
                                     say, client: AsyncWebClient, message_ts: str):
        """
        Process an analytics query and send response.
        
        Args:
            question: User's question
            user_id: Slack user ID
            say: Slack say function
            client: Slack web client
            message_ts: Message timestamp
        """
        try:
            # Use smart classification instead of simple keyword matching
            query_type = sql_engine.classify_query(question)
            
            if query_type == "OFF_TOPIC":
                response = response_formatter.format_off_topic_response(question)
                await say(response)
                return
            
            # Process the analytics query
            query_result = sql_engine.process_query(question)
            
            # Handle off-topic classification from process_query as well
            if query_result.get("error") == "off_topic":
                await say(query_result.get("message", "I can only help with app analytics questions."))
                return
            
            # Format the response
            formatted_response = response_formatter.format_response(query_result, question)
            
            # Store in user session for follow-up requests
            self.session_manager.store_query_result(user_id, question, query_result)
            
            # Send the main response
            await self._send_formatted_response(say, formatted_response, question)
            
        except Exception as e:
            logger.error(f"Error processing analytics query: {e}", exc_info=True)
            error_response = response_formatter.format_error_response(str(e))
            await say(error_response)
    
    async def _send_formatted_response(self, say, formatted_response: Dict[str, Any], 
                                     question: str):
        """
        Send a formatted response with appropriate buttons and formatting.
        
        Args:
            say: Slack say function
            formatted_response: Formatted response data
            question: Original question
        """
        response_text = formatted_response["response_text"]
        response_type = formatted_response["response_type"]
        can_export_csv = formatted_response["can_export_csv"]
        
        # Create action buttons
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": response_text
                }
            }
        ]
        
        # Add action buttons if applicable
        if can_export_csv or formatted_response["sql_query"]:
            actions = {
                "type": "actions",
                "elements": []
            }
            
            if can_export_csv:
                actions["elements"].append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Export as CSV"
                    },
                    "action_id": "export_csv",
                    "style": "primary"
                })
            
            if formatted_response["sql_query"]:
                actions["elements"].append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 Show SQL"
                    },
                    "action_id": "show_sql"
                })
            
            # Add help button
            actions["elements"].append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "❓ Help"
                },
                "action_id": "help_button"
            })
            
            blocks.append(actions)
        
        await say(blocks=blocks)
    
    async def _handle_export_request(self, text: str, user_id: str, 
                                   say, client: AsyncWebClient) -> bool:
        """
        Handle CSV export requests.
        
        Args:
            text: User's message text
            user_id: Slack user ID
            say: Slack say function
            client: Slack web client
            
        Returns:
            True if this was an export request, False otherwise
        """
        export_patterns = [
            r"export.*csv", r"download.*csv", r"csv.*export",
            r"export.*data", r"download.*data", r"save.*csv"
        ]
        
        if any(re.search(pattern, text.lower()) for pattern in export_patterns):
            await self._handle_csv_export_request(user_id, say, client)
            return True
        
        return False
    
    async def _handle_sql_request(self, text: str, user_id: str, 
                                say, client: AsyncWebClient) -> bool:
        """
        Handle SQL query display requests.
        
        Args:
            text: User's message text
            user_id: Slack user ID
            say: Slack say function
            client: Slack web client
            
        Returns:
            True if this was a SQL request, False otherwise
        """
        sql_patterns = [
            r"show.*sql", r"sql.*query", r"see.*sql",
            r"what.*sql", r"sql.*used", r"query.*used"
        ]
        
        if any(re.search(pattern, text.lower()) for pattern in sql_patterns):
            await self._handle_sql_display_request(user_id, say, client)
            return True
        
        return False
    
    async def _handle_csv_export(self, body: Dict[str, Any], client: AsyncWebClient):
        """Handle CSV export button action."""
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        
        await self._handle_csv_export_request(user_id, None, client, channel_id)
    
    async def _handle_csv_export_request(self, user_id: str, say, 
                                       client: AsyncWebClient, channel_id: str = None):
        """
        Handle CSV export request.
        
        Args:
            user_id: Slack user ID
            say: Slack say function (optional)
            client: Slack web client
            channel_id: Channel ID for file upload
        """
        try:
            # Get the last query result from session
            last_result = self.session_manager.get_last_query_result(user_id)
            
            if not last_result:
                message = "❌ No recent query found to export. Please ask a question first!"
                if say:
                    await say(message)
                else:
                    await client.chat_postMessage(channel=channel_id, text=message)
                return
            
            # Generate CSV file
            csv_file_path, filename = await self.csv_handler.create_csv_file(
                last_result["result_data"],
                last_result["question"]
            )
            
            # Upload file to Slack
            await client.files_upload_v2(
                channel=channel_id,
                file=csv_file_path,
                filename=filename,
                title=f"Analytics Export: {last_result['question'][:50]}...",
                initial_comment="📊 Here's your data export!"
            )
            
            # Clean up temporary file
            os.unlink(csv_file_path)
            
            logger.info(f"CSV exported for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}", exc_info=True)
            error_message = f"❌ Failed to export CSV: {str(e)}"
            if say:
                await say(error_message)
            else:
                await client.chat_postMessage(channel=channel_id, text=error_message)
    
    async def _handle_show_sql(self, body: Dict[str, Any], client: AsyncWebClient):
        """Handle SQL query display button action."""
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        
        await self._handle_sql_display_request(user_id, None, client, channel_id)
    
    async def _handle_sql_display_request(self, user_id: str, say, 
                                        client: AsyncWebClient, channel_id: str = None):
        """
        Handle SQL query display request.
        
        Args:
            user_id: Slack user ID
            say: Slack say function (optional)
            client: Slack web client
            channel_id: Channel ID for message
        """
        try:
            # Get the last query result from session
            last_result = self.session_manager.get_last_query_result(user_id)
            
            if not last_result:
                message = "❌ No recent query found. Please ask a question first!"
                if say:
                    await say(message)
                else:
                    await client.chat_postMessage(channel=channel_id, text=message)
                return
            
            sql_query = last_result["sql_query"]
            question = last_result["question"]
            
            # Format SQL query for display
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔍 **SQL Query for:** _{question}_"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```sql\n{sql_query}\n```"
                    }
                }
            ]
            
            if say:
                await say(blocks=blocks)
            else:
                await client.chat_postMessage(channel=channel_id, blocks=blocks)
            
        except Exception as e:
            logger.error(f"Error displaying SQL: {e}", exc_info=True)
            error_message = f"❌ Failed to display SQL: {str(e)}"
            if say:
                await say(error_message)
            else:
                await client.chat_postMessage(channel=channel_id, text=error_message)
    
    async def _send_help_message(self, say):
        """Send help message with usage examples."""
        help_text = """
🤖 **Rounds Analytics Bot** - Your AI assistant for app portfolio insights!

**What I can help you with:**
• App performance metrics and analytics
• Revenue analysis across platforms and countries
• User acquisition and install data
• Comparative analysis and rankings

**Example questions:**
• "How many apps do we have?"
• "Which country generates the most revenue?"
• "Show me top iOS apps by popularity"
• "Compare Android vs iOS performance this month"
• "What's our total revenue from TikTok?"

**Additional features:**
• 📊 Export results as CSV files
• 🔍 View the SQL queries I generate
• 💡 Get smart interpretations of your data

**Commands:**
• Just mention me or send a direct message
• Use `/analytics [your question]` for quick queries
• Type "help" for this message

Ready to dive into your data? Ask me anything about your app portfolio! 🚀
"""
        
        await say(help_text)
    
    async def _send_typing_indicator(self, client: AsyncWebClient, channel: str):
        """Send typing indicator to show bot is processing."""
        try:
            await client.conversations_setTopic(
                channel=channel,
                topic="🤖 Analytics Bot is thinking..."
            )
        except SlackApiError:
            # If we can't set topic (e.g., in DMs), just continue
            pass
    
    async def start(self):
        """Start the Slack bot."""
        handler = AsyncSocketModeHandler(self.app, settings.slack_app_token)
        logger.info("Starting Rounds Analytics Bot...")
        await handler.start_async()


# Global bot instance
analytics_bot = RoundsAnalyticsBot() 