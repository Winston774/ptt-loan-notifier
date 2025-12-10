"""
自動站內信服務整合層
整合爬蟲、AI 生成、發送功能
"""
import logging
import random
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime

from .config import auto_mail_settings
from .ptt_mailer import PTTMailer
from .content_generator import ContentGenerator
from .mail_tracker import MailTracker

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoMailService:
    """自動站內信服務"""
    
    def __init__(self):
        self.mailer = PTTMailer()
        self.generator = ContentGenerator()
        self.tracker = MailTracker()
        self._pending_mails: List[Dict] = []
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
    
    def check_article_keywords(self, article: Dict[str, Any]) -> bool:
        """
        檢查文章是否包含關鍵字
        
        Args:
            article: 文章資料
            
        Returns:
            是否包含關鍵字
        """
        keywords = auto_mail_settings.keywords_list
        title = article.get('title', '')
        content = article.get('content', '')
        
        text = f"{title} {content}".lower()
        
        for keyword in keywords:
            if keyword.lower() in text:
                logger.info(f"文章 '{title}' 包含關鍵字 '{keyword}'")
                return True
        
        return False
    
    def process_article(self, article: Dict[str, Any], immediate: bool = False) -> bool:
        """
        處理單篇文章
        
        Args:
            article: 文章資料字典，需包含：
                - article_id: 文章 ID
                - title: 標題
                - author: 作者
                - content: 內容
            immediate: 是否立即發送（不等待延遲）
            
        Returns:
            是否成功處理（加入佇列或發送）
        """
        article_id = article.get('article_id', '')
        author = article.get('author', '')
        title = article.get('title', '')
        content = article.get('content', '')
        
        # 驗證必要欄位
        if not all([article_id, author, title]):
            logger.error(f"文章資料不完整: {article}")
            return False
        
        # 檢查是否已處理過此文章
        if self.tracker.has_processed_article(article_id):
            logger.info(f"文章 '{title}' 已處理過，跳過")
            return False
        
        # 檢查是否已發送給此作者
        if self.tracker.has_sent_to(author):
            logger.info(f"已發送過信件給 {author}，跳過")
            return False
        
        # 檢查今日額度
        if not self.tracker.can_send_today():
            logger.warning("已達今日發送上限")
            return False
        
        # 生成信件內容
        mail_title, mail_content = self.generator.generate_mail_content(
            article_title=title,
            article_content=content,
            author=author
        )
        
        if not mail_title or not mail_content:
            logger.error(f"無法生成信件內容，文章: {title}")
            return False
        
        # 準備發送資料
        mail_data = {
            'ptt_id': author,
            'article_id': article_id,
            'article_title': title,
            'mail_title': mail_title,
            'mail_content': mail_content
        }
        
        if immediate:
            # 立即發送
            return self._send_mail(mail_data)
        else:
            # 加入待發送佇列，延遲發送
            self._schedule_mail(mail_data)
            return True
    
    def _schedule_mail(self, mail_data: Dict[str, Any]):
        """
        排程發送信件（3-5分鐘延遲）
        
        Args:
            mail_data: 信件資料
        """
        delay = random.randint(
            auto_mail_settings.MIN_DELAY_SECONDS,
            auto_mail_settings.MAX_DELAY_SECONDS
        )
        
        logger.info(f"排程發送信件給 {mail_data['ptt_id']}，延遲 {delay} 秒")
        
        def delayed_send():
            time.sleep(delay)
            self._send_mail(mail_data)
        
        thread = threading.Thread(target=delayed_send, daemon=True)
        thread.start()
    
    def _send_mail(self, mail_data: Dict[str, Any]) -> bool:
        """
        發送信件
        
        Args:
            mail_data: 信件資料
            
        Returns:
            是否成功
        """
        ptt_id = mail_data['ptt_id']
        mail_title = mail_data['mail_title']
        mail_content = mail_data['mail_content']
        article_id = mail_data['article_id']
        article_title = mail_data['article_title']
        
        try:
            # 登入 PTT
            if not self.mailer.login():
                logger.error("PTT 登入失敗，無法發送信件")
                self.tracker.record_sent(
                    ptt_id=ptt_id,
                    article_id=article_id,
                    article_title=article_title,
                    mail_title=mail_title,
                    success=False
                )
                return False
            
            # 發送信件
            success = self.mailer.send_mail(ptt_id, mail_title, mail_content)
            
            # 記錄結果
            self.tracker.record_sent(
                ptt_id=ptt_id,
                article_id=article_id,
                article_title=article_title,
                mail_title=mail_title,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(f"發送信件時發生錯誤: {e}")
            self.tracker.record_sent(
                ptt_id=ptt_id,
                article_id=article_id,
                article_title=article_title,
                mail_title=mail_title,
                success=False
            )
            return False
        finally:
            # 登出
            self.mailer.logout()
    
    def process_articles_batch(
        self, 
        articles: List[Dict[str, Any]], 
        immediate: bool = False
    ) -> Dict[str, int]:
        """
        批次處理多篇文章
        
        Args:
            articles: 文章列表
            immediate: 是否立即發送
            
        Returns:
            處理統計 {'processed': N, 'skipped': N, 'failed': N}
        """
        stats = {'processed': 0, 'skipped': 0, 'failed': 0}
        
        for article in articles:
            # 先檢查是否包含關鍵字
            if not self.check_article_keywords(article):
                stats['skipped'] += 1
                continue
            
            # 檢查額度
            if not self.tracker.can_send_today():
                logger.warning("已達今日上限，停止處理")
                break
            
            # 處理文章
            if self.process_article(article, immediate=immediate):
                stats['processed'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"批次處理完成: {stats}")
        return stats
    
    def get_status(self) -> Dict[str, Any]:
        """
        取得服務狀態
        
        Returns:
            狀態資訊
        """
        return {
            'today_sent': self.tracker.get_today_count(),
            'daily_limit': auto_mail_settings.DAILY_LIMIT,
            'remaining_quota': self.tracker.get_remaining_quota(),
            'recent_records': self.tracker.get_recent_records(5)
        }


# 全域服務實例
auto_mail_service = AutoMailService()
