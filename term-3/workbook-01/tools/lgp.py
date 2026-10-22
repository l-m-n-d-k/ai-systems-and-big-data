"""Сборка пакетов Loginom (.lgp): узлы клонируются из примеров Loginom, затем правятся колонки и параметры движка."""
import uuid, zipfile, copy, glob, os, re
import xml.etree.ElementTree as ET
import bgb

EX = '/home/lmndk/Downloads/loginom-community/examples'
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
XSI = bgb.XSI
V = dict(text='dd767700-1321-4c70-ab92-2acfc4db4492', filt='a0e49d86-6fe3-43fc-8046-29d1ce92c03d',
         sort='62a25d53-677f-45ef-abe7-537dfdc2ea4b', calc='c7b69712-557f-4e51-bba5-db9cc2659e7a',
         lgd_in='35a6e054-ee0c-42f6-bda6-af10b57a36aa', lgd_out='70fd0efe-6caa-4151-95e0-1868586e32c9',
         txt_out='767b14f8-3852-4463-9ede-7345c4ddb183')
P_IN, P_OUT, P_ELSE = '9dc72a3f-56bf-3bfc-84ec-f979daf4da6b', '4ba0e2c2-69ad-3a32-bbdc-75714efe7a51', '99559aff-aff4-3e08-8f1e-a290790bba03'
P_IMPORT_OUT = '58f7e6c3-511e-39d7-8853-036e0a1a7612'
MAP_EXT = '936daf67-3d6e-474b-982f-98133c27a35b'
G = lambda: str(uuid.uuid4())
V['reform'] = 'dc279f34-55cf-4fee-8bb4-e10de32c88f2'
# дополнения к таблицам, проверенные на примерах (ChangedInfo) или взятые из строк Loginom (ValueNull)
bgb.tables()['setbits']['ChangedInfo'].update({'fpName': 0, 'fpDisplayName': 1})
bgb.tables()['types']['Engine|TBGImportTextFile|ValueNull'] = 7
bgb.tables()['types']['Engine|TBGExportNative|FileName'] = 7  # как у TBGImportNative
bgb.tables()['enum']['ConcatenationType']['ctOr'] = 1  # порядок enum TBGConcatenationType взят из RTTI Loginom: ctAnd, ctOr


class Col:
    def __init__(s, name, label, dtype, kind=None):
        s.name, s.label, s.dtype = name, label, dtype
        s.kind = kind or ('dkDiscrete' if dtype in ('dtString', 'dtBoolean') else 'dkContinuous')

_protos = {}
def proto(key, prefer_small=True):
    """Узел-прототип из примеров: самый компактный узел с нужным VendorGuid."""
    if key in _protos: return copy.deepcopy(_protos[key])
    best = None
    for p in sorted(glob.glob(EX + '/*/*.lgp')):
        try: z = zipfile.ZipFile(p)
        except Exception: continue
        try: r = ET.fromstring(z.read('Unit_0/Unit.xml').decode('utf-8-sig'))
        except Exception: continue
        for n in r.find('WorkFlow/Nodes').iter('Item'):
            if n.attrib.get('VendorGuid') == V[key] and n.find('Component/Engine') is not None:
                if best is None or len(ET.tostring(n)) < len(ET.tostring(best)): best = n
    if best is None: raise KeyError(key)
    _protos[key] = best
    return copy.deepcopy(best)

def sock(node, kind, name):
    for it in node.find(f'Component/{kind}'):
        if it.attrib.get('Name') == name: return it

def set_cols(container, cols, mapping=False, inp=True):
    """Заменяет ColumnDefs в DataSource сокета."""
    cd = container.find('.//DataSource/ColumnDefs')
    for c in list(cd): cd.remove(c)
    for c in cols:
        it = ET.SubElement(cd, 'Item', Name=c.name, DisplayName=c.label, DataType=c.dtype, DataKind=c.kind)
        if inp: it.set('InputColumnInfoName', c.name)
        if mapping:
            ex = ET.SubElement(ET.SubElement(it, 'Extensions'), 'Item', Guid=MAP_EXT)
            e = ET.SubElement(ex, 'Extension'); e.set(XSI, 'TBGColumnDefMappingExtension'); ET.SubElement(e, 'Mapping', Source=c.name)

def finish(node, name, left, top):
    node.set('Guid', G()); node.set('DisplayName', name)
    pos = node.find('Position'); pos.set('Left', str(left)); pos.set('Top', str(top))
    return node

def set_engine(node, engine):
    comp = node.find('Component'); old = comp.find('Engine'); i = list(comp).index(old); comp.remove(old); comp.insert(i, engine)

