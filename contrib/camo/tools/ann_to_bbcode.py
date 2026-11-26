#!/usr/bin/env python3
# Copyright (c) 2026, The CAMO Project. BSD-3-Clause, see LICENSE.
"""Convert contrib/camo/ANNOUNCE-DRAFT.md (light Markdown) to BitcoinTalk BBCode, ready to paste.

  python3 contrib/camo/tools/ann_to_bbcode.py [ANNOUNCE-DRAFT.md] > ANNOUNCE-BBCODE.txt

Handles what the draft uses: # title, ## headings, paragraphs (wrapped lines are joined), - lists (indented lines
continue the item), | tables |, ![alt](url) images, **bold**, *italic*, `code`, bare https:// links and
<!-- comments --> (dropped). ![alt|160](url) sets an image width. The first line is the thread subject
(BitcoinTalk takes it separately)."""
import re
import sys


def inline(text):
    text = re.sub(r'`([^`]+)`', lambda m: '\0tt' + m.group(1).replace('*', '\0star') + '\0/tt', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', text)
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'[i]\1[/i]', text)
    text = re.sub(r'(?<![\]=])(https?://[^\s,)]+[^\s,).])', r'[url]\1[/url]', text)
    return text.replace('\0tt', '[tt]').replace('\0/tt', '[/tt]').replace('\0star', '*')


def convert(md):
    md = re.sub(r'<!--.*?-->', '', md, flags=re.S)
    lines = md.split('\n')
    out, subject = [], None
    para, items, table = [], [], []

    def flush():
        if para:
            out.append(inline(' '.join(para)))
            out.append('')
            para.clear()
        if items:
            out.append('[list]')
            out.extend('[li]' + inline(i) + '[/li]' for i in items)
            out.append('[/list]')
            out.append('')
            items.clear()
        if table:
            rows = [r for r in table if not (re.fullmatch(r'[\s|:-]+', r) and '-' in r)]
            out.append('[table]')
            for n, row in enumerate(rows):
                cells = [c.strip() for c in row.strip().strip('|').split('|')]
                if n == 0 and all(not c for c in cells):
                    continue
                cells = [('[b]%s[/b]' % inline(c) if n == 0 and c else inline(c)) for c in cells]
                out.append('[tr]' + ''.join('[td]%s[/td]' % c for c in cells) + '[/tr]')
            out.append('[/table]')
            out.append('')
            table.clear()

    for line in lines:
        img = re.fullmatch(r'!\[([^\]]*)\]\((\S+)\)', line.strip())
        if img:
            flush()
            alt, _, width = img.group(1).partition('|')   # ![alt|width](url): width in pixels, optional
            size = ' width=%s' % width if width.isdigit() else ''
            out.append('[center][img%s]%s[/img][/center]' % (size, img.group(2)))
            out.append('')
        elif line.startswith('# '):
            flush()
            subject = line[2:].strip()
            out.append('[center][size=18pt][b]%s[/b][/size][/center]' % inline(subject))
            out.append('')
        elif line.startswith('## '):
            flush()
            out.append('[size=14pt][b]%s[/b][/size]' % inline(line[3:].strip()))
        elif line.startswith('|'):
            if para or items:
                flush()
            table.append(line)
        elif line.startswith('- '):
            if para or table:
                flush()
            items.append(line[2:].strip())
        elif line.startswith('  ') and items and line.strip():
            items[-1] += ' ' + line.strip()
        elif not line.strip():
            flush()
        else:
            if items or table:
                flush()
            para.append(line.strip())
    flush()
    while out and not out[-1]:
        out.pop()
    return subject, '\n'.join(out) + '\n'


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'contrib/camo/ANNOUNCE-DRAFT.md'
    subject, body = convert(open(path, encoding='utf-8').read())
    sys.stdout.write('Subject: %s\n\n%s' % (subject, body))
