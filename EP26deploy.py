import streamlit as st 
import pandas as pd 
import numpy as np 
from docx import Document
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


st.set_page_config(layout="wide")

st.title("🎯 Межлотовая вариация. Оценка по документу CLSI EP26-A")

tab0, tab1, tab2, tab3, tab4 = st.tabs(["Отчёт 📋", "👉 Инструкция", "Таблица 𝒜𝟏", "Таблица 𝒜𝟐","Таблица 𝒜𝟑"])

# Table A1 (1 level)
df1 = pd.read_excel('TableA1ep26.xlsx',engine='openpyxl')
df1.replace(np.nan,'⚠️',inplace=True)

# Table A2 (2 levels)
df2 = pd.read_excel('TableA2ep26.xlsx',engine='openpyxl')
df2.replace(np.nan,'⚠️',inplace=True)

# Table A3 (3 levels)
df3 = pd.read_excel('TableA3ep26.xlsx',engine='openpyxl')
df3.replace(np.nan,'⚠️',inplace=True)


err1 = '⚠️'

sheader = st.sidebar.subheader('⚙️ Внесите информацию о тесте')
sname = st.sidebar.text_input("Введите название теста")
sed = st.sidebar.text_input('Единицы измерения')
slot_old = st.sidebar.text_input("Текущий лот №")
slot_new = st.sidebar.text_input("Новый лот №")
org = st.sidebar.text_input("Организация")
analyzer = st.sidebar.text_input("Анализатор")
executor = st.sidebar.text_input("Выполнил")
approver = st.sidebar.text_input("Согласовал")


# Для отчёта
def style_doc(doc):
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)


def add_info_line(doc, label, value):
    p = doc.add_paragraph()
    p.add_run(f"{label}: ").bold = True
    p.add_run(str(value))

#  Вспомогательные функции для оформления 

def _set_cell_border(cell, **kwargs):

    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.find(qn('w:tcBorders'))
    if tc_borders is None:
        tc_borders = OxmlElement('w:tcBorders')
        tc_pr.append(tc_borders)

    for edge in ('top', 'left', 'bottom', 'right'):
        if edge in kwargs:
            tag = qn(f'w:{edge}')
            existing = tc_borders.find(tag)
            if existing is not None:
                tc_borders.remove(existing)
            border = OxmlElement(f'w:{edge}')
            settings = kwargs[edge]
            if settings is None:
                border.set(qn('w:val'), 'nil')
            else:
                border.set(qn('w:val'), settings.get('val', 'single'))
                border.set(qn('w:sz'), settings.get('sz', '4'))
                border.set(qn('w:color'), settings.get('color', '000000'))
            tc_borders.append(border)


def _clear_all_borders(cell):
    """Убрать все границы у ячейки."""
    _set_cell_border(
        cell,
        top=None, bottom=None, left=None, right=None )


def _set_horizontal_border(cell, position, weight='4', color='000000'):
    """position: 'top' или 'bottom'. weight: '4' тонкая, '12' толстая."""
    _set_cell_border(cell, **{position: {'sz': weight, 'val': 'single', 'color': color}})


