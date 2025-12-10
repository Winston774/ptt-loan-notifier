"""
PTT 登入與站內信發送模組
使用 PyPtt 套件實現
"""
import logging
from typing import Optional
import PyPtt

from .config import auto_mail_settings

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PTTMailer:
    """PTT 站內信發送器"""
    
    def __init__(self):
        self.ptt_bot: Optional[PyPtt.API] = None
        self.is_logged_in = False
    
    def login(self) -> bool:
        """
        登入 PTT
        
        Returns:
            登入是否成功
        """
        if self.is_logged_in:
            logger.info("已經登入 PTT")
            return True
        
        username = auto_mail_settings.PTT_USERNAME
        password = auto_mail_settings.PTT_PASSWORD
        
        if not username or not password:
            logger.error("PTT 帳號或密碼未設定")
            return False
        
        try:
            logger.info(f"正在登入 PTT，帳號: {username}")
            self.ptt_bot = PyPtt.API()
            self.ptt_bot.login(
                ptt_id=username,
                ptt_pw=password,
                kick_other_session=False  # 不踢掉其他登入
            )
            self.is_logged_in = True
            logger.info("PTT 登入成功")
            return True
        except PyPtt.exceptions.LoginError as e:
            logger.error(f"PTT 登入失敗: {e}")
            return False
        except PyPtt.exceptions.WrongIDorPassword:
            logger.error("PTT 帳號或密碼錯誤")
            return False
        except Exception as e:
            logger.error(f"PTT 登入時發生未知錯誤: {e}")
            return False
    
    def send_mail(self, ptt_id: str, title: str, content: str) -> bool:
        """
        發送站內信
        
        Args:
            ptt_id: 收件人 PTT ID
            title: 信件標題
            content: 信件內容
            
        Returns:
            發送是否成功
        """
        if not self.is_logged_in or self.ptt_bot is None:
            logger.error("尚未登入 PTT，無法發送信件")
            return False
        
        try:
            logger.info(f"正在發送站內信給 {ptt_id}，標題: {title}")
            self.ptt_bot.mail(
                ptt_id=ptt_id,
                title=title,
                content=content,
                sign_file=auto_mail_settings.MAIL_SIGN_FILE,
                backup=auto_mail_settings.MAIL_BACKUP
            )
            logger.info(f"成功發送站內信給 {ptt_id}")
            return True
        except PyPtt.exceptions.NoSuchUser:
            logger.error(f"使用者 {ptt_id} 不存在")
            return False
        except PyPtt.exceptions.UnregisteredUser:
            logger.error(f"使用者 {ptt_id} 尚未完成註冊")
            return False
        except Exception as e:
            logger.error(f"發送站內信時發生錯誤: {e}")
            return False
    
    def logout(self):
        """登出 PTT"""
        if self.ptt_bot is not None and self.is_logged_in:
            try:
                self.ptt_bot.logout()
                logger.info("已登出 PTT")
            except Exception as e:
                logger.error(f"登出 PTT 時發生錯誤: {e}")
            finally:
                self.is_logged_in = False
                self.ptt_bot = None
    
    def __enter__(self):
        """Context manager 進入"""
        self.login()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 離開"""
        self.logout()
        return False


# 便捷函數
def send_ptt_mail(ptt_id: str, title: str, content: str) -> bool:
    """
    便捷函數：發送 PTT 站內信
    
    會自動處理登入和登出
    """
    with PTTMailer() as mailer:
        if mailer.is_logged_in:
            return mailer.send_mail(ptt_id, title, content)
    return False
