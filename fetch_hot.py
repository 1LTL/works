#!/usr/bin/env python3
"""
羊洋阳工作台 - 抖音热点自动抓取脚本

功能：
1. 抓取抖音热榜（热搜 + 上升热点）
2. 筛选出适合翻唱博主二创的热点（音乐/歌曲/情感/影视相关）
3. 生成 hot_data.json 供工作台读取
4. 自动给出二创建议（温柔男声翻唱风格）

用法：
    python3 fetch_hot.py          # 抓取一次
    python3 fetch_hot.py --loop   # 每小时自动抓取一次（适合挂服务器）
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os

# 输出文件路径（和工作台 HTML 同目录）
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hot_data.json')

# 抖音热榜接口
DOUYIN_HOT_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json",
}

# 翻唱博主关注的关键词（命中则标记为高相关）
MUSIC_KEYWORDS = [
    '歌', '曲', '音乐', '翻唱', '唱', '歌手', '演唱会', '专辑', '单曲',
    '歌词', '旋律', '吉他', '钢琴', '伴奏', '原唱', 'cover',
    '情歌', '情书', '爱情', '思念', '想念', '回忆', '青春',
    '电影', '电视剧', 'OST', '插曲', '主题曲', '影视',
    '怀旧', '经典', '老歌', '金曲',
]


def fetch_douyin_hot():
    """抓取抖音热榜数据"""
    req = urllib.request.Request(DOUYIN_HOT_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    word_list = data.get('data', {}).get('word_list', [])
    trending_list = data.get('data', {}).get('trending_list', [])

    hot_items = []
    for item in word_list:
        hot_items.append({
            'word': item.get('word', ''),
            'hot_value': item.get('hot_value', 0),
            'position': item.get('position', 0),
            'type': 'hot'  # 热搜榜
        })

    trending_items = []
    for item in trending_list:
        trending_items.append({
            'word': item.get('word', ''),
            'hot_value': item.get('hot_value', 0),
            'video_count': item.get('video_count', 0),
            'type': 'trending'  # 上升热点
        })

    return hot_items, trending_items


def is_music_related(word):
    """判断热点是否和音乐/翻唱相关"""
    return any(kw in word for kw in MUSIC_KEYWORDS)


def generate_cover_suggestion(word):
    """根据热点词生成二创建议（温柔男声翻唱风格）"""
    suggestions = []

    if any(kw in word for kw in ['歌', '曲', '唱', '歌手', '原唱', 'cover', '翻唱']):
        suggestions.append('直接翻唱这首歌，用温柔男声 + 无声卡清唱')
        suggestions.append('降调处理，突出低音质感')
    elif any(kw in word for kw in ['电影', '电视剧', 'OST', '插曲', '主题曲', '影视']):
        suggestions.append('翻唱这部影视作品的插曲/主题曲，打「回忆杀」标签')
        suggestions.append('配合剧情画面混剪，歌词屏显')
    elif any(kw in word for kw in ['爱情', '情书', '思念', '想念', '回忆', '青春']):
        suggestions.append('选一首契合情绪的情歌翻唱，标题蹭热点')
        suggestions.append('文案带热点词，封面走氛围感')
    elif any(kw in word for kw in ['怀旧', '经典', '老歌', '金曲']):
        suggestions.append('老歌新唱，改成慢板吉他版')
        suggestions.append('打「怀旧」「睡前听」标签')
    else:
        # 通用建议：用音乐视角切入热点
        suggestions.append('找一首和该热点情绪匹配的歌翻唱，标题蹭热点')
        suggestions.append('评论区带热点话题，提升曝光')

    return suggestions


def build_hot_data(hot_items, trending_items):
    """组装最终数据"""
    now = datetime.now()

    # 筛选音乐相关的热搜（优先展示）
    music_related = [it for it in hot_items if is_music_related(it['word'])]
    others = [it for it in hot_items if not is_music_related(it['word'])]

    # 给每个热点加二创建议
    all_hot = music_related + others
    ranked = []
    for i, item in enumerate(all_hot):
        related = is_music_related(item['word'])
        ranked.append({
            'rank': i + 1,
            'word': item['word'],
            'hot_value': item['hot_value'],
            'hot_label': format_hot(item['hot_value']),
            'music_related': related,
            'suggestions': generate_cover_suggestion(item['word']),
            'search_url': f"https://www.douyin.com/search/{urllib.parse.quote(item['word'])}",
            'type': item['type']
        })

    # 上升热点（取前10）
    trending = []
    for i, item in enumerate(trending_items[:10]):
        trending.append({
            'rank': i + 1,
            'word': item['word'],
            'video_count': item.get('video_count', 0),
            'music_related': is_music_related(item['word']),
            'suggestions': generate_cover_suggestion(item['word']),
            'search_url': f"https://www.douyin.com/search/{urllib.parse.quote(item['word'])}"
        })

    return {
        'update_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'update_date': now.strftime('%Y-%m-%d'),
        'hot_list': ranked[:20],        # 热搜榜前20
        'trending_list': trending,       # 上升热点前10
        'music_related_count': len(music_related),
        'total_count': len(all_hot)
    }


def format_hot(value):
    """格式化热度值"""
    if value >= 10000000:
        return f"{value / 10000000:.1f}千万"
    elif value >= 10000:
        return f"{value / 10000:.1f}万"
    return str(value)


def save_data(data):
    """保存为 JSON"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 数据已保存到 {OUTPUT_FILE}")
    print(f"  更新时间: {data['update_time']}")
    print(f"  热搜总数: {data['total_count']}，音乐相关: {data['music_related_count']}")


def run_once():
    """抓取一次"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在抓取抖音热榜...")
        hot_items, trending_items = fetch_douyin_hot()
        data = build_hot_data(hot_items, trending_items)
        save_data(data)
        return True
    except Exception as e:
        print(f"✗ 抓取失败: {e}")
        return False


def run_loop(interval=3600):
    """循环抓取（默认每小时一次）"""
    print(f"启动循环模式，每 {interval} 秒抓取一次（Ctrl+C 退出）")
    while True:
        run_once()
        print(f"下次抓取: {interval} 秒后\n")
        time.sleep(interval)


if __name__ == '__main__':
    import sys
    # 补上 urllib.parse（脚本顶部 import 时某些环境可能缺失）
    import urllib.parse

    if '--loop' in sys.argv:
        # 可指定间隔：python3 fetch_hot.py --loop 1800
        try:
            idx = sys.argv.index('--loop')
            interval = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 3600
        except (ValueError, IndexError):
            interval = 3600
        run_loop(interval)
    else:
        run_once()
