"""English-only, read-only manuscript comparison and local live preview (stdlib)."""
from pathlib import Path
import argparse
import difflib
import hashlib
import html
import json
import re
import threading
import time
import subprocess
import shutil
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = CURRENT = OUT = None
BASE_LABEL = 'Baseline'
CURRENT_LABEL = 'Current'
PANDOC_COMMAND = None
CJK = re.compile(r'[\u3400-\u9fff]')
MATH = re.compile(r'\$\$[\s\S]*?\$\$|(?<!\\)\$(?:\\.|[^$])*?(?<!\\)\$')
MATH_HTML = {}


def prepare_math(blocks):
    """Batch convert intact formulas to offline browser-native MathML."""
    formulas = list(dict.fromkeys(m[0] for b in blocks for m in MATH.finditer(b)))
    missing = [f for f in formulas if f not in MATH_HTML]
    if not missing:
        return
    command = PANDOC_COMMAND or ([shutil.which('pandoc')] if shutil.which('pandoc') else None)
    if not command:
        raise RuntimeError('Math requires Pandoc. Supply --pandoc-command-json with a JSON argument array.')
    snippets = []
    for f in missing:
        # Pandoc's MathML writer does not support LaTeX equation tags.
        expression = re.sub(r'\\tag\{[^}]+\}', '', f)
        snippets.append(expression)
    result = subprocess.run(command + ['-f', 'markdown+tex_math_dollars',
                             '-t', 'html5', '--mathml'], input='\n\n'.join(snippets),
                            encoding='utf-8', capture_output=True, check=True)
    rendered = re.findall(r'<math\b[\s\S]*?</math>', result.stdout)
    if len(rendered) != len(missing) or result.stderr.strip():
        raise ValueError(f'MathML conversion incomplete: {len(rendered)}/{len(missing)}. {result.stderr}')
    for formula, markup in zip(missing, rendered):
        markup = re.sub(r'<annotation\b[\s\S]*?</annotation>', '', markup)
        tag = re.search(r'\\tag\{([^}]+)\}', formula)
        number = f'<span class="eqno">({html.escape(tag[1])})</span>' if tag else ''
        MATH_HTML[formula] = '<span class="formula" title="' + html.escape(formula, quote=True) + '">' + markup + number + '</span>'


def render_text(text):
    parts, end = [], 0
    for match in MATH.finditer(text):
        parts.append(html.escape(text[end:match.start()]))
        parts.append(MATH_HTML[match[0]])
        end = match.end()
    parts.append(html.escape(text[end:]))
    return ''.join(parts)


def clean(text):
    text = re.sub(r'!\[[^\]]*\]\([^\n]*?\)', '', text)
    text = re.sub(r'</?(?:span|sub|sup|em|strong|p|div|br|a|b|i)\b[^>]*>', '', text, flags=re.I)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = text.replace('**', '').replace('__', '')
    text = re.sub(r'(?<!\\)\*([^*\n]+)\*', r'\1', text)
    text = re.sub(r'^(\[\d+\])\s*', r'\1 ', text)
    text = re.sub(r'^\s*[■●]\s*', '', text)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def extract(source):
    """Keep English paragraphs, English half of bilingual headings/cells, and math."""
    def table_to_rows(match):
        table = match[0]
        rows = []
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', table, re.S | re.I):
            cells = re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.S | re.I)
            rows.append('| ' + ' | '.join(re.sub(r'\s+', ' ', c) for c in cells) + ' |')
        caption = re.search(r'<caption\b[^>]*>(.*?)</caption>', table, re.S | re.I)
        text = '\n'.join(rows)
        if caption:
            parts = re.split(r'<br\s*/?>', caption[1], flags=re.I)
            text += '\n\n' + ' '.join(clean(p) for p in parts if not CJK.search(p))
        return '\n\n' + text + '\n\n'
    source = re.sub(r'<table\b[^>]*>.*?</table>', table_to_rows, source, flags=re.S | re.I)
    result = []
    for block in re.split(r'\n\s*\n', source):
        block = block.strip()
        if not block or block.startswith('<!--') or block.startswith('!['):
            continue
        if block.startswith('|'):
            for row in block.splitlines():
                if re.fullmatch(r'[\s|:\-]+', row):
                    continue
                cells = []
                for cell in re.split(r'(?<!\\)\|', row.strip().strip('|')):
                    parts = re.split(r'<br\s*/?>', cell, flags=re.I)
                    cells.append(' '.join(clean(p) for p in parts if not CJK.search(p)).strip())
                result.append(' | '.join(cells))
            continue
        if CJK.search(block):
            # This manuscript uses a spaced slash only for bilingual headings/captions.
            if ' / ' in block and (block.startswith('#') or block.startswith('**')):
                prefix, block = block.split(' / ', 1)
                numbering = re.match(r'^#+\s*(\d+(?:\.\d+)*)', prefix)
                english_number = re.match(r'^(\d+(?:\.\d+)*)\s+', block)
                if numbering and not english_number:
                    block = numbering[1] + ' ' + block
            else:
                continue
        block = clean(re.sub(r'^#+\s*', '', block))
        if not block or CJK.search(block) or re.fullmatch(r'[-*_\s]+', block):
            continue
        if block.lower() == 'public summary':
            block = 'Public summary'
        result.append(block)
    return result