def _set_cell_shading(cell, color_hex):
    """Заливка ячейки цветом (hex без #)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tc_pr.append(shd)


def _format_cell_text(cell, text, bold=False, italic=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                     size=None, color=None):
    """Записать текст в ячейку с форматированием. Стирает существующее содержимое."""
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = alignment
    run = p.add_run(str(text))
    run.bold = bold
    run.italic = italic
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


#  Стиль "научной таблицы"

def add_scientific_table(doc, df, title=None, footer_row=None):

    if title:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(12)
        p.paragraph_format.space_after = Pt(2)

    n_cols = len(df.columns)
    n_data_rows = len(df)
    n_total_rows = 1 + n_data_rows + (1 if footer_row else 0)

    table = doc.add_table(rows=n_total_rows, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # Сначала убираем все границы у всех ячеек
    for row in table.rows:
        for cell in row.cells:
            _clear_all_borders(cell)

    # Заголовок: толстая линия сверху, тонкая снизу
    header_cells = table.rows[0].cells
    for i, col_name in enumerate(df.columns):
        _format_cell_text(header_cells[i], col_name, bold=True, size=11)
        _set_cell_border(
            header_cells[i],
            top={'sz': '12', 'val': 'single', 'color': '000000'},
            bottom={'sz': '4', 'val': 'single', 'color': '000000'}
        )

    # Данные
    for row_idx, (_, row_data) in enumerate(df.iterrows()):
        cells = table.rows[row_idx + 1].cells
        is_last_data_row = (row_idx == n_data_rows - 1) and not footer_row
        for i, val in enumerate(row_data):
            _format_cell_text(cells[i], val, size=11)
            if is_last_data_row:
                _set_cell_border(
                    cells[i],
                    bottom={'sz': '12', 'val': 'single', 'color': '000000'}  )

    # Итоговая строка (если есть)
    if footer_row:
        footer_cells = table.rows[-1].cells
        label = footer_row.get('label', '')
        value = footer_row.get('value', '')
        colspan = footer_row.get('colspan', n_cols - 1)

        # Объединяем ячейки для подписи
        merged = footer_cells[0]
        for i in range(1, colspan):
            merged = merged.merge(footer_cells[i])
        _format_cell_text(merged, label, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, size=11)
        _set_cell_border(
            merged,
            top={'sz': '4', 'val': 'single', 'color': '000000'},
            bottom={'sz': '12', 'val': 'single', 'color': '000000'}  )

        # Значение в последних ячейках
        for i in range(colspan, n_cols):
            _format_cell_text(footer_cells[i], value if i == colspan else '', bold=True, size=11)
            _set_cell_border(
                footer_cells[i],
                top={'sz': '4', 'val': 'single', 'color': '000000'},
                bottom={'sz': '12', 'val': 'single', 'color': '000000'}  )

    doc.add_paragraph()  # отступ после таблицы
    return table


#  Таблица 3, разбитая по уровням 

def add_table3_by_levels(doc, tablo3_dict, levels_info):

    # Заголовок Таблицы 3
    p = doc.add_paragraph()
    run = p.add_run("Таблица 3. Результаты сравнения лотов")
    run.bold = True
    run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(4)

    df_full = pd.DataFrame(tablo3_dict)

    for info in levels_info:
        lvl = info['level']
        conc = info['concentration']
        units = info.get('units', '')

        # Подзаголовок уровня — курсив
        sub = doc.add_paragraph()
        sub_run = sub.add_run(f"Уровень {lvl} — концентрация {conc} {units}".strip())
        sub_run.italic = True
        sub_run.font.size = Pt(11)
        sub.paragraph_format.space_before = Pt(6)
        sub.paragraph_format.space_after = Pt(2)

        # Данные этого уровня
        df_lvl = df_full[df_full['Уровень'] == lvl].reset_index(drop=True)

        # Формируем таблицу с № вместо «Уровень»
        df_display = pd.DataFrame({
            '№': range(1, len(df_lvl) + 1),
            'Текущий лот': df_lvl['Результат (текущий лот)'],
            'Новый лот': df_lvl['Результат (новый лот)'],
            'Разница': [f"{'+' if d > 0 else ''}{d}" for d in df_lvl['Разница']] })

        # Средняя абсолютная разница для футера
        mean_abs = round(abs(df_lvl['Разница'].mean()), 2) if len(df_lvl) > 0 else 0

        add_scientific_table(
            doc,
            df_display,
            title=None,
            footer_row={
                'label': 'Абсолютная средняя разница',
                'value': mean_abs,
                'colspan': 3 })


#  Заключение в рамочке 

def add_conclusion_box(doc, text, passed=True):

    if passed:
        bar_color = '1D6E3A'      # зелёный
        bg_color = 'F6FAF7'       # светло-зелёный
    else:
        bar_color = 'A32D2D'      # красный
        bg_color = 'FCEBEB'       # светло-красный

    # Таблица из 1 строки и 2 ячеек: узкая цветная полоска + текст
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Ширина: полоска ~0.1 см, остальное под текст
    bar_cell = table.rows[0].cells[0]
    text_cell = table.rows[0].cells[1]

    bar_cell.width = Cm(0.15)
    text_cell.width = Cm(15.5)

    # Полоска: только заливка цветом, без границ, без текста
    _clear_all_borders(bar_cell)
    _set_cell_shading(bar_cell, bar_color)
    bar_cell.text = ''

    # Текстовая ячейка: светлый фон, без границ
    _clear_all_borders(text_cell)
    _set_cell_shading(text_cell, bg_color)

    text_cell.text = ''
    p1 = text_cell.paragraphs[0]
    run1 = p1.add_run('Заключение')
    run1.bold = True
    run1.font.size = Pt(12)

    p2 = text_cell.add_paragraph()
    run2 = p2.add_run(text)
    run2.font.size = Pt(11)
    p2.paragraph_format.space_after = Pt(0)

    doc.add_paragraph()


# ============ Подписи внизу ============

def add_signatures(doc, executor, approver):
    """Две колонки с подписями внизу отчёта."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(36)

    table = doc.add_table(rows=3, cols=2)
    table.autofit = True
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Все границы убираем
    for row in table.rows:
        for cell in row.cells:
            _clear_all_borders(cell)

    # Строка 1: подписи (роли)
    _format_cell_text(table.rows[0].cells[0], 'Выполнил',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11,
                     color=(85, 85, 85))
    _format_cell_text(table.rows[0].cells[1], 'Согласовал',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11,
                     color=(85, 85, 85))

    # Строка 2: пустая для подписи (с линией снизу)
    for cell in table.rows[1].cells:
        cell.text = ''
        _set_horizontal_border(cell, 'bottom', weight='4')
        # Высота для подписи
        p_empty = cell.paragraphs[0]
        p_empty.paragraph_format.space_before = Pt(24)

    # Строка 3: ФИО под линией
    _format_cell_text(table.rows[2].cells[0], executor or '',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11)
    _format_cell_text(table.rows[2].cells[1], approver or '',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11)


