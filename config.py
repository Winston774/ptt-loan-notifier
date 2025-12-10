from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """應用程式設定，從環境變數讀取"""
    
    # 資料庫設定
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/ptt_crawler"
    
    # LINE Bot 設定
    LINE_CHANNEL_TOKEN: str = ""
    LINE_CHANNEL_SECRET: str = ""
    
    # PTT 設定
    PTT_BOARD_URL: str = "https://www.ptt.cc/bbs/Loan/index.html"
    KEYWORDS: str = "信貸,個人信貸"
    
    # 排程設定 (台北時區)
    SCHEDULE_START_HOUR: int = 7
    SCHEDULE_END_HOUR: int = 20
    SCHEDULE_INTERVAL_MINUTES: int = 1
    
    # 資料保留天數
    RETENTION_DAYS: int = 180
    
    # 時區
    TIMEZONE: str = "Asia/Taipei"
    
    @property
    def keywords_list(self) -> List[str]:
        """將關鍵字字串轉換為列表"""
        return [k.strip() for k in self.KEYWORDS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略其他環境變數 (如 auto_mail 的設定)


settings = Settings()
