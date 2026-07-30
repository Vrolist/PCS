"""生产模式：从 Vite manifest.json 查找构建后的资源路径。"""
import json

from django import template
from django.contrib.staticfiles.finders import find
from django.utils.safestring import mark_safe

register = template.Library()

_manifest_cache = None


def _load_manifest():
    global _manifest_cache
    if _manifest_cache is None:
        manifest_path = find("frontend/.vite/manifest.json")
        if manifest_path:
            with open(manifest_path) as f:
                _manifest_cache = json.load(f)
        else:
            _manifest_cache = {}
    return _manifest_cache


@register.simple_tag
def vite_asset(source):
    """
    用法: {% vite_asset 'src/main.ts' %}
    根据 Vite manifest 输出对应的 <script> 和 <link> 标签。
    """
    manifest = _load_manifest()
    entry = manifest.get(source)
    if not entry:
        return ""

    tags = []
    # CSS（可能有多个）
    for css in entry.get("css", []):
        tags.append(f'<link rel="stylesheet" href="/static/frontend/{css}">')
    # JS
    js_file = entry.get("file")
    if js_file:
        tags.append(f'<script type="module" src="/static/frontend/{js_file}"></script>')

    return mark_safe("\n  ".join(tags))
