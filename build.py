#!/usr/bin/env python3
"""Build every page, recompute weather summaries and optionally export PDFs.

Python is the only build/analysis language. A browser displays HTML/CSS/JS;
XeLaTeX compiles the Python-generated .tex sources when --pdf is requested.
"""
from __future__ import annotations
import argparse
import calendar
import csv
import html
import json
import math
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
E = html.escape
MONTHS = list(calendar.month_name)[1:]
COLORS = ["#440154", "#482173", "#433e85", "#38588c", "#2d708e", "#25858e",
          "#1e9b8a", "#2ab07f", "#52c569", "#86d549", "#c2df23", "#fde725"]


def read_weather(path: Path = ROOT / "weather.csv") -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["month"] = int(row["month"])
        row["year"] = int(row["year"])
        for name in ("tmax", "tmin", "prcp"):
            row[name] = float(row[name])
            if not math.isfinite(row[name]):
                raise ValueError(f"Non-finite {name}")
    if len(rows) != 10000 or any(r["year"] not in range(2005, 2011) for r in rows):
        raise ValueError("The approved sample must contain 10,000 rows from 2005-2010.")
    return rows


def monthly_summary(rows: list[dict]) -> list[dict]:
    result = []
    for month in range(1, 13):
        group = [row for row in rows if row["month"] == month]
        if not group:
            raise ValueError(f"No observations for month {month}")
        result.append({"month": month, "name": MONTHS[month - 1], "count": len(group),
                       "tmax_mean": statistics.mean(row["tmax"] for row in group),
                       "prcp_mean": statistics.mean(row["prcp"] for row in group)})
    return result


def make_figures(rows: list[dict], summary: list[dict]) -> list[go.Figure]:
    box, scatter, bar = go.Figure(), go.Figure(), go.Figure()
    for index, item in enumerate(summary):
        name, color = item["name"], COLORS[index]
        values = [row["tmin"] for row in rows if row["month"] == index + 1]
        box.add_trace(go.Box(x=[name] * len(values), y=values, name=name,
                             marker_color=color, line_color=color, fillcolor=color,
                             quartilemethod="linear", opacity=0.75))
        scatter.add_trace(go.Scatter(x=[name], y=[item["tmax_mean"]], name=name,
                                     mode="markers", marker={"color": color, "size": 7}))
        bar.add_trace(go.Bar(x=[name], y=[item["prcp_mean"]], name=name, marker_color=color))
    titles = ["Boxplot of Minimum Temperature Distribution in each month",
              "Mean Maximum Temperature by month", "Mean Precipitation (mm) by month"]
    ylabels = ["tmin (°C)", "mean of maximum temperature (°C)", "Mean of Precipitation (mm)"]
    for figure, title, ylabel in zip((box, scatter, bar), titles, ylabels):
        figure.update_layout(template="plotly_white", title={"text": title, "x": 0.5},
                             margin={"l": 65, "r": 15, "t": 65, "b": 90},
                             xaxis={"title": "month", "categoryorder": "array", "categoryarray": MONTHS},
                             yaxis_title=ylabel, legend_title_text="<month>",
                             font={"family": "Arial, sans-serif", "size": 12}, autosize=True)
    return [box, scatter, bar]


def nav(profile: dict, home: bool = False) -> str:
    links = (("关于我", "index.html#about"), ("教育与经历", "index.html#education"),
             ("数据作品", "index.html#projects")) if home else (("Home", "index.html"), ("Resume", "myresume.html"))
    links += (("Plotly", "plotly.html"), ("Dashboard", "dashboard.html"))
    rendered = "".join(f'<a href="{href}">{E(label)}</a>' for label, href in links)
    brand = f'{E(profile["name_en"])} · {E(profile["nickname"])}' if home else "Joyce"
    tail = '<a href="myresume.html">Resume</a><a href="index.pdf">PDF</a>' if home else '<a href="myresume.pdf">PDF</a>'
    return (f'<header class="topbar"><nav class="nav-inner" aria-label="Main navigation">'
            f'<a class="brand" href="index.html">{brand}</a>{rendered}<span class="nav-spacer"></span>'
            f'{tail}<a href="{E(profile["repository"])}">GitHub</a></nav></header>')


