"""Формат BGB (.bin внутри .lgp Loginom 7.4): бинарная запись XML-дерева.

Заголовок: b'BGB\\xc3\\x01\\x00\\x00\\x00\\x01'. Элемент: имя, xsi:type (пустая строка, если нет), число атрибутов,
атрибуты (имя, байт типа, значение), число детей, дети. Строки и числа длин - 'знак-величина':
7 бит на байт, в последнем байте 6 бит величины и бит 0x40 = минус.
Типы: 1 bool, 2 datetime(double), 3 double, 4 varint, 5 int32, 7 string, 8 char, 9 enum(1 байт), 10 набор флагов(varint), 11 guid.
"""
import uuid, struct, datetime, json, os, zipfile, glob, collections
import xml.etree.ElementTree as ET
XSI = '{http://www.w3.org/2001/XMLSchema-instance}type'
HDR = b'BGB\xc3\x01\x00\x00\x00\x01'
HERE = os.path.dirname(os.path.abspath(__file__))

class Fail(Exception): pass
class R:
    def __init__(s, b): s.b, s.i = b, 0
    def u8(s):
        if s.i >= len(s.b): raise Fail('eof')
        s.i += 1; return s.b[s.i - 1]
    def take(s, n):
        if s.i + n > len(s.b): raise Fail('eof')
        s.i += n; return bytes(s.b[s.i - n:s.i])
    def vlen(s):
        r = sh = 0
        while True:
            c = s.u8(); r |= (c & 0x7f) << sh; sh += 7
            if not c & 0x80: return r & ~(0x40 << (sh - 7)) if False else (r if not (c & 0x40) else -(r & ~(0x40 << (sh - 7))))
    def name(s):
        try: return s.take(s.vlen()).decode('utf8')
        except UnicodeDecodeError: raise Fail('utf8')

def venc(n):
    m, neg, out = abs(n), n < 0, bytearray()
    while m >= 64: out.append((m & 0x7f) | 0x80); m >>= 7
    out.append(m | (0x40 if neg else 0)); return bytes(out)
def senc(x): b = x.encode('utf8'); return venc(len(b)) + b

FIXED = {1: 1, 2: 8, 3: 8, 5: 4, 8: 1, 9: 1, 11: 16}
TEXTW = {0x14: 8, 0x05: 8, 0x0b: 1}
def read_elem(r):
    tag = r.name(); xt = r.name(); n = r.vlen(); at = []; text = None
    for _ in range(n):
        an = r.name()
        if an == '':
            r.u8(); T = r.u8(); b2 = r.u8()
            if T == 0:
                if b2 != 1: raise Fail('str')
                text = ('s', r.take(r.vlen()))
            else: text = ('v', T, r.take(TEXTW[T]))
            continue
        t = r.u8()
        if t in FIXED: v = r.take(FIXED[t])
        elif t == 7: v = r.take(r.vlen())
        elif t in (4, 10): st = r.i; r.vlen(); v = bytes(r.b[st:r.i])
        else: raise Fail(f'type {t}')
        at.append((an, t, v))
    k = r.vlen()
    return (tag, xt, at, text, [read_elem(r) for _ in range(k)])
def decode(b):
    r = R(b)
    if r.take(9) != HDR: raise Fail('hdr')
    e = read_elem(r)
    if r.i != len(b): raise Fail('tail')
    return e

# --- таблицы: имена enum/наборов берутся из пар xml/bin примеров Loginom ---
def _walk(b, x, T):
    tag, xt, at, text, ch = b
    xa = [(k, v) for k, v in x.attrib.items() if k != XSI]
    assert tag == x.tag and len(at) == len(xa) and len(ch) == len(list(x))
    for (an, t, raw), (xn, xv) in zip(at, xa):
        assert an == xn
        T['types'].setdefault((tag, xt, an), t)
        if T['types'][(tag, xt, an)] != t: T['types'][(tag, xt, an)] = -1
        if t == 9: T['enum'][an][xv] = raw[0]
        if t == 10: T['sets'][an].append((xv.split(), R(raw).vlen()))
    for bc, xc in zip(ch, x): _walk(bc, xc, T)