def tokens(text):
    # Math is an indivisible token, so ins/del never splits a TeX command.
    return re.findall(MATH.pattern + r'|\s+|[\w]+(?:[’\x27][\w]+)*|[^\w\s]', text)


def word_diff(a, b):
    aa, bb = tokens(a), tokens(b)
    left, right = [], []
    for op, i, j, k, l in difflib.SequenceMatcher(None, aa, bb, autojunk=False).get_opcodes():
        x, y = render_text(''.join(aa[i:j])), render_text(''.join(bb[k:l]))
        left.append(x if op == 'equal' else '<del>' + x + '</del>' if x else '')
        right.append(y if op == 'equal' else '<ins>' + y + '</ins>' if y else '')
    return ''.join(left), ''.join(right)


def structural_keys(blocks):
    """Identify stable roles; list numbers are scoped to their enclosing section.

    References use DOI rather than mutable citation numbers. Ambiguous repeated
    identities are not used as hard anchors. Reordering still preserves each
    input's reading order and may therefore appear as insertion/deletion.
    """
    scope = 'front'
    keys = []
    for text in blocks:
        key = None
        heading = re.match(r'^(\d+(?:\.\d+)*)\s+[A-Za-z]', text)
        caption = re.match(r'^(Supplementary\s+)?(Figure|Table)\s+(\d+)(?:\.|\s*\|)', text)
        item = re.match(r'^\((\d+)\)\s', text)
        equation = re.search(r'\\tag\{([^}]+)\}', text) if text.startswith('$$') else None
        if heading and len(text) < 160 and ' | ' not in text:
            scope = heading[1]
            key = ('section', scope)
        elif caption:
            key = ('caption', caption[1] or '', caption[2], caption[3])
        elif item:
            key = ('item', scope, item[1])
        elif equation:
            key = ('equation', equation[1])
        elif re.match(r'^\[\d+\]', text):
            doi = re.search(r'10\.\d{4,9}/[^\s]+', text)
            # A number alone is not a bibliographic identity after renumbering.
            key = ('reference', doi[0].rstrip('.,;').lower()) if doi else None
        elif ' | ' in text:
            cells = text.split(' | ')
            if len(cells) > 1 and re.fullmatch(r'\d{4}', cells[1]):
                author = re.sub(r'\s*\[.*?\]', '', cells[0]).strip()
                key = ('review-row', author, cells[1])
        elif text.startswith('Abstract:'):
            key = ('abstract',)
        elif text.startswith('Keywords:'):
            key = ('keywords',)
        keys.append(key)
    return keys


def similarity(a, b):
    # autojunk's frequent-character suppression misclassifies long rewritten
    # paragraphs. Word overlap remains stable with added introductory sentences.
    aa = Counter(re.findall(r'\w+', a.lower()))
    bb = Counter(re.findall(r'\w+', b.lower()))
    total = sum(aa.values()) + sum(bb.values())
    return 2 * sum((aa & bb).values()) / total if total else float(a == b)


