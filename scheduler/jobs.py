import logging
from datetime import datetime
from typing import List

import pytz
from sqlalchemy.orm import Session

from config import settings
from database.models import SessionLocal, UserTier
from database import crud
from crawler.ptt_scraper import crawl_new_articles
from notification.line_bot import push_article_notification, push_batch_notification

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_within_schedule_hours() -> bool:
    """檢查目前時間是否在排程時間內 (07:00-20:00)"""
    tz = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(tz)
    return settings.SCHEDULE_START_HOUR <= now.hour < settings.SCHEDULE_END_HOUR


def crawl_and_notify():
    """
    主要排程任務：抓取新文章並通知用戶
    
    流程：
    1. 檢查是否在排程時間內
    2. 抓取 PTT 借貸版新文章
    3. 過濾符合關鍵字的文章
    4. 儲存新文章到資料庫
    5. 為 Premium 用戶即時通知
    6. 為 Standard 用戶建立待發送通知
    """
    # 檢查排程時間
    if not is_within_schedule_hours():
        logger.info("目前不在排程時間內，跳過抓取")
        return
    
    logger.info("開始抓取 PTT 借貸版...")
    
    db = SessionLocal()
    try:
        # 抓取新文章
        articles = crawl_new_articles()
        logger.info(f"找到 {len(articles)} 篇符合關鍵字的文章")
        
        if not articles:
            return
        
        # 取得所有啟用的用戶
        all_users = crud.get_all_active_users(db)
        premium_users = [u for u in all_users if u.tier == UserTier.PREMIUM]
        standard_users = [u for u in all_users if u.tier == UserTier.STANDARD]
        
        for article_data in articles:
            article_id = article_data.get('article_id')
            if not article_id:
                continue
            
            # 檢查是否已存在
            existing = crud.get_article_by_ptt_id(db, article_id)
            if existing:
                logger.debug(f"文章已存在: {article_id}")
                continue
            
            # 儲存新文章
            db_article = crud.create_article(
                db=db,
                article_id=article_id,
                title=article_data.get('title', ''),
                author=article_data.get('author', ''),
                content=article_data.get('content', ''),
                url=article_data.get('url', ''),
                post_time=article_data.get('post_time')
            )
            logger.info(f"新增文章: {db_article.title[:30]}...")
            
            # Premium 用戶即時通知
            for user in premium_users:
                success = push_article_notification(
                    user_id=user.line_user_id,
                    title=db_article.title,
                    author=db_article.author,
                    url=db_article.url,
                    post_time=db_article.post_time
                )
                if success:
                    # 建立已發送的通知記錄
                    notification = crud.create_notification(db, user.id, db_article.id)
                    crud.mark_notification_sent(db, notification.id)
            
            # Standard 用戶建立待發送通知
            for user in standard_users:
                if not crud.has_notification_for_article(db, user.id, db_article.id):
                    crud.create_notification(db, user.id, db_article.id)
        
        logger.info("抓取任務完成")
        
    except Exception as e:
        logger.error(f"抓取任務發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()


def send_hourly_notifications():
    """
    每小時執行：發送 Standard 用戶的累積通知
    """
    logger.info("開始發送 Standard 用戶的累積通知...")
    
    db = SessionLocal()
    try:
        # 取得所有 Standard 用戶
        standard_users = crud.get_active_users_by_tier(db, UserTier.STANDARD)
        
        for user in standard_users:
            # 取得待發送通知
            pending = crud.get_pending_notifications_for_user(db, user.id)
            
            if not pending:
                continue
            
            # 準備文章資料
            articles = []
            notification_ids = []
            for notification in pending:
                article = notification.article
                articles.append({
                    'title': article.title,
                    'author': article.author,
                    'url': article.url,
                    'post_time': article.post_time
                })
                notification_ids.append(notification.id)
            
            # 發送批次通知
            success = push_batch_notification(user.line_user_id, articles)
            
            if success:
                # 標記為已發送
                crud.mark_notifications_sent(db, notification_ids)
                logger.info(f"已發送 {len(articles)} 篇文章通知給用戶 {user.id}")
        
        logger.info("累積通知發送完成")
        
    except Exception as e:
        logger.error(f"發送累積通知發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_old_articles():
    """
    每日執行：清理超過保留期限的舊文章
    """
    logger.info(f"開始清理超過 {settings.RETENTION_DAYS} 天的舊文章...")
    
    db = SessionLocal()
    try:
        count = crud.delete_old_articles(db)
        logger.info(f"已刪除 {count} 篇舊文章")
    except Exception as e:
        logger.error(f"清理舊文章發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()
