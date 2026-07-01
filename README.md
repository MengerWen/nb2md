# ipynb_to_md / Notebook 转 Markdown

`ipynb_to_md` converts Jupyter Notebook files (`.ipynb`) into Markdown (`.md`) while preserving code, Markdown cells, text output, errors, images, HTML tables, JSON, LaTeX, raw cells, and attachments as much as possible.

`ipynb_to_md` 用于把 Jupyter Notebook 文件转换为 Markdown，同时尽量保留代码、Markdown、文本输出、报错、图片、HTML 表格、JSON、LaTeX、raw cell 和粘贴图片附件。

## Install / 安装

Create an isolated Conda environment named `nb2md`:

创建专用 Conda 环境 `nb2md`：

```powershell
conda create -n nb2md python=3.11 -y
conda activate nb2md
cd D:\MG\ipynb_to_md
python -m pip install -r requirements.txt
```

## Global Command / 全局命令

The wrapper is installed at:

全局 wrapper 位于：

```text
D:\MG\bin\ipynb2md.bat
```

Add `D:\MG\bin` to your user `Path`, then reopen PowerShell or CMD.

请把 `D:\MG\bin` 加入用户 `Path`，然后重新打开 PowerShell 或 CMD。

Verify:

验证：

```powershell
where.exe ipynb2md
ipynb2md --help
```

Note: in PowerShell, use `where.exe ipynb2md`, not `where ipynb2md`.

注意：PowerShell 里请用 `where.exe ipynb2md`，不要直接用 `where ipynb2md`。

## Usage / 使用

```powershell
ipynb2md "D:\path\to\notebook.ipynb"
ipynb2md "D:\path\to\notebook.ipynb" "D:\path\to\notebook.md"
ipynb2md "D:\path\to\notebook.ipynb" -o "D:\path\to\notebook.md"
ipynb2md "D:\path\to\notebook.ipynb" --html-policy auto
ipynb2md "D:\path\to\notebook.ipynb" --no-outputs
ipynb2md "D:\path\to\notebook.ipynb" --include-execution-count
ipynb2md "D:\path\to\notebook.ipynb" --cell-separators
```

If no output path is given, the Markdown file is written next to the input notebook with the same base name. Existing Markdown files are overwritten by default. Use `--no-overwrite` to fail instead.

如果不指定输出路径，默认在输入 notebook 同目录生成同名 `.md`。默认覆盖已有 Markdown；如需禁止覆盖，请使用 `--no-overwrite`。

## Output Structure / 输出结构

```text
demo.ipynb
demo.md
demo_files/
  cell_0002_output_0001.png
  cell_0003_output_0001.html
  cell_0004_attachment_image.png
```

Asset links in Markdown use relative paths with `/`.

Markdown 中的资源链接使用 `/` 风格相对路径。

## Supported Outputs / 支持的输出类型

- Markdown cells are preserved as Markdown.
- Code cells are written as fenced code blocks.
- `stream` output is written as `text` code blocks.
- Tracebacks are written as `traceback` code blocks.
- `text/markdown` is emitted directly.
- `text/latex` is kept as display math.
- `image/png`, `image/jpeg`, and `image/svg+xml` are saved into `_files`.
- HTML tables are converted to Markdown tables when safe.
- Complex HTML, Plotly, Bokeh, widgets, and rich JS output are saved as `.html` attachments.
- JSON is written as `json` code blocks or saved as `.json` for rich specs.
- Raw cells are preserved by default.
- Markdown attachments such as `attachment:image.png` are extracted and relinked.

## HTML Strategy / HTML 策略

The converter follows this rule:

转换器遵循：

```text
Convert to Markdown when accurate;
save as an attachment when Markdown would lose information;
keep raw HTML only as a fallback;
never silently drop output.
```

默认会移除普通 `<script>`，普通 HTML 通过 `markdownify` 转 Markdown；HTML 中的 base64 图片会保存到 assets。远程图片默认不下载，保留原始 URL。未来可以增加 `--download-remote-images`。

## Test Checklist / 测试清单

Use small notebooks to verify:

建议准备小 notebook 验证：

1. Markdown-only notebook.
2. Code-only notebook with no output.
3. `print()` output.
4. pandas DataFrame output.
5. matplotlib image output.
6. plain HTML output.
7. traceback output.
8. paths containing Chinese characters.
9. paths containing spaces.
10. explicit output path.
11. default output path.
12. pre-existing output `_files` folder.
13. complex HTML saved as `.html`.
14. `image/png` saved and linked.
15. `text/markdown` emitted directly.
16. `text/latex` preserved as `$$...$$`.
17. Markdown image attachment extracted from `attachment:`.
18. running the same notebook twice leaves stable assets without stale files.
19. missing input file returns a non-zero exit code with a clear error.

## FAQ / 常见问题

**Why create a new Conda environment? / 为什么要新建环境？**  
To avoid polluting existing project environments such as `base`, `rq`, `cta_v1`, `pytorch_env`, or `zhihu2Mark`。这样不会污染已有项目环境。

**Does it download remote images? / 会下载远程图片吗？**  
No. Remote image URLs are preserved in Markdown by default. 默认不下载远程图片，只保留链接。

**What happens to old assets? / 旧资源会怎样？**  
Before each conversion, the matching `<output-stem>_files` folder is cleared and recreated, so repeated runs do not leave stale generated files. 每次转换前会清理匹配的 `<输出文件名>_files` 目录，避免残留旧文件。
