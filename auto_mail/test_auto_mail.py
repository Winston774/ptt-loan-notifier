"""
PTT 自動站內信功能測試腳本

使用方式:
    python -m auto_mail.test_auto_mail --mode <模式>

模式選項:
    login   - 測試 PTT 登入功能
    ai      - 測試 AI 內容生成
    tracker - 測試發送記錄追蹤
    full    - 完整流程測試（發送測試信給指定用戶）
    crawl   - 整合爬蟲測試（抓取文章並處理）
    status  - 查看服務狀態
"""
import argparse
import sys
import os

# 確保能正確 import 專案模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_mail.config import auto_mail_settings
from auto_mail.ptt_mailer import PTTMailer
from auto_mail.content_generator import ContentGenerator
from auto_mail.mail_tracker import MailTracker
from auto_mail.auto_mail_service import AutoMailService


def test_login():
    """測試 PTT 登入"""
    print("=" * 50)
    print("測試 PTT 登入功能")
    print("=" * 50)
    
    if not auto_mail_settings.PTT_USERNAME:
        print("[X] 錯誤: PTT_USERNAME 未設定")
        print("請在 .env 檔案中設定 PTT_USERNAME 和 PTT_PASSWORD")
        return False
    
    print(f"帳號: {auto_mail_settings.PTT_USERNAME}")
    
    mailer = PTTMailer()
    try:
        success = mailer.login()
        if success:
            print("[OK] PTT 登入成功!")
            mailer.logout()
            print("[OK] PTT 登出成功!")
            return True
        else:
            print("[X] PTT 登入失敗")
            return False
    except Exception as e:
        print(f"[X] 發生錯誤: {e}")
        return False


def test_ai_generation():
    """測試 AI 內容生成"""
    print("=" * 50)
    print("測試 AI 內容生成功能")
    print("=" * 50)
    
    if not auto_mail_settings.GEMINI_API_KEY:
        print("[X] 錯誤: GEMINI_API_KEY 未設定")
        print("請在 .env 檔案中設定 GEMINI_API_KEY")
        return False
    
    # 範例文章
    sample_article = {
        'title': '[請益] 想問信貸利率問題',
        'author': 'TestUser',
        'content': '''
        各位版友好，
        
        小弟最近有資金需求，想申請個人信貸。
        目前有正職工作，年薪約60萬，
        想貸款30萬左右，請問目前各家銀行的利率大概是多少？
        
        信用狀況良好，沒有卡債問題。
        
        謝謝各位
        '''
    }
    
    print(f"測試文章標題: {sample_article['title']}")
    print(f"測試文章作者: {sample_article['author']}")
    print("-" * 50)
    
    generator = ContentGenerator()
    try:
        title, content = generator.generate_mail_content(
            article_title=sample_article['title'],
            article_content=sample_article['content'],
            author=sample_article['author']
        )
        
        if title and content:
            print("[OK] AI 內容生成成功!")
            print("-" * 50)
            print(f"生成的信件標題: {title}")
            print("-" * 50)
            print("生成的信件內容:")
            print(content)
            print("-" * 50)
            return True
        else:
            print("[X] AI 內容生成失敗")
            return False
    except Exception as e:
        print(f"[X] 發生錯誤: {e}")
        return False


def test_tracker():
    """測試發送記錄追蹤"""
    print("=" * 50)
    print("測試發送記錄追蹤功能")
    print("=" * 50)
    
    tracker = MailTracker()
    
    # 測試記錄功能
    test_ptt_id = "TestUser123"
    test_article_id = "M.1234567890.A.ABC"
    
    print(f"測試 PTT ID: {test_ptt_id}")
    print(f"測試文章 ID: {test_article_id}")
    print("-" * 50)
    
    # 檢查是否已發送
    has_sent = tracker.has_sent_to(test_ptt_id)
    print(f"是否已發送過給 {test_ptt_id}: {has_sent}")
    
    # 今日統計
    today_count = tracker.get_today_count()
    remaining = tracker.get_remaining_quota()
    print(f"今日已發送: {today_count}")
    print(f"剩餘配額: {remaining}")
    print(f"每日上限: {auto_mail_settings.DAILY_LIMIT}")
    
    # 最近記錄
    print("-" * 50)
    print("最近發送記錄:")
    records = tracker.get_recent_records(5)
    if records:
        for record in records:
            ptt_id, article_title, mail_title, sent_at, success = record
            status = "[OK]" if success else "[X]"
            print(f"  {status} {ptt_id} - {article_title} ({sent_at})")
    else:
        print("  (無記錄)")
    
    print("[OK] 記錄追蹤功能正常")
    return True


