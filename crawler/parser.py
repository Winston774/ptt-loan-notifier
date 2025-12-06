import re
from datetime import datetime
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import pytz

from config import settings


def parse_article_list(html: str) -> list[Dict[str, Any]]:
    """
    解析 PTT 看板的文章列表頁面
    
    Returns:
        list: 文章資訊列表，每個元素包含 title, url, author, date, article_id
    """
    soup = BeautifulSoup(html, 'lxml')
    articles = []
    
    # 找到所有文章區塊
    for entry in soup.select('div.r-ent'):
        try:
            # 標題和連結
            title_elem = entry.select_one('div.title a')
            if not title_elem:
                continue  # 可能是已刪除的文章
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            
            # 完整 URL
            if url and not url.startswith('http'):
                url = f"https://www.ptt.cc{url}"
            
            # 從 URL 提取文章 ID
            article_id = extract_article_id(url)
            
            # 作者
            author_elem = entry.select_one('div.meta div.author')
            author = author_elem.get_text(strip=True) if author_elem else ''
            
            # 日期 (格式: 12/05)
            date_elem = entry.select_one('div.meta div.date')
            date_str = date_elem.get_text(strip=True) if date_elem else ''
            
            articles.append({
                'title': title,
                'url': url,
                'author': author,
                'date': date_str,
                'article_id': article_id
            })
            
        except Exception as e:
            print(f"解析文章列表項目失敗: {e}")
            continue
    
    return articles


def parse_article_content(html: str) -> Dict[str, Any]:
    """
    解析 PTT 文章內容頁面
    
    Returns:
        dict: 包含 content, post_time 等詳細資訊
    """
    soup = BeautifulSoup(html, 'lxml')
    result = {
        'content': '',
        'post_time': None,
        'author': '',
        'title': '',
        'board': ''
    }
    
    try:
        # 解析 meta 資訊 (作者、看板、標題、時間)
        metalines = soup.select('div.article-metaline')
        for metaline in metalines:
            tag = metaline.select_one('span.article-meta-tag')
            value = metaline.select_one('span.article-meta-value')
            if tag and value:
                tag_text = tag.get_text(strip=True)
                value_text = value.get_text(strip=True)
                
                if tag_text == '作者':
                    result['author'] = value_text.split('(')[0].strip()
                elif tag_text == '看板':
                    result['board'] = value_text
                elif tag_text == '標題':
                    result['title'] = value_text
                elif tag_text == '時間':
                    result['post_time'] = parse_ptt_datetime(value_text)
        
        # 解析文章內容
        main_content = soup.select_one('div#main-content')
        if main_content:
            # 移除 meta 資訊和推文
            for elem in main_content.select('div.article-metaline, div.article-metaline-right, div.push'):
                elem.decompose()
            
            # 取得純文字內容
            content = main_content.get_text()
            
            # 移除簽名檔 (--\n 之後的內容)
            if '\n--\n' in content:
                content = content.split('\n--\n')[0]
            
            result['content'] = content.strip()
    
    except Exception as e:
        print(f"解析文章內容失敗: {e}")
    
    return result


def extract_article_id(url: str) -> str:
    """
    從 PTT 文章 URL 提取文章 ID
    
    Example:
        https://www.ptt.cc/bbs/Loan/M.1701234567.A.123.html -> M.1701234567.A.123
    """
    match = re.search(r'/([A-Z]\.\d+\.[A-Z]\.[A-Z0-9]+)\.html', url)
    return match.group(1) if match else ''


def parse_ptt_datetime(datetime_str: str) -> Optional[datetime]:
    """
    解析 PTT 的時間格式
    
    Example:
        'Fri Dec  6 01:23:45 2024' -> datetime object
    """
    try:
        # PTT 時間格式: Wed Dec  4 12:34:56 2024
        dt = datetime.strptime(datetime_str, '%a %b %d %H:%M:%S %Y')
        # 設定為台北時區
        tz = pytz.timezone(settings.TIMEZONE)
        return tz.localize(dt)
    except ValueError:
        try:
            # 嘗試其他可能的格式
            dt = datetime.strptime(datetime_str, '%a %b  %d %H:%M:%S %Y')
            tz = pytz.timezone(settings.TIMEZONE)
            return tz.localize(dt)
        except ValueError:
            return None


def filter_by_keywords(articles: list[Dict[str, Any]], keywords: list[str]) -> list[Dict[str, Any]]:
    """
    根據關鍵字過濾文章
    
    Args:
        articles: 文章列表
        keywords: 關鍵字列表
        
    Returns:
        包含任一關鍵字的文章列表
    """
    filtered = []
    for article in articles:
        title = article.get('title', '')
        for keyword in keywords:
            if keyword in title:
                filtered.append(article)
                break
    return filtered


def get_previous_page_url(html: str) -> Optional[str]:
    """
    取得上一頁的 URL
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # 找到 "上頁" 連結
    for link in soup.select('div.btn-group-paging a'):
        if '上頁' in link.get_text():
            href = link.get('href', '')
            if href:
                return f"https://www.ptt.cc{href}"
    
    return None