def align(a, b):
    """First align stable structural identities, then prose inside those bounds."""
    ka, kb = structural_keys(a), structural_keys(b)
    ca, cb = Counter(ka), Counter(kb)
    shared = {k for k in ka if k is not None and ca[k] == cb[k] == 1}
    ia = [(i, k) for i, k in enumerate(ka) if k in shared]
    ib = [(i, k) for i, k in enumerate(kb) if k in shared]
    anchors = []
    matcher = difflib.SequenceMatcher(None, [k for _, k in ia], [k for _, k in ib], autojunk=False)
    for block in matcher.get_matching_blocks():
        anchors.extend((ia[block.a + d][0], ib[block.b + d][0]) for d in range(block.size))
    x = y = 0
    for i, j in anchors:
        yield from align_prose(a[x:i], b[y:j], ka[x:i], kb[y:j])
        yield a[i], b[j]
        x, y = i + 1, j + 1
    yield from align_prose(a[x:], b[y:], ka[x:], kb[y:])


def comparison_rows(a, b):
    """Pair confident moves at the current location; label baseline relocation.

    Only unique structural identities or mutually best high-overlap prose in
    the same section qualify. Ambiguous candidates remain separate.
    """
    rows = list(align(a, b))
    ka, kb = structural_keys(a), structural_keys(b)
    scopes_a, scopes_b = [], []
    for keys, scopes in [(ka, scopes_a), (kb, scopes_b)]:
        scope = 'front'
        for key in keys:
            if key and key[0] == 'section':
                scope = key[1]
            scopes.append(scope)
    old, new = {}, {}
    i = j = 0
    for r, (x, y) in enumerate(rows):
        if x and not y:
            old[r] = (i, ka[i], scopes_a[i])
        if y and not x:
            new[r] = (j, kb[j], scopes_b[j])
        i += bool(x)
        j += bool(y)
    candidates = []
    ca, cb = Counter(ka), Counter(kb)
    for r, (i, key_a, scope_a) in old.items():
        for s, (j, key_b, scope_b) in new.items():
            if key_a is not None or key_b is not None:
                score = 1.0 if key_a == key_b and key_a is not None and ca[key_a] == cb[key_b] == 1 else 0
            elif scope_a == scope_b:
                score = similarity(rows[r][0], rows[s][1])
            else:
                score = 0
            if score >= .80:
                candidates.append((score, r, s))
    matches = {}
    removed = set()
    for score, r, s in sorted(candidates, reverse=True):
        # A close alternative is evidence of ambiguity, not an invitation to guess.
        rivals = [v for v, rr, ss in candidates if (rr == r or ss == s) and (rr, ss) != (r, s)]
        if rivals and score - max(rivals) < .08:
            continue
        if r in removed or s in matches:
            continue
        matches[s] = (r, old[r][0] + 1, new[s][0] + 1)
        removed.add(r)
    for r, (x, y) in enumerate(rows):
        if r in removed:
            continue
        if r in matches:
            origin, before, after = matches[r]
            yield rows[origin][0], y, f'Relocated for comparison · baseline block {before} → current block {after}'
        else:
            yield x, y, ''


def align_prose(a, b, ka, kb):
    """Monotonic local alignment; never pair different structural identities."""
    for op, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == 'equal':
            yield from zip(a[i:j], b[k:l])
        elif op == 'delete':
            yield from ((x, '') for x in a[i:j])
        elif op == 'insert':
            yield from (('', y) for y in b[k:l])
        else:
            old, new = a[i:j], b[k:l]
            # A single prose replacement bounded by the same neighbouring
            # anchors is comparable even when its wording changes completely.
            if len(old) == len(new) == 1 and ka[i] is None and kb[k] is None:
                yield old[0], new[0]
                continue
            m, n = len(old), len(new)
            score = [[0.] * (n + 1) for _ in range(m + 1)]
            step = {}
            for x in range(1, m + 1):
                for y in range(1, n + 1):
                    sim = similarity(old[x-1], new[y-1])
                    ak, bk = ka[i+x-1], kb[k+y-1]
                    compatible = ak == bk or (ak is None and bk is None)
                    choices = [(score[x-1][y], 'd'), (score[x][y-1], 'i')]
                    if compatible and sim >= .38:
                        choices.append((score[x-1][y-1] + sim, 'p'))
                    score[x][y], step[x, y] = max(choices)
            rows = []
            x, y = m, n
            while x or y:
                s = 'i' if not x else 'd' if not y else step[x, y]
                if s == 'p':
                    rows.append((old[x-1], new[y-1])); x -= 1; y -= 1
                elif s == 'd':
                    rows.append((old[x-1], '')); x -= 1
                else:
                    rows.append(('', new[y-1])); y -= 1
            yield from reversed(rows)


