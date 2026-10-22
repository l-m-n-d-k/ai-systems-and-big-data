"""Генерация решений практических заданий рабочей тетради №1 (Loginom 7.4)."""
import sys, os, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lgp import *
DOCS = os.path.join(HERE, '..', 'docs'); OUT = os.path.join(HERE, '..', 'solution')
os.makedirs(OUT, exist_ok=True)
for f in ['Потребление электрической энергии.txt', 'Продажи по чекам.lgd', 'Товары.txt', '1 показатель.txt', 'Несколько показателей.txt']:
    shutil.copy(os.path.join(DOCS, f), OUT)
chain = lambda *ns: [link(a, port(a, 'OutputPorts', 'DataSet' if a.find('Component/Engine').attrib[XSI] in ('TBGImportTextFile', 'TBGImportNative') else 'DataSource'),
                          b, port(b, 'InputPorts', 'DataSource')) for a, b in zip(ns, ns[1:])]

# --- часть 1: задания 1-5 (имена полей такие же, как их даёт Loginom при импорте: Data, Obyekt, ...) ---
cols = [Col('Data', 'Дата', 'dtDateTime'), Col('Obyekt', 'Объект', 'dtString'),
        Col('Potreblenie_el_energiya_kVt_chas', 'Потребление эл энергия,кВт час', 'dtFloat')]
imp = text_import('Потребление электрической энергии', 'Потребление электрической энергии.txt', cols, 96, 160, skip=0,
                  DecimalSeparator=',', DateFormat='dd/mm/yyyy', DateSeparator='.')
flt = row_filter('Фильтр строк', cols, [(cols[1], 'frtEqual', 'vrtString', 'Объект 1'),
                                        (cols[1], 'frtEqual', 'vrtString', 'Объект 2', 'ctOr')], 352, 160)
srt = sorting('Сортировка', cols, [(cols[2], 'sdAsc')], 608, 160)
exp = lgd_export('result_electro.lgd', 'result_electro.lgd', cols, 864, 160)
build(f'{OUT}/Рабочая_тетрадь_1_часть_1.lgp', 'workbook_01_part1', [imp, flt, srt, exp], chain(imp, flt, srt, exp))

# --- часть 2: задания 6-7 ---
imp = lgd_import('Продажи по чекам', 'Продажи по чекам.lgd', 96, 160)
calc = calculator('Калькулятор', [], [
    ('CurrentDate', 'Текущая дата', 'dtDateTime', 'Today()', False),
    ('Amount', 'Сумма', 'dtFloat', 'COST * CNT', True),
    ('CumAmount', 'Накопительная сумма', 'dtFloat', 'CumulativeSum("Amount")', False, True),
    ('Status', 'Статус', 'dtString', 'IF(Amount > 20000, "001", "002")', False),
    ('DivZero', 'Деление на ноль', 'dtFloat', 'COST / 0', False)], 352, 160)
build(f'{OUT}/Рабочая_тетрадь_1_часть_2_задания_6-7.lgp', 'workbook_01_part2', [imp, calc], chain(imp, calc))

# --- часть 2: задание 8 ---
g = [Col('Art', 'Артикул', 'dtString'), Col('Name', 'Наименование', 'dtString'), Col('SaleDate', 'Дата продажи', 'dtDateTime')]
m = Col('MonthDiff', 'Месяцев с последней продажи', 'dtInteger')
imp = text_import('Товары', 'Товары.txt', g, 96, 160, DateFormat='dd/mm/yyyy', DateSeparator='.', ValueNull='null')
flt = row_filter('Артикул не пустой', g, [(g[0], 'frtIsNotNull', None, None)], 352, 160)
c1 = calculator('Месяцев до 01.04.2018', g, [('MonthDiff', m.label, 'dtInteger', 'MonthsBetween(SaleDate, EncodeDate(2018, 4, 1))', False)], 608, 160)
srt = sorting('Сортировка по месяцам', g + [m], [(m, 'sdDesc')], 864, 160)
c2 = calculator('Вывод из продажи', g + [m], [('Withdraw', 'Вывод из продажи', 'dtBoolean', 'MonthDiff > 10', False)], 1120, 160)
build(f'{OUT}/Рабочая_тетрадь_1_часть_2_задание_8.lgp', 'workbook_01_part2_task8', [imp, flt, c1, srt, c2], chain(imp, flt, c1, srt, c2))

# --- часть 3: задания 9-10 ---
c1p = [Col('ID', 'ID', 'dtString'), Col('Date', 'Дата', 'dtDateTime'), Col('Value', 'Показатель', 'dtFloat')]
tf = dict(DecimalSeparator='.', DateFormat='dd/mm/yyyy', DateSeparator='.', TimeSeparator=':')
i1 = text_import('1 показатель', '1 показатель.txt', c1p, 96, 160, **tf)
i2 = text_import('Несколько показателей', 'Несколько показателей.txt',
                 c1p + [Col('Value2', 'Показатель 2', 'dtFloat'), Col('Value3', 'Показатель 3', 'dtFloat'), Col('Value4', 'Показатель 4', 'dtFloat'), Col('Value5', 'Показатель 5', 'dtInteger')], 96, 400, **tf)
fp = field_params('Параметры полей', c1p, {'ID': 'Идентификатор'}, 352, 160)
ex1 = lgd_export('export.lgd', 'export.lgd', c1p, 608, 80)
ex2 = lgd_export_mapped('export2.lgd', 'export2.lgd', [(Col('Client', 'Клиент', 'dtString'), 'ID'), (Col('LastDate', 'Дата последней покупки', 'dtDateTime'), 'Date'),
                                                         (Col('Churn', 'Вероятность оттока', 'dtFloat'), 'Value')], 608, 240)
l = chain(i1, fp)
l += [link(fp, port(fp, 'OutputPorts', 'DataSource'), ex1, port(ex1, 'InputPorts', 'DataSource')), link(fp, port(fp, 'OutputPorts', 'DataSource'), ex2, port(ex2, 'InputPorts', 'DataSource'))]
build(f'{OUT}/Рабочая_тетрадь_1_часть_3_задания_9-10.lgp', 'workbook_01_part3', [i1, i2, fp, ex1, ex2], l)
print('готово')
