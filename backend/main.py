import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from haokan_crawler import HaokanCrawler

app = FastAPI(title="Haokan Video Monitor")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置
CONFIG_FILE = "/app/config/accounts.json"
DATA_FILE = "/app/data/records.json"

import glob

DATA_DIR = "/app/data"
CONFIG_FILE = "/app/config/accounts.json"
DATA_FILE = "/app/data/records.json" # Legacy path, will also read from glob

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

def load_data() -> List[Dict]:
    """读取 data 目录下所有的 json 文件并合并"""
    all_data = []
    
    # 1. 读取 legacy records.json
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
        except:
            pass

    # 2. 读取新格式的 crawl_*.json
    json_files = glob.glob(os.path.join(DATA_DIR, "crawl_*.json"))
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
        except:
            pass
            
    return all_data

def save_crawl_batch(data: List[Dict]):
    """将本次爬取的数据保存为独立文件"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"crawl_{timestamp}.json"
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_data(data: List[Dict]):
    # Deprecated: Old save method, kept for compatibility if needed, but we use save_crawl_batch now
    pass

def load_accounts() -> List[Dict]:
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
            # 兼容旧格式（纯字符串列表）
            if accounts and isinstance(accounts[0], str):
                return [{"id": acc, "name": f"用户_{acc}"} for acc in accounts]
            return accounts
    except:
        return []

def parse_play_count(play_count_str: str) -> int:
    """解析播放量字符串为整数"""
    try:
        if not play_count_str:
            return 0
        # 处理可能带有的单位（虽然通常API返回纯数字）
        if '万' in play_count_str:
            return int(float(play_count_str.replace('万', '')) * 10000)
        return int(play_count_str)
    except:
        return 0

def crawl_job():
    print(f"[{datetime.now()}] Starting scheduled crawl job...")
    accounts_list = load_accounts()
    if not accounts_list:
        print("No accounts configured.")
        return

    current_crawl_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    session_records = []
    
    for account in accounts_list:
        app_id = account['id']
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Crawling account: {app_id} (Attempt {attempt + 1}/{max_retries})")
                crawler = HaokanCrawler(app_id=app_id)
                # 获取该账号的所有视频
                videos = crawler.get_video_info_list()
                
                for video in videos:
                    # 添加元数据
                    record = video.copy()
                    record['app_id'] = app_id
                    record['author_name'] = account.get('name', '') # 添加作者昵称
                    record['crawl_time'] = current_crawl_time
                    record['vid'] = video.get('vid', '') # 确保有vid
                    
                    session_records.append(record)
                
                # 如果成功，跳出重试循环
                break
                
            except Exception as e:
                print(f"Error crawling {app_id}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5) # 等待5秒后重试
                else:
                    print(f"Failed to crawl {app_id} after {max_retries} attempts.")

    if session_records:
        save_crawl_batch(session_records)
        print(f"Saved {len(session_records)} records.")
    
    print(f"[{datetime.now()}] Crawl job finished.")

# 启动调度器
scheduler = BackgroundScheduler()
# 每小时整点触发 (minute='0')
scheduler.add_job(crawl_job, 'cron', minute='0')
scheduler.start()

@app.get("/")
def root():
    return {"status": "running", "time": datetime.now()}

@app.get("/api/data")
def get_data(limit: int = 100):
    data = load_data()
    return data[:limit]

@app.get("/api/stats/dashboard")
def get_dashboard_stats():
    """获取全局数据总览"""
    all_records = load_data()
    accounts = load_accounts()
    
    # 全局汇总数据
    global_stats = {
        "total_play_count": 0,
        "hour_growth": 0,
        "day_growth": 0,
        "yesterday_growth": 0,
        "last_week_total": 0,
        "last_month_total": 0,
        "yesterday_total": 0,
        "video_count": 0
    }
    
    # 账号维度列表数据
    accounts_stats = []

    # 整理所有视频数据 {vid: [records]}
    all_videos_map = {}
    for record in all_records:
        vid = record.get('vid') or record.get('title')
        if vid not in all_videos_map:
            all_videos_map[vid] = []
        all_videos_map[vid].append(record)

    current_time = datetime.now()

    # 计算每个账号的指标
    for acc in accounts:
        app_id = acc['id']
        acc_stats = {
            "app_id": app_id,
            "name": acc.get('name', f"用户_{app_id}"),
            "video_count": 0,
            "hour_growth": 0,
            "day_growth": 0,
            "yesterday_growth": 0
        }
        
        acc_total_play = 0
        
        # 找出属于该账号的视频
        # 优化：可以在一次遍历中做，但为了逻辑清晰分开写
        # 这里假设 all_videos_map 中的视频可以通过 app_id 关联（record里有）
        
        for vid, records in all_videos_map.items():
            # 检查这个视频是否属于该账号（取最新记录判断）
            if not records or records[0].get('app_id') != app_id:
                continue
                
            records.sort(key=lambda x: x['crawl_time'], reverse=True)
            latest = records[0]
            latest_play = parse_play_count(latest.get('play_count', '0'))
            latest_time = datetime.strptime(latest['crawl_time'], "%Y-%m-%d %H:%M:%S")
            
            acc_stats["video_count"] += 1
            acc_total_play += latest_play
            
            # 寻找历史记录
            one_hour_ago = None
            one_day_ago = None     # 24h ago
            two_days_ago = None    # 48h ago (for yesterday growth)
            seven_days_ago = None  # Last Week
            thirty_days_ago = None # Last Month
            
            for rec in records:
                rec_time = datetime.strptime(rec['crawl_time'], "%Y-%m-%d %H:%M:%S")
                diff_seconds = (latest_time - rec_time).total_seconds()
                
                # 1 hour (allow some margin, e.g. 50 mins to 70 mins)
                if diff_seconds >= 3000 and one_hour_ago is None:
                    one_hour_ago = rec
                
                # 24 hours
                if diff_seconds >= 80000 and one_day_ago is None:
                    one_day_ago = rec
                
                # 48 hours
                if diff_seconds >= 166000 and two_days_ago is None:
                    two_days_ago = rec
                
                # 7 days
                if diff_seconds >= 600000 and seven_days_ago is None:
                    seven_days_ago = rec
                
                # 30 days
                if diff_seconds >= 2500000 and thirty_days_ago is None:
                    thirty_days_ago = rec
            
            # 计算增长
            if one_hour_ago:
                g = latest_play - parse_play_count(one_hour_ago.get('play_count', '0'))
                acc_stats["hour_growth"] += g
                global_stats["hour_growth"] += g
                
            if one_day_ago:
                day_play = parse_play_count(one_day_ago.get('play_count', '0'))
                g = latest_play - day_play
                acc_stats["day_growth"] += g
                global_stats["day_growth"] += g
                
                # Yesterday Total (Snapshot at 24h ago)
                global_stats["yesterday_total"] += day_play
                
            # Yesterday Growth = (Value at 24h ago) - (Value at 48h ago)
            if one_day_ago and two_days_ago:
                day_play = parse_play_count(one_day_ago.get('play_count', '0'))
                two_day_play = parse_play_count(two_days_ago.get('play_count', '0'))
                g = day_play - two_day_play
                acc_stats["yesterday_growth"] += g
                global_stats["yesterday_growth"] += g
            
            # Last Week Total
            if seven_days_ago:
                global_stats["last_week_total"] += parse_play_count(seven_days_ago.get('play_count', '0'))
            
            # Last Month Total
            if thirty_days_ago:
                global_stats["last_month_total"] += parse_play_count(thirty_days_ago.get('play_count', '0'))
                
        
        acc_stats["total_play_count"] = acc_total_play
        global_stats["total_play_count"] += acc_total_play
        global_stats["video_count"] += acc_stats["video_count"]
        accounts_stats.append(acc_stats)
        
    return {
        "global": global_stats,
        "accounts": accounts_stats
    }

@app.get("/api/stats/account/{target_app_id}")
def get_account_details(target_app_id: str):
    """获取指定账号的详细视频列表及增长数据"""
    all_records = load_data()
    accounts = load_accounts()
    
    # 获取账号名称
    account_info = next((a for a in accounts if a['id'] == target_app_id), None)
    account_name = account_info.get('name', f"用户_{target_app_id}") if account_info else target_app_id

    # 过滤该账号的记录
    account_records = [r for r in all_records if r.get('app_id') == target_app_id]
    
    if not account_records:
        return {
            "info": {"id": target_app_id, "name": account_name},
            "stats": {"hour_growth": 0, "day_growth": 0, "yesterday_growth": 0},
            "videos": []
        }
        
    # 按 vid 分组
    videos_map = {}
    for record in account_records:
        vid = record.get('vid') or record.get('title')
        if vid not in videos_map:
            videos_map[vid] = []
        videos_map[vid].append(record)
        
    video_list = []
    total_hour_growth = 0
    total_day_growth = 0
    total_yesterday_growth = 0
    
    for vid, records in videos_map.items():
        records.sort(key=lambda x: x['crawl_time'], reverse=True)
        latest = records[0]
        latest_play = parse_play_count(latest.get('play_count', '0'))
        latest_time = datetime.strptime(latest['crawl_time'], "%Y-%m-%d %H:%M:%S")
        
        hour_growth = 0
        day_growth = 0
        yesterday_growth = 0
        
        # 计算增长
        one_hour_ago = None
        one_day_ago = None
        two_days_ago = None
        
        for rec in records:
            rec_time = datetime.strptime(rec['crawl_time'], "%Y-%m-%d %H:%M:%S")
            diff = (latest_time - rec_time).total_seconds()
            
            if diff >= 3000 and one_hour_ago is None:
                one_hour_ago = rec
            if diff >= 80000 and one_day_ago is None:
                one_day_ago = rec
            if diff >= 166000 and two_days_ago is None:
                two_days_ago = rec
                
        if one_hour_ago:
            hour_growth = latest_play - parse_play_count(one_hour_ago.get('play_count', '0'))
            
        if one_day_ago:
            day_val = parse_play_count(one_day_ago.get('play_count', '0'))
            day_growth = latest_play - day_val
            
            if two_days_ago:
                two_day_val = parse_play_count(two_days_ago.get('play_count', '0'))
                yesterday_growth = day_val - two_day_val
            
        total_hour_growth += hour_growth
        total_day_growth += day_growth
        total_yesterday_growth += yesterday_growth
        
        video_info = {
            "vid": vid,
            "title": latest.get('title'),
            "publish_time": latest.get('publish_time'),
            "play_count": latest_play,
            "play_count_text": latest.get('play_count_text'),
            "hour_growth": hour_growth,
            "day_growth": day_growth,
            "yesterday_growth": yesterday_growth,
            "crawl_time": latest.get('crawl_time')
        }
        video_list.append(video_info)
        
    # 按发布时间排序
    video_list.sort(key=lambda x: x['publish_time'], reverse=True)
    
    return {
        "info": {"id": target_app_id, "name": account_name},
        "stats": {
            "hour_growth": total_hour_growth,
            "day_growth": total_day_growth,
            "yesterday_growth": total_yesterday_growth
        },
        "videos": video_list
    }

@app.get("/api/stats/video/{vid_or_title}")
def get_video_history(vid_or_title: str):
    """获取单个视频的历史趋势数据"""
    all_records = load_data()
    
    # 查找匹配的记录
    # 注意：vid 在 URL 中可能需要编码，这里假设是安全的字符串
    history = []
    for r in all_records:
        if r.get('vid') == vid_or_title or r.get('title') == vid_or_title:
            history.append({
                "crawl_time": r.get('crawl_time'),
                "play_count": parse_play_count(r.get('play_count', '0')),
                "play_count_text": r.get('play_count_text')
            })
            
    # 按时间正序排列
    history.sort(key=lambda x: x['crawl_time'])
    return history

@app.get("/api/crawlers/trigger")
def trigger_crawl():
    """手动触发一次爬取"""
    scheduler.get_job(job_id='manual_crawl') # Check if running?
    # 简单起见直接异步运行或同步运行
    # 为了快速响应，这里在后台运行，但 APScheduler 主要是定时
    # 我们可以直接调用函数，但这会阻塞
    # 放在后台任务中
    from threading import Thread
    t = Thread(target=crawl_job)
    t.start()
    return {"message": "Crawl job started in background"}

@app.get("/api/config")
def get_config():
    return {"accounts": load_accounts()}

@app.post("/api/config")
def update_config(accounts: List[Dict]):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)
    return {"status": "updated", "accounts": accounts}

if __name__ == "__main__":
    import uvicorn
    # 启动时立即运行一次爬取（可选，避免等待1小时）
    # crawl_job() 
    uvicorn.run(app, host="0.0.0.0", port=8000)