STYLE = '''body{margin:0;background:#f5f6f8;color:#202a35;font:17px/1.7 Georgia,serif}header{position:sticky;top:0;background:#fff;padding:16px 3%;border-bottom:1px solid #ccd3dc;z-index:2;font:14px/1.5 system-ui}h1{font-size:21px;margin:0 0 6px}button,input{padding:7px;margin-right:12px}main{max-width:1700px;margin:auto;padding:20px}.labels,.row{display:grid;grid-template-columns:1fr 1fr;gap:20px}.labels{font:bold 16px system-ui;padding:15px;background:#e7edf4}.row{border-bottom:1px solid #d7dfe8;scroll-margin-top:170px}.cell{padding:18px;overflow-wrap:anywhere;white-space:pre-wrap;min-width:0}.cell:nth-child(2){border-left:1px solid #d7dfe8}del{background:#ffe1e1;color:#8c1925;text-decoration:line-through}ins{background:#d8f3dc;color:#135b30;text-decoration:none}.changed{background:#fff}.hidden{display:none}small{color:#64748b}#status{margin-left:14px}'''
SCRIPT = '''const rows=[...document.querySelectorAll('.row')];function filter(){let q=document.querySelector('#search').value.toLowerCase();rows.forEach(r=>r.classList.toggle('hidden',(document.querySelector('#only').checked&&!r.classList.contains('changed'))||!r.textContent.toLowerCase().includes(q)))}document.querySelector('#search').oninput=filter;document.querySelector('#only').onchange=filter;let pos=-1;function jump(d){let r=rows.filter(x=>x.classList.contains('changed')&&!x.classList.contains('hidden'));if(!r.length)return;pos=(pos+d+r.length)%r.length;r[pos].scrollIntoView({behavior:'smooth'});}if(location.protocol.startsWith('http')){document.querySelector('#status').textContent='Live sync active';setInterval(async()=>{try{let r=await fetch('/version',{cache:'no-store'});if(!r.ok)throw Error();let v=await r.text();if(v!==document.body.dataset.version){sessionStorage.setItem('diffScroll',scrollY);location.reload()}}catch(e){document.querySelector('#status').textContent='Sync disconnected — restart launcher'}},2500)}else document.querySelector('#status').textContent='Offline snapshot — run launcher for live sync';let saved=sessionStorage.getItem('diffScroll');if(saved){scrollTo(0,+saved);sessionStorage.removeItem('diffScroll')}'''


STYLE += '.formula{display:inline-block;vertical-align:middle}.formula:has(math[display="block"]){max-width:100%;overflow:auto;padding:4px}.formula math{font-size:1em}math[display="block"]{margin:.6em 0}.eqno{display:inline-block;margin-left:1em}ins .formula,del .formula{background:inherit}del .formula{border-bottom:2px solid #bc5360}'