def document(title: str, body: str, profile: dict, *, home: bool = False,
             dashboard: bool = False, plots: bool = False) -> str:
    klass = "dashboard-page" if dashboard else ("" if home else "viz-page")
    js = '<script src="plotly.min.js"></script>' if plots else ""
    return (f'<!doctype html><html lang="{"zh-CN" if home else "en"}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="generator" content="Python">'
            f'<title>{E(title)} · Joyce</title><link rel="stylesheet" href="home.css">{js}</head>'
            f'<body class="{klass}">{nav(profile,home)}{body}</body></html>')


def home_page(p: dict) -> str:
    education = "".join(
        f'<div class="school"><p><strong>{E(item["school_zh"])}</strong></p>'
        f'<p>{E(item["period_zh"])}，{E(item["degree"])}。</p>'
        + (f'<p>GPA：{E(item["gpa"])}。</p>' if item["gpa"] else "") + '</div>'
        for item in p["education"])
    experience = '<ul>' + "".join(
        f'<li><strong>{E(job["home_label"])}</strong>（{E(job["period_zh"])}）：{E(job["summary_zh"])}</li>'
        for job in p["jobs"]) + '</ul>'
    sections = [
        ("about", "关于我", f'<p>{E(p["bio_zh"])}</p><p><a href="myresume.html">查看完整简历</a> · <a href="myresume.pdf">下载简历 PDF</a></p>'),
        ("education", "教育背景", education),
        ("experience", "工作与实习经历", experience),
        ("projects", "数据分析作品", '<p><strong>纽约州 NOAA 气象数据探索</strong><br>该作品展示散点图、柱状图与箱线图，体现了从数据整理到交互式可视化的分析实践。</p><p><a href="plotly.html">查看交互图表</a> · <a href="dashboard.html">查看仪表板</a> · <a href="https://p8105.com/dataset_noaa.html">数据集说明</a></p>'),
        ("skills", "技能与兴趣", f'<p><strong>分析工具：</strong>{E(p["tools_home"])}<br><strong>语言：</strong>中文、英文。<br><strong>个人兴趣：</strong>{E(p["hobbies_zh"])}</p>'),
        ("contact", "联系与资料", f'<p><a href="{E(p["github"])}">GitHub</a> · <a href="{E(p["linkedin"])}">LinkedIn</a></p><p><strong>Phone number：</strong>{E(p["phone"])}<br><strong>Email：</strong><a href="mailto:{E(p["email"])}">{E(p["email"])}</a><br><strong>Address：</strong>{E(p["address"])}</p>')]
    content = "".join(f'<section id="{ident}"><h2>{title}</h2>{inner}</section>' for ident, title, inner in sections)
    toc = "".join(f'<a href="#{ident}">{title}</a>' for ident, title, _ in sections)
    body = (f'<div class="page-grid"><main><div class="name-block"><h1>{E(p["name_zh"])}</h1><p class="subtitle">{E(p["nickname"])}</p></div>'
            f'<div class="hero"><img src="portrait.jpeg" alt="Qiaoyi Xu"><p>{E(p["mission_zh"])}</p>'
            f'<a class="button primary" href="index.pdf">下载个人主页 PDF</a><a class="button" href="{E(p["linkedin"])}">LinkedIn</a></div>'
            f'{content}</main><aside class="toc"><strong>本页导航</strong>{toc}<a href="index.pdf">PDF</a></aside></div>'
            f'<footer class="site-footer">{E(p["name_en"])} · 公共卫生与数据分析</footer>')
    return document(p["name_zh"], body, p, home=True)


def resume_body(p: dict) -> str:
    body = [f'<div id="qiaoyijoyce-xu" class="section level1"><h1>{E(p["resume_name"])}</h1>',
            '<div id="basic-information" class="section level2"><h2>BASIC INFORMATION</h2>',
            '<p><img src="portrait.jpeg" style="width:40%" alt="Qiaoyi Xu"></p>',
            f'<p><em>Phone number</em>: {E(p["phone"])}</p>',
            f'<p><em>Email</em>: <a href="mailto:{E(p["email"])}">{E(p["email"])}</a></p>',
            f'<p><em>Address</em>: {E(p["address"])}</p><p><br></p></div>',
            '<div id="education" class="section level2"><h2>EDUCATION</h2>']
    for item in p["education"]:
        body.append(f'<p style="text-align:left;"><strong>{E(item["school"])}</strong> <span style="float:right;">{E(item["period"])}</span></p>')
        gpa = f'<span style="float:right;">GPA:{E(item["gpa"])}</span>' if item["gpa"] else ""
        body.append(f'<p style="text-align:left;"><em>{E(item["degree"])}</em> {gpa}</p>')
    body.append('<p><br></p></div><div id="professional-experience" class="section level2"><h2>PROFESSIONAL EXPERIENCE</h2>')
    for job in p["jobs"]:
        body.append(f'<p style="text-align:left;"><strong>{E(job["company"])}</strong> <span style="float:right;">{E(job["period"])}</span></p>')
        for role in job["roles"]:
            body.append(f'<p style="text-align:left;"><em>{E(role["title"])}</em></p><ul>')
            body.extend(f'<li>{E(bullet)}</li>' for bullet in role["bullets"])
            body.append('</ul>')
    body.append(f'<p><br></p></div><div id="skills" class="section level2"><h2>SKILLS</h2><p>Languages: {E(p["languages"])}</p><p>Technical: {E(p["technical"])}</p></div></div>')
    return "\n".join(body)


