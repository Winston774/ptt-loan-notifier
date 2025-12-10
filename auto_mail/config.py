"""
自動站內信功能的獨立設定檔
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class AutoMailSettings(BaseSettings):
    """自動站內信設定"""
    
    # PTT 帳號設定
    PTT_USERNAME: str = ""
    PTT_PASSWORD: str = ""
    
    # AI 設定 (使用 Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # 發送限制
    DAILY_LIMIT: int = 30  # 每日發送上限
    MIN_DELAY_SECONDS: int = 180  # 最短延遲 3 分鐘
    MAX_DELAY_SECONDS: int = 300  # 最長延遲 5 分鐘
    
    # 資料庫設定 (使用獨立 SQLite)
    SQLITE_DB_PATH: str = "auto_mail/sent_mails.db"
    
    # 信件設定
    MAIL_SIGN_FILE: int = 0  # 簽名檔編號，0 = 不使用
    MAIL_BACKUP: bool = True  # 是否備份信件
    
    # 關鍵字 (與主系統相同)
    KEYWORDS: str = "信貸,個人信貸"
    
    @property
    def keywords_list(self) -> list[str]:
        """將關鍵字字串轉換為列表"""
        return [k.strip() for k in self.KEYWORDS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略其他環境變數


auto_mail_settings = AutoMailSettings()
