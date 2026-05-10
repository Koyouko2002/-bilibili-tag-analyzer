# -*- coding: utf-8 -*-
"""
B站指定IP创作数量时间趋势分析 - 4段方案查整月
把每天拆成4段: 00-07, 08-15, 16-19, 20-23
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import time
import random
import os
import hashlib


plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
REQUEST_DELAY = 1.0


class Bilibili4SegmentMonthSearch:
    def __init__(self, keyword):
        self.keyword = keyword
        self.daily_counts = {}  # 'YYYY-MM-DD' -> total count
        self.segment_details = []  # 详细分段数据
        self.total_requests = 0

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        buvid3 = hashlib.md5(str(time.time() + random.random()).encode()).hexdigest()[:32]
        session.cookies.set('buvid3', buvid3, domain='.bilibili.com')
        return session

    def query_segment(self, year, month, day, start_hour, end_hour):
        """查询指定时间段的投稿量"""
        seg_start = datetime(year, month, day, start_hour, 0, 0)
        seg_end = datetime(year, month, day, end_hour - 1, 59, 59)

        begin_ts = int(seg_start.timestamp())
        end_ts = int(seg_end.timestamp())

        url = 'https://api.bilibili.com/x/web-interface/search/type'
        total_count = 0

        for page in range(1, 6):
            time.sleep(random.uniform(REQUEST_DELAY - 0.2, REQUEST_DELAY + 0.2))
            session = self._create_session()
            self.total_requests += 1

            try:
                response = session.get(url, params={
                    'search_type': 'video', 'keyword': self.keyword,
                    'page': page, 'page_size': 30, 'order': 'pubdate',
                    'pubtime_begin_s': begin_ts, 'pubtime_end_s': end_ts,
                }, timeout=15)
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

    def crawl_day(self, year, month, day):
        """查询一天4段"""
        day_str = f"{year}-{month:02d}-{day:02d}"
        segments = [
            (0, 8, '00:00-07:59'),
            (8, 16, '08:00-15:59'),
            (16, 20, '16:00-19:59'),
            (20, 24, '20:00-23:59'),
        ]

        day_total = 0
        day_capped = 0

        for start_hour, end_hour, seg_name in segments:
            count = self.query_segment(year, month, day, start_hour, end_hour)

            self.segment_details.append({
                'date': day_str,
                'segment': seg_name,
                'start_hour': start_hour,
                'end_hour': end_hour,
                'count': count
            })

            day_total += count
            if count >= 150:
                day_capped += 1

        return day_total, day_capped

    def crawl_month(self, year, month):
        """爬取整月每天数据"""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        days_in_month = (next_month - datetime(year, month, 1)).days

        print(f"\n{'='*60}")
        print(f"开始采集 IP「{self.keyword}」 ...")
        print(f"查询范围：{year}年{month:02d}月（{days_in_month}天）")
        print(f"每日拆分：00-07, 08-15, 16-19, 20-23（四段）")
        print(f"{'='*60}")

        total = days_in_month
        start_time = datetime.now()

        for day in range(1, days_in_month + 1):
            day_total, day_capped = self.crawl_day(year, month, day)
            day_str = f"{year}-{month:02d}-{day:02d}"
            self.daily_counts[day_str] = {'total': day_total, 'capped': day_capped}

            capped_str = f"(触顶{day_capped}段)" if day_capped > 0 else ""
            print(f"  [{day:02d}/{total}] {day_str}: {day_total}条 {capped_str}")

            # 每5天报告进度
            if day % 5 == 0:
                elapsed = (datetime.now() - start_time).seconds
                remaining = (elapsed / day) * (total - day)
                req_estimated = int(self.total_requests / day * total)
                print(f"\n  -- 进度: {day}/{total}, 已请求{self.total_requests}次, 预计共约{req_estimated}次")
                print(f"     已耗时{elapsed}秒, 预计剩余{int(remaining)}秒")

        end_time = datetime.now()
        total_videos = sum(v['total'] for v in self.daily_counts.values())
        days_capped = sum(1 for v in self.daily_counts.values() if v['capped'] > 0)

        print(f"\n采集完成！")
        print(f"  总视频数：{total_videos} 条")
        print(f"  触顶天数：{days_capped} 天")
        print(f"  总请求次数：{self.total_requests} 次")
        print(f"  总耗时：{(end_time - start_time).seconds} 秒")


class Bilibili4SegmentMonthAnalyzer:
    def __init__(self, keyword, save_dir='bilibili_results_4seg_month'):
        self.keyword = keyword
        self.save_dir = save_dir
        self.analyzer = Bilibili4SegmentMonthSearch(keyword)
        self.df_daily = None
        self.df_segments = None
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def run(self, year, month):
        self.year = year
        self.month = month

        print("\n" + "="*60)
        print("    B站指定IP 4段方案查询整月")
        print("="*60)
        print(f"\n查询：{year}年{month:02d}月 每日4段统计")

        self.analyzer.crawl_month(year, month)
        self._process_data()

        if self.df_daily.empty:
            print("\n[错误] 未能获取到有效数据")
            return None

        self._generate_chart()
        self._save_to_excel()
        self._print_summary()

        return self.df_daily

    def _process_data(self):
        if not self.analyzer.daily_counts:
            self.df_daily = pd.DataFrame()
            return

        self.df_daily = pd.DataFrame([
            {'统计日期': k, '日投稿量': v['total'], '触顶段数': v['capped']}
            for k, v in sorted(self.analyzer.daily_counts.items())
        ])

        if self.analyzer.segment_details:
            self.df_segments = pd.DataFrame(self.analyzer.segment_details)

        print(f"\n数据处理完成：{len(self.df_daily)} 天")

    def _generate_chart(self):
        if self.df_daily.empty or len(self.df_daily) < 2:
            print("\n[警告] 数据不足")
            return

        fig, ax = plt.subplots(figsize=(16, 8))
        dates = pd.to_datetime(self.df_daily['统计日期'])

        ax.bar(dates, self.df_daily['日投稿量'], width=0.8,
               color='#00A1D4', alpha=0.6, label='日投稿量', zorder=2)

        ax.plot(dates, self.df_daily['日投稿量'],
                marker='o', linewidth=2, markersize=6,
                color='#FF9500', label='趋势线', zorder=3)

        # 标注触顶天数
        topped = self.df_daily[self.df_daily['触顶段数'] > 0]
        for _, row in topped.iterrows():
            ax.annotate(f'触顶({row["触顶段数"]}段)', (pd.to_datetime(row['统计日期']), row['日投稿量']),
                       textcoords="offset points", xytext=(0, 10),
                       ha='center', fontsize=8, color='red')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('投稿数量', fontsize=12, color='#00A1D4')
        ax.tick_params(axis='y', labelcolor='#00A1D4')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//15)))
        plt.xticks(rotation=45, fontsize=9)

        total = self.df_daily['日投稿量'].sum()
        month_str = self.df_daily['统计日期'].iloc[0][:7]
        topped_count = len(topped)
        plt.title(
            f'B站 IP「{self.keyword}」{month_str}每日投稿量统计（4段方案）\n'
            f'总投稿 {total} 部 | 触顶天数 {topped_count} 天 | 请求 {self.analyzer.total_requests} 次',
            fontsize=13, fontweight='bold', pad=20
        )

        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        ax.legend(loc='upper left')
        plt.tight_layout()

        chart_path = os.path.join(self.save_dir, f'{self.keyword}_{self.year}{self.month:02d}_4seg_month.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"\n趋势图已保存至：{chart_path}")

    def _save_to_excel(self):
        if self.df_daily.empty:
            return

        month_str = self.df_daily['统计日期'].iloc[0][:7]
        excel_path = os.path.join(self.save_dir, f'{self.keyword}_{month_str}_4seg_month.xlsx')

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            self.df_daily.to_excel(writer, sheet_name='每日统计', index=False)
            if self.df_segments is not None and not self.df_segments.empty:
                self.df_segments.to_excel(writer, sheet_name='分段明细', index=False)

        print(f"数据已保存至：{excel_path}")

    def _print_summary(self):
        if self.df_daily.empty:
            return

        total = self.df_daily['日投稿量'].sum()
        topped_days = self.df_daily[self.df_daily['触顶段数'] > 0]

        print(f"\n{'='*60}")
        print(f"统计结果摘要")
        print(f"{'='*60}")
        print(f"  IP关键词：{self.keyword}")
        print(f"  统计月份：{self.df_daily['统计日期'].iloc[0][:7]}")
        print(f"  覆盖天数：{len(self.df_daily)} 天")
        print(f"  触顶天数：{len(topped_days)} 天")
        print(f"  总投稿量：{total} 部")
        print(f"  日均投稿：{total / len(self.df_daily):.1f} 部")
        print(f"  请求总次数：{self.analyzer.total_requests} 次")

        if len(topped_days) > 0:
            print(f"\n  触顶日期详情：")
            for _, row in topped_days.iterrows():
                print(f"    {row['统计日期']}: 触顶{row['触顶段数']}段, 共{row['日投稿量']}条")

        peak = self.df_daily.loc[self.df_daily['日投稿量'].idxmax()]
        print(f"\n  峰值日期：{peak['统计日期']}（{peak['日投稿量']} 部）")


def main():
    analyzer = Bilibili4SegmentMonthAnalyzer(keyword="东方Project")
    result = analyzer.run(year=2026, month=4)

    if result is not None:
        print("\n" + "="*60)
        print("程序执行完毕")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()