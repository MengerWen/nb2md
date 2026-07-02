# ipynb_to_md

## English

`ipynb_to_md` converts Jupyter Notebook files (`.ipynb`) into Markdown (`.md`) while preserving code, Markdown cells, text output, errors, images, HTML tables, JSON, LaTeX, raw cells, and attachments as much as possible.

### Install

Create an isolated Conda environment named `nb2md`:

```powershell
conda create -n nb2md python=3.11 -y
conda activate nb2md
cd D:\MG\ipynb_to_md
python -m pip install -r requirements.txt
```

### Global Command

The wrapper is installed at:

```text
D:\MG\bin\ipynb2md.bat
```

Add `D:\MG\bin` to your user `Path`, then reopen PowerShell or CMD.

Verify:

```powershell
where.exe ipynb2md
ipynb2md --help
```

Note: in PowerShell, use `where.exe ipynb2md`, not `where ipynb2md`.

### Usage

```powershell
ipynb2md "D:\path\to\notebook.ipynb"
ipynb2md "D:\path\to\notebook.ipynb" "D:\path\to\notebook.md"
ipynb2md "D:\path\to\notebook.ipynb" -o "D:\path\to\notebook.md"
ipynb2md "D:\path\to\notebook.ipynb" --html-policy auto
ipynb2md "D:\path\to\notebook.ipynb" --no-outputs
ipynb2md "D:\path\to\notebook.ipynb" --include-execution-count
ipynb2md "D:\path\to\notebook.ipynb" --cell-separators
ipynb2md "D:\path\to\notebook.ipynb" --output-style plain
```

If no output path is given, the Markdown file is written next to the input notebook with the same base name. Existing Markdown files are overwritten by default. Use `--no-overwrite` to fail instead.

### Output Style

By default, code cell outputs are wrapped in an Obsidian callout:

````markdown
> [!nb-output] Output
> ```text
> hello
> ```
````

This makes rendered outputs visibly different from author-written notebook Markdown cells. The callout wrapper applies uniformly to stream output, tracebacks, plain text, JSON, images, `text/markdown`, LaTeX, HTML tables converted to Markdown, and HTML/JSON asset links. Empty lines inside the output are also quoted so the callout does not end early.

Use `--output-style plain` to keep the old layout without callouts:

```powershell
ipynb2md "D:\path\to\notebook.ipynb" --output-style plain
```

In Obsidian, `[!nb-output]` renders as a callout. In renderers that do not support Obsidian callouts, such as GitHub, it degrades to a normal blockquote and remains visually distinguishable.

### Output Structure

```text
demo.ipynb
demo.md
demo_files/
  cell_0002_output_0001.png
  cell_0003_output_0001.html
  cell_0004_attachment_image.png
```

Asset links in Markdown use relative paths with `/`.

### Supported Outputs

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

### HTML Strategy

The converter follows this rule:

```text
Convert to Markdown when accurate;
save as an attachment when Markdown would lose information;
keep raw HTML only as a fallback;
never silently drop output.
```

By default, ordinary `<script>` blocks are removed, normal HTML is converted through `markdownify`, base64 images inside HTML are saved to assets, and remote images are kept as URLs without downloading. A future `--download-remote-images` option can be added if needed.

### Test Checklist

Use small notebooks to verify:

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

### FAQ

**Why create a new Conda environment?**  
To avoid polluting existing project environments such as `base`, `rq`, `cta_v1`, `pytorch_env`, or `zhihu2Mark`.

**Does it download remote images?**  
No. Remote image URLs are preserved in Markdown by default.

**What happens to old assets?**  
Before each conversion, the matching `<output-stem>_files` folder is cleared and recreated, so repeated runs do not leave stale generated files.

## 中文

`ipynb_to_md` 用于把 Jupyter Notebook 文件（`.ipynb`）转换为 Markdown（`.md`），并尽量保留代码、Markdown 单元格、文本输出、报错、图片、HTML 表格、JSON、LaTeX、raw cell 和粘贴图片附件。

### 安装

创建专用 Conda 环境 `nb2md`：

```powershell
conda create -n nb2md python=3.11 -y
conda activate nb2md
cd D:\MG\ipynb_to_md
python -m pip install -r requirements.txt
```

### 全局命令

全局 wrapper 位于：

```text
D:\MG\bin\ipynb2md.bat
```

请把 `D:\MG\bin` 加入用户 `Path`，然后重新打开 PowerShell 或 CMD。

验证：

```powershell
where.exe ipynb2md
ipynb2md --help
```

注意：PowerShell 里请用 `where.exe ipynb2md`，不要直接用 `where ipynb2md`。

### 使用

