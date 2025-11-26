import requests
import time
import json
from typing import Dict, List, Optional, Iterator
from dataclasses import dataclass

@dataclass
class VideoInfo:
    """视频信息数据类"""
    vid: str
    title: str
    publish_time: str
    cover_src: str
    cover_src_pc: str
    thumbnails: str
    duration: str
    poster: str
    playcnt: str
    playcntText: str

@dataclass
class ApiResponse:
    """API响应数据类"""
    errno: int
    errmsg: str
    logid: str
    response_count: int
    has_more: int
    ctime: str
    results: List[VideoInfo]

class HaokanCrawler:
    """百度好看视频爬虫类"""
    
    def __init__(self, app_id: str = "1844117067895852", base_url: str = "https://haokan.baidu.com/web/author/listall"):
        self.app_id = app_id
        self.base_url = base_url
        self.session = requests.Session()
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://haokan.baidu.com/',
        })
    
    def fetch_author_list(self, ctime: Optional[str] = None, rn: int = 20, 
                         video_type: str = "haokan|tabhubVideo") -> ApiResponse:
        """
        获取作者列表数据
        
        Args:
            ctime: 时间戳，用于分页，如果为None则获取第一页
            rn: 每页数量，默认20
            video_type: 视频类型
            
        Returns:
            ApiResponse: 解析后的API响应数据
        """
        params = {
            'app_id': self.app_id,
            'video_type': video_type,
            'rn': rn
        }
        
        # 如果有ctime参数，加入到查询参数中
        if ctime:
            params['ctime'] = ctime
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 验证返回数据的基本结构
            if data.get('errno') != 0:
                raise Exception(f"API返回错误: {data.get('errmsg', '未知错误')}")
            
            # 解析视频结果
            results = []
            for item in data.get('data', {}).get('results', []):
                if item.get('type') == 'video':
                    content = item.get('content', {})
                    video_info = VideoInfo(
                        vid=content.get('vid', ''),
                        title=content.get('title', ''),
                        publish_time=content.get('publish_time', ''),
                        cover_src=content.get('cover_src', ''),
                        cover_src_pc=content.get('cover_src_pc', ''),
                        thumbnails=content.get('thumbnails', ''),
                        duration=content.get('duration', ''),
                        poster=content.get('poster', ''),
                        playcnt=content.get('playcnt', ''),
                        playcntText=content.get('playcntText', '')
                    )
                    results.append(video_info)
            
            return ApiResponse(
                errno=data.get('errno', -1),
                errmsg=data.get('errmsg', ''),
                logid=data.get('logid', ''),
                response_count=data.get('data', {}).get('response_count', 0),
                has_more=data.get('data', {}).get('has_more', 0),
                ctime=data.get('data', {}).get('ctime', ''),
                results=results
            )
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求错误: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析错误: {e}")
        except Exception as e:
            raise Exception(f"数据处理错误: {e}")
    
    def fetch_all_videos(self, delay: float = 1.0) -> Iterator[ApiResponse]:
        """
        获取所有视频数据的迭代器（自动获取所有页）
        
        Args:
            delay: 每次请求间隔时间（秒）
            
        Yields:
            ApiResponse: 每页的数据
        """
        ctime = None
        pages_fetched = 0
        has_more = True
        
        while has_more:
            try:
                response = self.fetch_author_list(ctime=ctime)
                yield response
                
                # 检查是否有更多数据
                has_more = response.has_more == 1 and len(response.results) > 0
                
                if has_more:
                    # 更新ctime用于下一页
                    ctime = response.ctime
                    pages_fetched += 1
                    
                    # 添加延迟，避免请求过快
                    time.sleep(delay)
                else:
                    print(f"所有数据获取完成，共获取 {pages_fetched + 1} 页数据")
                    
            except Exception as e:
                print(f"第{pages_fetched + 1}页获取失败: {e}")
                has_more = False

    def get_author_info(self, vid: str) -> Dict[str, str]:
        """
        获取作者信息
        
        Args:
            vid: 视频ID，用于获取作者信息
            
        Returns:
            Dict: 包含作者昵称等信息
        """
        url = "https://haokan.baidu.com/haokan/ui-web/author/info"
        params = {
            'vid': vid
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 0:
                author_data = data.get('data', {}).get('response', {}).get('author', {})
                return {
                    'name': author_data.get('author', ''),
                    'avatar': author_data.get('author_icon', ''),
                    'fans_count': data.get('data', {}).get('response', {}).get('cnt', {}).get('fansCnt', 0)
                }
            return {}
        except Exception as e:
            print(f"获取作者信息失败: {e}")
            return {}

    def get_video_info_list(self) -> List[Dict[str, str]]:
        """
        获取所有视频的基本信息列表
        
        Returns:
            List[Dict[str, str]]: 包含标题、发布时间和播放量的视频列表
        """
        videos_list = []
        # 使用 fetch_all_videos 获取所有数据
        for response in self.fetch_all_videos(delay=0.5):
            for video in response.results:
                video_data = {
                    "title": video.title,
                    "publish_time": video.publish_time,
                    "play_count": video.playcnt,
                    "play_count_text": video.playcntText
                }
                videos_list.append(video_data)
        
        return videos_list

def main():
    """示例使用"""
    crawler = HaokanCrawler(app_id=1843978956421847)
    
    print("开始获取百度好看视频数据...")
    
    # 获取所有视频数据
    total_videos = 0
    for page, response in enumerate(crawler.fetch_all_videos(), 1):
        print(f"\n=== 第{page}页 ===")
        print(f"响应码: {response.errno}")
        print(f"消息: {response.errmsg}")
        print(f"返回数量: {response.response_count}")
        print(f"是否有更多: {response.has_more}")
        print(f"下一页ctime: {response.ctime}")
        
        for i, video in enumerate(response.results, 1):
            print(f"{i}. {video.title} (播放: {video.playcntText})")
        
        total_videos += len(response.results)
    
    print(f"\n总共获取了 {total_videos} 个视频")

if __name__ == "__main__":
    main()