# ============ Главная функция: generate_report ============

def generate_report(org, executor, approver, analyzer, sname, sed, slot_old, slot_new,
    tablo, tablo2, tablo3, tablo4, slevel, cc):

    doc = Document()

    # Стиль документа
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # ===== Шапка организации (как в оригинале) =====
    header = doc.add_table(rows=4, cols=3)
    header.style = 'Table Grid'

    header.cell(0, 0).text = "Организация"
    header.cell(0, 1).merge(header.cell(0, 2))
    header.cell(0, 1).text = str(org)

    header.cell(1, 0).text = "Выполнил"
    header.cell(1, 1).merge(header.cell(1, 2))
    header.cell(1, 1).text = str(executor)

    header.cell(2, 0).text = "Согласовал"
    header.cell(2, 1).merge(header.cell(2, 2))
    header.cell(2, 1).text = str(approver)

    header.cell(3, 0).text = "Дата"
    header.cell(3, 1).merge(header.cell(3, 2))
    header.cell(3, 1).text = datetime.now().strftime("%d.%m.%Y")

    doc.add_paragraph()

    # ===== Титул =====
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run('ОТЧЁТ')
    run_title.bold = True
    run_title.font.size = Pt(15)

    p_subtitle = doc.add_paragraph()
    p_subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_subtitle = p_subtitle.add_run('Оценка межлотовой вариации по CLSI EP26-A')
    run_subtitle.bold = True
    run_subtitle.font.size = Pt(13)
    p_subtitle.paragraph_format.space_after = Pt(18)

    # ===== Информация о тесте (без рамок, в две колонки) =====
    info_table = doc.add_table(rows=2, cols=4)
    info_table.autofit = True

    for row in info_table.rows:
        for cell in row.cells:
            _clear_all_borders(cell)

    _format_cell_text(info_table.rows[0].cells[0], 'Анализатор',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11, color=(85, 85, 85))
    _format_cell_text(info_table.rows[0].cells[1], analyzer or '',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11)
    _format_cell_text(info_table.rows[0].cells[2], 'Тест',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11, color=(85, 85, 85))
    test_str = f"{sname}, {sed}" if sed else (sname or '')
    _format_cell_text(info_table.rows[0].cells[3], test_str,
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11)

    _format_cell_text(info_table.rows[1].cells[0], 'Текущий лот',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11, color=(85, 85, 85))
    _format_cell_text(info_table.rows[1].cells[1], slot_old or '',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11)
    _format_cell_text(info_table.rows[1].cells[2], 'Новый лот',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11, color=(85, 85, 85))
    _format_cell_text(info_table.rows[1].cells[3], slot_new or '',
                     alignment=WD_ALIGN_PARAGRAPH.LEFT, size=11)

    doc.add_paragraph()

    # ===== Таблица 1 =====
    add_scientific_table(
        doc,
        pd.DataFrame(tablo),
        title='Таблица 1. Аналитические характеристики теста')

    # ===== Таблица 2 =====
    add_scientific_table(
        doc,
        pd.DataFrame(tablo2),
        title='Таблица 2. Расчётные параметры CLSI EP26-A')

    # ===== Таблица 3 (по уровням) =====
    levels_info = [
        {'level': i + 1, 'concentration': cc[i], 'units': sed or ''}
        for i in range(slevel)]
    add_table3_by_levels(doc, tablo3, levels_info)

    # ===== Таблица 4 =====
    add_scientific_table(
        doc,
        pd.DataFrame(tablo4),
        title='Таблица 4. Анализ и оценка сравнения лотов')

    # ===== Заключение =====
    has_failure = '❌ Не прошёл' in str(tablo4)
    if has_failure:
        conclusion_text = (
            f'Обнаружены отклонения между лотами. '
            f'Новый лот {slot_new} требует дополнительной проверки.')
    else:
        conclusion_text = (
            f'Межлотовая вариация находится в допустимых пределах. '
            f'Новый лот {slot_new} принят к использованию.')

    add_conclusion_box(doc, conclusion_text, passed=not has_failure)

    # ===== Подписи =====
    add_signatures(doc, executor, approver)

    # Сохранение
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


