from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import pytz

from .models import Article, User, Notification, UserTier
from config import settings


# ==================== Article CRUD ====================

def get_article_by_ptt_id(db: Session, article_id: str) -> Optional[Article]:
    """根據 PTT 文章 ID 查詢文章"""
    return db.query(Article).filter(Article.article_id == article_id).first()


def create_article(db: Session, article_id: str, title: str, author: str, 
                   content: str, url: str, post_time: Optional[datetime] = None) -> Article:
    """建立新文章"""
    db_article = Article(
        article_id=article_id,
        title=title,
        author=author,
        content=content,
        url=url,
        post_time=post_time
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


def get_articles_to_delete(db: Session) -> List[Article]:
    """取得超過保留期限的文章"""
    tz = pytz.timezone(settings.TIMEZONE)
    cutoff_date = datetime.now(tz) - timedelta(days=settings.RETENTION_DAYS)
    return db.query(Article).filter(Article.created_at < cutoff_date).all()


def delete_old_articles(db: Session) -> int:
    """刪除超過保留期限的文章，回傳刪除數量"""
    tz = pytz.timezone(settings.TIMEZONE)
    cutoff_date = datetime.now(tz) - timedelta(days=settings.RETENTION_DAYS)
    
    # 先刪除相關的通知記錄
    old_articles = db.query(Article).filter(Article.created_at < cutoff_date).all()
    article_ids = [a.id for a in old_articles]
    
    if article_ids:
        db.query(Notification).filter(Notification.article_id.in_(article_ids)).delete(synchronize_session=False)
        count = db.query(Article).filter(Article.id.in_(article_ids)).delete(synchronize_session=False)
        db.commit()
        return count
    return 0


# ==================== User CRUD ====================

def get_user_by_line_id(db: Session, line_user_id: str) -> Optional[User]:
    """根據 LINE User ID 查詢用戶"""
    return db.query(User).filter(User.line_user_id == line_user_id).first()


def create_user(db: Session, line_user_id: str, tier: UserTier = UserTier.STANDARD) -> User:
    """建立新用戶"""
    db_user = User(
        line_user_id=line_user_id,
        tier=tier,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_or_create_user(db: Session, line_user_id: str, tier: UserTier = UserTier.STANDARD) -> User:
    """取得用戶，若不存在則建立"""
    user = get_user_by_line_id(db, line_user_id)
    if not user:
        user = create_user(db, line_user_id, tier)
    return user


def get_active_users_by_tier(db: Session, tier: UserTier) -> List[User]:
    """取得指定等級的所有啟用用戶"""
    return db.query(User).filter(
        and_(User.tier == tier, User.is_active == True)
    ).all()


def get_all_active_users(db: Session) -> List[User]:
    """取得所有啟用的用戶"""
    return db.query(User).filter(User.is_active == True).all()


def update_user_tier(db: Session, line_user_id: str, tier: UserTier) -> Optional[User]:
    """更新用戶等級"""
    user = get_user_by_line_id(db, line_user_id)
    if user:
        user.tier = tier
        db.commit()
        db.refresh(user)
    return user


# ==================== Notification CRUD ====================

def create_notification(db: Session, user_id: int, article_id: int) -> Notification:
    """建立新通知記錄（待發送狀態）"""
    db_notification = Notification(
        user_id=user_id,
        article_id=article_id,
        sent_at=None
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_pending_notifications_for_user(db: Session, user_id: int) -> List[Notification]:
    """取得用戶的待發送通知"""
    return db.query(Notification).filter(
        and_(Notification.user_id == user_id, Notification.sent_at == None)
    ).all()


def get_pending_notifications_for_standard_users(db: Session) -> List[Notification]:
    """取得所有 Standard 用戶的待發送通知"""
    return db.query(Notification).join(User).filter(
        and_(
            Notification.sent_at == None,
            User.tier == UserTier.STANDARD,
            User.is_active == True
        )
    ).all()


def mark_notification_sent(db: Session, notification_id: int) -> None:
    """標記通知為已發送"""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification:
        notification.sent_at = datetime.utcnow()
        db.commit()


def mark_notifications_sent(db: Session, notification_ids: List[int]) -> None:
    """批次標記通知為已發送"""
    db.query(Notification).filter(Notification.id.in_(notification_ids)).update(
        {"sent_at": datetime.utcnow()},
        synchronize_session=False
    )
    db.commit()


def has_notification_for_article(db: Session, user_id: int, article_id: int) -> bool:
    """檢查用戶是否已有該文章的通知記錄"""
    return db.query(Notification).filter(
        and_(Notification.user_id == user_id, Notification.article_id == article_id)
    ).first() is not None