def resume_page(p: dict) -> str:
    template = (ROOT / "resume-template.html").read_text(encoding="utf-8")
    if template.count("<!-- RESUME_BODY -->") != 1:
        raise ValueError("Resume template must have exactly one body marker.")
    return template.replace("<!-- RESUME_BODY -->", resume_body(p))


def plot_div(figure: go.Figure, ident: str, dashboard: bool = False) -> str:
    fig = go.Figure(figure)
    if dashboard:
        fig.update_layout(margin={"l": 60, "r": 10, "t": 55, "b": 90}, height=None, width=None)
    return pio.to_html(fig, full_html=False, include_plotlyjs=False, div_id=ident,
                       default_width="100%", default_height="100%" if dashboard else "470px",
                       config={"responsive": True, "displaylogo": False})


def plot_page(figures: list[go.Figure], p: dict) -> str:
    titles = ["Plotly box plot", "Plotly Scatter plot", "Plotly bar plot"]
    captions = ["This boxplot shows Minimum Temperature Distribution in each month during 2005-2010. It shows the possible minimum temperature range in each month. In New York, the coldest season is from December to February.",
                "This plot shows mean maximum temperature in each month during 2005-2010. The hottest time of year is during June-August.",
                "This figure shows mean precipitation in each month during 2005-2010. Precipitation is higher in June, July, and October in this sample."]
    cards = "".join(f'<section><h2>{title}</h2><div class="viz-card">{plot_div(fig, "plot-"+str(i))}</div><p>{E(caption)}</p></section>'
                    for i, (title, fig, caption) in enumerate(zip(titles, figures, captions)))
    code = '''import csv, statistics
import plotly.graph_objects as go
with open("weather.csv", newline="") as f:
    rows = list(csv.DictReader(f))
january = [float(r["tmin"]) for r in rows if int(r["month"]) == 1]
figure = go.Figure(go.Box(y=january, name="January"))'''
    body = f'<main class="viz-main"><h1>Plots of NY NOAA dataset</h1><p>10,000 complete observations from 2005-2010. Python reads the approved fixed sample, computes monthly summaries, and generates all three interactive figures.</p><details><summary>Python code</summary><pre>{E(code)}</pre></details>{cards}<h2>Dashboard</h2><p><a href="dashboard.html">Open the interactive dashboard</a></p><p><a href="{E(p["repository"])}/blob/main/build.py">View the full Python source</a></p></main>'
    return document("Plotly", body, p, plots=True)


def dashboard_page(figures: list[go.Figure], p: dict) -> str:
    labels = ["Chart A: Boxplot", "Chart B: Scatter plot", "Chart C: Bar plot"]
    cards = "".join(f'<section class="viz-card {"box-card" if i == 0 else ""}"><div class="chart-title">{title}</div><div class="plot">{plot_div(fig,"dashboard-"+str(i),True)}</div></section>'
                    for i, (title, fig) in enumerate(zip(labels, figures)))
    return document("Dashboard", '<main class="dashboard-grid">'+cards+'</main>', p, dashboard=True, plots=True)


def tex_escape(value: str) -> str:
    chars = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
             "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(chars.get(c, c) for c in value)