with tab0:
    bb0 = st.container(border=True)
    c001 , c002, c003 = bb0.columns(3)
    ste = c001.number_input("TE %")
    slevel = c002.number_input('Количество уровней для проверки (от 1 до 3)', min_value=1, max_value=3, step=1)
   
    
    if slevel == 1:
        DF = df1
    if slevel == 2:
        DF = df2
    if slevel == 3:
        DF = df3

    bb1 = st.container(border=True)
    c01, c02, c03, c04 = bb1.columns(4)
    c1, c2, c3, c4 = bb1.columns(4)
    bb15 = st.container(border=True)
    bcl0, bcl1, bcl2 = bb15.columns(3,border=True, vertical_alignment='center')
    bcls = [bcl0, bcl1, bcl2]
    BC0, BC1, BC2 = bb15.columns(3, border=True, vertical_alignment='top')
    
    bclot0,bclot1 = BC0.columns(2)
    bc2lot2,bclot3 = BC1.columns(2)
    bclot4,bclot5 = BC2.columns(2)

    bclot00,bclot01 = BC0.columns(2)
    bc2lot02,bclot03 = BC1.columns(2)
    bclot04,bclot05 = BC2.columns(2)

    bc0,bc1 = BC0.columns(2)
    bc2,bc3 = BC1.columns(2)
    bc4,bc5 = BC2.columns(2)
    bcslots = [bclot0,bclot1,bc2lot2,bclot3,bclot4,bclot5]
    bcslots2 = [bclot00,bclot01,bc2lot02,bclot03,bclot04,bclot05]
    bcs = [bc0,bc1,bc2,bc3,bc4,bc5]
    b22 = st.container(border=True, horizontal_alignment='center', vertical_alignment='center')
    aa =[1,1,1]
    bb=[1,1,1]
    cc = [1,1,1]

    ff=[0.6,0.6,0.6]
    fractions = [0.55, 0.6, 0.7, 0.8, 0.9]

    ckeys = ['ckey1','ckey2','ckey3']
    fkeys = ['fkey1','fkey2','fkey3']

    c01.markdown("**Концентрация**")
    c02.markdown("**Выберите фракцию CD**")
    cr03 = c03.radio("CVr or SDr", options=['CVr','Sr'], horizontal=True, label_visibility='collapsed')
    cr04 = c04.radio("CVwlr or SDwlr", options=['CVwrl','Swlr'], horizontal=True, label_visibility='collapsed')
    for i in range(0,slevel):

        cc[i] = c1.number_input(f"{i+1} уровень", key = f'cc{i}')
      
        ff[i] = c2.selectbox(f"Фракция CD {i+1}", fractions, key = fkeys[i])

        if cr03 == 'CVr':
            aa[i] = c3.number_input(f"CVr{i+1}")
        else:
            aa[i] = c3.number_input(f"Sr{i+1}")
        if cr04 == 'CVwrl':
            bb[i] = c4.number_input(f"CVwrl{i+1}")
        else:
            bb[i] = c4.number_input(f"Swrl{i+1}")
    


    if bb[0] !=0:
        tablo = {"Концентрация": [cc[0]],
             "CD": [cc[0]*ste/100],
             "Sr": [aa[0]] if cr03 == 'Sr' else [aa[0]*cc[0]/100],
             "Swrl": [bb[0]] if cr04 == 'Swlr' else [bb[0]*cc[0]/100],
             "CD/Swrl":[round(cc[0]*ste/100/bb[0],2)] if cr04 == 'Swlr' else [round(cc[0]*ste/100/(bb[0]*cc[0]/100),2)],
             "Sr/Swrl":[round(aa[0]/bb[0],2) ]}
    else:
        tablo = {"Концентрация": [cc[0]],
             "CD": [cc[0]*ste/100],
             "Sr": [aa[0]] if cr03 == 'Sr' else [aa[0]*cc[0]/100],
             "Swrl": [err1],
             "CD/Swrl":[err1],
             "Sr/Swrl":[err1]}

        
    nform = b22.form('Форма внесения результатов')

    if slevel !=1:
        nform.write(f"Таблица 1. Аналитические характеристики теста {sname} для {slevel} уровней концентраций")
    else:
        nform.write(f"Таблица 1. Аналитические характеристики теста {sname} для {slevel} уровня концентрации")


    for i in range(1,slevel):
        if bb[i] !=0:
            tablo["Концентрация"].append(cc[i])
            tablo["CD"].append(cc[i]*ste/100)
            tablo["Sr"].append(aa[i] if cr03 == 'Sr' else aa[i]*cc[i]/100)
            tablo["Swrl"].append(bb[i] if cr04 == 'Swlr' else bb[i]*cc[i]/100)
            tablo["CD/Swrl"].append(round(cc[i]*ste/100/bb[i],2) if cr04 == 'Swlr' else round(cc[i]*ste/100/(bb[i]*cc[i]/100),2))
            tablo["Sr/Swrl"].append(round(aa[i]/bb[i],2) )
        else:
            tablo["Концентрация"].append(cc[i])
            tablo["CD"].append(cc[i]*ste/100)
            tablo["Sr"].append(aa[i] if cr03 == 'Sr' else aa[i]*cc[i]/100)
            tablo["Swrl"].append(err1)
            tablo["CD/Swrl"].append(err1)
            tablo["Sr/Swrl"].append(err1)

    nform.dataframe(tablo, hide_index=True)
    

    nn = ['⚠️','⚠️','⚠️']
    pp = ['⚠️','⚠️','⚠️']
    def table_search(df,i):
        if bb[i] != 0:
            cd0 = cc[i]*ste/100/bb[i] if cr04 == 'Swlr' else cc[i]*ste/100/(bb[i]*cc[i]/100)
            uno = np.array(df['CD_Swrl'].unique())
            fvector1 = uno - cd0
            if any (x <=0 for x in fvector1):
                idx = np.argmin(np.abs((fvector1)[np.where(fvector1<=0)]))
            else:
                st.warning('❗ В таблицах А1-А3 не учтены случаи, когда отношение CD/Swrl меньше 1')
            cdf = df[df['CD_Swrl']==uno[idx]]
            srsw0 = aa[i]/bb[i]
            uno2 = np.array(cdf['Sr_Swrl'].unique())
            fvector2 = uno2-srsw0
            if any (x <=0 for x in fvector2):
                idx2 = np.argmin(np.abs(fvector2[np.where(fvector2<=0)]))
            else:
                idx2 = np.argmin(np.abs(fvector2))
            sdf = cdf[cdf['Sr_Swrl']==uno2[idx2]]
            n = list(sdf[f'N_{ff[i]}'])[0]
            power = list(sdf[f'P_{ff[i]}'])[0]
            nn[i] = n
            pp[i] = power
        else:
            st.warning("Внесите Swrl или CVwrl ⚠️")
 
    for i in range (0,slevel):
        table_search(DF,i)


    nform.write("Таблица 2. Вспомогательная таблица, заполненная с учетом данных CSI EP26-A")
    tablo2 = {"Концентрация": [cc[0]],
         "CD": [cc[0]*ste/100],
         "RL": [f'{ff[0]} x CD = {round(ff[0] * cc[0]*ste/100,2)}'],
         "Количество образцов N":[nn[0]],
         "Статистическая мощность":[pp[0]]}
    for i in range(1,slevel):
        tablo2["Концентрация"].append(cc[i])
        tablo2["CD"].append(cc[i]*ste/100)
        tablo2["RL"].append(f'{ff[i]} x CD = {round(ff[i] * cc[i]*ste/100,2)}') 
        tablo2["Количество образцов N"].append(nn[i])
        tablo2["Статистическая мощность"].append(pp[i])
    nform.dataframe(tablo2, hide_index=True)

    nform.write("Таблица 3. Результаты, полученные на разных лотах реагентов")


    tablo3 = {'Уровень':[],
            'Результат (текущий лот)':[],
            'Результат (новый лот)':[],
            'Разница':[],}
    
    for i in range (0,slevel):
        if nn[i] != '⚠️':
            bcls[i].markdown(f"**Уровень {i+1}** (N = {int(nn[i])}, Мощность = {pp[i]})")
        else:
            bcls[i].markdown(f"**Уровень {i+1}** (N = {(nn[i])}, Мощность = {pp[i]})")
        bcslots[i+i].markdown("**Текущий лот:**")
        bcslots[1+i+i].markdown("**Новый лот:**")
        bcslots2[i+i].markdown(f"{slot_old}")
        bcslots2[1+i+i].markdown(f"{slot_new}")


        if nn[i] !='⚠️':
            for n in range(0,int(nn[i])):
                tablo3['Уровень'].append(i+1)
                nstar = bcs[i+i].number_input(f'Уровень {i+1} образец {n+1}', label_visibility='collapsed')
                nnew = bcs[i+i+1].number_input(f"Образец {i+1} уровень {n+1}",label_visibility='collapsed')
                tablo3['Результат (текущий лот)'].append(round(nstar,2))
                tablo3['Результат (новый лот)'].append(round(nnew,2))
                tablo3['Разница'].append(round(nnew - nstar,2))
        else:
            st.warning("Мало образцов.Проверьте введенные данные")


    nform.dataframe(tablo3, hide_index=True)

    tdf3 = pd.DataFrame(tablo3)
      
    nform.write("Таблица 4. Анализ полученных результатов")
    tablo4 = {'Уровень':[],
              'Концентрация': [],
              'Абсолютная средняя разница': [],
              'RL': [],
              'Заключение': []}
    for i in range (0, slevel):
        tablo4["Уровень"].append(i+1)
        tablo4["Концентрация"].append(cc[i])
        dif = round(abs(tdf3[tdf3['Уровень']==i+1]['Разница'].mean()),2)
        tablo4["Абсолютная средняя разница"].append(dif)
        tablo4['RL'].append(round(ff[i] * cc[i]*ste/100,2))
        tablo4["Заключение"].append('✅ Приемлемо' if dif<(ff[i] * cc[i]*ste/100) else '❌ Не прошёл')
   
    nform.dataframe(tablo4, hide_index=True)
    
    nbutton = nform.form_submit_button("📝 Сформировать отчёт")

    if nbutton:
        report = generate_report(org, executor, approver, analyzer, sname, sed, slot_old, slot_new, tablo, tablo2, tablo3, tablo4, slevel, cc)
        st.download_button(
            label="💾 Скачать отчёт DOCX",
            data=report,
            file_name=f"EP26_{sname}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with tab1:
    st.subheader('Инструкция по работе с приложением')
    with st.expander('Основные разделы', expanded=True):
        st.write('⚙️ **Внесите информацию о тесте** - эти данные не используются непосредственно в расчётах. ' \
        'Заполните их для получения готового отчёта')
        st.write('**Отчёт** 📋 - основная вкладка для внесения результатов и получения отчёта')
        st.write('👉 **Инструкция** - непосредственно этот раздел с подсказками')
        st.write('**Таблица 𝒜𝟏, Таблица 𝒜𝟐, Таблица 𝒜𝟑** - таблицы в цифровом формате, ' \
        'составленные по документу CLSI EP26-A для одного, двух и трёх уровней концентраций соответственно. ' \
        'Приводятся в качестве справки. По ним осуществляется поиск необходимого числа образцов и расчёт мощности в данном приложении.' \
        'В документе в приложении В приводится методика расчёта числа образцов и мощности для случаев, ' \
        'не охваченных таблицами А1-А3, но в данном приложении применение этого раздела пока не реализовано.')
    with st.expander('1️⃣', expanded=True):
        st.write('Для начала необходимо внести значение общей допустимой ошибки (Total Error (TE) в %). ' \
        'От значения TE напрямую зависит параметр Critical Diferense (CD), ' \
        'который по сути является выражением TE в абсолютных единицах для заданной концентрации')
        st.write('Выберите количество уровней концентраций, вблизи значений которых будет проводиться сравнение двух лотов.' \
        'Количество уровней концентраций должно подбираться исходя из числа критических/пороговых значений для данного теста. ')
    with st.expander('2️⃣', expanded=True):
        st.write('В следующем блоке необходимо внести значения концентраций для каждого уровня')
        st.write('Для каждого уровня необходимо выбрать фракцию CD, которая является той долей от критической разницы CD,' \
        ' с которой будут сравниваться полученные нами данные. ' \
        'Для этой доли от CD в документе CLSI EP26-A есть термин Rejection limit (RL) - предел исключения/выбраковки. ' \
        'В документе в таблицах А1-А3 приводятся расчёты для фракций 0.55, 0.6, 0.7, 0.8, 0.9.' \
        'Поскольку в данном приложении поиск необходимого числа образцов и расчёт мощности происходит по таблицам '
        '(как и в базовом сценарии по документу CLSI EP26-A), то и предлагается выбор только данных фракций.' \
        'От выбора фракции зависит расчёт мощности и число необходимых образцов для сравнения.' \
        'Чем меньше фракция CD, тем больше мощность, но тем и большее число образцов может потребоваться для сравнения. ' \
        'Вы должны определить желаемую мощность для теста, которую хотите достигнуть. ' \
        'Обычно для критически выжных показателей подбирают мощность не менее 0.9')
        st.write('В следующих колонках необходимо внести аналитические характеристики теста для каждой концентрации в одном из форматов, на ваш выбор:' \
        'Либо указать CV - коэффициент вариации, либо S - в формате стандартного отклонения.' )
        st.write('CVr или Sr - для внутрисейной воспроизводимости.')
        st.write('CVwrl или Swrl - для межсерийной воспроизводимости.')
        st.write('Вне зависимости от того, в каком формате вы внесете эти данные, ' \
        'в расчётах, поиске по таблице и в финальном отчёте будет принимать участие Sr и Swrl (как в документе).')
        st.write('Заполнение этих полей важно, в противном случае, вы увидите предупреждение "Внесите Swrl или CVwrl ⚠️"')
    with st.expander('3️⃣', expanded=True):
        st.write('После заполнения информации в предыдущем блоке автоматически ' \
        'по таблицам найдется и отобразится необходимое количество образцов и мощность критерия. ')
        st.write('Для получения приемлемых значений, может потребоваться корректировка фракции CD')
        st.write('Если после заполнения появился знак ⚠️ или предупреждение - ' \
        'либо в таблицах для ваших параметров нет рссчитанных значений (во вкладках с таблицами А1-А3 эти пробелы заполнены значком ⚠️), ' \
        'что обычно означает, что рассчитанные значения N заведомо неприемлемы (слишком большие) для применения,' \
        'либо таблицы не охватывают приведенные вами характеристики тест-системы.')
        st.write('Внесите результаты пар измерений для каждого уровня и лота')
    with st.expander('4️⃣', expanded=True):
        st.write('После заполнения всех полей приведенные ниже 4 таблицы автоматически заполнятся.')
        st.write('Эти таблицы практически повторяют таблицы из примеров, приведенных в документе CLSI EP26-A и составляют основу отчёта.')
        st.write('После таблиц есть кнопка "📝 Сформировать отчёт", ' \
        'нажав на которую приложение предложит скачать его в формате .docx, появится кнопка "💾 Скачать отчёт DOCX".')



with tab2:
    st.subheader('Таблица А1')
    st.markdown("**Количество образцов необходимое для обнаружения критической разницы между лотами для одного уровня принятия решений (с частотой ложных отклонений <= 5%)**")
    st.dataframe(df1)

with tab3:
    st.subheader('Таблица А2')
    st.markdown("**Количество образцов необходимое для обнаружения критической разницы между лотами для двух уровней принятия решений (с частотой ложных отклонений <= 2.5%)**")
    st.dataframe(df2)

with tab4:
    st.subheader('Таблица А3')
    st.markdown("**Количество образцов необходимое для обнаружения критической разницы между лотами для трёх уровней принятия решений (с частотой ложных отклонений <= 1,67%)**")
    st.dataframe(df3)