def build_tables(examples):
    T = {'types': {}, 'enum': collections.defaultdict(dict), 'sets': collections.defaultdict(list)}
    n = 0
    for f in sorted(glob.glob(examples + '/*/*.lgp')):
        try: z = zipfile.ZipFile(f)
        except Exception: continue
        for name in z.namelist():
            if not name.endswith('.bin'): continue
            try:
                x = ET.fromstring(z.read(name[:-3] + 'xml').decode('utf-8-sig'))
                _walk(decode(z.read(name)), x, T); n += 1
            except Exception: pass
    bits = collections.defaultdict(dict)
    for an, eqs in T['sets'].items():
        ch = True
        while ch:
            ch = False
            for names, val in eqs:
                known = sum(1 << bits[an][k] for k in names if k in bits[an]); unk = [k for k in names if k not in bits[an]]
                rest = val & ~known
                if len(unk) == 1 and rest and rest & (rest - 1) == 0: bits[an][unk[0]] = rest.bit_length() - 1; ch = True
    out = {'types': {'|'.join(k): v for k, v in T['types'].items()}, 'enum': T['enum'], 'setbits': bits}
    json.dump(out, open(os.path.join(HERE, 'tables.json'), 'w'), ensure_ascii=False)
    return n

# --- кодировщик XML -> bin ---
_T = None
def tables():
    global _T
    if _T is None: _T = json.load(open(os.path.join(HERE, 'tables.json')))
    return _T
VT = {'vrtInt64': 0x14, 'vrtDouble': 0x05, 'vrtBoolean': 0x0b}
def val(t, an, v):
    T = tables()
    if t == 1: return b'\x01' if v == 'true' else b'\x00'
    if t == 7: return senc(v)
    if t == 11: return uuid.UUID(v).bytes_le
    if t == 9: return bytes([T['enum'][an][v]])
    if t == 10: return venc(sum(1 << T['setbits'][an][k] for k in v.split()))
    if t == 3: return struct.pack('<d', float(v))
    if t == 2:
        d = datetime.datetime.fromisoformat(v) - datetime.datetime(1899, 12, 30)
        return struct.pack('<d', d.days + d.seconds / 86400)
    if t == 5: return struct.pack('<i', int(v))
    if t == 4: return venc(int(v))
    if t == 8: return bytes([ord(v)]) if v else b'\x00'
    raise ValueError(t)
def enc_elem(x):
    T = tables()
    xt = x.attrib.get(XSI, '')
    at = [(k, v) for k, v in x.attrib.items() if k != XSI]
    istext = (x.tag.startswith('CompareValue') or x.tag == 'I') and 'VarType' in x.attrib and ((x.text or '').strip() != '' or x.attrib['VarType'] == 'vrtString')
    out = senc(x.tag) + senc(xt) + venc(len(at) + (1 if istext else 0))
    for an, v in at:
        t = T['types'].get(f'{x.tag}|{xt}|{an}')
        if t is None or t < 0: raise KeyError(f'нет типа для {x.tag}.{an}')
        out += senc(an) + bytes([t]) + val(t, an, v)
    if istext:
        vt = x.attrib['VarType']
        if vt == 'vrtString': out += b'\x00\x00\x00\x01' + senc(x.text or '')
        else:
            txt = x.text.strip(); out += b'\x00\x00' + bytes([VT[vt]]) + b'\x00'
            out += (b'\x01' if txt == 'true' else b'\x00') if vt == 'vrtBoolean' else (struct.pack('<q', int(txt)) if vt == 'vrtInt64' else struct.pack('<d', float(txt)))
    ch = list(x); out += venc(len(ch))
    for c in ch: out += enc_elem(c)
    return out
def encode(xml_text):
    return HDR + enc_elem(ET.fromstring(xml_text.lstrip('﻿')))
