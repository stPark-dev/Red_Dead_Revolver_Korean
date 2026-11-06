"""Product build: source ISO + strtbl translations -> patched ISO (+ manifest).

usage: build_patch.py OUT.iso [--policy dev|beta|release] [--tr text/strtbl_ko.jsonl] [--budget BYTES]

Every string table copy gets the selected text; every copy of berrylium/damaged/regulatorcondensed
gets the Hangul glyphs the selected text needs, on new 4bpp 256x256 pages inserted by name.
A character with neither a glyph nor a Hangul rendering fails the build (Unmapped), except glyph-less
characters the original entry already contained (the game drops them, as in the original).
"""
import sys, os, re, math, json, hashlib, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import iso9660, dave, dave_patch, davename, strtbl, fontb, fontgen, translation, textcodec, pupshow, gfxtext

SRC_ISO = 'orig/Red Dead Revolver (USA).iso'
SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'
BASELINE = 'text/strtbl_src.jsonl'
LAYOUT_REFS = 'text/layout_refs.json'
PUP_BASELINE = 'text/pupshow_src.jsonl'
CODE_LITERALS = 'text/code_literals.json'
GFX_TR = 'text/gfx_ko.json'
SWUI_LAYOUT = 'text/swui_layout.json'
SUB_SPACE = 8  # assumed space advance for subtitle width comparison (same for source and translation)
BPP = 4
FONTS = {  # font: (cell w,h, yoff, Korean typeface)  cell/yoff matched to each font's capital letters
    'berrylium': ((22, 22), -20, '../fonts/NotoSerifKR-Bold.otf'),
    'damaged': ((32, 32), -36, '../fonts/NotoSerifKR-Black.otf'),
    'regulatorcondensed': ((24, 26), -23, '../fonts/NotoSansKR-Bold.otf'),
    'steelfish': ((22, 26), -29, '../fonts/NotoSansKR-Bold.otf'),
    'narrow_lables': ((12, 12), -22, '../fonts/NotoSansKR-Bold.otf'),
    'courier18': ((16, 16), -14, '../fonts/NotoSansKR-Bold.otf'),
    'bosshealth': ((32, 34), -32, '../fonts/NotoSerifKR-Black.otf'),
    'arial14': ((14, 14), -22, '../fonts/NotoSansKR-Bold.otf'),
}
PAGE_SIZES = (32, 64, 128, 256)
WHITESPACE = set(' \n')
DEFAULT_BUDGET = 600_000  # total new page bytes; 591KB verified at menu + level 1, 1.2MB corrupts textures


class Unmapped(ValueError):
    pass


def is_hangul(c):
    return 0xAC00 <= ord(c) <= 0xD7A3


def glyph_plan(src_by_id, selected, codes_by_font):
    """{font: sorted new Hangul chars}; raises Unmapped for any other character without a glyph.

    An entry is checked against every font that renders it: its own font plus any layout font
    (src record 'fonts'), since a layout <FONT:...> overrides the table font.
    """
    need = {f: set() for f in codes_by_font}
    bad = []
    for rid, text in selected.items():
        rec = src_by_id[rid]
        orig = set(textcodec.from_tokens(rec['src']))
        for font in sorted(set([rec['font']] + list(rec.get('fonts', [])))):
            new_chars = set(text) - WHITESPACE - orig
            if font not in codes_by_font:
                if any(not c.isascii() for c in new_chars):
                    bad.append('%s: font %s cannot take new glyphs (%s)' % (rid, font, ''.join(sorted(new_chars))[:20]))
                continue
            for c in set(text) - WHITESPACE:
                if ord(c) in codes_by_font[font]: continue
                if is_hangul(c): need[font].add(c)
                elif c not in orig: bad.append('%s: U+%04X %r has no glyph in %s' % (rid, ord(c), c, font))
    if bad: raise Unmapped('unmapped characters:\n' + '\n'.join(sorted(bad)[:50]))
    return {f: sorted(s) for f, s in need.items()}


