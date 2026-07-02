from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import re
import shutil
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import nbformat
import pandas as pd
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown


VERSION = "1.0.0"


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(item) for item in value)
    return str(value)


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def sanitize_filename(name: str, fallback: str = "asset") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned or fallback


def fence_block(content: str, language: str = "text") -> str:
    content = content.rstrip("\n")
    longest = max((len(match.group(0)) for match in re.finditer(r"`{3,}", content)), default=2)
    fence = "`" * max(3, longest + 1)
    language = language.strip()
    return f"{fence}{language}\n{content}\n{fence}"


def json_text(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return value
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    return json.dumps(value, ensure_ascii=False, indent=2)


def is_json_mime(mime: str) -> bool:
    return mime == "application/json" or (mime.startswith("application/vnd.") and mime.endswith("+json"))


def image_extension(mime: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/svg+xml": ".svg",
    }.get(mime, ".bin")


@dataclass
class Config:
    input_path: Path
    output_path: Path
    asset_dir: Path
    code_fence_language: str = "python"
    include_execution_count: bool = False
    include_cell_separators: bool = False
    include_outputs: bool = True
    skip_raw: bool = False
    html_policy: str = "auto"
    image_policy: str = "save"
    table_policy: str = "auto"
    output_style: str = "callout"
    overwrite: bool = True
    strict_mode: bool = False
    prefer_mime_order: list[str] = field(
        default_factory=lambda: [
            "text/markdown",
            "text/latex",
            "image/png",
            "image/jpeg",
            "image/svg+xml",
            "text/html",
            "application/json",
            "text/plain",
        ]
    )


class AssetManager:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.asset_dir = config.asset_dir
        self.output_path = config.output_path
        self._used_names: set[str] = set()
        self._prepared = False

    def prepare(self) -> None:
        if self._prepared:
            return
        expected = f"{self.output_path.stem}_files"
        if self.asset_dir.exists() and self.asset_dir.is_dir() and self.asset_dir.name == expected:
            shutil.rmtree(self.asset_dir)
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self._prepared = True

    def unique_filename(self, desired: str) -> str:
        desired = sanitize_filename(desired)
        stem = Path(desired).stem or "asset"
        suffix = Path(desired).suffix
        candidate = f"{stem}{suffix}"
        index = 2
        while candidate.lower() in self._used_names or (self.asset_dir / candidate).exists():
            candidate = f"{stem}_{index:02d}{suffix}"
            index += 1
        self._used_names.add(candidate.lower())
        return candidate

    def save_binary(self, desired: str, data: bytes) -> Path:
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        filename = self.unique_filename(desired)
        path = self.asset_dir / filename
        path.write_bytes(data)
        return path

    def save_text(self, desired: str, text: str) -> Path:
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        filename = self.unique_filename(desired)
        path = self.asset_dir / filename
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def relative_path(self, path: Path) -> str:
        rel = os.path.relpath(path, self.output_path.parent)
        return rel.replace("\\", "/")

    def decode_and_save_base64(self, desired: str, encoded: str) -> Path:
        compact = re.sub(r"\s+", "", encoded)
        data = base64.b64decode(compact, validate=False)
        return self.save_binary(desired, data)


class OutputRenderer:
    def __init__(self, config: Config, assets: AssetManager) -> None:
        self.config = config
        self.assets = assets

    def render_outputs(self, outputs: list[Any], cell_index: int) -> str:
        rendered: list[str] = []
        for output_index, output in enumerate(outputs, start=1):
            chunk = self.render_output(output, cell_index, output_index)
            if chunk.strip():
                rendered.append(chunk.strip("\n"))
        return "\n\n".join(rendered)

    def render_output(self, output: Any, cell_index: int, output_index: int) -> str:
        output_type = output.get("output_type", "")
        if output_type == "stream":
            return self.render_stream(output)
        if output_type == "error":
            return self.render_error(output)
        if output_type in {"display_data", "execute_result"}:
            return self.render_display_or_execute_result(output, cell_index, output_index)
        return self.render_plain_text(as_text(output))

    def render_stream(self, output: Any) -> str:
        text = as_text(output.get("text", ""))
        if not text:
            return ""
        return fence_block(text, "text")

    def render_error(self, output: Any) -> str:
        traceback = output.get("traceback")
        if traceback:
            text = "\n".join(as_text(line) for line in traceback)
        else:
            ename = as_text(output.get("ename", "Error"))
            evalue = as_text(output.get("evalue", ""))
            text = f"{ename}: {evalue}".strip()
        return fence_block(text, "traceback")

    def render_display_or_execute_result(self, output: Any, cell_index: int, output_index: int) -> str:
        data = output.get("data", {}) or {}
        if not isinstance(data, dict):
            return self.render_plain_text(as_text(data))

        if "text/markdown" in data:
            return self.render_markdown(data["text/markdown"])
        if "text/latex" in data:
            return self.render_latex(data["text/latex"])

        for mime in ("image/png", "image/jpeg", "image/svg+xml"):
            if mime in data:
                return self.render_image(data[mime], mime, cell_index, output_index)

        if "text/html" in data:
            html_result = self.render_html(data["text/html"], cell_index, output_index)
            if html_result.strip():
                return html_result

        json_mime = next((mime for mime in data if is_json_mime(mime)), None)
        if json_mime:
            return self.render_json(data[json_mime], json_mime, cell_index, output_index)

        if "text/plain" in data:
            return self.render_plain_text(data["text/plain"])

        if data:
            return self.render_json(dict(data), "application/json", cell_index, output_index)
        return ""

    def render_markdown(self, value: Any) -> str:
        return ensure_trailing_newline(as_text(value)).strip("\n")

    def render_latex(self, value: Any) -> str:
        text = as_text(value).strip()
        if not text:
            return ""
        if (text.startswith("$$") and text.endswith("$$")) or (text.startswith("\\[") and text.endswith("\\]")):
            return text
        if text.startswith("$") and text.endswith("$"):
            return text
        return f"$$\n{text}\n$$"

    def render_image(self, value: Any, mime: str, cell_index: int, output_index: int) -> str:
        if self.config.image_policy == "skip":
            return ""
        ext = image_extension(mime)
        text = as_text(value)
        if self.config.image_policy == "inline_base64" and mime != "image/svg+xml":
            compact = re.sub(r"\s+", "", text)
            return f"![output](data:{mime};base64,{compact})"
        filename = f"cell_{cell_index:04d}_output_{output_index:04d}{ext}"
        if mime == "image/svg+xml":
            path = self.assets.save_text(filename, text)
        else:
            path = self.assets.decode_and_save_base64(filename, text)
        return f"![output]({self.assets.relative_path(path)})"

    def render_html(self, value: Any, cell_index: int, output_index: int) -> str:
        raw_html = as_text(value).strip()
        if not raw_html:
            return ""
        if self.config.html_policy == "keep":
            return raw_html
        if self.config.html_policy == "asset":
            return self.save_html_attachment(raw_html, cell_index, output_index)

        soup = BeautifulSoup(raw_html, "html.parser")
        if self.is_complex_html(raw_html, soup):
            return self.save_html_attachment(raw_html, cell_index, output_index)

        self.rewrite_data_images(soup, cell_index, output_index)

        style_tags = soup.find_all("style")
        if self.has_important_style(style_tags):
            return self.save_html_attachment(raw_html, cell_index, output_index)
        for tag in soup.find_all("script"):
            tag.decompose()
        for tag in style_tags:
            tag.decompose()

        if self.config.table_policy != "html" and soup.find("table") and self.is_table_focused(soup):
            table_md = self.render_html_tables(str(soup))
            if table_md.strip():
                return table_md

        converted = html_to_markdown(str(soup), heading_style="ATX").strip()
        if converted:
            return converted
        return self.save_html_attachment(raw_html, cell_index, output_index)

    def rewrite_data_images(self, soup: BeautifulSoup, cell_index: int, output_index: int) -> None:
        image_count = 0
        for img in soup.find_all("img"):
            src = img.get("src", "")
            match = re.match(r"data:(image/[^;]+);base64,(.+)", src, flags=re.I | re.S)
            if not match:
                continue
            image_count += 1
            mime = match.group(1).lower()
            ext = image_extension(mime)
            filename = f"cell_{cell_index:04d}_output_{output_index:04d}_html_image_{image_count:04d}{ext}"
            path = self.assets.decode_and_save_base64(filename, match.group(2))
            img["src"] = self.assets.relative_path(path)

    def is_complex_html(self, raw_html: str, soup: BeautifulSoup) -> bool:
        lowered = raw_html.lower()
        complex_markers = [
            "plotly",
            "bokeh",
            "requirejs",
            "application/vnd",
            "jupyter-widget",
            "widget-view",
            "vega-embed",
        ]
        if soup.find("script"):
            return True
        return any(marker in lowered for marker in complex_markers)

    def has_important_style(self, style_tags: list[Any]) -> bool:
        text = "\n".join(tag.get_text(" ", strip=True).lower() for tag in style_tags)
        important = ["background-color", "font-weight", "color:", "border", "display:none", "visibility:hidden"]
        if not text:
            return False
        return any(marker in text for marker in important) and "dataframe" not in text

    def is_table_focused(self, soup: BeautifulSoup) -> bool:
        clone = BeautifulSoup(str(soup), "html.parser")
        for tag in clone.find_all(["table", "style", "script"]):
            tag.decompose()
        return not clone.get_text(" ", strip=True)

    def render_html_tables(self, html_value: str) -> str:
        if self.config.table_policy == "html":
            return ""
        try:
            tables = pd.read_html(io.StringIO(html_value))
        except Exception:
            if self.config.table_policy == "markdown":
                raise
            return ""
        rendered: list[str] = []
        for df in tables:
            try:
                rendered.append(df.to_markdown(index=False))
            except Exception:
                if self.config.table_policy == "markdown":
                    raise
        return "\n\n".join(rendered)

    def save_html_attachment(self, raw_html: str, cell_index: int, output_index: int) -> str:
        filename = f"cell_{cell_index:04d}_output_{output_index:04d}.html"
        document = raw_html
        if "<html" not in raw_html.lower():
            document = f"<!doctype html>\n<meta charset=\"utf-8\">\n{raw_html}"
        path = self.assets.save_text(filename, document)
        return f"[HTML output]({self.assets.relative_path(path)})"

    def render_json(self, value: Any, mime: str, cell_index: int, output_index: int) -> str:
        text = json_text(value)
        lowered = mime.lower() + " " + text[:500].lower()
        if any(marker in lowered for marker in ["plotly", "vega", "application/vnd"]):
            filename = f"cell_{cell_index:04d}_output_{output_index:04d}.json"
            path = self.assets.save_text(filename, text)
            return f"[JSON output]({self.assets.relative_path(path)})"
        return fence_block(text, "json")

    def render_plain_text(self, value: Any) -> str:
        text = as_text(value)
        if not text:
            return ""
        return fence_block(text, "text")


class NotebookConverter:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.assets = AssetManager(config)
        self.renderer = OutputRenderer(config, self.assets)
        self.nb: Any = None

    def load_notebook(self) -> None:
        with self.config.input_path.open("r", encoding="utf-8") as handle:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Cell is missing an id field.*")
                self.nb = nbformat.read(handle, as_version=4)
        self.config.code_fence_language = self.detect_language()

    def detect_language(self) -> str:
        metadata = self.nb.get("metadata", {}) if self.nb else {}
        for path in (("kernelspec", "language"), ("language_info", "name")):
            value: Any = metadata
            for key in path:
                value = value.get(key, {}) if isinstance(value, dict) else {}
            if isinstance(value, str) and value.strip():
                return value.strip()
        return self.config.code_fence_language or "python"

    def convert(self) -> str:
        if self.nb is None:
            self.load_notebook()
        self.assets.prepare()
        parts: list[str] = []
        cells = self.nb.get("cells", [])
        for cell_index, cell in enumerate(cells, start=1):
            chunk = self.render_cell(cell, cell_index)
            if not chunk.strip():
                continue
            if self.config.include_cell_separators:
                parts.append(f"<!-- cell {cell_index:04d} -->\n\n{chunk.strip()}")
            else:
                parts.append(chunk.strip("\n"))
        return "\n\n".join(parts).rstrip() + "\n"

    def render_cell(self, cell: Any, cell_index: int) -> str:
        cell_type = cell.get("cell_type", "")
        if cell_type == "markdown":
            return self.render_markdown_cell(cell, cell_index)
        if cell_type == "code":
            return self.render_code_cell(cell, cell_index)
        if cell_type == "raw":
            return self.render_raw_cell(cell)
        return as_text(cell.get("source", ""))

    def render_markdown_cell(self, cell: Any, cell_index: int) -> str:
        text = as_text(cell.get("source", ""))
        attachments = cell.get("attachments", {}) or {}
        if attachments:
            text = self.extract_attachments(text, attachments, cell_index)
        return ensure_trailing_newline(text)

    def extract_attachments(self, text: str, attachments: dict[str, Any], cell_index: int) -> str:
        replacements: dict[str, str] = {}
        for attachment_name, bundle in attachments.items():
            if not isinstance(bundle, dict):
                continue
            mime = next((key for key in ("image/png", "image/jpeg", "image/svg+xml") if key in bundle), None)
            if mime is None and bundle:
                mime = next(iter(bundle.keys()))
            if mime is None:
                continue
            ext = image_extension(mime)
            desired = f"cell_{cell_index:04d}_attachment_{sanitize_filename(Path(attachment_name).stem)}{ext}"
            if mime == "image/svg+xml":
                path = self.assets.save_text(desired, as_text(bundle[mime]))
            else:
                path = self.assets.decode_and_save_base64(desired, as_text(bundle[mime]))
            replacements[attachment_name] = self.assets.relative_path(path)

        for original, relative in replacements.items():
            text = text.replace(f"attachment:{original}", relative)
            text = text.replace(f"attachment:{quote(original)}", relative)
        return text

    def render_code_cell(self, cell: Any, cell_index: int) -> str:
        source = as_text(cell.get("source", ""))
        execution_count = cell.get("execution_count")
        if self.config.include_execution_count:
            if execution_count is not None:
                source = f"# In[{execution_count}]:\n{source}"
        pieces = [fence_block(source, self.config.code_fence_language)]
        if self.config.include_outputs:
            outputs = cell.get("outputs", []) or []
            rendered_outputs = self.renderer.render_outputs(outputs, cell_index)
            if rendered_outputs.strip():
                if self.config.output_style == "callout":
                    pieces.append(self.format_output_callout(rendered_outputs, execution_count))
                else:
                    pieces.append(rendered_outputs)
        return "\n\n".join(pieces)

    def format_output_callout(self, text: str, execution_count: Any) -> str:
        title = "Output"
        if self.config.include_execution_count and execution_count is not None:
            title = f"{title} [{execution_count}]"
        lines = [f"> [!nb-output] {title}"]
        for line in text.splitlines():
            lines.append(">" if line == "" else f"> {line}")
        return "\n".join(lines)

    def render_raw_cell(self, cell: Any) -> str:
        if self.config.skip_raw:
            return ""
        return ensure_trailing_newline(as_text(cell.get("source", "")))

    def write_files(self, content: str) -> None:
        if self.config.output_path.exists() and not self.config.overwrite:
            raise FileExistsError(f"Output file already exists: {self.config.output_path}")
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.output_path.write_text(content, encoding="utf-8", newline="\n")


def build_config(args: argparse.Namespace) -> Config:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input notebook does not exist: {input_path}")
    if input_path.suffix.lower() != ".ipynb":
        raise ValueError(f"Input file must be a .ipynb notebook: {input_path}")

    output_arg = args.output or args.output_pos
    if args.output and args.output_pos:
        raise ValueError("Specify output either as positional OUTPUT or with -o/--output, not both.")
    output_path = Path(output_arg).expanduser().resolve() if output_arg else input_path.with_suffix(".md")
    asset_dir = output_path.parent / f"{output_path.stem}_files"

    return Config(
        input_path=input_path,
        output_path=output_path,
        asset_dir=asset_dir,
        include_execution_count=args.include_execution_count,
        include_cell_separators=args.cell_separators,
        include_outputs=not args.no_outputs,
        skip_raw=args.skip_raw,
        html_policy=args.html_policy,
        image_policy=args.image_policy,
        table_policy=args.table_policy,
        output_style=args.output_style,
        overwrite=not args.no_overwrite,
        strict_mode=args.strict,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ipynb2md",
        description="Convert a Jupyter .ipynb notebook to Markdown while preserving outputs and assets.",
    )
    parser.add_argument("input", help="Input .ipynb file")
    parser.add_argument("output_pos", nargs="?", help="Optional output .md file")
    parser.add_argument("-o", "--output", help="Output .md file")
    parser.add_argument("--html-policy", choices=["auto", "convert", "keep", "asset"], default="auto")
    parser.add_argument("--image-policy", choices=["save", "inline_base64", "skip"], default="save")
    parser.add_argument("--table-policy", choices=["auto", "markdown", "html"], default="auto")
    parser.add_argument(
        "--output-style",
        choices=["callout", "plain"],
        default="callout",
        help="Render code cell outputs as Obsidian callouts or preserve the old plain layout",
    )
    parser.add_argument("--no-outputs", action="store_true", help="Do not include code cell outputs")
    parser.add_argument("--include-execution-count", action="store_true", help="Add execution count comments above code")
    parser.add_argument("--cell-separators", action="store_true", help="Insert HTML comments between cells")
    parser.add_argument("--skip-raw", action="store_true", help="Skip raw cells")
    parser.add_argument("--overwrite", action="store_true", help="Compatibility flag: overwrite is the default")
    parser.add_argument("--no-overwrite", action="store_true", help="Fail if the output Markdown already exists")
    parser.add_argument("--strict", action="store_true", help="Raise on recoverable conversion problems")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        config = build_config(args)
        converter = NotebookConverter(config)
        converter.load_notebook()
        content = converter.convert()
        converter.write_files(content)
        print(f"Wrote Markdown: {config.output_path}")
        print(f"Wrote assets:   {config.asset_dir}")
        return 0
    except Exception as exc:
        print(f"ipynb2md error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
