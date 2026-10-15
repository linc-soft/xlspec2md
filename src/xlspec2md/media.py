# -*- coding: utf-8 -*-
"""埋め込みメディア抽出: PNG/JPG はそのまま、EMF/WMF は LibreOffice 変換を予約。"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from .models import ImageAsset

_IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


def extract_media(xlsx_path: str) -> list[ImageAsset]:
    """画像一覧を ImageAsset 化（実ファイルの展開は convert 実行時に行う）。"""
    assets = []
    with zipfile.ZipFile(xlsx_path) as z:
        names = [n for n in z.namelist() if n.startswith("xl/media/")]
    for n in names:
        ext = Path(n).suffix.lower()
        kind = ext.lstrip(".")
        if ext in _IMG_EXT:
            assets.append(ImageAsset(name=Path(n).name, kind=kind))
        elif ext in (".emf", ".wmf"):
            assets.append(ImageAsset(name=Path(n).name, kind=kind,
                                     note="EMF/WMF: LibreOffice 変換が必要"))
    return assets


def export_media(xlsx_path: str, out_dir: Path, warnings: list[str]) -> list[Path]:
    """xl/media を out_dir に展開。EMF/WMF は soffice があれば PNG 変換。"""
    import zipfile
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    with zipfile.ZipFile(xlsx_path) as z:
        for n in z.namelist():
            if not n.startswith("xl/media/"):
                continue
            data = z.read(n)
            p = out_dir / Path(n).name
            p.write_bytes(data)
            written.append(p)
            if p.suffix.lower() in (".emf", ".wmf"):
                if soffice:
                    with tempfile.TemporaryDirectory() as td:
                        r = subprocess.run(
                            [soffice, "--headless", "--convert-to", "png",
                             "--outdir", td, str(p)],
                            capture_output=True, timeout=120)
                        png = Path(td) / (p.stem + ".png")
                        if png.exists():
                            shutil.copy(png, p.with_suffix(".png"))
                            written.append(p.with_suffix(".png"))
                        else:
                            warnings.append(f"{p.name}: EMF→PNG 変換に失敗しました")
                else:
                    warnings.append(f"{p.name}: EMF/WMF は soffice 未検出のため "
                                    f"PNG 変換をスキップしました（Docker 内では変換されます）")
    return written