def choose_page(n, cell):
    """Smallest square page holding all n glyphs on one page; 256 when several pages are needed."""
    for p in PAGE_SIZES:
        if n and (p // cell[0]) * (p // cell[1]) >= n: return p
    return PAGE_SIZES[-1]


def pages_needed(n, cell, page):
    per = (page // cell[0]) * (page // cell[1])
    return -(-n // per)


def check_budget(new_pages, old_pages, page_bytes, budget):
    for f, n in new_pages.items():
        if n + old_pages[f] > fontb.MAX_PAGES:
            raise ValueError('%s needs %d pages (limit %d)' % (f, n + old_pages[f], fontb.MAX_PAGES))
    pb = page_bytes if isinstance(page_bytes, dict) else {f: page_bytes for f in new_pages}
    total = sum(n * pb[f] for f, n in new_pages.items())
    if total > budget: raise ValueError('new glyph pages %d bytes exceed budget %d' % (total, budget))
    return total


def pupshow_patch(orig, texts):
    """Subtitle file bytes with cues {key: display text} replaced; unchanged cues keep their bytes."""
    doc = pupshow.parse(orig)
    cues = pupshow.cues(doc)
    new = {int(k): t for k, t in texts.items() if t != pupshow.display(cues[int(k)])}
    return pupshow.build(pupshow.with_text(doc, new)) if new else orig


def subtitle_width_limit(recs, widths):
    """Widest display line of the reachable source subtitles: translations may not exceed it."""
    return max(pupshow.line_width(line, widths, SUB_SPACE)
               for r in recs if r['reach'] == 'game' for line in textcodec.from_tokens(r['src']).split('\n'))


def merge_code_literals(refs, code):
    """refs with code-referenced literals (strings the game code looks up by key, e.g. 'Player 1 Paused')
    added to refs['literals'], so they are translated like layout literals. Each needs fonts and evidence."""
    lits = dict(refs['literals'])
    for lit, ent in code['literals'].items():
        if lit in lits or lit in refs['key_fonts']:
            raise ValueError('code literal already a layout literal or key: %r' % lit)
        if not ent.get('fonts') or not ent.get('evidence'):
            raise ValueError('code literal needs fonts and evidence: %r' % lit)
        lits[lit] = {'fonts': list(ent['fonts'])}
    return dict(refs, literals=lits)


def gfx_plan(spec, copies, policy):
    """{entry name: new IPU bytes} for every image (and alias) in spec; copies = {name: [bytes of each copy]}."""
    out = {}
    for name, img in spec['images'].items():
        if policy == 'release' and img.get('state') != 'distribution_eligible':
            raise SystemExit('graphics text not distribution_eligible: %s' % name)
        if policy == 'beta' and img.get('state') not in translation.BETA_STATES:
            raise SystemExit('graphics text not ready for beta: %s' % name)
        names = [name] + list(img.get('aliases', []))
        for n in names:
            if n not in copies: raise ValueError('graphics image not found: %s' % n)
            if any(hashlib.sha1(c).hexdigest() != img['src_sha1'] for c in copies[n]):
                raise ValueError('copy of %s differs from the spec source' % n)
        data = gfxtext.apply(copies[name][0], img, spec['fonts'], spec['colors'])
        out.update({n: data for n in names})
    return out


BUILD_INPUTS = ('text/', 'tools/')


def require_clean(policy, porcelain):
    """Beta and release builds are published, so their inputs must be committed (the manifest names the commit)."""
    if policy == 'dev': return
    dirty = [l[3:] for l in porcelain.splitlines() if l[3:].startswith(BUILD_INPUTS)]
    if dirty: raise SystemExit('%s build needs committed inputs; uncommitted: %s' % (policy, ', '.join(dirty)))


def text_width(text, widths, space, tracking=0):
    """Unscaled advance of one line: glyph width + tracking per glyph, the font's space width per space."""
    w = 0
    for c in text:
        if c == ' ': w += space
        elif ord(c) in widths: w += widths[ord(c)] + tracking
        else: raise Unmapped('no glyph width for %r' % c)
    return w


def swui_recenter(text, rule, shown, widths, space, tracking=0, english=None):
    """Rewrite the x of each <BUTTON|COMBO:x,...:label:> in rule['labels'] for the shown (translated) text.
    Default: centre each label on rule['center_x'] (the original layout centres the English labels by hand).
    mode 'group': the labels form one row (e.g. Yes/No); keep the English gaps between them and centre the
    row on the English row's centre (english[label] is the original text)."""
    pats, xs = {}, {}
    for lab in rule['labels']:
        pat = re.compile(r'<(BUTTON|COMBO):(-?[\d.]+),([^:>]*):%s:' % re.escape(lab))
        if len(pat.findall(text)) != 1: raise ValueError('button %r not found exactly once' % lab)
        pats[lab] = pat
    wk = {lab: text_width(shown[lab], widths, space, tracking) * rule['scale'] for lab in rule['labels']}
    if rule.get('mode') == 'group':
        x0 = {lab: float(pats[lab].search(text).group(2)) for lab in rule['labels']}
        we = {lab: text_width(english[lab], widths, space, tracking) * rule['scale'] for lab in rule['labels']}
        row = sorted(rule['labels'], key=x0.get)
        centre = (x0[row[0]] + x0[row[-1]] + we[row[-1]]) / 2
        gaps = [x0[b] - (x0[a] + we[a]) for a, b in zip(row, row[1:])]
        pos = centre - (sum(wk.values()) + sum(gaps)) / 2
        for i, lab in enumerate(row):
            xs[lab] = math.floor(pos + 0.5)
            if i < len(gaps): pos += wk[lab] + gaps[i]
    else:
        xs = {lab: math.floor(rule['center_x'] - wk[lab] / 2 + 0.5) for lab in rule['labels']}
    for lab in rule['labels']:
        text = pats[lab].sub(lambda m: '<%s:%d,%s:%s:' % (m.group(1), xs[lab], m.group(3), lab), text)
    return text


def swui_plan(spec, arcs, extra, fonts, srcs, keys, keys_en):
    """{swui name: recentred bytes}; every copy must be identical. A label shows its layout-literal
    translation, else its string-table translation (keys: {key: shown text}), else itself."""
    shown_all = {lit: textcodec.from_tokens(ko) for t in extra.values() for lit, (_, ko) in t.items()}
    copies = gfx_copies(arcs, set(spec['files']))
    out = {}
    for name, rule in spec['files'].items():
        cs = copies.get(name)
        if not cs or any(c != cs[0] for c in cs): raise ValueError('swui copies missing or differ: %s' % name)
        f = rule['font']
        desc = fontb.parse(fonts[f][1] if fonts.get(f) and fonts[f][1] else srcs[f])
        widths = {g['code']: g['w'] for g in desc['glyphs']}
        tracking, space = font_metrics(srcs[f])
        shown = {lab: shown_all.get(lab, keys.get(lab, lab)) for lab in rule['labels']}
        english = {lab: keys_en.get(lab, lab) for lab in rule['labels']}
        out[name] = swui_recenter(cs[0].decode('latin1'), rule, shown, widths, space, tracking, english).encode('latin1')
    return out


def font_metrics(fonttex):
    """(tracking, space advance): descriptor header u32 at +8 and +12 (berrylium 1, 14)."""
    return int.from_bytes(fonttex[8:12], 'little'), int.from_bytes(fonttex[12:16], 'little')


def gfx_copies(arcs, names):
    out = {}
    for _, raw in arcs:
        d, _, ents, _, _ = dave.read_dave_bytes(raw)
        for n, e in zip(davename.names_of(d), ents):
            if n in names: out.setdefault(n, []).append(dave.entry_data(d, e))
    return out


def renderer(ttf):
    def render(ch, w, h):
        im = Image.new('L', (w, h), 0)
        ft = ImageFont.truetype(ttf, h - 2)
        l, t, r, b = ft.getbbox(ch)
        ImageDraw.Draw(im).text(((w - (r - l)) // 2 - l, (h - (b - t)) // 2 - t), ch, 255, font=ft)
        return im
    return render


def archives(img):
    for path, lba, size in iso9660.list_files(img):
        if path.endswith('.DAT') and path != 'STREAMS.DAT':
            raw = bytes(img[lba * 2048: lba * 2048 + size])
            if raw[:4] == b'Dave': yield path, raw


def font_sources(arcs):
    """{font: fonttex bytes} from the first archive holding each configured font."""
    out = {}
    for path, raw in arcs:
        d, _, ents, _, _ = dave.read_dave_bytes(raw)
        for n, e in zip(davename.names_of(d), ents):
            f = n[:-len('.fonttex')] if n.endswith('.fonttex') else None
            if f in FONTS and f not in out: out[f] = dave.entry_data(d, e)
    missing = set(FONTS) - set(out)
    if missing: raise ValueError('fonts not found: %s' % sorted(missing))
    return out


def make_fonts(front, srcs, plan):
    d, _, ents, _, _ = dave.read_dave_bytes(front)
    names = davename.names_of(d)
    pal = fontb.parse_page(dave.entry_data(d, ents[names.index('regulatorcondensed_00.tex')]))['palette']
    out = {}
    for f, chars in plan.items():
        src = srcs[f]
        if not chars:
            out[f] = (src, None, {}); continue
        cell, yoff, ttf = FONTS[f]
        desc0 = fontb.parse(src)
        ps = choose_page(len(chars), cell)
        desc, pages = fontgen.add_pages(desc0, chars, cell, yoff, (ps, ps), BPP, pal, renderer(ttf))
        n0 = len(desc0['pages'])
        out[f] = (src, fontb.build(desc), {'%s_%02d.tex' % (f, n0 + i): p for i, p in enumerate(pages)})
    return out


def patch_archive(raw, texts_by_table, fonts, extra=None, gfx=None):
    """gfx: {entry name: replacement bytes} for whole-file replacements (IPU images, swui layouts)."""
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    names = davename.names_of(d)
    reps, new = {}, {}
    for name, e in zip(names, ents):
        if name in (gfx or {}):
            reps[e['idx']] = gfx[name]
        elif name in texts_by_table and name.endswith('.txt'):
            orig = dave.entry_data(d, e)
            data = pupshow_patch(orig, texts_by_table[name])
            if data != orig: reps[e['idx']] = data
        elif name in texts_by_table:
            t = strtbl.parse(dave.entry_data(d, e))
            add = {k: tuple(v) for k, v in (extra or {}).get(name, {}).items()}
            if add: t = strtbl.add_entries(t, {k: (f, textcodec.from_tokens(x)) for k, (f, x) in add.items()})
            changed = len(add)
            for key, ent in strtbl.entries_by_key(t).items():
                text = texts_by_table[name].get(key)
                if text is not None and text != ent['text']:
                    ent['text'] = text; changed += 1
            if changed: reps[e['idx']] = strtbl.build(t)
        f = name[:-len('.fonttex')] if name.endswith('.fonttex') else None
        if f in fonts and fonts[f][1] is not None:
            src, desc, pages = fonts[f]
            if dave.entry_data(d, e) != src: raise ValueError('font copy differs: %s' % name)
            reps[e['idx']] = desc
            new.update(pages)
    if not reps and not new: return None
    # repack: keep the original data order (appended data made level loads seek back and forth)
    return dave_patch.repack(raw, dave_patch.insert(dave_patch.patch(raw, reps), new))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--policy', default='dev', choices=['dev', 'beta', 'release'])
    ap.add_argument('--tr', default='text/strtbl_ko.jsonl'); ap.add_argument('--budget', type=int, default=DEFAULT_BUDGET)
    ap.add_argument('--pup-tr', default='text/pupshow_ko.jsonl', help='cutscene subtitle translations')
    ap.add_argument('--layout-tr', default='text/layout_ko.json',
                    help='layout literals translated by adding them as new keys to a string table')
    ap.add_argument('--gfx-tr', default=GFX_TR, help='Korean redraw of text baked into IPU images')
    a = ap.parse_args(argv)
    git = lambda *args: subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout
    require_clean(a.policy, git('status', '--porcelain'))
    commit = git('rev-parse', 'HEAD').strip()
    src_by_id = {r['id']: r for r in translation.load_jsonl(BASELINE)}
    recs = translation.load_jsonl(a.tr) if os.path.exists(a.tr) else []
    selected = translation.select(src_by_id, recs, a.policy)
    pup_src = {r['id']: r for r in translation.load_jsonl(PUP_BASELINE)}
    pup_recs = translation.load_jsonl(a.pup_tr) if os.path.exists(a.pup_tr) else []
    pup_sel = translation.select(pup_src, pup_recs, a.policy)
    src_by_id.update(pup_src); selected.update(pup_sel)
    refs = json.load(open(LAYOUT_REFS))
    if os.path.exists(CODE_LITERALS):
        refs = merge_code_literals(refs, json.load(open(CODE_LITERALS, encoding='utf-8')))
    for rid, rec in src_by_id.items():
        if rec['key'] in refs['key_fonts']: rec['fonts'] = refs['key_fonts'][rec['key']]['fonts']
    extra = {}
    if os.path.exists(a.layout_tr):
        lt = json.load(open(a.layout_tr, encoding='utf-8'))
        for lit, ent in lt['entries'].items():
            if lit not in refs['literals']: raise SystemExit('not a layout literal: %r' % lit)
            if a.policy == 'release' and ent.get('state') != 'distribution_eligible':
                raise SystemExit('layout literal not distribution_eligible: %r' % lit)
            if a.policy == 'beta' and ent.get('state') not in translation.BETA_STATES:
                raise SystemExit('layout literal not ready for beta: %r' % lit)
            fonts = refs['literals'][lit]['fonts']
            rid = '%s/%s' % (lt['table'], lit)
            if rid in src_by_id: raise SystemExit('layout literal already a key: ' + rid)
            src_by_id[rid] = dict(id=rid, table=lt['table'], key=lit, font=fonts[0], fonts=fonts, src=lit)
            selected[rid] = textcodec.from_tokens(ent['ko'])
            extra.setdefault(lt['table'], {})[lit] = (fonts[0], ent['ko'])
    img = bytearray(open(SRC_ISO, 'rb').read())
    if hashlib.sha1(img).hexdigest() != SRC_SHA1: raise SystemExit('source ISO SHA1 mismatch')
    arcs = list(archives(img))
    front = dict(arcs)['FRONT.DAT']
    srcs = font_sources(arcs)
    descs = {f: fontb.parse(b) for f, b in srcs.items()}
    plan = glyph_plan(src_by_id, selected, {f: {g['code'] for g in x['glyphs']} for f, x in descs.items()})
    bw = {g['code']: g['w'] for g in descs[pupshow.FONT]['glyphs']}
    bw.update({ord(c): FONTS[pupshow.FONT][0][0] for c in plan[pupshow.FONT]})
    limit = subtitle_width_limit(pup_src.values(), bw)
    wide = pupshow.too_wide(pup_sel, bw, limit, SUB_SPACE)
    if wide: raise SystemExit('subtitle lines too wide:\n' + '\n'.join(wide))
    psize = {f: choose_page(len(c), FONTS[f][0]) for f, c in plan.items()}
    npages = {f: pages_needed(len(c), FONTS[f][0], psize[f]) for f, c in plan.items()}
    page_bytes = {f: 14 + 4 * (1 << BPP) + p * p * BPP // 8 for f, p in psize.items()}
    total = check_budget(npages, {f: len(x['pages']) for f, x in descs.items()}, page_bytes, a.budget)
    fonts = make_fonts(front, srcs, plan)
    gfx = {}
    if os.path.exists(a.gfx_tr):
        gspec = json.load(open(a.gfx_tr, encoding='utf-8'))
        wanted = {n for k, v in gspec['images'].items() for n in [k] + v.get('aliases', [])}
        gfx = gfx_plan(gspec, gfx_copies(arcs, wanted), a.policy)
    if os.path.exists(SWUI_LAYOUT):
        keys = {src_by_id[rid]['key']: t for rid, t in selected.items() if src_by_id[rid]['table'] == 'swat.strtbl'}
        keys_en = {r['key']: textcodec.from_tokens(r['src']) for r in src_by_id.values() if r['table'] == 'swat.strtbl'}
        gfx.update(swui_plan(json.load(open(SWUI_LAYOUT, encoding='utf-8')), arcs, extra, fonts, srcs, keys, keys_en))
    texts_by_table = {}
    for rid, text in selected.items():
        texts_by_table.setdefault(src_by_id[rid]['table'], {})[src_by_id[rid]['key']] = text
    new_files = {}
    for path, raw in arcs:
        new = patch_archive(raw, texts_by_table, fonts, extra, gfx)
        if new is not None: new_files[path] = new
    touched = sorted(new_files)
    iso9660.replace_all(img, new_files)  # keep file order: appending at the end made level loads seek far
    iso9660.finalize(img)
    open(a.out, 'wb').write(img)
    states = {}
    for r in recs: states[r['state']] = states.get(r['state'], 0) + 1
    manifest = dict(policy=a.policy, distributable={'dev': False, 'beta': 'beta'}.get(a.policy),
                    source_commit=commit, source_sha1=SRC_SHA1, out_sha1=hashlib.sha1(img).hexdigest(), states=states,
                    translated=sum(1 for r in recs if r.get('ko') is not None or 'same_as' in r),
                    entries=len(src_by_id), subtitles=dict(translated=sum(1 for r in pup_recs if r.get('ko')),
                                                           cues=len(pup_src), width_limit=limit),
                    new_glyphs={f: len(c) for f, c in plan.items()},
                    new_pages=npages, new_page_bytes=total, gfx_images=sorted(gfx), archives=len(touched))
    json.dump(manifest, open(a.out + '.manifest.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    main()