def resume_tex(p: dict) -> str:
    t = tex_escape
    lines = [(ROOT / "resume-preamble.tex").read_text(), r"\begin{document}",
             r"\section{"+t(p["resume_name"])+"}", r"\subsection{BASIC INFORMATION}",
             r"\includegraphics[width=0.4\linewidth]{portrait.jpeg}"+"\n",
             r"\emph{Phone number}: "+t(p["phone"])+"\n",
             r"\emph{Email}: \href{mailto:"+p["email"]+"}{"+t(p["email"])+"}\n",
             r"\emph{Address}: "+t(p["address"])+"\n", r"\bigskip", r"\subsection{EDUCATION}"]
    for item in p["education"]:
        lines += [r"\textbf{"+t(item["school"])+r"} \hfill "+t(item["period"])+"\n",
                  r"\emph{"+t(item["degree"])+"}"+(r" \hfill GPA:"+t(item["gpa"]) if item["gpa"] else "")+"\n"]
    lines += [r"\bigskip", r"\subsection{PROFESSIONAL EXPERIENCE}"]
    for i, job in enumerate(p["jobs"]):
        if i == 1:
            lines.append(r"\newpage")
        lines.append(r"\textbf{"+t(job["company"])+r"} \hfill "+t(job["period"])+"\n")
        for role in job["roles"]:
            lines += [r"\emph{"+t(role["title"])+"}\n",r"\begin{itemize}",r"\tightlist"]
            lines.extend(r"\item "+t(bullet) for bullet in role["bullets"])
            lines.append(r"\end{itemize}")
    lines += [r"\bigskip",r"\subsection{SKILLS}","Languages: "+t(p["languages"])+"\n",
              "Technical: "+t(p["technical"]),r"\end{document}"]
    return "\n".join(lines)


def home_tex(p: dict) -> str:
    t=tex_escape
    lines=[r"\documentclass[UTF8,fontset=fandol,a4paper,10pt]{ctexart}",r"\usepackage[margin=22mm]{geometry}",
           r"\usepackage{graphicx,pdfpages}",r"\usepackage[colorlinks=true,urlcolor=blue]{hyperref}",r"\setlength{\parindent}{0pt}",
           r"\setlength{\parskip}{6pt}",r"\title{"+t(p["name_zh"])+"}",r"\author{"+t(p["nickname"])+"}",r"\date{}",
           r"\begin{document}",r"\maketitle",r"\section*{关于我}",t(p["bio_zh"]),r"\section*{教育背景}"]
    for item in p["education"]:
        lines += [r"\textbf{"+t(item["school_zh"])+"}\n",t(item["period_zh"])+"，"+t(item["degree"])+"。\n"]
        if item["gpa"]:lines.append("GPA："+t(item["gpa"])+"。\n")
    lines += [r"\section*{工作与实习经历}",r"\begin{itemize}"]
    for job in p["jobs"]:lines.append(r"\item \textbf{"+t(job["home_label"])+"}（"+t(job["period_zh"])+"）："+t(job["summary_zh"]))
    lines += [r"\end{itemize}",r"\section*{数据分析作品}","纽约州 NOAA 气象数据探索。",
              r"\href{"+p["site_url"]+r"plotly.html}{Plotly} · \href{"+p["site_url"]+"dashboard.html}{Dashboard}",
              r"\section*{技能与兴趣}","分析工具："+t(p["tools_home"])+r"\\ 语言：中文、英文。\\ 个人兴趣："+t(p["hobbies_zh"]),
              r"\section*{联系与资料}","Phone number: "+t(p["phone"])+r"\\ Email: \href{mailto:"+p["email"]+"}{"+t(p["email"])+r"}\\ Address: "+t(p["address"]),r"\end{document}"]
    lines[-1:] = [r"\clearpage", r"\includepdf[pages=-]{myresume.pdf}",
                  r"\clearpage", r"\section*{数据分析作品：纽约州 NOAA 气象数据}",
                  "以下图表由 Python 基于 2005-2010 年的 10,000 条完整气象样本生成。按月份汇总全部年份；温度单位为摄氏度，降水单位为毫米。图表用于描述该固定样本的季节性特征。",
                  r"\href{https://p8105.com/dataset_noaa.html}{数据来源与说明}；完整样本及处理方法随网站源码提供。",
                  r"\subsection*{1. 每月最低温度分布}",
                  r"\includegraphics[width=\linewidth]{chart-box.pdf}",
                  "箱体表示第 25 至第 75 百分位数，中线表示中位数，须线延伸至 1.5 倍四分位距以内的观测值，圆点表示其余观测值。暖季的最低温度整体较高，冬季分布较低且离散程度更大。",
                  r"\href{"+p["site_url"]+r"plotly.html}{查看在线交互图表}",
                  r"\clearpage",r"\section*{数据分析作品（续）}",r"\subsection*{2. 每月平均最高温度}",
                  r"\includegraphics[width=\linewidth]{chart-temperature.pdf}",
                  "每个点表示样本中对应月份的最高温度均值。7 月附近达到高值，冬季较低，显示出清晰的季节性变化。各月份样本量不同，均值未作站点或年份加权，不能据此推断长期气候趋势。",
                  r"\href{"+p["site_url"]+r"plotly.html}{查看在线交互图表}",
                  r"\clearpage",r"\section*{数据分析作品（续）}",r"\subsection*{3. 每月平均日降水量}",
                  r"\includegraphics[width=\linewidth]{chart-precipitation.pdf}",
                  "柱高表示样本中对应月份的平均日降水量，包含无降水观测，并非月累计降水量。该固定样本中 10 月的均值最高；月份之间的差异仅作描述性展示，不代表统计检验结果。",
                  r"\href{"+p["site_url"]+r"dashboard.html}{查看在线 Dashboard}。PDF 为静态展示；悬停、缩放和图例筛选请使用在线版本。",
                  r"\end{document}"]
    return "\n".join(lines)


