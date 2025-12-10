import logging
from contextlib import asynccontextmanager

import pytz
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from config import settings
from database.models import init_db, get_db, UserTier
from database import crud
from scheduler.jobs import crawl_and_notify, send_hourly_notifications, cleanup_old_articles

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# APScheduler 實例
scheduler = AsyncIOScheduler(timezone=pytz.timezone(settings.TIMEZONE))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時
    logger.info("正在初始化資料庫...")
    init_db()
    
    logger.info("正在設定排程任務...")
    
    # 排程 1: 每分鐘抓取 (07:00-20:00)
    scheduler.add_job(
        crawl_and_notify,
        IntervalTrigger(minutes=settings.SCHEDULE_INTERVAL_MINUTES),
        id='crawl_job',
        name='PTT 爬蟲任務',
        replace_existing=True
    )
    
    # 排程 2: 每小時整點發送 Standard 用戶通知
    scheduler.add_job(
        send_hourly_notifications,
        CronTrigger(minute=0),  # 每小時整點
        id='hourly_notification_job',
        name='Standard 用戶通知任務',
        replace_existing=True
    )
    
    # 排程 3: 每日凌晨 3 點清理舊文章
    scheduler.add_job(
        cleanup_old_articles,
        CronTrigger(hour=3, minute=0),
        id='cleanup_job',
        name='清理舊文章任務',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("排程器已啟動")
    logger.info(f"排程時間: {settings.SCHEDULE_START_HOUR}:00 - {settings.SCHEDULE_END_HOUR}:00")
    logger.info(f"抓取間隔: 每 {settings.SCHEDULE_INTERVAL_MINUTES} 分鐘")
    
    yield
    
    # 關閉時
    logger.info("正在關閉排程器...")
    scheduler.shutdown()


# FastAPI 應用程式
app = FastAPI(
    title="PTT 借貸版爬蟲 API",
    description="自動監控 PTT 借貸版並透過 LINE Bot 通知",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """首頁"""
    return {
        "name": "PTT 借貸版爬蟲",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點 (給 Zeabur 使用)"""
    return {"status": "healthy"}


@app.post("/trigger")
async def trigger_crawl():
    """手動觸發爬蟲 (測試用)"""
    try:
        crawl_and_notify()
        return {"status": "success", "message": "爬蟲任務已執行"}
    except Exception as e:
        logger.error(f"手動觸發失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger/hourly")
async def trigger_hourly_notification():
    """手動觸發 Standard 用戶通知 (測試用)"""
    try:
        send_hourly_notifications()
        return {"status": "success", "message": "通知任務已執行"}
    except Exception as e:
        logger.error(f"手動觸發失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs():
    """列出所有排程任務"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None
        })
    return {"jobs": jobs}


# ==================== LINE Webhook ====================

from fastapi import Request, Header
from notification.line_bot import handler

@app.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """LINE Bot Webhook - 接收用戶訊息並自動註冊"""
    body = await request.body()
    body_text = body.decode('utf-8')
    
    try:
        # 解析事件
        import json
        events = json.loads(body_text).get('events', [])
        
        for event in events:
            # 取得用戶 ID
            user_id = event.get('source', {}).get('userId')
            if user_id:
                # 自動註冊用戶（如果不存在）
                user = crud.get_or_create_user(db, user_id, UserTier.STANDARD)
                logger.info(f"用戶已註冊/確認: {user_id}, 等級: {user.tier.value}")
                
                # 如果是訊息事件，回覆歡迎訊息
                event_type = event.get('type')
                if event_type == 'follow':
                    # 新加入好友
                    from notification.line_bot import push_message_to_user
                    push_message_to_user(
                        user_id,
                        "🎉 歡迎加入 PTT 信貸通知！\n\n"
                        "您已被設為 Standard 會員，將於每小時收到通知。\n"
                        f"您的 User ID: {user_id}"
                    )
                elif event_type == 'message':
                    # 用戶發送訊息
                    from notification.line_bot import push_message_to_user
                    push_message_to_user(
                        user_id,
                        f"✅ 您已註冊成功！\n\n"
                        f"會員等級: {user.tier.value.upper()}\n"
                        f"User ID: {user_id}\n\n"
                        "當有信貸相關文章時，您會收到通知！"
                    )
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook 處理錯誤: {e}")
        return {"status": "error", "message": str(e)}


# ==================== 用戶管理 API ====================

@app.post("/users")
async def add_user(
    line_user_id: str = Query(..., description="LINE User ID"),
    tier: str = Query("standard", description="用戶等級: premium 或 standard"),
    db: Session = Depends(get_db)
):
    """新增用戶"""
    try:
        user_tier = UserTier.PREMIUM if tier.lower() == "premium" else UserTier.STANDARD
        user = crud.get_or_create_user(db, line_user_id, user_tier)
        return {
            "status": "success",
            "user": {
                "id": user.id,
                "line_user_id": user.line_user_id,
                "tier": user.tier.value,
                "is_active": user.is_active
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/{line_user_id}/tier")
async def update_user_tier(
    line_user_id: str,
    tier: str = Query(..., description="用戶等級: premium 或 standard"),
    db: Session = Depends(get_db)
):
    """更新用戶等級"""
    user_tier = UserTier.PREMIUM if tier.lower() == "premium" else UserTier.STANDARD
    user = crud.update_user_tier(db, line_user_id, user_tier)
    
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "line_user_id": user.line_user_id,
            "tier": user.tier.value
        }
    }


@app.get("/users")
async def list_users(db: Session = Depends(get_db)):
    """列出所有用戶"""
    users = crud.get_all_active_users(db)
    return {
        "users": [
            {
                "id": u.id,
                "line_user_id": u.line_user_id,
                "tier": u.tier.value,
                "is_active": u.is_active
            }
            for u in users
        ]
    }


# ==================== 統計 API ====================

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """取得系統統計"""
    from database.models import Article, User, Notification
    
    total_articles = db.query(Article).count()
    total_users = db.query(User).filter(User.is_active == True).count()
    pending_notifications = db.query(Notification).filter(Notification.sent_at == None).count()
    
    return {
        "total_articles": total_articles,
        "total_users": total_users,
        "pending_notifications": pending_notifications
    }


# ==================== 測試 API ====================

@app.post("/test-notification")
async def test_notification(
    line_user_id: str = Query(..., description="LINE User ID"),
    db: Session = Depends(get_db)
):
    """測試 LINE 通知功能"""
    from notification.line_bot import push_message_to_user
    
    try:
        success = push_message_to_user(
            line_user_id,
            "🎉 測試成功！\n\n你的 PTT 借貸版通知系統已正確設定。\n\n當有新的信貸相關文章時，你會收到通知！"
        )
        if success:
            return {"status": "success", "message": "測試通知已發送"}
        else:
            return {"status": "error", "message": "通知發送失敗，請檢查 LINE_CHANNEL_TOKEN 設定"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"發送失敗: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
