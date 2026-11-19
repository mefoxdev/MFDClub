"""Minimal Valve KeyValues (VDF) text parser/serializer (stdlib only)."""
from __future__ import annotations


class VdfError(ValueError):
    pass


def _tokens(text: str):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == "/" and text[i:i + 2] == "//":
            while i < n and text[i] != "\n":
                i += 1
        elif c in "{}":
            yield c
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    esc = text[i + 1]
                    buf.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(esc, "\\" + esc))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            if i >= n:
                raise VdfError("unterminated string")
            i += 1
            yield ("s", "".join(buf))
        else:
            raise VdfError(f"unexpected character {c!r} at {i}")


def loads(text: str) -> dict:
    toks = list(_tokens(text))
    pos = 0

    def block() -> dict:
        nonlocal pos
        out: dict = {}
        while pos < len(toks):
            t = toks[pos]
            if t == "}":
                pos += 1
                return out
            if not isinstance(t, tuple):
                raise VdfError("expected key")
            key = t[1]
            pos += 1
            if pos >= len(toks):
                raise VdfError("missing value")
            v = toks[pos]
            if v == "{":
                pos += 1
                out[key] = block()
            elif isinstance(v, tuple):
                out[key] = v[1]
                pos += 1
            else:
                raise VdfError("unexpected token")
        return out

    result = block()
    return result


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def dumps(data: dict, indent: int = 0) -> str:
    pad = "\t" * indent
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f'{pad}"{_esc(k)}"\n{pad}{{\n{dumps(v, indent + 1)}{pad}}}\n')
        else:
            lines.append(f'{pad}"{_esc(k)}"\t\t"{_esc(str(v))}"\n')
    return "".join(lines)