def build():
    raw_a, raw_b = BASE.read_bytes(), CURRENT.read_bytes()
    a, b = extract(raw_a.decode('utf-8-sig')), extract(raw_b.decode('utf-8-sig'))
    aligned = list(comparison_rows(a, b))
    if Counter(x for x, _, _ in aligned if x) != Counter(a) or Counter(y for _, y, _ in aligned if y) != Counter(b):
        raise ValueError('Alignment lost or duplicated extracted content')
    if [y for _, y, _ in aligned if y] != b:
        raise ValueError('Alignment changed current reading order')
    prepare_math(a + b)
    version = hashlib.sha256(raw_a + raw_b + Path(__file__).read_bytes() + (BASE_LABEL + CURRENT_LABEL).encode()).hexdigest()
    rows, changed = [], 0
    moves = []
    for x, y, moved in aligned:
        changed += x != y or bool(moved)
        left, right = word_diff(x, y) if x != y else (render_text(x), render_text(y))
        if moved:
            moves.append(dict(location=moved, baseline=x, current=y))
            badge = '<div style="font:12px/1.5 system-ui;color:#465e86;margin-bottom:8px">' + html.escape(moved) + '</div>'
            left, right = badge + left, badge + right
        rows.append(f'<section class="row {"changed" if x != y or moved else ""}"><div class="cell">{left}</div><div class="cell">{right}</div></section>')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Manuscript — English revision comparison</title><style>{STYLE}</style><body data-version="{version}"><header><h1>Manuscript · English revision comparison</h1><div>Baseline: {html.escape(BASE_LABEL)}<br>Current: {html.escape(CURRENT_LABEL)}. English text only. Figures omitted; captions, tables and equation source retained.</div><small>{time.strftime('%Y-%m-%d %H:%M:%S')} · {changed} changed blocks · Word/punctuation diff · Moved text may appear as deletion + insertion</small><div><label><input id="only" type="checkbox">Changes only</label><input id="search" placeholder="Find text"><button onclick="jump(-1)">Previous change</button><button onclick="jump(1)">Next change</button><span id="status"></span></div></header><main><div class="labels"><div>{html.escape(BASE_LABEL)} · deletions in red</div><div>{html.escape(CURRENT_LABEL)} · additions in green</div></div>{''.join(rows)}</main><script>{SCRIPT}</script></body></html>'''
    page = page.replace('captions, tables and equation source retained.',
                        'captions, tables and rendered equations retained. Changed formulas are highlighted as whole units; hover to inspect TeX.')
    page = page.replace('Moved text may appear as deletion + insertion', 'Confident moves paired at current location; ambiguous moves remain separate')
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / '英文逐词对比.html'
    temp = output.with_suffix('.tmp')
    temp.write_text(page, encoding='utf-8'); temp.replace(output)
    for name, blocks in [('baseline_english.txt', a), ('current_english.txt', b)]:
        (OUT / name).write_text('\n\n'.join(blocks), encoding='utf-8')
    metadata = dict(baseline_label=BASE_LABEL, current_label=CURRENT_LABEL, baseline=str(BASE), current=str(CURRENT), baseline_sha256=hashlib.sha256(raw_a).hexdigest(), current_sha256=hashlib.sha256(raw_b).hexdigest(), version=version, baseline_blocks=len(a), current_blocks=len(b), changed_blocks=changed)
    (OUT / 'provenance.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'relocated_blocks.json').write_text(json.dumps(moves, ensure_ascii=False, indent=2), encoding='utf-8')
    return version, page


def serve(port):
    lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ['/', '/version']:
                self.send_error(404); return
            try:
                with lock:
                    fingerprint = (BASE.stat().st_mtime_ns, CURRENT.stat().st_mtime_ns)
                    if fingerprint != self.server.fingerprint:
                        self.server.version, self.server.page = build()
                        self.server.fingerprint = fingerprint
                    text = self.server.version if self.path == '/version' else self.server.page
                data = text.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8' if self.path == '/version' else 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data)
            except Exception as exc:
                self.send_error(500, str(exc))
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.fingerprint = None
    print(f'Live preview: http://127.0.0.1:{port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline-label', default='Baseline')
    parser.add_argument('--current-label', default='Current')
    parser.add_argument('--pandoc-command-json', help='JSON array: executable followed by optional wrapper arguments')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args()
    BASE, CURRENT, OUT = args.baseline.resolve(), args.current.resolve(), args.out.resolve()
    BASE_LABEL, CURRENT_LABEL = args.baseline_label, args.current_label
    if not BASE.is_file() or not CURRENT.is_file():
        parser.error('Both input Markdown files must exist')
    outputs = ['英文逐词对比.html', 'baseline_english.txt', 'current_english.txt', 'provenance.json', 'relocated_blocks.json']
    if BASE == CURRENT or any((OUT / name) in (BASE, CURRENT) for name in outputs):
        parser.error('Use distinct inputs and a separate derived-output directory')
    if args.pandoc_command_json:
        PANDOC_COMMAND = json.loads(args.pandoc_command_json)
        if not isinstance(PANDOC_COMMAND, list) or not PANDOC_COMMAND or not all(isinstance(x, str) and x for x in PANDOC_COMMAND):
            parser.error('--pandoc-command-json must be a nonempty array of strings')
    if args.serve:
        serve(args.port)
    else:
        build()
        print(OUT / '英文逐词对比.html')
