"""
測試爬蟲腳本 - 爬取 PTT 借貸版並顯示結果
"""
import sys
import json
sys.path.insert(0, r'd:\Vibe project\PTT')

from crawler.ptt_scraper import PTTScraper

def main():
    print("=" * 60)
    print("🔍 開始爬取 PTT 借貸版...")
    print("=" * 60)
    
    scraper = PTTScraper()
    
    # 先取得文章列表（不過濾關鍵字，查看所有文章）
    print("\n📋 取得文章列表...")
    articles = scraper.get_article_list()
    
    print(f"\n✅ 共找到 {len(articles)} 篇文章\n")
    print("-" * 60)
    
    # 顯示所有文章標題
    for i, article in enumerate(articles, 1):
        print(f"{i:2}. [{article['date']}] {article['title']}")
        print(f"    👤 作者: {article['author']}")
        print(f"    🔗 {article['url']}")
        print()
    
    # 過濾包含「信貸」或「個人信貸」的文章
    keywords = ["信貸", "個人信貸"]
    filtered = []
    for article in articles:
        if any(kw in article['title'] for kw in keywords):
            filtered.append(article)
    
    print("=" * 60)
    print(f"🏷️ 符合關鍵字【信貸/個人信貸】的文章: {len(filtered)} 篇")
    print("=" * 60)
    
    if filtered:
        for article in filtered:
            print(f"\n📌 {article['title']}")
            print(f"   👤 作者: {article['author']}")
            print(f"   📅 日期: {article['date']}")
            print(f"   🔗 {article['url']}")
            
            # 取得文章內容
            print(f"\n   📄 正在抓取文章內容...")
            content_data = scraper.get_article_content(article['url'])
            if content_data.get('content'):
                content = content_data['content']
                # 只顯示前 500 字
                preview = content[:500] + "..." if len(content) > 500 else content
                print(f"\n   內容預覽:\n   {'-' * 50}")
                for line in preview.split('\n')[:15]:
                    print(f"   {line}")
                print(f"   {'-' * 50}")
                print(f"   (全文共 {len(content)} 字)")
            else:
                print("   ⚠️ 無法取得文章內容")
    else:
        print("\n⚠️ 目前沒有符合關鍵字的文章")
    
    print("\n" + "=" * 60)
    print("✅ 爬蟲測試完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