def test_full(target_ptt_id: str):
    """完整流程測試"""
    print("=" * 50)
    print("完整流程測試（會發送真實站內信）")
    print("=" * 50)
    
    if not target_ptt_id:
        print("[X] 錯誤: 請使用 --target 指定測試收件人 PTT ID")
        return False
    
    print(f"[!] 警告: 這會發送真實站內信給 {target_ptt_id}")
    confirm = input("確定要繼續嗎? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("已取消測試")
        return False
    
    # 準備測試文章
    test_article = {
        'article_id': f'TEST_{int(__import__("time").time())}',
        'title': '[測試] 信貸利率諮詢',
        'author': target_ptt_id,
        'content': '''
        測試文章內容。
        
        這是一篇關於個人信貸的測試文章，
        用於測試自動站內信功能。
        '''
    }
    
    service = AutoMailService()
    
    print("開始處理文章...")
    success = service.process_article(test_article, immediate=True)
    
    if success:
        print("[OK] 完整流程測試成功!")
        print(f"站內信已發送給 {target_ptt_id}")
    else:
        print("[X] 完整流程測試失敗")
    
    return success


def test_crawl():
    """整合爬蟲測試"""
    print("=" * 50)
    print("整合爬蟲測試")
    print("=" * 50)
    
    try:
        from crawler.ptt_scraper import scraper
    except ImportError:
        print("[X] 無法匯入爬蟲模組")
        return False
    
    print("正在抓取 PTT Loan 版文章...")
    articles = scraper.get_new_articles()
    
    print(f"找到 {len(articles)} 篇符合關鍵字的文章")
    
    if not articles:
        print("沒有找到符合條件的文章")
        return True
    
    print("-" * 50)
    for i, article in enumerate(articles):
        print(f"{i+1}. {article.get('title', 'N/A')}")
        print(f"   作者: {article.get('author', 'N/A')}")
    print("-" * 50)
    
    print("[!] 警告: 繼續將會發送真實站內信")
    confirm = input("確定要處理這些文章嗎? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("已取消處理")
        return True
    
    service = AutoMailService()
    stats = service.process_articles_batch(articles, immediate=True)
    
    print("-" * 50)
    print(f"處理結果:")
    print(f"  [OK] 成功處理: {stats['processed']}")
    print(f"  [>>] 跳過: {stats['skipped']}")
    print(f"  [X] 失敗: {stats['failed']}")
    
    return True


def show_status():
    """顯示服務狀態"""
    print("=" * 50)
    print("自動站內信服務狀態")
    print("=" * 50)
    
    service = AutoMailService()
    status = service.get_status()
    
    print(f"今日已發送: {status['today_sent']} / {status['daily_limit']}")
    print(f"剩餘配額: {status['remaining_quota']}")
    print("-" * 50)
    
    print("環境變數檢查:")
    print(f"  PTT_USERNAME: {'[OK] 已設定' if auto_mail_settings.PTT_USERNAME else '[X] 未設定'}")
    print(f"  PTT_PASSWORD: {'[OK] 已設定' if auto_mail_settings.PTT_PASSWORD else '[X] 未設定'}")
    print(f"  GEMINI_API_KEY: {'[OK] 已設定' if auto_mail_settings.GEMINI_API_KEY else '[X] 未設定'}")
    print("-" * 50)
    
    print("最近發送記錄:")
    for record in status['recent_records']:
        ptt_id, article_title, mail_title, sent_at, success = record
        status_icon = "[OK]" if success else "[X]"
        print(f"  {status_icon} {ptt_id} - {mail_title or article_title} ({sent_at})")
    
    if not status['recent_records']:
        print("  (無記錄)")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='PTT 自動站內信功能測試腳本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['login', 'ai', 'tracker', 'full', 'crawl', 'status'],
        default='status',
        help='測試模式'
    )
    parser.add_argument(
        '--target', '-t',
        help='完整測試模式的目標 PTT ID'
    )
    
    args = parser.parse_args()
    
    print()
    print("[*] PTT 自動站內信測試工具")
    print()
    
    if args.mode == 'login':
        success = test_login()
    elif args.mode == 'ai':
        success = test_ai_generation()
    elif args.mode == 'tracker':
        success = test_tracker()
    elif args.mode == 'full':
        success = test_full(args.target)
    elif args.mode == 'crawl':
        success = test_crawl()
    elif args.mode == 'status':
        success = show_status()
    else:
        print(f"未知模式: {args.mode}")
        success = False
    
    print()
    if success:
        print("[OK] 測試完成")
    else:
        print("[X] 測試失敗")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
