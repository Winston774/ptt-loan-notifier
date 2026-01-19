import sys
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

# Mock config settings before importing module that uses them
sys.modules['config'] = MagicMock()
sys.modules['config'].settings.TELEGRAM_BOT_TOKEN = "mock_token"
sys.modules['config'].settings.TIMEZONE = "Asia/Taipei"

# Import the module to test
from notification import telegram_bot

async def test_telegram_notification():
    print("Testing Telegram Notification Module...")
    
    # Mock Bot
    mock_bot = MagicMock()
    mock_bot.send_message = MagicMock(return_value=asyncio.Future())
    mock_bot.send_message.return_value.set_result(True)
    
    with patch('notification.telegram_bot.get_bot', return_value=mock_bot):
        # Test 1: Single Message
        print("1. Testing push_message_to_user...")
        result = await telegram_bot.push_message_to_user("12345", "Test Message")
        assert result is True
        mock_bot.send_message.assert_called()
        print("   Pass")

        # Test 2: Article Notification
        print("2. Testing push_article_notification...")
        await telegram_bot.push_article_notification(
            "12345", 
            "Test Title", 
            "Test Author", 
            "http://test.url",
            datetime.now()
        )
        mock_bot.send_message.assert_called()
        print("   Pass")

        # Test 3: Batch Notification
        print("3. Testing push_batch_notification...")
        articles = [
            {"title": "Title 1", "url": "http://url1"},
            {"title": "Title 2", "url": "http://url2"}
        ]
        await telegram_bot.push_batch_notification("12345", articles)
        mock_bot.send_message.assert_called()
        print("   Pass")

    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(test_telegram_notification())
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
