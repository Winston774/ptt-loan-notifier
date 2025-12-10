"""
PTT 自動站內信模組 (獨立測試版)

此模組用於自動發送站內信給發布信貸相關文章的 PTT 用戶。
功能包含：
- PTT 登入與站內信發送
- AI 信件內容生成 (使用 Gemini)
- 發送記錄追蹤
- 頻率限制控制
"""

from .config import auto_mail_settings
from .ptt_mailer import PTTMailer
from .content_generator import ContentGenerator
from .mail_tracker import MailTracker
from .auto_mail_service import AutoMailService

__all__ = [
    'auto_mail_settings',
    'PTTMailer',
    'ContentGenerator', 
    'MailTracker',
    'AutoMailService',
]
