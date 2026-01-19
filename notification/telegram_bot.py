import logging
import asyncio
from typing import List, Optional
from datetime import datetime
import telegram
from telegram.constants import ParseMode

from config import settings

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bot():
    return telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)

def format_article_message(title: str, author: str, url: str, post_time: Optional[datetime] = None) -> str:
    """
    建立文章通知的文字訊息
    """
    import pytz
    
    if post_time:
        tz = pytz.timezone(settings.TIMEZONE)
        if post_time.tzinfo is None:
            post_time = pytz.utc.localize(post_time).astimezone(tz)
        else:
            post_time = post_time.astimezone(tz)
        time_str = post_time.strftime("%Y/%m/%d %H:%M")
    else:
        time_str = "未知時間"
        
    message = (
        f"📢 <b>PTT 信貸通知</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"👤 作者: {author}\n"
        f"🕒 時間: {time_str}\n"
        f"🔗 <a href='{url}'>查看文章</a>"
    )
    return message

async def push_message_to_user(user_id: str, message: str) -> bool:
    """
    發送文字訊息給用戶
    """
    try:
        bot = get_bot()
        await bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.HTML)
        logger.info(f"成功發送訊息給 {user_id}")
        return True
    except Exception as e:
        logger.error(f"發送訊息失敗: {e}")
        return False

async def push_article_notification(user_id: str, title: str, author: str, url: str, 
                                  post_time: Optional[datetime] = None) -> bool:
    """
    發送單篇文章通知給用戶
    """
    try:
        message = format_article_message(title, author, url, post_time)
        bot = get_bot()
        await bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.HTML)
        logger.info(f"成功發送文章通知給 {user_id}: {title[:20]}...")
        return True
    except Exception as e:
        logger.error(f"發送文章通知失敗: {e}")
        return False

async def push_batch_notification(user_id: str, articles: List[dict]) -> bool:
    """
    發送批次文章通知給用戶
    """
    if not articles:
        return True
    
    try:
        bot = get_bot()
        
        # Telegram 訊息長度限制，可能需要分批或簡化
        # 這裡簡單地將多篇合併，每篇顯示精簡資訊
        messages = []
        current_chunk = "📢 <b>PTT 信貸通知 (彙整)</b>\n\n"
        
        for article in articles:
            title = article.get('title', '')
            url = article.get('url', '')
            item_text = f"🔹 <a href='{url}'>{title}</a>\n"
            
            if len(current_chunk) + len(item_text) > 4000:
                messages.append(current_chunk)
                current_chunk = item_text
            else:
                current_chunk += item_text
                
        if current_chunk:
            messages.append(current_chunk)
            
        for msg in messages:
            await bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.HTML)
            
        logger.info(f"成功發送批次通知給 {user_id}: {len(articles)} 篇文章")
        return True
    except Exception as e:
        logger.error(f"發送批次通知失敗: {e}")
        return False