def port(node, kind, name):
    for it in node.find(kind):
        if it.attrib.get('Name') == name: return it.attrib['Guid']

def text_import(name, filename, cols, left, top, codepage=1251, skip=1, **kw):
    n = proto('text'); n = finish(n, name, left, top)
    e = ET.Element('Engine'); e.set(XSI, 'TBGImportTextFile'); e.set('FileName', filename); e.set('CodePage', str(codepage))
    for k, v in kw.items(): e.set(k, v)
    if skip: e.set('RowsToSkip', str(skip))   # по умолчанию (как в тетради): заголовок в первой строке, пропустить 0
    e.set('ColumnsRequired', 'false')
    cd = ET.SubElement(e, 'ColumnDefs')
    for c in cols: ET.SubElement(cd, 'Item', Name=c.name, DisplayName=c.label, DataType=c.dtype, DataKind=c.kind, UsageType='utActive')
    set_engine(n, e); return n

def lgd_import(name, filename, left, top):
    n = finish(proto('lgd_in'), name, left, top)
    e = ET.Element('Engine'); e.set(XSI, 'TBGImportNative'); e.set('FileName', filename); set_engine(n, e); return n

def row_filter(name, cols, conds, left, top):
    n = finish(proto('filt'), name, left, top)
    set_cols(sock(n, 'InputSockets', 'DataSource'), cols)
    e = ET.Element('Engine'); e.set(XSI, 'TBGFilterDataEngine'); f = ET.SubElement(e, 'Filter', UseGlobalCaseSensitive='false')
    for cond in conds:
        c, rel, vt, v = cond[:4]; cat = cond[4] if len(cond) > 4 else 'ctAnd'
        it = ET.SubElement(f, 'Item', Guid=G(), Name=c.name, DisplayName=c.label, ConcatenationType=cat, DataType=c.dtype, RelationType=rel)
        if vt: cv = ET.SubElement(it, 'CompareValue', VarType=vt); cv.text = str(v)
    set_engine(n, e); return n

def sorting(name, cols, order, left, top):
    n = finish(proto('sort'), name, left, top)
    set_cols(sock(n, 'InputSockets', 'DataSource'), cols)
    set_cols(sock(n, 'OutputSockets', 'DataSource'), cols, mapping=True, inp=False)
    e = ET.Element('Engine'); e.set(XSI, 'TBGSortingEngine'); sc = ET.SubElement(e, 'SortingColumns')
    for c, d in order:
        it = ET.SubElement(sc, 'Item', Name=c.name)
        if d != 'sdAsc': it.set('SortDirection', d)
    set_engine(n, e); return n

def calculator(name, cols, exprs, left, top):
    """exprs: [(name, label, dtype, expression, intermediate)]"""
    n = finish(proto('calc'), name, left, top)
    set_cols(sock(n, 'InputSockets', 'DataSource'), cols)
    e = ET.Element('Engine'); e.set(XSI, 'TBGCalcData'); ex = ET.SubElement(e, 'Expressions')
    for spec in exprs:
        nm, lb, dt, expr, inter = spec[:5]
        it = ET.SubElement(ex, 'Item', Name=nm, DisplayName=lb, DataType=dt, Expression=expr)
        if inter: it.set('Intermediate', 'true')
        if len(spec) > 5 and spec[5]: it.set('Cached', 'true')
    set_engine(n, e); return n

def clean_vars(n):
    """Узел-прототип из чужого примера мог принести свои управляющие переменные: делаем сокет «чистым», как у остальных узлов."""
    old = sock(n, 'InputSockets', 'ControlVariables')
    new = ET.fromstring('<Socket xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="TBGTuneVariablesSocket" Virgin="true"><Constraints/>'
                        '<Variables SyncThroughVariables="true"><Elements/></Variables></Socket>')
    old.remove(old.find('Socket')); old.append(new)

def lgd_export(name, filename, cols, left, top):
    """Экспорт в .lgd: каркас берётся у экспорта в текстовый файл."""
    n = finish(proto('txt_out'), name, left, top); n.set('VendorGuid', V['lgd_out']); clean_vars(n)
    set_cols(sock(n, 'InputSockets', 'DataSource'), cols)
    e = ET.Element('Engine'); e.set(XSI, 'TBGExportNative'); e.set('FileName', filename); set_engine(n, e); return n

def link(a, ap, b, bp):
    l = ET.Element('Item', Guid=G())
    ET.SubElement(l, 'SourcePort', NodeGuid=a.attrib['Guid'], PortGuid=ap); ET.SubElement(l, 'TargetPort', NodeGuid=b.attrib['Guid'], PortGuid=bp)
    return l

