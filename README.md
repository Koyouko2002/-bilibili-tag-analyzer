● 项目技术介绍

  1. 核心语言

  - Python 3.x - 主要编程语言

  2. 数据获取

  - requests - HTTP请求库，用于调用B站搜索API
  - session管理 - 维持cookie和请求头
  - User-Agent伪造 - 模拟浏览器访问

  3. 时间范围控制

  利用B站API的 pubtime_begin_s 和 pubtime_end_s 参数：
  时间戳转换：
  利用B站API的 pubtime_begin_s 和 pubtime_end_s 参数：
  时间戳转换：
  datetime → timestamp → API参数
  实现按月/按日/按时段精确查询

  4. 数据处理

  - pandas - 数据清洗和结构化存储
  - Excel读写 - openpyxl引擎

  5. 数据可视化

  - matplotlib - 绑定中文显示（SimHei字体）
  - 图表类型：柱状图 + 折线图组合



  6. 文件结构


 bilibili_ip_analyzer_daily.py   # 按日查询版
 bilibili_ip_analyzer_hourly.py  # 按小时查询版
 bilibili_ip_analyzer_4seg_month.py # 4段查整月


