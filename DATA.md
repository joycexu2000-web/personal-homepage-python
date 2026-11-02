# 数据与内容来源

个人信息为本人已确认版本。简历的主题、字体、栏目和日期右对齐布局继承自 https://qiaoyixu.github.io/myresume.html 。前端第三方库原有许可证注释保留在版式模板中。

气象数据源为 p8105.datasets 的 ny_noaa 数据：https://github.com/p8105/p8105.datasets 。原作品说明：https://p8105.com/dataset_noaa.html 。

weather.csv 为原作品相同的 10,000 条完整历史样本，年份为 2005–2010，包含 id、date、year、month、day、tmax、tmin、prcp。温度为摄氏度；降水为毫米。保留固定样本而不改用 Python 随机重新抽样，是为了保持已有图表数值一致。

Python 独立读取 CSV，重新计算温度与降水月均值，创建箱线图、散点图和柱状图。chart-reference.json 中的计数和月均值只用于独立验证，不用于生成统计量。12 个月的样本量与 24 个均值均已和原图核对。新图的降水轴按数据实际尺度明确标为 mm。

本项目不包含 R 或 Quarto 源文件，也不在构建中调用这些工具。
