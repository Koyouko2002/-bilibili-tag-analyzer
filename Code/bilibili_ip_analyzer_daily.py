# -*- coding: utf-8 -*-
"""
B站指定IP创作数量时间趋势分析 - 按日查询版
===========================
功能：输入IP关键词，按天查询指定月份每天的创作数量

原理：B站搜索API支持 pubtime_begin_s 和 pubtime_end_s 参数
     指定每天的时间范围，直接获取当天投稿数量

依赖：requests, pandas, matplotlib, openpyxl
用法：python bilibili_ip_analyzer_daily.py

作者：Python爬虫工程师
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


# ==================== 配置 ====================
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 请求间隔（秒）
REQUEST_DELAY = 1.5


def get_day_timestamps(year, month, day):
    """获取指定日期的时间戳范围（当天0点-23:59:59）"""
    day_start = datetime(year, month, day)
    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

    begin_ts = int(day_start.timestamp())
    end_ts = int(day_end.timestamp())
    return begin_ts, end_ts


class BilibiliDailySearch:
    """B站按日直接查询爬虫"""

    def __init__(self, keyword):
        self.keyword = keyword
        self.daily_counts = {}  # 'YYYY-MM-DD' -> count
        self.session_count = 0

    def _create_session(self):
        """创建带随机cookie的session"""
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

    def query_day(self, year, month, day, max_page=5):
        """
        查询指定一天的投稿数量
        :param year: 年份
        :param month: 月份
        :param day: 日期
        :param max_page: 最大翻页数（默认5页，每页30条，共150条）
        :return: 当日投稿数量
        """
        begin_ts, end_ts = get_day_timestamps(year, month, day)
        day_str = f"{year}-{month:02d}-{day:02d}"

        url = 'https://api.bilibili.com/x/web-interface/search/type'
        total_count = 0

        for page in range(1, max_page + 1):
            time.sleep(random.uniform(REQUEST_DELAY - 0.3, REQUEST_DELAY + 0.3))

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
                    print(f"    [API错误] code={data['code']}")
                    break

                results = data['data'].get('result') or []
                if not results:
                    break

                total_count += len(results)

                # 如果返回数量少于page_size，说明已经拿完了
                if len(results) < 30:
                    break

            except Exception as e:
                print(f"    [请求异常] {type(e).__name__}")
                break

        return total_count

    def crawl_month(self, year, month, max_page=5):
        """爬取指定月份每天的数据"""
        # 获取该月天数
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)

        days_in_month = (next_month - datetime(year, month, 1)).days

        month_str = f"{year}年{month:02d}月"
        print(f"\n{'='*60}")
        print(f"开始采集 IP「{self.keyword}」 ...")
        print(f"查询范围：{month_str}")
        print(f"天数：{days_in_month} 天")
        print(f"每日期翻页上限：{max_page} 页（每页30条）")
        print(f"{'='*60}")

        total = days_in_month
        print(f"共 {total} 天待查询\n")

        start_time = datetime.now()

        for day in range(1, days_in_month + 1):
            print(f"  [{day}/{total}] {year}-{month:02d}-{day:02d}: ", end='', flush=True)

            count = self.query_day(year, month, day, max_page)
            day_str = f"{year}-{month:02d}-{day:02d}"
            self.daily_counts[day_str] = count

            if count > 0:
                print(f"{count}条")
            else:
                print("无")

            # 每7天显示进度
            if day % 7 == 0:
                elapsed = (datetime.now() - start_time).seconds
                remaining = (elapsed / day) * (total - day)
                print(f"\n  -- 进度: {day}/{total}, 已耗时{elapsed}秒, 预计剩余{int(remaining)}秒")

        end_time = datetime.now()
        total_videos = sum(self.daily_counts.values())
        has_data_days = sum(1 for v in self.daily_counts.values() if v > 0)

        print(f"\n采集完成！")
        print(f"  总视频数：{total_videos} 条")
        print(f"  有投稿天数：{has_data_days} 天")
        print(f"  总耗时：{(end_time - start_time).seconds} 秒")


class BilibiliIPDailyAnalyzer:
    """B站IP按日查询分析器"""

    def __init__(self, keyword, save_dir='bilibili_results_daily'):
        self.keyword = keyword
        self.save_dir = save_dir
        self.analyzer = BilibiliDailySearch(keyword)
        self.df_daily = None

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def run(self, year, month, max_page=5):
        """运行完整分析流程"""
        print("\n" + "="*60)
        print("    B站指定IP按日查询分析工具")
        print("="*60)
        print(f"\n查询：{year}年{month:02d}月 每日投稿量")
        print("策略：使用 pubtime_begin_s/end_s 参数直接按日查询")

        # 1. 爬取数据
        self.analyzer.crawl_month(year, month, max_page=max_page)

        # 2. 处理数据
        self._process_data()

        if self.df_daily.empty:
            print("\n[错误] 未能获取到有效数据")
            return None

        # 3. 生成图表
        self._generate_chart()

        # 4. 保存Excel
        self._save_to_excel()

        # 5. 打印摘要
        self._print_summary()

        return self.df_daily

    def _process_data(self):
        """处理数据"""
        if not self.analyzer.daily_counts:
            self.df_daily = pd.DataFrame()
            return

        self.df_daily = pd.DataFrame([
            {'统计日期': k, '日投稿量': v}
            for k, v in sorted(self.analyzer.daily_counts.items())
        ])
        print(f"\n数据处理完成：{len(self.df_daily)} 天")

    def _generate_chart(self):
        """生成趋势图"""
        if self.df_daily.empty or len(self.df_daily) < 2:
            print("\n[警告] 数据不足")
            return

        fig, ax = plt.subplots(figsize=(16, 8))
        dates = pd.to_datetime(self.df_daily['统计日期'])

        # 柱状图
        ax.bar(dates, self.df_daily['日投稿量'], width=0.8,
               color='#00A1D4', alpha=0.6, label='日投稿量', zorder=2)

        # 折线
        ax.plot(dates, self.df_daily['日投稿量'],
                marker='o', linewidth=2, markersize=6,
                color='#FF9500', label='趋势线', zorder=3)

        # 数据标签
        for date, count in zip(dates, self.df_daily['日投稿量']):
            if count > 0:
                ax.annotate(f'{count}', (date, count),
                           textcoords="offset points", xytext=(0, 8),
                           ha='center', fontsize=8, color='#333333')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('投稿数量', fontsize=12, color='#00A1D4')
        ax.tick_params(axis='y', labelcolor='#00A1D4')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//15)))
        plt.xticks(rotation=45, fontsize=9)

        total = self.df_daily['日投稿量'].sum()
        month_str = self.df_daily['统计日期'].iloc[0][:7]
        plt.title(
            f'B站 IP「{self.keyword}」{month_str}每日投稿量统计\n'
            f'总投稿 {total} 部',
            fontsize=13, fontweight='bold', pad=20
        )

        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        ax.legend(loc='upper left')
        plt.tight_layout()

        chart_path = os.path.join(self.save_dir, f'{self.keyword}_{month_str}_daily.png')
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"\n趋势图已保存至：{chart_path}")

    def _save_to_excel(self):
        """保存Excel"""
        if self.df_daily.empty:
            return

        month_str = self.df_daily['统计日期'].iloc[0][:7]
        excel_path = os.path.join(self.save_dir, f'{self.keyword}_{month_str}_daily.xlsx')
        self.df_daily.to_excel(excel_path, index=False)
        print(f"数据已保存至：{excel_path}")

    def _print_summary(self):
        """打印摘要"""
        if self.df_daily.empty:
            return

        total = self.df_daily['日投稿量'].sum()
        has_data = self.df_daily[self.df_daily['日投稿量'] > 0]

        print(f"\n{'='*60}")
        print(f"统计结果摘要")
        print(f"{'='*60}")
        print(f"  IP关键词：{self.keyword}")
        print(f"  统计月份：{self.df_daily['统计日期'].iloc[0][:7]}")
        print(f"  覆盖天数：{len(self.df_daily)} 天")
        print(f"  有投稿天数：{len(has_data)} 天")
        print(f"  总投稿量：{total} 部")
        print(f"  日均投稿：{total / len(self.df_daily):.1f} 部")

        if len(has_data) > 0:
            peak = has_data.loc[has_data['日投稿量'].idxmax()]
            print(f"  峰值日期：{peak['统计日期']}（{peak['日投稿量']} 部）")


def main():
    """主函数 - 查询2026年4月"""
    analyzer = BilibiliIPDailyAnalyzer(keyword="东方Project")
    result = analyzer.run(year=2026, month=4, max_page=5)

    if result is not None:
        print("\n" + "="*60)
        print("程序执行完毕")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()