def _service_nodes():
    z = zipfile.ZipFile(EX + '/day-status/day-status.lgp')
    r = ET.fromstring(z.read('Unit_0/Unit.xml').decode('utf-8-sig'))
    return r.find('WorkFlow/ServiceNodes')

def unit_xml(nodes, links):
    u = ET.Element('Unit'); w = ET.SubElement(u, 'WorkFlow'); w.set(XSI, 'TBGPackageModelWorkFlow')
    ET.SubElement(w, 'Nodes').extend(nodes); ET.SubElement(w, 'Links').extend(links)
    w.append(_service_nodes()); ET.SubElement(w, 'ServiceLinks'); ET.SubElement(w, 'Annotations')
    mv = ET.SubElement(u, 'ModelViews'); ET.SubElement(mv, 'Nodes'); ET.SubElement(mv, 'Links')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(u, encoding='unicode')

def build(out, pkg_name, nodes, links):
    X = lambda s: ('\ufeff' + s).encode('utf-8')
    files = {
        'PackageInfo.xml': X(f'<?xml version="1.0" encoding="UTF-8"?>\n<PackageInfo Guid="{G()}" Name="{pkg_name}" ApplicationVersion="7.4.1" UseBasePackageFileStorage="true" Locale="ru_RU" MarkdownEnabled="false"/>'),
        'Variables.xml': X('<?xml version="1.0" encoding="UTF-8"?>\n<Variables><Elements/></Variables>'),
        'References.xml': X('<?xml version="1.0" encoding="UTF-8"?>\n<References/>'),
        'Reports.xml': X('<?xml version="1.0" encoding="UTF-8"?>\n<Reports/>'),
        'Unit_0/Info.xml': X(f'<?xml version="1.0" encoding="UTF-8"?>\n<Info Guid="{G()}" Name="Unit1" DisplayName="Модуль1"/>'),
        'Unit_0/Unit.xml': X(unit_xml(nodes, links)),
        'PackageIndex.xml': X('<?xml version="1.0" encoding="UTF-8"?>\n<PackageIndex><PackageInfo BinFile="\\PackageInfo.bin" XMLFile="\\PackageInfo.xml"/>'
            '<References BinFile="\\References.bin" XMLFile="\\References.xml"/><Reports BinFile="\\Reports.bin" XMLFile="\\Reports.xml"/>'
            '<Variables BinFile="\\Variables.bin" XMLFile="\\Variables.xml"/><Units><Item BasePath="\\Unit_0"><Info BinFile="\\Unit_0\\Info.bin" XMLFile="\\Unit_0\\Info.xml"/>'
            '<Unit BinFile="\\Unit_0\\Unit.bin" XMLFile="\\Unit_0\\Unit.xml"/></Item></Units></PackageIndex>'),
    }
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as o:
        for n, d in files.items():
            o.writestr(n, d); o.writestr(n[:-3] + 'bin', bgb.encode(d.decode('utf-8-sig')))

def field_params(name, cols, labels, left, top):
    """Параметры полей: labels = {имя_поля: новая_метка}"""
    n = finish(proto('reform'), name, left, top)
    set_cols(sock(n, 'InputSockets', 'DataSource'), cols)
    for it in sock(n, 'InputSockets', 'DataSource').iter('Item'):
        if it.attrib.get('Name') in labels:
            ex = ET.SubElement(ET.SubElement(it, 'Extensions'), 'Item', Guid='d3d82f11-b5e6-406f-802b-76a19a2afb6c')
            e = ET.SubElement(ex, 'Extension', DisplayName=labels[it.attrib['Name']], ChangedInfo='fpDisplayName'); e.set(XSI, 'TBGReformColumnDefExtension')
    set_engine(n, ET.fromstring('<Engine xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="TBGReformColumnsEngine"/>'))
    return n

def lgd_export_mapped(name, filename, out_cols, left, top):
    """Экспорт с заданной структурой: out_cols = [(Col, имя_входного_поля)]"""
    n = finish(proto('txt_out'), name, left, top); n.set('VendorGuid', V['lgd_out']); clean_vars(n)
    cd = sock(n, 'InputSockets', 'DataSource').find('.//DataSource/ColumnDefs')
    for c in list(cd): cd.remove(c)
    for c, src in out_cols:
        ET.SubElement(cd, 'Item', Name=c.name, DisplayName=c.label, DataType=c.dtype, DataKind=c.kind, InputColumnInfoName=src)
    e = ET.Element('Engine'); e.set(XSI, 'TBGExportNative'); e.set('FileName', filename); set_engine(n, e); return n
