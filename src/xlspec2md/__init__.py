# -*- coding: utf-8 -*-
"""xlspec2md: 基本設計書 Excel → Markdown / JSON IR / mockup HTML"""
from .engine import convert_file
from .models import DocumentIR

__all__ = ["convert_file", "DocumentIR"]
__version__ = "0.1.0"
