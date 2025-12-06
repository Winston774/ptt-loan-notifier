import logging
from typing import List, Optional
from datetime import datetime

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer
)
from linebot.v3.exceptions import InvalidSignatureError

from config import settings

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LINE Bot 設定
configuration = Configuration(access_token=settings.LINE_CHANNEL_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


def create_article_flex_message(title: str, author: str, url: str, post_time: Optional[datetime] = None) -> dict:
    """
    建立文章通知的 Flex Message
    
    Args:
        title: 文章標題
        author: 發文者
        url: 文章連結
        post_time: 發文時間
        
    Returns:
        Flex Message JSON
    """
    time_str = post_time.strftime("%Y/%m/%d %H:%M") if post_time else "未知時間"
    
    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📢 PTT 信貸通知",
                    "weight": "bold",
                    "color": "#1DB446",
                    "size": "sm"
                }
            ],
            "paddingBottom": "8px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "md",
                    "wrap": True,
                    "maxLines": 3
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "作者",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": author,
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 4
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "時間",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": time_str,
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 4
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "查看文章",
                        "uri": url
                    },
                    "color": "#1DB446"
                }
            ],
            "flex": 0
        }
    }


def create_batch_flex_message(articles: List[dict]) -> dict:
    """
    建立批次通知的 Flex Message (用於 Standard 用戶)
    
    Args:
        articles: 文章列表，每個元素包含 title, author, url, post_time
        
    Returns:
        Flex Message JSON (carousel)
    """
    bubbles = []
    for article in articles[:10]:  # 最多 10 篇
        bubble = create_article_flex_message(
            title=article.get('title', ''),
            author=article.get('author', ''),
            url=article.get('url', ''),
            post_time=article.get('post_time')
        )
        bubbles.append(bubble)
    
    return {
        "type": "carousel",
        "contents": bubbles
    }


def push_message_to_user(user_id: str, message: str) -> bool:
    """
    發送文字訊息給用戶
    
    Args:
        user_id: LINE User ID
        message: 訊息內容
        
    Returns:
        是否發送成功
    """
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
            )
        logger.info(f"成功發送訊息給 {user_id}")
        return True
    except Exception as e:
        logger.error(f"發送訊息失敗: {e}")
        return False


def push_article_notification(user_id: str, title: str, author: str, url: str, 
                              post_time: Optional[datetime] = None) -> bool:
    """
    發送單篇文章通知給用戶 (用於 Premium 用戶即時通知)
    
    Args:
        user_id: LINE User ID
        title: 文章標題
        author: 發文者
        url: 文章連結
        post_time: 發文時間
        
    Returns:
        是否發送成功
    """
    try:
        flex_content = create_article_flex_message(title, author, url, post_time)
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[
                        FlexMessage(
                            alt_text=f"📢 PTT 信貸通知: {title}",
                            contents=FlexContainer.from_dict(flex_content)
                        )
                    ]
                )
            )
        logger.info(f"成功發送文章通知給 {user_id}: {title[:20]}...")
        return True
    except Exception as e:
        logger.error(f"發送文章通知失敗: {e}")
        return False


def push_batch_notification(user_id: str, articles: List[dict]) -> bool:
    """
    發送批次文章通知給用戶 (用於 Standard 用戶每小時通知)
    
    Args:
        user_id: LINE User ID
        articles: 文章列表
        
    Returns:
        是否發送成功
    """
    if not articles:
        return True
    
    try:
        if len(articles) == 1:
            # 只有一篇，使用單篇格式
            article = articles[0]
            return push_article_notification(
                user_id,
                article.get('title', ''),
                article.get('author', ''),
                article.get('url', ''),
                article.get('post_time')
            )
        
        # 多篇使用 carousel
        flex_content = create_batch_flex_message(articles)
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[
                        FlexMessage(
                            alt_text=f"📢 PTT 信貸通知 ({len(articles)} 篇新文章)",
                            contents=FlexContainer.from_dict(flex_content)
                        )
                    ]
                )
            )
        logger.info(f"成功發送批次通知給 {user_id}: {len(articles)} 篇文章")
        return True
    except Exception as e:
        logger.error(f"發送批次通知失敗: {e}")
        return False
