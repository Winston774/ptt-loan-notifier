import requests
import random
import time
import logging
from typing import List, Dict, Any, Optional

from config import settings
from .parser import (
    parse_article_list, 
    parse_article_content, 
    filter_by_keywords,
    get_previous_page_url
)

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PTTScraper:
    """PTT 爬蟲類別"""
    
    def __init__(self):
        self.session = requests.Session()
        # 設定必要的 cookie 以繞過年齡驗證
        self.session.cookies.set('over18', '1', domain='.ptt.cc')
        # 設定 User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """隨機延遲，避免過於頻繁的請求"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        抓取頁面內容
        
        Args:
            url: 要抓取的 URL
            
        Returns:
            頁面 HTML 內容，失敗回傳 None
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"抓取頁面失敗 {url}: {e}")
            return None
    
    def get_article_list(self, url: str = None) -> List[Dict[str, Any]]:
        """
        取得文章列表
        
        Args:
            url: 看板 URL，預設使用設定中的 URL
            
        Returns:
            文章列表
        """
        if url is None:
            url = settings.PTT_BOARD_URL
        
        html = self.fetch_page(url)
        if not html:
            return []
        
        return parse_article_list(html)
    
    def get_article_content(self, url: str) -> Dict[str, Any]:
        """
        取得文章內容
        
        Args:
            url: 文章 URL
            
        Returns:
            文章內容資訊
        """
        self._random_delay(0.5, 1.5)  # 減少延遲以加快抓取速度
        
        html = self.fetch_page(url)
        if not html:
            return {}
        
        return parse_article_content(html)
    
    def get_filtered_articles(self, pages: int = 1) -> List[Dict[str, Any]]:
        """
        取得符合關鍵字的文章列表
        
        Args:
            pages: 要抓取的頁數
            
        Returns:
            符合關鍵字的文章列表（包含完整內容）
        """
        all_articles = []
        current_url = settings.PTT_BOARD_URL
        keywords = settings.keywords_list
        
        for page_num in range(pages):
            logger.info(f"正在抓取第 {page_num + 1} 頁: {current_url}")
            
            # 取得文章列表
            html = self.fetch_page(current_url)
            if not html:
                break
            
            articles = parse_article_list(html)
            
            # 過濾符合關鍵字的文章
            filtered = filter_by_keywords(articles, keywords)
            logger.info(f"找到 {len(filtered)} 篇符合關鍵字的文章")
            
            # 抓取每篇文章的完整內容
            for article in filtered:
                content_data = self.get_article_content(article['url'])
                article.update(content_data)
                all_articles.append(article)
            
            # 取得上一頁連結
            if page_num < pages - 1:
                prev_url = get_previous_page_url(html)
                if prev_url:
                    current_url = prev_url
                    self._random_delay()
                else:
                    break
        
        return all_articles
    
    def get_new_articles(self) -> List[Dict[str, Any]]:
        """
        只抓取最新一頁的符合關鍵字文章
        適用於定時任務，每分鐘檢查一次
        
        Returns:
            符合關鍵字的新文章列表
        """
        return self.get_filtered_articles(pages=1)


# 建立全域 scraper 實例
scraper = PTTScraper()


def crawl_new_articles() -> List[Dict[str, Any]]:
    """
    便捷函數：抓取新文章
    """
    return scraper.get_new_articles()