def static_charts(rows: list[dict], summary: list[dict]) -> None:
    """Render vector figures from the same data used by the interactive pages."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42})
    names = ["chart-box", "chart-temperature", "chart-precipitation"]
    titles = ["Minimum temperature distribution by month",
              "Mean maximum temperature by month", "Mean daily precipitation by month"]
    labels = ["Minimum temperature (°C)", "Mean maximum temperature (°C)",
              "Mean daily precipitation (mm)"]
    for i, name in enumerate(names):
        fig, ax = plt.subplots(figsize=(8.2, 5.0), layout="constrained")
        if i == 0:
            values = [[r["tmin"] for r in rows if r["month"] == m] for m in range(1, 13)]
            boxes = ax.boxplot(values, patch_artist=True, tick_labels=MONTHS,
                               medianprops={"color": "#203d49"},
                               flierprops={"markersize": 2, "alpha": 0.35})
            for box, color in zip(boxes["boxes"], COLORS):
                box.set_facecolor(color)
                box.set_alpha(0.7)
        elif i == 1:
            ax.scatter(range(1,13), [x["tmax_mean"] for x in summary], c=COLORS, s=55)
        else:
            ax.bar(range(1,13), [x["prcp_mean"] for x in summary], color=COLORS, width=0.72)
        ax.set_xticks(range(1,13), MONTHS, rotation=45, ha="right")
        ax.set(xlabel="Month", ylabel=labels[i], title=titles[i])
        ax.grid(axis="y", alpha=0.18)
        ax.set_axisbelow(True)
        fig.savefig(OUT / (name + ".pdf"))
        plt.close(fig)


def compile_pdfs() -> None:
    engine = shutil.which("xelatex")
    if not engine and Path("/Library/TeX/texbin/xelatex").exists():
        engine = "/Library/TeX/texbin/xelatex"
    if not engine:
        raise RuntimeError("XeLaTeX is required for --pdf. Install MacTeX or TeX Live with ctex/Fandol.")
    for filename in ("myresume.tex", "index.tex"):
        for _ in range(2):
            run = subprocess.run([engine,"-interaction=nonstopmode","-halt-on-error",filename],
                                 cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            if run.returncode:
                raise RuntimeError(filename+" failed:\n"+run.stdout[-6000:])
        for ext in (".aux", ".log", ".out"):
            (OUT / Path(filename).with_suffix(ext)).unlink(missing_ok=True)


def build(pdf: bool = False) -> None:
    p = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    rows = read_weather()
    summary = monthly_summary(rows)
    figures = make_figures(rows, summary)
    OUT.mkdir(exist_ok=True)
    files = {"index.html": home_page(p), "myresume.html": resume_page(p),
             "plotly.html": plot_page(figures,p), "dashboard.html": dashboard_page(figures,p),
             "index.tex": home_tex(p), "myresume.tex": resume_tex(p),
             "monthly-summary.json": json.dumps(summary,ensure_ascii=False,indent=2),
             "plotly.min.js": get_plotlyjs(), ".nojekyll": ""}
    for name, content in files.items():
        (OUT / name).write_text(content,encoding="utf-8")
    for name in ("portrait.jpeg", "home.css"):
        shutil.copy2(ROOT / name, OUT / name)
    if pdf:
        static_charts(rows, summary)
        compile_pdfs()
    print("Built 4 pages with Python; recomputed 12 monthly summaries from 10,000 rows.")
    if pdf:
        print("Exported index.pdf and myresume.pdf with XeLaTeX.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", action="store_true", help="Also compile the generated LaTeX PDFs.")
    build(parser.parse_args().pdf)
