from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

from config import settings

# 建立資料庫引擎 (支援 psycopg3)
# 將 postgresql:// 轉換為 postgresql+psycopg:// 以使用 psycopg3 驅動
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserTier(str, enum.Enum):
    """用戶等級"""
    PREMIUM = "premium"
    STANDARD = "standard"


class Article(Base):
    """PTT 文章模型"""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(50), unique=True, index=True, nullable=False)  # PTT 文章 ID
    title = Column(String(255), nullable=False)  # 文章標題
    author = Column(String(50), nullable=False)  # 發文者
    content = Column(Text, nullable=True)  # 完整內容
    url = Column(String(255), nullable=False)  # 文章連結
    post_time = Column(DateTime, nullable=True)  # 發文時間
    created_at = Column(DateTime, default=datetime.utcnow)  # 抓取時間
    
    # 關聯
    notifications = relationship("Notification", back_populates="article")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:20]}...)>"


class User(Base):
    """用戶模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(String(50), unique=True, index=True, nullable=False)  # Telegram User ID
    tier = Column(SQLEnum(UserTier), default=UserTier.STANDARD, nullable=False)  # 會員等級
    is_active = Column(Boolean, default=True, nullable=False)  # 是否啟用通知
    created_at = Column(DateTime, default=datetime.utcnow)  # 註冊時間
    
    # 關聯
    notifications = relationship("Notification", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, tier={self.tier})>"


class Notification(Base):
    """通知記錄模型"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    sent_at = Column(DateTime, nullable=True)  # 發送時間 (NULL = 待發送)
    created_at = Column(DateTime, default=datetime.utcnow)  # 建立時間
    
    # 關聯
    user = relationship("User", back_populates="notifications")
    article = relationship("Article", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, sent={self.sent_at is not None})>"


def init_db():
    """初始化資料庫，建立所有表格並處理必要的遷移"""
    Base.metadata.create_all(bind=engine)
    
    # 執行手動遷移 (如果從舊版 LINE Bot 遷移)
    from sqlalchemy import text
    with engine.connect() as conn:
        # 檢查 users 表是否有 telegram_user_id 欄位
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='telegram_user_id'"
        ))
        if not result.fetchone():
            print("偵測到舊版資料庫結構，正在新增 telegram_user_id 欄位...")
            conn.execute(text("ALTER TABLE users ADD COLUMN telegram_user_id VARCHAR(50) UNIQUE"))
            conn.commit()
            print("telegram_user_id 欄位新增完成。")
            
        # 檢查是否存在 line_user_id 且具有 NOT NULL 限制
        result = conn.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='line_user_id'"
        ))
        row = result.fetchone()
        if row and row[0] == 'NO':
            print("正在移除 line_user_id 的 NOT NULL 限制...")
            conn.execute(text("ALTER TABLE users ALTER COLUMN line_user_id DROP NOT NULL"))
            conn.commit()
            print("限制移除完成代。")


def get_db():
    """取得資料庫 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
