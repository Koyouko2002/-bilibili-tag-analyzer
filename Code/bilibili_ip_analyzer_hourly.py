# -*- coding: utf-8 -*-
"""
B站指定IP创作数量时间趋势分析 - 按小时查询版
===========================
功能：查询指定日期每小时的创作数量

原理：B站搜索API支持 pubtime_begin_s 和 pubtime_end_s 参数
     指定每小时的时间范围，直接获取该小时投稿数量

依赖：requests, pandas, matplotlib, openpyxl
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import random
import os
import hashlib


# ==================== 配置 ====================
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

REQUEST_DELAY = 1.0


class BilibiliHourlySearch:
    """B站按小时查询爬虫"""

    def __init__(self, keyword):
        self.keyword = keyword
        self.hourly_counts = {}  # 'HH:00' -> count
        self.session_count = 0

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        buvid3 = hashlib.md5(str(time.time() + random.random()).encode()).hexdigest()[:32]
        session.cookies.set('buvid3', buvid3, domain='.bilibili.com')
        self.session_count += 1
        return session

    def query_hour(self, year, month, day, hour, max_page=5):
        """
        查询指定小时的投稿数量
        """
        hour_start = datetime(year, month, day, hour, 0, 0)
        hour_end = hour_start + timedelta(hours=1) - timedelta(seconds=1)

        begin_ts = int(hour_start.timestamp())
        end_ts = int(hour_end.timestamp())

        url = 'https://api.bilibili.com/x/web-interface/search/type'
        total_count = 0

        for page in range(1, max_page + 1):
            time.sleep(random.uniform(REQUEST_DELAY - 0.2, REQUEST_DELAY + 0.2))

            session = self._create_session()
            params = {
                'search_type': 'video',
                'keyword': self.keyword,
                'page': page,
                'page_size': 30,
                'order': 'pubdate',
                'pubtime_begin_s': begin_ts,
                'pubtime_end_s': end_ts,
            }

            try:
                response = session.get(url, params=params, timeout=15)
                data = response.json()

                if data['code'] != 0:
                    break

                results = data['data'].get('result') or []
                if not results:
                    break

                total_count += len(results)

                if len(results) < 30:
                    break

            except Exception:
                break

        return total_count

    def crawl_day(self, year, month, day, max_page=5):
        """爬取指定日期每小时的数据"""
        date_str = f"{year}-{month:02d}-{day:02d}"
        print(f"\n{'='*60}")
        print(f"开始采集 IP「{self.keyword}」 ...")
        print(f"查询日期：{date_str}")
        print(f"每小时翻页上限：{max_page} 页（每页30条）")
        print(f"{'='*60}")

        total = 24
        start_time = datetime.now()

        for hour in range(24):
            time_str = f"{hour:02d}:00"
            print(f"  [{hour:02d}:00]: ", end='', flush=True)

            count = self.query_hour(year, month, day, hour, max_page)
            self.hourly_counts[time_str] = count

            if count > 0:
                print(f"{count}条")
            else:
                print("无")

            if hour % 6 == 5:
                elapsed = (datetime.now() - start_time).seconds
                remaining = (elapsed / (hour + 1)) * (total - hour - 1)
                print(f"\n  -- 进度: {hour+1}/{total}, 已耗时{elapsed}秒, 预计剩余{int(remaining)}秒")

        end_time = datetime.now()
        total_videos = sum(self.hourly_counts.values())
        has_data_hours = sum(1 for v in self.hourly_counts.values() if v > 0)

        print(f"\n采集完成！")
        print(f"  总视频数：{total_videos} 条")
        print(f"  有投稿小时：{has_data_hours} 小时")
        print(f"  总耗时：{(end_time - start_time).seconds} 秒")


class BilibiliIPHourlyAnalyzer:
    """B站IP按小时查询分析器"""

    def __init__(self, keyword, save_dir='bilibili_results_hourly'):
        self.keyword = keyword
        self.save_dir = save_dir
        self.analyzer = BilibiliHourlySearch(keyword)
        self.df_hourly = None

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def run(self, year, month, day, max_page=5):
        print("\n" + "="*60)
        print("    B站指定IP按小时查询分析工具")
        print("="*60)
        print(f"\n查询：{year}年{month:02d}月{day:02d}日 每小时投稿量")

        self.analyzer.crawl_day(year, month, day, max_page)
        self._process_data()

        if self.df_hourly.empty:
            print("\n[错误] 未能获取到有效数据")
            return None

        self._generate_chart(year, month, day)
        self._save_to_excel(year, month, day)
        self._print_summary(year, month, day)

        return self.df_hourly

    def _process_data(self):
        if not self.analyzer.hourly_counts:
            self.df_hourly = pd.DataFrame()
            return

        self.df_hourly = pd.DataFrame([
            {'统计小时': k, '时投稿量': v}
            for k, v in sorted(self.analyzer.hourly_counts.items())
        ])
        print(f"\n数据处理完成：{len(self.df_hourly)} 小时")

    def _generate_chart(self, year, month, day):
        if self.df_hourly.empty:
            print("\n[警告] 数据不足")
            return

        fig, ax = plt.subplots(figsize=(16, 8))

        hours = list(range(24))
        counts = [self.df_hourly[self.df_hourly['统计小时'] == f"{h:02d}:00"]['时投稿量'].values[0] for h in hours]

        # 柱状图
        ax.bar(hours, counts, width=0.8, color='#00A1D4', alpha=0.6, label='时投稿量', zorder=2)

        # 折线
        ax.plot(hours, counts, marker='o', linewidth=2, markersize=8,
                color='#FF9500', label='趋势线', zorder=3)

        # 数据标签
        for h, c in zip(hours, counts):
            if c > 0:
                ax.annotate(f'{c}', (h, c), textcoords="offset points", xytext=(0, 8),
                           ha='center', fontsize=9, color='#333333')

        ax.set_xlabel('小时', fontsize=12)
        ax.set_ylabel('投稿数量', fontsize=12, color='#00A1D4')
        ax.tick_params(axis='y', labelcolor='#00A1D4')
        ax.set_xticks(hours)

        date_str = f"{year}{month:02d}{day:02d}"
        total = sum(counts)
        plt.title(
            f'B站 IP「{self.keyword}」{date_str}每小时投稿量统计\n'
            f'总投稿 {total} 部',
            fontsize=13, fontweight='bold', pad=20
        )

        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        ax.legend(loc='upper left')
        plt.tight_layout()

        chart_path = os.path.join(self.save_dir, f'{self.keyword}_{date_str}_hourly.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"\n趋势图已保存至：{chart_path}")

    def _save_to_excel(self, year, month, day):
        if self.df_hourly.empty:
            return

        date_str = f"{year}{month:02d}{day:02d}"
        excel_path = os.path.join(self.save_dir, f'{self.keyword}_{date_str}_hourly.xlsx')
        self.df_hourly.to_excel(excel_path, index=False)
        print(f"数据已保存至：{excel_path}")

    def _print_summary(self, year, month, day):
        if self.df_hourly.empty:
            return

        total = self.df_hourly['时投稿量'].sum()
        has_data = self.df_hourly[self.df_hourly['时投稿量'] > 0]

        print(f"\n{'='*60}")
        print(f"统计结果摘要")
        print(f"{'='*60}")
        print(f"  IP关键词：{self.keyword}")
        print(f"  统计日期：{year}年{month:02d}月{day:02d}日")
        print(f"  有投稿小时：{len(has_data)} 小时")
        print(f"  总投稿量：{total} 部")
        print(f"  时均投稿：{total / 24:.1f} 部")

        if len(has_data) > 0:
            peak = has_data.loc[has_data['时投稿量'].idxmax()]
            print(f"  峰值小时：{peak['统计小时']}（{peak['时投稿量']} 部）")


def main():
    analyzer = BilibiliIPHourlyAnalyzer(keyword="东方Project")
    result = analyzer.run(year=2026, month=4, day=1, max_page=5)

    if result is not None:
        print("\n" + "="*60)
        print("程序执行完毕")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()