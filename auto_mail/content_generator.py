"""
AI 信件內容生成模組
使用 Google Gemini API
"""
import logging
from typing import Tuple, Optional
import google.generativeai as genai

from .config import auto_mail_settings

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 信件生成 Prompt 模板
MAIL_GENERATION_PROMPT = """
你是一位專業的信貸顧問助手。請根據以下 PTT Loan 版的文章內容，撰寫一封個人化的站內信給文章作者。

文章標題: {article_title}
文章作者: {author}
文章內容:
{article_content}

請生成一封站內信，要求：
1. 信件標題要專業、吸引人，但不能像垃圾郵件
2. 內容要針對作者在文章中提到的需求進行回應
3. 簡單介紹你可以提供的信貸服務
4. 語氣要專業、友善，不要太過推銷
5. 字數控制在 300 字以內
6. 不要使用表情符號

請以下列格式回覆：
標題: [信件標題]
---
[信件內容]
"""


class ContentGenerator:
    """AI 信件內容生成器"""
    
    def __init__(self):
        self.model = None
        self._initialized = False
    
    def _initialize(self):
        """初始化 Gemini API"""
        if self._initialized:
            return
        
        api_key = auto_mail_settings.GEMINI_API_KEY
        if not api_key:
            logger.error("GEMINI_API_KEY 未設定")
            raise ValueError("GEMINI_API_KEY 未設定")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(auto_mail_settings.GEMINI_MODEL)
        self._initialized = True
        logger.info(f"Gemini API 初始化完成，使用模型: {auto_mail_settings.GEMINI_MODEL}")
    
    def generate_mail_content(
        self,
        article_title: str,
        article_content: str,
        author: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        生成信件內容
        
        Args:
            article_title: 文章標題
            article_content: 文章內容
            author: 文章作者
            
        Returns:
            (信件標題, 信件內容) 或 (None, None) 如果失敗
        """
        try:
            self._initialize()
            
            # 準備 prompt
            prompt = MAIL_GENERATION_PROMPT.format(
                article_title=article_title,
                author=author,
                article_content=article_content[:2000]  # 限制內容長度
            )
            
            logger.info(f"正在為文章 '{article_title}' 生成信件內容...")
            
            # 呼叫 Gemini API
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # 解析回應
            title, content = self._parse_response(result_text)
            
            if title and content:
                logger.info(f"成功生成信件，標題: {title}")
                return title, content
            else:
                logger.error("無法解析 AI 回應")
                return None, None
                
        except Exception as e:
            logger.error(f"生成信件內容時發生錯誤: {e}")
            return None, None
    
    def _parse_response(self, response_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 AI 回應
        
        Args:
            response_text: AI 回應文字
            
        Returns:
            (信件標題, 信件內容)
        """
        try:
            # 尋找標題
            lines = response_text.strip().split('\n')
            title = None
            content_start_idx = 0
            
            for i, line in enumerate(lines):
                if line.startswith('標題:') or line.startswith('標題：'):
                    title = line.replace('標題:', '').replace('標題：', '').strip()
                    content_start_idx = i + 1
                    break
            
            # 跳過分隔線
            for i in range(content_start_idx, len(lines)):
                if lines[i].strip() == '---' or lines[i].strip() == '':
                    content_start_idx = i + 1
                else:
                    break
            
            # 取得內容
            content = '\n'.join(lines[content_start_idx:]).strip()
            
            return title, content
            
        except Exception as e:
            logger.error(f"解析 AI 回應時發生錯誤: {e}")
            return None, None


# 全域實例
content_generator = ContentGenerator()


def generate_mail(article_title: str, article_content: str, author: str) -> Tuple[Optional[str], Optional[str]]:
    """便捷函數：生成信件內容"""
    return content_generator.generate_mail_content(article_title, article_content, author)
