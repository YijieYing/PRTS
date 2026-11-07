#!/usr/bin/env python3
"""Markdown subset -> email-safe HTML (inline styles only; mail clients drop <style> and external CSS).

Covers what the weekly report uses: #/##/### headings, paragraphs, **bold**, `code`, [links](url),
- / 1. lists, | tables |. Swiss-style: black type, one red accent, generous whitespace.
usage: render.py report.md > report.html
"""
import html
import re
import sys

ACCENT, MUTE, LINE = "#e4002b", "#7a7a75", "#e2e2dc"
FONT = "'Helvetica Neue',Helvetica,Arial,'PingFang SC','Hiragino Sans GB',sans-serif"
MONO = "'SF Mono',Menlo,Consolas,monospace"


def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", rf'<code style="font-family:{MONO};font-size:12px;background:#f2f2ee;padding:1px 4px">\1</code>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", rf'<a href="\2" style="color:{ACCENT};text-decoration:none">\1</a>', t)
    return t


def render(md):
    out, lines, i = [], md.splitlines(), 0
    para = []

    def flush():
        if para:
            out.append(f'<p style="margin:0 0 12px">{inline(" ".join(para))}</p>')
            para.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        h = re.match(r"^(#{1,3}) (.*)", line)
        if h:
            flush()
            level, text = len(h.group(1)), inline(h.group(2))
            if level == 1:
                out.append(f'<h1 style="font-size:24px;line-height:1.2;letter-spacing:-.02em;margin:0 0 6px;padding-bottom:12px;'
                           f'border-bottom:2px solid #111">{text}</h1>')
            elif level == 2:
                out.append(f'<h2 style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin:28px 0 10px;'
                           f'padding-top:8px;border-top:1px solid #111">{text}</h2>')
            else:
                out.append(f'<h3 style="font-size:14px;margin:16px 0 6px">{text}</h3>')
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            body = []
            for r, cells in enumerate(rows):
                tag, weight = ("th", "700") if r == 0 else ("td", "400")
                tds = "".join(f'<{tag} style="text-align:{"left" if c == 0 else "right"};padding:6px 14px 6px 0;'
                              f'border-bottom:1px solid {"#111" if r == 0 else LINE};font-weight:{weight};'
                              f'font-variant-numeric:tabular-nums">{inline(x)}</{tag}>' for c, x in enumerate(cells))
                body.append(f"<tr>{tds}</tr>")
            out.append(f'<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;margin:4px 0 14px">{"".join(body)}</table>')
        elif re.match(r"^\s*([-*]|\d+\.) ", line):
            flush()
            ordered = bool(re.match(r"^\s*\d+\.", line))
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i]))
                i += 1
            i -= 1
            tag = "ol" if ordered else "ul"
            lis = "".join(f'<li style="margin:0 0 6px">{inline(x)}</li>' for x in items)
            out.append(f'<{tag} style="margin:0 0 12px;padding-left:20px">{lis}</{tag}>')
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return (f'<div style="max-width:680px;margin:0 auto;padding:28px 20px;font-family:{FONT};font-size:14px;'
            f'line-height:1.65;color:#111;background:#fff">{"".join(out)}'
            f'<p style="margin:28px 0 0;padding-top:10px;border-top:1px solid {LINE};font-size:11px;color:{MUTE};'
            f'letter-spacing:.06em">PRTS REPORTER · 只发给你本人</p></div>')


if __name__ == "__main__":
    print(render(open(sys.argv[1], encoding="utf-8").read()))
