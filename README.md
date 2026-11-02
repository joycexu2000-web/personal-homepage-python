# 徐乔依 · Joyce — Personal Homepage

Qiaoyi (Joyce) Xu 的个人主页，包含个人介绍、英文简历与气象数据交互图表。

- 主页：https://joycexu2000-web.github.io/personal-homepage-python/
- 简历：https://joycexu2000-web.github.io/personal-homepage-python/myresume.html
- 简历 PDF：https://joycexu2000-web.github.io/personal-homepage-python/myresume.pdf
- Plotly：https://joycexu2000-web.github.io/personal-homepage-python/plotly.html
- Dashboard：https://joycexu2000-web.github.io/personal-homepage-python/dashboard.html

## 实现

**四个网页、个人信息正文、数据统计和交互图表均由 Python 生成**。浏览器显示标准 HTML/CSS/JavaScript；PDF 由 Python 生成 LaTeX 源文件，再调用 XeLaTeX 编译。

`build.py` 是统一入口。它读取 `profile.json` 和 `weather.csv`，重新计算 12 个月的统计量，使用 Python Plotly 创建三种图表，再生成主页、简历、图表页和仪表板。简历沿用本人已确认的版式与字体。所有页面使用站内相对链接。

## 构建

需要 Python 3.10 或更新版本。先在项目文件夹运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 build.py --pdf
python3 -m unittest -v test_site.py
```

Windows 的环境激活命令为 `.venv\Scripts\activate`。

`--pdf` 需要安装 XeLaTeX，例如 MacTeX 或包含 ctex/Fandol 字体的 TeX Live。只重新生成网页和 `.tex` 可以运行 `python3 build.py`；此时保留已有 PDF，不重新编译它。生成的 PDF 与对应 `.tex` 一起位于 docs 中。

本地预览：`python3 -m http.server 8000 --directory docs`，然后打开 http://localhost:8000/。

## 修改

- `profile.json`：姓名、联系方式、教育、工作和技能；由主页、简历及 LaTeX 共用。
- `weather.csv`：固定的 10,000 条历史样本，数据尺度见 DATA.md。
- `home.css`：主页、图表页、仪表板样式。
- `resume-template.html`：已确认的简历前端版式，Python 填入其正文。
- `resume-preamble.tex`：简历 LaTeX 排版设置。
- `test_site.py`：验证统计量、身份信息、图表数量和站内链接。

修改后重新构建并提交源码和 docs。不要只修改 docs 中的生成网页。

## GitHub Pages

仓库 Settings → Pages → Deploy from a branch → main → /docs → Save。

docs 中已包含发布文件，启用 Pages 后可直接公开访问。Python 是构建工具，不需要在 GitHub Pages 上运行服务器。Plotly JavaScript、样式与照片也随站点发布。
