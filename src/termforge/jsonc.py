"""Lector de JSON con comentarios (JSONC).

El settings.json de Windows Terminal permite comentarios (// y /* */) y comas
finales, que el módulo json estándar rechaza. Este módulo los limpia sin tocar
el contenido de los strings.
"""

from __future__ import annotations

import json
from typing import Any


def strip_jsonc(text: str) -> str:
    """Quita comentarios y comas finales, respetando los strings."""
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False

    while i < n:
        c = text[i]

        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue

        if c == '"':
            in_string = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] not in "\r\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end == -1:
                raise ValueError("comentario /* sin cerrar")
            i = end + 2
        else:
            out.append(c)
            i += 1

    return _remove_trailing_commas("".join(out))


def _remove_trailing_commas(text: str) -> str:
    out: list[str] = []
    in_string = False
    i, n = 0, len(text)

    while i < n:
        c = text[i]

        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue

        if c == '"':
            in_string = True
        elif c == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
        out.append(c)
        i += 1

    return "".join(out)


def loads(text: str) -> Any:
    """Equivalente a json.loads, pero tolera comentarios, comas finales y BOM."""
    return json.loads(strip_jsonc(text.lstrip("﻿")))
