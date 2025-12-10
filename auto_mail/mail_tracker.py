"""
發送記錄追蹤模組
使用獨立 SQLite 資料庫
"""
import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, List, Tuple
from pathlib import Path

from .config import auto_mail_settings

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MailTracker:
    """站內信發送記錄追蹤器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化追蹤器
        
        Args:
            db_path: 資料庫路徑，預設使用設定中的路徑
        """
        self.db_path = db_path or auto_mail_settings.SQLITE_DB_PATH
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """確保資料庫和表格存在"""
        # 確保目錄存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 建立發送記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_mails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ptt_id TEXT NOT NULL,
                article_id TEXT NOT NULL,
                article_title TEXT,
                mail_title TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 1
            )
        ''')
        
        # 建立索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ptt_id ON sent_mails(ptt_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sent_at ON sent_mails(sent_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_article_id ON sent_mails(article_id)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"資料庫初始化完成: {self.db_path}")
    
    def has_sent_to(self, ptt_id: str) -> bool:
        """
        檢查是否已發送過信件給指定用戶
        
        Args:
            ptt_id: PTT 用戶 ID
            
        Returns:
            是否已發送過
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT COUNT(*) FROM sent_mails WHERE ptt_id = ? AND success = 1',
            (ptt_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def has_processed_article(self, article_id: str) -> bool:
        """
        檢查是否已處理過指定文章
        
        Args:
            article_id: 文章 ID
            
        Returns:
            是否已處理過
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT COUNT(*) FROM sent_mails WHERE article_id = ?',
            (article_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def record_sent(
        self,
        ptt_id: str,
        article_id: str,
        article_title: str = "",
        mail_title: str = "",
        success: bool = True
    ):
        """
        記錄發送紀錄
        
        Args:
            ptt_id: 收件人 PTT ID
            article_id: 來源文章 ID
            article_title: 文章標題
            mail_title: 信件標題
            success: 是否成功發送
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sent_mails (ptt_id, article_id, article_title, mail_title, success)
            VALUES (?, ?, ?, ?, ?)
        ''', (ptt_id, article_id, article_title, mail_title, 1 if success else 0))
        
        conn.commit()
        conn.close()
        
        status = "成功" if success else "失敗"
        logger.info(f"記錄發送紀錄: {ptt_id} ({status})")
    
    def get_today_count(self) -> int:
        """
        取得今日已發送數量
        
        Returns:
            今日已發送數量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM sent_mails 
            WHERE DATE(sent_at) = ? AND success = 1
        ''', (today,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def can_send_today(self) -> bool:
        """
        檢查今日是否還能發送
        
        Returns:
            是否還能發送
        """
        today_count = self.get_today_count()
        can_send = today_count < auto_mail_settings.DAILY_LIMIT
        
        if not can_send:
            logger.warning(f"已達今日發送上限 ({auto_mail_settings.DAILY_LIMIT} 封)")
        
        return can_send
    
    def get_remaining_quota(self) -> int:
        """
        取得今日剩餘配額
        
        Returns:
            剩餘配額
        """
        return max(0, auto_mail_settings.DAILY_LIMIT - self.get_today_count())
    
    def get_recent_records(self, limit: int = 10) -> List[Tuple]:
        """
        取得最近的發送記錄
        
        Args:
            limit: 回傳筆數
            
        Returns:
            發送記錄列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ptt_id, article_title, mail_title, sent_at, success
            FROM sent_mails
            ORDER BY sent_at DESC
            LIMIT ?
        ''', (limit,))
        
        records = cursor.fetchall()
        conn.close()
        
        return records


# 全域實例
mail_tracker = MailTracker()