```powershell
ipynb2md "D:\path\to\notebook.ipynb"
ipynb2md "D:\path\to\notebook.ipynb" "D:\path\to\notebook.md"
ipynb2md "D:\path\to\notebook.ipynb" -o "D:\path\to\notebook.md"
ipynb2md "D:\path\to\notebook.ipynb" --html-policy auto
ipynb2md "D:\path\to\notebook.ipynb" --no-outputs
ipynb2md "D:\path\to\notebook.ipynb" --include-execution-count
ipynb2md "D:\path\to\notebook.ipynb" --cell-separators
ipynb2md "D:\path\to\notebook.ipynb" --output-style plain
```

如果不指定输出路径，默认在输入 notebook 同目录生成同名 `.md`。默认覆盖已有 Markdown；如需禁止覆盖，请使用 `--no-overwrite`。

### 输出样式

默认情况下，code cell 的输出会包裹在 Obsidian callout 中：

````markdown
> [!nb-output] Output
> ```text
> hello
> ```
````

这样可以让运行结果与 notebook 作者手写的 Markdown 单元格明显区分。这个 callout 会统一包裹 stream、traceback、plain text、JSON、图片、`text/markdown`、LaTeX、HTML 转成的 Markdown 表格，以及 HTML/JSON 附件链接。输出内部的空行也会带 `>`，避免 callout 提前结束。

如果需要旧版行为，可以使用 `--output-style plain`：

```powershell
ipynb2md "D:\path\to\notebook.ipynb" --output-style plain
```

在 Obsidian 中，`[!nb-output]` 会渲染为 callout；在 GitHub 等不支持 Obsidian callout 的渲染器中，它会退化为普通 blockquote，但仍然能区分运行输出和手写笔记。

### 输出结构

```text
demo.ipynb
demo.md
demo_files/
  cell_0002_output_0001.png
  cell_0003_output_0001.html
  cell_0004_attachment_image.png
```

Markdown 中的资源链接使用 `/` 风格相对路径。

### 支持的输出类型

- Markdown cells 原样保留为 Markdown。
- Code cells 写成 fenced code block。
- `stream` 输出写成 `text` 代码块。
- Traceback 写成 `traceback` 代码块。
- `text/markdown` 直接作为 Markdown 输出。
- `text/latex` 保留为数学公式。
- `image/png`、`image/jpeg` 和 `image/svg+xml` 保存到 `_files` 目录。
- HTML 表格在安全时转换为 Markdown 表格。
- 复杂 HTML、Plotly、Bokeh、widgets 和复杂 JS 输出保存为 `.html` 附件。
- JSON 写成 `json` 代码块，或在富媒体 spec 场景保存为 `.json` 附件。
- Raw cells 默认保留。
- Markdown 中的 `attachment:image.png` 会被提取并改写链接。

### HTML 策略

转换器遵循：

```text
能准确转成 Markdown 的，就转成 Markdown；
转成 Markdown 会丢信息的，就保存为附件；
附件也不合适的，就原样保留 HTML；
任何时候都不悄悄丢输出。
```

默认会移除普通 `<script>`，普通 HTML 通过 `markdownify` 转 Markdown，HTML 中的 base64 图片会保存到 assets。远程图片默认不下载，只保留原始 URL。未来可以增加 `--download-remote-images`。

### 测试清单

建议准备小 notebook 验证：

1. 只有 markdown cell 的 notebook。
2. 只有 code cell、无输出。
3. code cell 有 `print()` 输出。
4. code cell 有 pandas DataFrame 输出。
5. code cell 有 matplotlib 图片输出。
6. code cell 有普通 HTML 输出。
7. code cell 有报错 traceback。
8. 路径中包含中文。
9. 路径中包含空格。
10. 指定输出路径。
11. 未指定输出路径。
12. output 文件夹已存在。
13. notebook 中有复杂 HTML，确认保存为 `.html` 附件。
14. notebook 中有 `image/png`，确认图片保存并正确引用。
15. notebook 中有 `text/markdown` output，确认直接作为 Markdown 输出。
16. notebook 中有 `text/latex` output，确认以 `$$...$$` 形式保留。
17. markdown cell 中粘贴了图片 attachment，确认图片被提取到 assets 且 `attachment:` 链接被改写。
18. 对同一 notebook 连续运行两次，确认结果稳定、assets 不残留上一次的陈旧文件。
19. 传入不存在的输入文件，确认返回非 0 退出码并给出清晰错误。

### 常见问题

**为什么要新建环境？**  
为了避免污染 `base`、`rq`、`cta_v1`、`pytorch_env`、`zhihu2Mark` 等已有项目环境。

**会下载远程图片吗？**  
不会。远程图片 URL 默认只会保留在 Markdown 中。

**旧资源会怎样？**  
每次转换前会清理匹配的 `<output-stem>_files` 目录并重新生成，所以重复运行不会留下旧的生成文件。
