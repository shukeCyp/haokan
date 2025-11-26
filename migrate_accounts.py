import json
import os
import sys
from typing import List, Dict
import requests

# 导入 Crawler
from backend.haokan_crawler import HaokanCrawler

CONFIG_FILE = "config/accounts.json"

def load_accounts_raw():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_accounts(accounts):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)

def migrate_accounts():
    print("开始迁移账号配置...")
    raw_accounts = load_accounts_raw()
    
    # 检查是否已经是新格式（列表中的元素是字典）
    if raw_accounts and isinstance(raw_accounts[0], dict):
        print("配置文件已经是新格式，无需迁移。")
        return

    new_accounts = []
    total = len(raw_accounts)
    
    print(f"找到 {total} 个账号，开始获取昵称...")
    
    for i, app_id in enumerate(raw_accounts, 1):
        print(f"[{i}/{total}] 处理账号: {app_id}")
        
        try:
            crawler = HaokanCrawler(app_id=app_id)
            # 先获取一个视频ID
            # 注意：为了获取作者信息，我们需要一个 vid。
            # 策略：先 fetch_author_list 获取列表，取第一个视频的 vid
            response = crawler.fetch_author_list(rn=1)
            
            author_name = f"用户_{app_id}" # 默认昵称
            
            if response.results:
                first_video = response.results[0]
                vid = first_video.vid
                
                # 获取作者信息
                author_info = crawler.get_author_info(vid)
                if author_info.get('name'):
                    author_name = author_info['name']
                    print(f"  -> 获取成功: {author_name}")
                else:
                    print("  -> 未能获取到昵称，使用默认值")
            else:
                 print("  -> 该账号没有视频，无法获取昵称")

            new_accounts.append({
                "id": app_id,
                "name": author_name
            })
            
        except Exception as e:
            print(f"  -> 处理出错: {e}")
            new_accounts.append({
                "id": app_id,
                "name": f"用户_{app_id}"
            })
            
    # 保存新配置
    save_accounts(new_accounts)
    print(f"\n迁移完成！已更新 {CONFIG_FILE}")

if __name__ == "__main__":
    migrate_accounts()

