import streamlit as st 
import pandas as pd 
import numpy as np 
import io
import datetime
from scipy.stats import chi2
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")


dft1 = pd.read_excel('ep15tables.xlsx', sheet_name='Table6', engine='openpyxl')
dft2 = pd.read_excel('ep15tables.xlsx', sheet_name='Table7', engine='openpyxl')
dft15 = pd.read_excel('ep15tables.xlsx', sheet_name='Table15A', engine='openpyxl')

minus = "\u2212"

# Боковая панель: выбор того, что оцениваем (воспроизводимость/правильность или и то и то, количество уровней и для готового отчёта)
st.title('👌 Верификация методики по документу CLSI EP15-A3')
swhat = st.sidebar.write('Что оцениваем?')
spres = st.sidebar.checkbox('Precision 📈', value = True)
trueness = st.sidebar.checkbox('Trueness 🎯', value= False)
snum = st.sidebar.number_input('Количество уровней', min_value=1, max_value=5,value=2)
#sexpand = st.sidebar.checkbox('Внести информацию для отчёта 📝',value=False) # убрал! пусть будет по дефолту

#if sexpand:
if spres is True and trueness is False:
    scont = st.sidebar.container(border=True, key = 'cont1')
    CM = scont.radio('Исследуемый материал', options=['Контрольный материал', 'Проба пациента'], key = 'CM')
    if CM == 'Контрольный материал':
        sqc = scont.text_input('Название QC', key = 'qc1')
        slot = scont.text_input('Лот QC', key = 'lot1')
        srok = scont.date_input('Срок годности', key = 'srok1', format = 'DD/MM/YYYY')
else:
    scont = st.sidebar.container(border=True, key = 'cont2')
    CM = scont.radio('Исследуемый материал', options=['Контрольный материал'], key = 'qconly')
    sqc = scont.text_input('Название QC', key = 'qc')
    slot = scont.text_input('Лот', key = 'lot')
    srok = scont.date_input('Срок годности', key = 'srok', format = 'DD/MM/YYYY')

sname = st.sidebar.text_input("Введите название теста")
sed = st.sidebar.text_input('Единицы измерения')
analyzer = st.sidebar.text_input("Анализатор")
org = st.sidebar.text_input("Организация")
lab = st.sidebar.text_input("Лаборатория/Отдел")
executor = st.sidebar.text_input("Выполнил")
approver = st.sidebar.text_input("Согласовал")

# Подготовка описательной таблицы
def describe(T):
    cols = ['День 1','День 2','День 3','День 4','День 5']
    total = T[['День 1','День 2','День 3','День 4','День 5']]
    Ms = []
    SDs = []
    CVs = []
    mins = []
    maxs = []
    for i in cols:
        m = np.mean(T[i])
        sd = np.std(T[i], ddof=1)
        cv = 100*sd/m
        Ms.append(round(m,3))
        SDs.append(round(sd,3))
        CVs.append(round(cv,2))
        mins.append(min(T[i].dropna(axis=0)))
        maxs.append(max(T[i].dropna(axis=0)))
    GM = total.to_numpy().mean()
    SDtot = np.std(total.to_numpy(),ddof=1)
    return Ms, SDs, CVs, GM, SDtot, mins, maxs

# Создание сраной таблицы
def describe_table(Ms, SDs, CVs, mins, maxs):
    des_table = {'': ['День 1','День 2','День 3','День 4','День 5'],
                 'Среднее': Ms,
                 'SD': SDs,
                 'CV': CVs,
                 'Минимальное значение': mins,
                 'Максимальное значение': maxs}
    d_t = pd.DataFrame.from_dict(des_table, orient='index')
    new_header = d_t.iloc[0]
    d_t = d_t[1:]
    d_t.rename(columns = new_header, inplace = True)
    return d_t


# Эта функция для Граббса не используется
def grabbs(T, Gcrit = 3.135):
    cols = ['День 1','День 2','День 3','День 4','День 5']
    total = T[['День 1','День 2','День 3','День 4','День 5']]
    values = []
    for k in cols:
        values = values + list(total[k])
    GM = total.to_numpy().mean()
    SDtot = np.std(total.to_numpy(),ddof=1)
    z = abs(values- GM)/SDtot
    outliers = []
    for k in range (0, len(z)):
        if z[k] > Gcrit:
            outliers.append(values[k])
    c11.markdown('**Тест Граббса для выявления выбросов:**')
    if len(outliers)>=1:
        c11.write(f'Выбросы: {outliers}')
    else:
        c11.write('Выбросы не обнаружены')


# Поиск фактора Граббса по формуле, а не по ебаным таблицам
# В документе, судя по всему, alpha = 0.01 иначе не получается Gcrit 3.135 при N = 25 
# Надо потом как-нибудь примастырить эту функцию
def get_gcrit(N):
    alpha = 0.01
    dof = N-2
    tcrit = stats.t.ppf(1-alpha/(2*N), dof)
    Gcrit = (N-1)/np.sqrt(N) * np.sqrt(tcrit**2/(N-2+tcrit**2))
    return Gcrit


# Поиск по таблице 6 (по куску, где 5х5 эксперимент)
def table6_search(dft1, p):
    col_p = dft1['P_5']
    col_df = dft1['DFwl_5']
    idx = np.argmin(abs(col_p - p))
    DFwl = col_df[idx]
    return DFwl

# Поиск по таблице 7
def table7_search(dft2, DF, levs):
    nsam = len(levs)
    row_df = dft2[dft2['DF'] == DF]
    F = list(row_df.iloc[:, nsam])[0]
    #st.write(F)
    return F

# Поиск по таблице 15А
def table15a_search(dft15, tau, nlab):
    tlablist = dft15['LABS'].unique()
    idx = np.argmin(abs(tlablist-nlab))
    labn = tlablist[idx]
    ndft15 = dft15[dft15['LABS'] == labn].reset_index()
    taucol = ndft15['TAU']
    dfcolt = ndft15['DFC']
    idt = np.argmin(abs(taucol - tau))
    dfc = dfcolt[idt]
    return dfc



anova_dict =  {"":[],
               "Всего измерений N": [],
               'Сумма квадратов SS между сериями(b)': [],
               'Сумма квадратов SS внутри серии (w)': [],
               'Сумма квадратов SS общая (total)': [],
               "Степени свободы DF1 (между сериями)": [],
               "Степени свободы DF2 (внутри серии)": [],
               "Средний квадрат MS1 (между сериями)": [],
               "Средний квадрат MS2 (внутри серии)": [],
               "Среднее количество повторов на серию n0": [],
               "Дисперсия Vb (между сериями)":[],
               "Дисперсия Vw (внутри серии)":[],
               "Общее среднее":[],
               'Повторяемость Sr / CVr %': [],
               "Внутрилабораторная непрецизионность Swl / CVwl %": [] }
               #'Повторяемость CVr %': [],
               #"Внутрилабораторная непрецизионность CVwl %": [] }



grubbs_dict = {"": [],
               "N": [],
               "Общее среднее": [],
               "SD":[],
               "Минимальное значение":[],
               "Максимальное значение":[],
               "Нижняя граница Граббса":[],
               "Верхняя граница Граббса":[],
               "Выбросы":[]}


ver_table_r1 = {"":[],
             'Наблюдаемый CVr': [],
             'Заявленный σ_r': [],
             'Верхняя верификационная граница, UVLr': [],
             'Внутренние требования к CVr': [],
             'Статус верификации': [],
             'Статус соответствия внутренним требованиям': []}

ver_table_wl1 = {"":[],
             'Наблюдаемый CVwl': [],
             'Заявленный σ_wl': [],
             'Верхняя верификационная граница, UVLwl': [],
             'Внутренние требования к CVwl': [],
             'Статус верификации': [],
             'Статус соответствия внутренним требованиям': []}

ver_table_r2 = {"":[],
             'Наблюдаемый CVr': [],
             'Заявленный σ_r': [],
             'Верхняя верификационная граница, UVLr': [],
             'Статус верификации': []}


ver_table_wl2 = {"":[],
             'Наблюдаемый CVwl': [],
             'Заявленный σ_wl': [],
             'Верхняя верификационная граница, UVLwl': [],
             'Статус верификации': []}


# Таблица оценки правильности (Trueness) по CLSI EP15-A3
trueness_dict = {"": [],
                 "Целевое значение": [],
                 "Среднее измеренное": [],
                 "Верификационный интервал":[],
                 #"Нижняя граница верификационного интервала": [],
                 #"Верхняя граница верификационного интервала": [],
                 "Абсолютное смещение": [],
                 "Относительное смещение, %": [],
                 "Предельно допустимое смещение, %": [],
                 "Статус смещения": [],
                 'Статус соответствия смещения внутренним требованиям': []}

trueness_est = {"": [],
                'Целевое значение': []}


# 
def trueness_calc(res, target, bias_lim, an, trueness_dict):
    # Оценка правильности
    #from scipy.stats import t as t_dist

    # Защита от рассинхрона списков (snum изменён после ввода уровней,
    # сценарий сменён на полпути и т.п.) — без неё SErms[an]/Us[an]/...
    # могли бы дать IndexError.
    if an >= len(SErms):
        return

    GM = res['GM']
    SWL = res['SWL']
    SR = res['SR']
    n_runs = res['k']            # число серий (дней)
    nrep = res['nrep']           # число повторов

    bias_abs = GM - target
    bias_pct = 100 * bias_abs / target if target != 0 else float('nan')

    # Стандартная ошибка среднего и полуширина 95% ДИ
    #SE = SWL / np.sqrt(n_runs)

    SEx = np.sqrt(1/n_runs * (SWL**2 - ((nrep-1)/nrep)*SR**2))
    SErm = SErms[an]
    SEc = np.sqrt(SEx**2 + SErm**2)
    alpha = 0.05

    if tradio == 'А. Референсный материал с заявленной неопределенностью': 
        dfx = n_runs - 1
        dfrm = 'infinity'
        dfc = dfx * ((SEc/SEx)**4)
        m = stats.t.ppf(1-alpha/(2*snum), dfc)
        VI_low = target - m*SEc
        VI_high = target + m*SEc
    if tradio == 'В. Материалы внешней оценки качества (ВОК)' or tradio == 'С. Результаты межлабораторного сравнения':
        tau = SErm/SEx
        dfc = table15a_search(dft15, tau, nlabs[an])
        m = stats.t.ppf(1-alpha/(2*snum), dfc)
        VI_low = target - m*SEc
        VI_high = target + m*SEc
    if tradio == 'D. Конвенциональное значение (искусственно приготовленный КМ, с добавлением известного количества аналита)' or tradio == 'Е. Коммерческий КМ без заявленной неопределенности':
        dfx = n_runs - 1
        dfrm = 'infinity'
        dfc = n_runs - 1
        m = stats.t.ppf(1-alpha/(2*snum), dfc)
        VI_low = target - m*SEc
        VI_high = target + m*SEc



    # Статус смещения.
    # 
    VI_ok = VI_low <= GM <= VI_high
    status_v = '✅ Статистически незначимое' if VI_ok else '❌ Статистически значимое'
    if bias_lim > 0:
        #
        status_b = '✅ Соответствует' if abs(bias_pct) <= bias_lim else '❌ Не соответствует'

    
    # почему бы и нет?
    trueness_est[''].append(f'Уровень {an+1}')
    trueness_est['Целевое значение'].append(round(target, 3))

    if tradio == 'А. Референсный материал с заявленной неопределенностью': 
        if 'Расширенная неопределенность КМ (U)' not in trueness_est:
            trueness_est['Расширенная неопределенность КМ (U)'] = []
            trueness_est['Расширенная неопределенность КМ (U)'].append(round(Us[an],2))
        else:
            trueness_est['Расширенная неопределенность КМ (U)'].append(round(Us[an],2))

        if 'Фактор покрытия' not in trueness_est:
            trueness_est['Фактор покрытия'] = []
            trueness_est['Фактор покрытия'].append(kas[an])
        else:
            trueness_est['Фактор покрытия'].append(kas[an])

    if tradio == 'В. Материалы внешней оценки качества (ВОК)' or tradio == 'С. Результаты межлабораторного сравнения':
        if 'Количество лабораторий' not in trueness_est:
            trueness_est['Количество лабораторий'] = []
            trueness_est['Количество лабораторий'].append(nlabs[an])
        else:
            trueness_est['Количество лабораторий'].append(nlabs[an])

        if 'tau' not in trueness_est:
            trueness_est['tau'] = []
            trueness_est['tau'].append(round(tau,3))
        else:
            trueness_est['tau'].append(round(tau,3))

    if tradio == 'А. Референсный материал с заявленной неопределенностью' or tradio == 'D. Конвенциональное значение (искусственно приготовленный КМ, с добавлением известного количества аналита)' or tradio == 'Е. Коммерческий КМ без заявленной неопределенности':
        if 'DFx' not in trueness_est:
            trueness_est['DFx'] = []
            trueness_est['DFx'].append(dfx)
        else:
            trueness_est['DFx'].append(dfx)

        if 'DFrm' not in trueness_est:
            trueness_est['DFrm'] = []
            trueness_est['DFrm'].append(dfrm)
        else:
            trueness_est['DFrm'].append(dfrm)

    if 'DFc' not in trueness_est:
        trueness_est['DFc'] = []
        trueness_est['DFc'].append(round(dfc))
    else:
        trueness_est['DFc'].append(round(dfc))

    if 'Стандартная ошибка среднего, SEx' not in trueness_est:
        trueness_est['Стандартная ошибка среднего, SEx'] = []
        trueness_est['Стандартная ошибка среднего, SEx'].append(round(SEx,3))
    else:
        trueness_est['Стандартная ошибка среднего, SEx'].append(round(SEx,3))

    if 'Стандартная ошибка КМ, SErm' not in trueness_est:
        trueness_est['Стандартная ошибка КМ, SErm'] = []
        trueness_est['Стандартная ошибка КМ, SErm'].append(round(SErm,3))
    else:
        trueness_est['Стандартная ошибка КМ, SErm'].append(round(SErm,3))

    if 'Комбинированная стандартная ошибка, SEc' not in trueness_est:
        trueness_est['Комбинированная стандартная ошибка, SEc'] = []
        trueness_est['Комбинированная стандартная ошибка, SEc'].append(round(SEc,3))
    else:
        trueness_est['Комбинированная стандартная ошибка, SEc'].append(round(SEc,3))

    if 'Множитель m (квантиль распределения Стьюдента)' not in trueness_est:
        trueness_est['Множитель m (квантиль распределения Стьюдента)'] = []
        trueness_est['Множитель m (квантиль распределения Стьюдента)'].append(round(m,3))
    else:
        trueness_est['Множитель m (квантиль распределения Стьюдента)'].append(round(m,3))
    
    if 'Нижняя граница верификационного интервала' not in trueness_est:
        trueness_est['Нижняя граница верификационного интервала'] = []
        trueness_est['Нижняя граница верификационного интервала'].append(round(VI_low, 3))
    else:
        trueness_est['Нижняя граница верификационного интервала'].append(round(VI_low, 3))
    
    if 'Верхняя граница верификационного интервала' not in trueness_est:
        trueness_est['Верхняя граница верификационного интервала'] = []
        trueness_est['Верхняя граница верификационного интервала'].append(round(VI_high, 3))
    else:
        trueness_est['Верхняя граница верификационного интервала'].append(round(VI_high, 3))


#

    trueness_dict[''].append(f'Уровень {an+1}')
    trueness_dict['Целевое значение'].append(round(target, 3))
    trueness_dict['Среднее измеренное'].append(round(GM, 3))
    trueness_dict['Верификационный интервал'].append(f'{round(VI_low, 3)} {minus} {round(VI_high, 3)}')
    trueness_dict['Абсолютное смещение'].append(round(bias_abs, 3))
    trueness_dict['Относительное смещение, %'].append(round(bias_pct, 2))
    #trueness_dict['Нижняя граница верификационного интервала'].append(round(VI_low, 3))
    #trueness_dict['Верхняя граница верификационного интервала'].append(round(VI_high, 3))
    trueness_dict['Предельно допустимое смещение, %'].append(bias_lim if bias_lim > 0 else '—')
    trueness_dict['Статус смещения'].append(status_v)
    trueness_dict['Статус соответствия смещения внутренним требованиям'].append(status_b if bias_lim > 0 else '—')



def specification_prepare(mcvrs, mcvws, levs, spmeans):
    DFr = 5*5 - 5
    DFrs = list(np.ones(len(levs)) * DFr)
    Frs = []
    UVLrs = []
    for r in range (0, len(levs)):
        F_r = table7_search(dft2, DFr, levs)
        Frs.append(F_r)
        UVLr = mcvrs[r]*F_r
        UVLrs.append(round(UVLr,2))
    ps = []
    DFwls = []
    Fwls = []
    UVLwls = []
    levels = []
    for l in range (0, len(levs)):
        level = f'Уровень {l+1}'
        levels.append(level)
        if mcvrs[l] !=0:
            p = mcvws[l]/mcvrs[l]
            ps.append(round(p,2))
            DFwl = table6_search(dft1, p)
            DFwls.append(DFwl)
            Fwl = table7_search(dft2,DFwl,levs)
            Fwls.append(round(Fwl,2))
            UVLwl = mcvws[l]*Fwl
            UVLwls.append(round(UVLwl,2))
        else:
            st.warning('⚠️❗ Заполните спецификации производителя!')
    return DFrs, Frs, UVLrs, ps, DFwls, levels, Fwls, UVLwls


def specification_table(mcvrs, mcvws, levels, spmeans, DFrs, Frs, UVLrs, ps, DFwls, Fwls, UVLwls):
    specification_dict = {'Уровень': levels,
                      'Среднее':spmeans,
                      'σ_r':mcvrs,
                      'DFr':DFrs,
                      'F_r':Frs,
                      'UVLr, %': UVLrs,
                      'σ_wl':mcvws,
                      'p':ps,
                      'DFwl':DFwls,
                      'F_wl':Fwls,
                      'UVLwl, %':UVLwls}
    s_t = pd.DataFrame.from_dict(specification_dict, orient='index')
    new_spec_header = s_t.iloc[0]
    s_t = s_t[1:]
    s_t.rename(columns = new_spec_header, inplace = True)

    return  s_t 




# ----

def anova(T, an, anova_dict, grubbs_dict, mcvrs, mcvws, UVLrs, UVLwls, cvr_vn, cva_vn, Gcrit = 3.135):
    total = T.iloc[:,1:]
    N = total.size
    k = total.shape[1]
    #
    GM = np.mean(total.stack())
    SDtot = np.std(total.stack().to_numpy(),ddof=1)

    #

    mean_i_list = []
    ssw_list = []
    ss_tot = []
    n2s = []
    NS = []
    values = []
    outliers = []
    total2 = total.copy()
    for i in range (0,k):
        t = T.iloc[:,1+i]
        ni = len(t) - len(t[t.isna()])
        NS.append(ni)
        n2 = ni**2
        n2s.append(n2)
        mean_i = np.mean(t.dropna(axis=0))
        mean_i_list.append(mean_i)
        ssw = sum((t.dropna(axis=0)-mean_i)**2)
        ssw_list.append(ssw)
        sst = sum((t.dropna(axis=0)-GM)**2)
        ss_tot.append(sst)

        values = values + list(t)
        z = abs(t - GM)/SDtot   # для Граббса
        schet = 0
        for g in range (0, len(z)):
            if z[g] > Gcrit:
                schet = schet + 1
                outliers.append(float(t[g]))
                total2.iloc[g, i] = np.nan
                if schet>=2:
                    st.warning('📢❗🚨 Два или более значений в течении одной серии являются выбросами! '
                               'Необходимо выявить причину! '
                               'Повторите серию!')
        if len(outliers)>2:
            st.warning('📢❗🚨 Много выбросов! Необходимо выявить причину, повторить серии! При необходимости свяжитесь с производителем!')
    


    SN2 = sum(n2s)
    Ns = sum(NS)
    nrep = Ns/k
    n0 = (Ns-(SN2/Ns))/(k-1)
    DF1 = k-1
    DF2 = Ns-k   # верно

    SS_b = sum(np.array(NS)*(np.array(mean_i_list)-GM)**2)   # взвешено по n_i: корректно и для несбалансированных серий
    SS_w = sum(ssw_list)
    SS_total = np.sum((total.to_numpy() - GM)**2)
    SS_w2 = round(SS_total - SS_b,3)
    SS_total2 = sum(ss_tot)

    MS_b = SS_b/DF1
    MS_w = SS_w/DF2


    # Прямой расчет DFwl согласно Appendix B4
    SN2 = sum(n2s)
    Ns = sum(NS)
    n0 = (Ns-(SN2/Ns))/(k-1)

    a1 = 1/n0
    a2 = (n0-1)/n0
    num = (a1*MS_b + a2*MS_w)**2
    den1 = ((a1*MS_b)**2)/DF1
    den2 = ((a2*MS_w)**2)/DF2
    DFwl = num/(den1+den2)

    # ХИ-квадрат для вычисления фактора F (Appendix B5)
    alpha = 0.05
    q_r = chi2.ppf(1-alpha/snum, DF2)
    q_wl = chi2.ppf(1-alpha/snum, DFwl)
    F_r = np.sqrt(q_r/DF2)
    F_wl = np.sqrt(q_wl/DFwl)

    #
    day_means = np.mean(total, axis=0)
    SS_between = total.shape[0] * np.sum((day_means-GM)**2)
    SS_within = np.sum((total - day_means)**2)

    MS1 = SS_between / DF1
    MS2 = SS_within / DF2
    VW = MS_w

    if MS_b < MS_w:
        VB = 0
    else:
        VB = (MS_b-MS_w)/n0

    SR = np.sqrt(VW)
    SWL = np.sqrt(VW+VB)
    CVR = 100 * SR / GM
    CVWL = 100 * SWL / GM
    
    # Сбор ANOVA - таблицы
    anova_dict[''].append(f'Уровень {an+1}')
    anova_dict["Всего измерений N"].append(Ns)
    anova_dict['Сумма квадратов SS между сериями(b)'].append(round(SS_b,3))
    anova_dict['Сумма квадратов SS внутри серии (w)'].append(round(SS_w,3))
    anova_dict['Сумма квадратов SS общая (total)'].append(round(SS_total,3))
    anova_dict["Степени свободы DF1 (между сериями)"].append(DF1)
    anova_dict["Степени свободы DF2 (внутри серии)"].append(DF2)
    anova_dict["Средний квадрат MS1 (между сериями)"].append(round(MS_b,3))
    anova_dict["Средний квадрат MS2 (внутри серии)"].append(round(MS_w,3))
    anova_dict['Среднее количество повторов на серию n0'].append(round(n0,2))
    anova_dict['Дисперсия Vb (между сериями)'].append(round(VB,3))
    anova_dict['Дисперсия Vw (внутри серии)'].append(round(VW,3))
    anova_dict['Общее среднее'].append(round(GM,3))
    anova_dict['Повторяемость Sr / CVr %'].append(f'{round(SR,3)}  /  {round(CVR,2)}%')
    anova_dict["Внутрилабораторная непрецизионность Swl / CVwl %"].append(f'{round(SWL,3)}  /  {round(CVWL,2)}%')


    # Граббсер:
    grubbs_dict[''].append(f'Уровень {an+1}')
    grubbs_dict['N'].append(Ns)
    grubbs_dict['Общее среднее'].append(round(GM,3))
    grubbs_dict['SD'].append(round(SDtot,3))
    grubbs_dict['Минимальное значение'].append(round(min(values),3))
    grubbs_dict['Максимальное значение'].append(round(max(values),3))
    grubbs_dict['Нижняя граница Граббса'].append(round(GM - Gcrit*SDtot, 3))
    grubbs_dict['Верхняя граница Граббса'].append(round(GM + Gcrit*SDtot, 3))
    grubbs_dict['Выбросы'].append(outliers if len(outliers)>=1 else "Не обнаружены")
 
    # Верификация
    ver_table_r1[''].append(f'Уровень {an+1}')
    ver_table_r1['Наблюдаемый CVr'].append(round(CVR,2))
    ver_table_r1['Заявленный σ_r'].append(mcvrs[an])
    ver_table_r1['Верхняя верификационная граница, UVLr'].append(round(UVLrs[an],2))
    ver_table_r1['Внутренние требования к CVr'].append(cvr_vn)
    ver_table_r1['Статус верификации'].append('✅ Прошла' if CVR<=UVLrs[an] else '❌ Не  прошла')
    ver_table_r1['Статус соответствия внутренним требованиям'].append('✅ Соответствует' if CVR <=cvr_vn else '❌ Не соответствует')

    ver_table_wl1[''].append(f'Уровень {an+1}')
    ver_table_wl1['Наблюдаемый CVwl'].append(round(CVWL,2))
    ver_table_wl1['Заявленный σ_wl'].append(mcvws[an])
    ver_table_wl1['Верхняя верификационная граница, UVLwl'].append(round(UVLwls[an],2))
    ver_table_wl1['Внутренние требования к CVwl'].append(cva_vn)
    ver_table_wl1['Статус верификации'].append('✅ Прошла' if CVWL<=UVLwls[an] else '❌ Не  прошла')
    ver_table_wl1['Статус соответствия внутренним требованиям'].append('✅ Соответствует' if CVWL <=cva_vn else '❌ Не соответствует')

    ver_table_r2[''].append(f'Уровень {an+1}')
    ver_table_r2['Наблюдаемый CVr'].append(round(CVR,2))
    ver_table_r2['Заявленный σ_r'].append(mcvrs[an])
    ver_table_r2['Верхняя верификационная граница, UVLr'].append(round(UVLrs[an],2))
    ver_table_r2['Статус верификации'].append('✅ Прошла' if CVR<=UVLrs[an] else '❌ Не  прошла')


    ver_table_wl2[''].append(f'Уровень {an+1}')
    ver_table_wl2['Наблюдаемый CVwl'].append(round(CVWL,2))
    ver_table_wl2['Заявленный σ_wl'].append(mcvws[an])
    ver_table_wl2['Верхняя верификационная граница, UVLwl'].append(round(UVLwls[an],2))
    ver_table_wl2['Статус верификации'].append('✅ Прошла' if CVWL<=UVLwls[an] else '❌ Не  прошла')


    # Если есть выбросы: (копипаст на пофиг)
    if len(outliers)>=1:
        GM = np.mean(total2.stack())
        #SDtot2 = np.std(total2.stack().to_numpy(),ddof=1)
        SDtot2 = np.nanstd(total2.values, ddof = 1)
        mean_i_list = []
        ssw_list2 = []
        ss_tot = []
        n2s = []
        NS = []
        values2 = []
        for i in range (0,k):
            t = total2.iloc[:,i]
            ni = len(t) - len(t[t.isna()])
            NS.append(ni)
            n2 = ni**2
            n2s.append(n2)
            mean_i = np.mean(t.dropna(axis=0))
            mean_i_list.append(mean_i)
            ssw = sum((t.dropna(axis=0)-mean_i)**2)
            ssw_list2.append(ssw)
            sst = np.sum((t.dropna(axis=0)-GM)**2)
            ss_tot.append(sst)
            values2 = values2 + list(t.dropna(axis=0))
   


        SN2 = sum(n2s)
        Ns = sum(NS)
        nrep = Ns/k     # эта хуйня потом нужна в расчёте стандартной ошибки среднего для трунесса
        n0 = (Ns-(SN2/Ns))/(k-1)
        DF1 = k-1
        DF2 = Ns-k   # верно
        SS_b = sum(np.array(NS)*(np.array(mean_i_list)-GM)**2)   # взвешено по n_i: корректно и для несбалансированных серий
        SS_w = np.sum(ssw_list2)
        #SS_total = np.sum((total2.stack().to_numpy() - GM)**2)
        SS_total = np.nansum((total2.to_numpy() - GM)**2)
        #SS_w2 = round(SS_total - SS_b,3)
        #SS_total2 = sum(ss_tot)
        MS_b = SS_b/DF1
        MS_w = SS_w/DF2
        # Прямой расчет DFwl согласно Appendix B4
        SN2 = sum(n2s)
        Ns = sum(NS)
        n0 = (Ns-(SN2/Ns))/(k-1)
        a1 = 1/n0
        a2 = (n0-1)/n0
        num = (a1*MS_b + a2*MS_w)**2
        den1 = ((a1*MS_b)**2)/DF1
        den2 = ((a2*MS_w)**2)/DF2
        DFwl = num/(den1+den2)
        # ХИ-квадрат для вычисления фактора F (Appendix B5)
        alpha = 0.05
        q_r = chi2.ppf(1-alpha/snum, DF2)
        q_wl = chi2.ppf(1-alpha/snum, DFwl)
        F_r = np.sqrt(q_r/DF2)
        F_wl = np.sqrt(q_wl/DFwl)
        #
        day_means = np.mean(total2, axis=0)
        SS_between = total2.shape[0] * np.sum((day_means-GM)**2)
        SS_within = np.sum((total2 - day_means)**2) 
        #MS1 = SS_between / DF1
        #MS2 = SS_within / DF2
        VW = MS_w

        if MS_b < MS_w:
            VB = 0
        else:
            VB = (MS_b-MS_w)/n0
        #VB = (MS_b-MS_w)/n0

        SR = np.sqrt(VW)
        SWL = np.sqrt(VW+VB)
        CVR = 100 * SR / GM
        CVWL = 100 * SWL / GM
    
        # Сбор ANOVA - таблицы
        anova_dict[''].append(f'Уровень {an+1} (выбросы исключены)')
        anova_dict["Всего измерений N"].append(Ns)
        anova_dict['Сумма квадратов SS между сериями(b)'].append(round(SS_b,3))
        anova_dict['Сумма квадратов SS внутри серии (w)'].append(round(SS_w,3))
        anova_dict['Сумма квадратов SS общая (total)'].append(round(SS_total,3))
        anova_dict["Степени свободы DF1 (между сериями)"].append(DF1)
        anova_dict["Степени свободы DF2 (внутри серии)"].append(DF2)
        anova_dict["Средний квадрат MS1 (между сериями)"].append(round(MS_b,3))
        anova_dict["Средний квадрат MS2 (внутри серии)"].append(round(MS_w,3))
        anova_dict['Среднее количество повторов на серию n0'].append(round(n0,2))
        anova_dict['Дисперсия Vb (между сериями)'].append(round(VB,3))
        anova_dict['Дисперсия Vw (внутри серии)'].append(round(VW,3))
        anova_dict['Общее среднее'].append(round(GM,3))
        anova_dict['Повторяемость Sr / CVr %'].append(f'{round(SR,3)}  /  {round(CVR,2)}%')
        anova_dict["Внутрилабораторная непрецизионность Swl / CVwl %"].append(f'{round(SWL,3)}  /  {round(CVWL,2)}%')


        # Граббсер:
        grubbs_dict[''].append(f'Уровень {an+1} (выбросы исключены)')
        grubbs_dict['N'].append(Ns)
        grubbs_dict['Общее среднее'].append(round(GM,3))
        grubbs_dict['SD'].append(round(SDtot2,3))
        grubbs_dict['Минимальное значение'].append(round(min(values2),3))
        grubbs_dict['Максимальное значение'].append(round(max(values2),3))
        grubbs_dict['Нижняя граница Граббса'].append('—')
        grubbs_dict['Верхняя граница Граббса'].append('—')
        grubbs_dict['Выбросы'].append('—')

        ver_table_r1[''].append(f'Уровень {an+1} (выбросы исключены)')
        ver_table_r1['Наблюдаемый CVr'].append(round(CVR,2))
        ver_table_r1['Заявленный σ_r'].append(mcvrs[an])
        ver_table_r1['Верхняя верификационная граница, UVLr'].append(round(UVLrs[an],2))
        ver_table_r1['Внутренние требования к CVr'].append(cvr_vn)
        ver_table_r1['Статус верификации'].append('✅ Прошла' if CVR<=UVLrs[an] else '❌ Не  прошла')
        ver_table_r1['Статус соответствия внутренним требованиям'].append('✅ Соответствует' if CVR <=cvr_vn else '❌ Не соответствует')

        ver_table_wl1[''].append(f'Уровень {an+1} (выбросы исключены)')
        ver_table_wl1['Наблюдаемый CVwl'].append(round(CVWL,2))
        ver_table_wl1['Заявленный σ_wl'].append(mcvws[an])
        ver_table_wl1['Верхняя верификационная граница, UVLwl'].append(round(UVLwls[an],2))
        ver_table_wl1['Внутренние требования к CVwl'].append(cva_vn)
        ver_table_wl1['Статус верификации'].append('✅ Прошла' if CVWL<=UVLwls[an] else '❌ Не  прошла')
        ver_table_wl1['Статус соответствия внутренним требованиям'].append('✅ Соответствует' if CVWL <=cva_vn else '❌ Не соответствует')

        ver_table_r2[''].append(f'Уровень {an+1} (выбросы исключены)')
        ver_table_r2['Наблюдаемый CVr'].append(round(CVR,2))
        ver_table_r2['Заявленный σ_r'].append(mcvrs[an])
        ver_table_r2['Верхняя верификационная граница, UVLr'].append(round(UVLrs[an],2))
        ver_table_r2['Статус верификации'].append('✅ Прошла' if CVR<=UVLrs[an] else '❌ Не  прошла')


        ver_table_wl2[''].append(f'Уровень {an+1} (выбросы исключены)')
        ver_table_wl2['Наблюдаемый CVwl'].append(round(CVWL,2))
        ver_table_wl2['Заявленный σ_wl'].append(mcvws[an])
        ver_table_wl2['Верхняя верификационная граница, UVLwl'].append(round(UVLwls[an],2))
        ver_table_wl2['Статус верификации'].append('✅ Прошла' if CVWL<=UVLwls[an] else '❌ Не  прошла')

           

    # Возврат финальных результатов уровня наружу (значения уже учитывают
    # исключение выбросов, если оно было) — нужно для раздела Trueness и отчёта.
    return {'GM': GM, 'SR': SR, 'SWL': SWL, 'CVR': CVR, 'CVWL': CVWL,
            'DFwl': DFwl, 'DF2': DF2, 'n0': n0, 'k': k, 'nrep': nrep, 'Ns': Ns}

def plot_box(df):
    fig, ax = plt.subplots()
    fig.set_size_inches(9,4.7)
    data = df.iloc[:,1:].to_numpy()
    sns.boxplot(data=data, ax=ax)
    # seaborn нумерует категории с 0; переименовываем тики, чтобы дни шли с 1
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels([str(d+1) for d in range(data.shape[1])])
    ax.set_xlabel("Дни")
    ax.set_ylabel("Результат")
    return fig


def plot_levey(T, Gcrit = 3.135):
    means = T.iloc[:,1:].to_numpy().mean(axis=0)
    GM = means.mean()
    SDtot = np.std(T.iloc[:,1:].stack().to_numpy(),ddof=1)
    Glow = GM - Gcrit*SDtot
    Ghigh = GM + Gcrit*SDtot
    values = []
    outliers = []
    ox = []
    dmeans = []
    for v in range (0, len(means)):
        t = T.iloc[:,1+v]
        dmeans.append(np.mean(t))
        values = values + list(t)
    for g in range (0, len(values)):
        z = abs(np.array(values) - GM)/SDtot   # для Граббса
        if z[g] > Gcrit:
            outliers.append(values[g])
            ox.append(g+1)
    fig, ax = plt.subplots()
    fig.set_size_inches(9,4.7)
    points = np.arange(0, 26).tolist()
    #points = np.linspace(0, 1, 25).tolist()
    ax.scatter(range(1,len(values)+1), values, marker='o')
    if len(outliers)>=1:
        ax.scatter(ox, outliers, color = 'orange')
    for z in range (0, len(means)):
        y = np.ones(5)*dmeans[z]
        x = points[points[z]*5+1 : points[z+1]*5+1]
        #ax.axhline(dmeans[z], xmin=points[z]*5, xmax=points[z+1]*5, color = 'g', alpha = 0.7)
        ax.plot(x,y,color='g')

    ax.axhline(means.mean(), linestyle='--', label = 'Общее среднее')
    ax.axhline(Glow, linestyle='--', color = 'r', label = 'Границы Граббса')
    ax.axhline(Ghigh, linestyle='--', color = 'r')
    x = range(1,len(values)+1)
    repeat_labels = [1,2,3,4,5] * 5
    ax.set_xticks(x)
    ax.set_xticklabels(repeat_labels)
    ax.set_xlabel("Повторы")
    day_centers = [2.5,7.5,12.5,17.5,22.5]
    secax = ax.secondary_xaxis('top')
    secax.set_xticks(day_centers)
    secax.set_xticklabels(['День 1','День 2','День 3','День 4','День 5'])
    #secax.set_xlabel("Дни")
    for d in [5.5, 10.5, 15.5, 20.5]:
        ax.axvline(d, linestyle='--', alpha=0.4)
    ax.set_ylabel("Результат")
    ax.legend()
    return fig

c01,c02 = st.columns(2)

tablo = {"Повторы":["1","2","3","4","5"],
         "День 1":[0,0,0,0,0],
         "День 2":[0,0,0,0,0],
         "День 3":[0,0,0,0,0],
         "День 4":[0,0,0,0,0],
         "День 5":[0,0,0,0,0]}

column_config={
        "col2": st.column_config.NumberColumn("День 1",step=0.003, min_value=0),
        "col3": st.column_config.NumberColumn("День 2",step=0.003, min_value=0),
        "col4": st.column_config.NumberColumn("День 3",step=0.003, min_value=0),
        "col5": st.column_config.NumberColumn("День 4",step=0.003, min_value=0),
        "col6": st.column_config.NumberColumn("День 5",step=0.003, min_value=0)}


df = pd.DataFrame(tablo)
df['День 1']=df['День 1'].astype(float)
df['День 2']=df['День 2'].astype(float)
df['День 3']=df['День 3'].astype(float)
df['День 4']=df['День 4'].astype(float)
df['День 5']=df['День 5'].astype(float)

if spres is True:
    container1 = c01.container(border=True, vertical_alignment='center', horizontal_alignment='center')
    container1.markdown('📑 ***Спецификации по прецизионности, указанные производителем***')
    c000100, c00100, c00200, c00300 = container1.columns(4)
    c00010, c0010, c0020, c0030 = container1.columns(4)
    c00011, c0011, c0021, c0031 = container1.columns(4)
    c00012, c0012, c0022, c0032 = container1.columns(4)
    c00013, c0013, c003, c0033 = container1.columns(4)
    c00014, c0014, c0024, c0034 = container1.columns(4)
    sp_cs = [c00010, c0010, c0020, c0030, c00011, c0011, c0021, c0031, c00012, c0012, c0022, c0032, c00013, c0013, c003, c0033, c00014, c0014, c0024, c0034]
 
    mcvrs = []
    mcvws = []
    levs = []
    spmeans = []

    c00100.markdown('***Среднее***')
    c00200.markdown(r'***$\sigma_r$***')
    c00300.markdown(r'***$\sigma_{wl}$***')
    for n in range (0, snum):
        lev = sp_cs[n*4].markdown(f'***Уровень {n+1}***')
        sp_mean = sp_cs[n*4+1].number_input('Среднее', key = n+100, label_visibility='collapsed', min_value=0.000)
        mcvr = sp_cs[n*4+2].number_input('CVr', key = n+200, label_visibility='collapsed', min_value=0.00)
        mcvw = sp_cs[n*4+3].number_input('CVwl', key = n+300, label_visibility='collapsed', min_value=0.00)
        levs.append(lev)
        spmeans.append(sp_mean)
        mcvrs.append(mcvr)
        mcvws.append(mcvw)
    container2 = c02.container(border=True)
    vntreb = container2.checkbox('⬅️ ***Дополнить отчёт сравнением с внутренними требованиями лаборатории к прецизионности***', value = False)
    cvr_vn = container2.number_input(r'Внутренние требования к $CV_r$', min_value=0.00)
    cva_vn = container2.number_input(r'Внутренние требования к $CV_a$', min_value=0.00)
else:
    # Если Precision выключен, эти переменные всё равно нужны дальше по коду —
    # задаём безопасные значения по умолчанию.
    mcvrs, mcvws, levs, spmeans = [], [], [], []
    cvr_vn, cva_vn, vntreb = 0.0, 0.0, False

# Блок ввода целевых значений для оценки правильности и прочей поебени
target_vals = []   # целевое (референсное) значение по каждому уровню
#bias_limits = []   # допустимый предел относительного смещения, %
Us = []
kas = []
SErms = []
SDg = []
nlabs = []
if trueness is True:
    tcont = st.container(border=True)
    tcol1,tcol2 = tcont.columns(2)
    tradio = tcol1.radio('***Выберите сценарий***', options=['А. Референсный материал с заявленной неопределенностью',
                                                        'В. Материалы внешней оценки качества (ВОК)',
                                                         'С. Результаты межлабораторного сравнения',
                                                         'D. Конвенциональное значение (искусственно приготовленный КМ, с добавлением известного количества аналита)',
                                                         'Е. Коммерческий КМ без заявленной неопределенности'])
    
    bias_lim = tcol2.number_input('***Предельно допустимое смещение, % в соответствии с внутренними требованиями***', min_value=0.00)

    if tradio == 'А. Референсный материал с заявленной неопределенностью':
        tcont.markdown('🎯 ***Целевые значения для оценки правильности (Trueness)***')
        tc = tcont.columns(4)
        tc[1].markdown('***Целевое значение***')
        tc[2].markdown('***Расширенная неопределенность U***')
        tc[3].markdown('***Фактор покрытия (для 95 или 99% ДИ)***')
        for n in range(0, snum):
            t_row = tcont.columns(4)
            t_row[0].markdown(f'***Уровень {n+1}***')
            tv = t_row[1].number_input('Целевое значение', key=f'atval{n}',
                                       label_visibility='collapsed', min_value=0.000)
            U = t_row[2].number_input('Неопределенность', key=f'U{n}',
                                   label_visibility='collapsed', min_value=0.00)
            ka = t_row[3].selectbox('Фактор покрытия', key=f'ka{n}',
                                   label_visibility='collapsed', options=[1.96, 2.58])
            SErm = U/ka
            target_vals.append(tv)
            Us.append(U)
            kas.append(ka)
            SErms.append(SErm)

    if tradio == 'В. Материалы внешней оценки качества (ВОК)' or tradio == 'С. Результаты межлабораторного сравнения':
        tcont.markdown('🎯 ***Необходимые данные для оценки правильности***')
        tc = tcont.columns(4)
        tc[1].markdown('***Целевое значение***')
        tc[2].markdown('***SD по группе***')
        tc[3].markdown('***Число лабораторий***')
        for n in range(0, snum):
            t_row = tcont.columns(4)
            t_row[0].markdown(f'***Уровень {n+1}***')
            tv = t_row[1].number_input('Целевое значение', key=f'labtval{n}',
                                       label_visibility='collapsed', min_value=0.000)
            SDgroup = t_row[2].number_input('SD по группе', key=f'SDgroup{n}',
                                   label_visibility='collapsed', min_value=0.000)
            nlab = t_row[3].number_input('Число лабораторий', key=f'nlab{n}',
                                   label_visibility='collapsed', min_value= 1 )
            SErm = SDgroup/np.sqrt(nlab)
            target_vals.append(tv)
            SDg.append(SDgroup)
            nlabs.append(nlab)
            SErms.append(SErm)


    if tradio == 'D. Конвенциональное значение (искусственно приготовленный КМ, с добавлением известного количества аналита)' or tradio == 'Е. Коммерческий КМ без заявленной неопределенности':
        tc = tcont.columns(3)
        tc[1].markdown('***Целевое значение***')
        tc[2].markdown('***Стандартная ошибка референсного материала***')
        for n in range(0, snum):
            t_row = tcont.columns(3)
            t_row[0].markdown(f'***Уровень {n+1}***')
            tv = t_row[1].number_input('Целевое значение', key=f'qctval{n}',
                                       label_visibility='collapsed', min_value=0.000)
            SDgroup = t_row[2].markdown(r'***$SE_{RM}$ = 0***')   
            target_vals.append(tv)
            SErm = 0
            SErms.append(SErm)



    
#    tcont.markdown('🎯 ***Целевые значения для оценки правильности (Trueness)***')
#    t_hdr = tcont.columns(3)
#    t_hdr[1].markdown('***Целевое значение***')
#    t_hdr[2].markdown('***Допуск на смещение, % (0 = без проверки)***')
#    for n in range(0, snum):
#        t_row = tcont.columns(3)
#        t_row[0].markdown(f'***Уровень {n+1}***')
#        tv = t_row[1].number_input('Целевое значение', key=f'tval{n}',
#                                   label_visibility='collapsed', min_value=0.000)
#        bl = t_row[2].number_input('Допуск на смещение', key=f'blim{n}',
#                                   label_visibility='collapsed', min_value=0.00)
#        target_vals.append(tv)
#        bias_limits.append(bl)


box = st.container(border=True, horizontal_alignment='center', vertical_alignment='center')
boxform = box.form('Форма внесения данных')
boxform.subheader('*Внесите в таблицы результаты эксперимента*')
Ts = []
Ts_date = []
cds = []
for n in range(0,snum):
    boxform.subheader(f'*Уровень {n+1}*')
    cd0, cd1, cd2, cd3, cd4, cd5 = boxform.columns(6)
    cds = cds + [cd0, cd1, cd2, cd3, cd4, cd5]
    cds[n*6].write('')
    date1 = cds[n*6+1].date_input('День 1', key = f'День 1 {n}', label_visibility = 'collapsed',format = 'DD/MM/YYYY')
    date2 = cds[n*6+2].date_input('День 2', key = f'День 2 {n}', label_visibility = 'collapsed',format = 'DD/MM/YYYY')
    date3 = cds[n*6+3].date_input('День 3', key = f'День 3 {n}', label_visibility = 'collapsed',format = 'DD/MM/YYYY')
    date4 = cds[n*6+4].date_input('День 4', key = f'День 4 {n}', label_visibility = 'collapsed',format = 'DD/MM/YYYY')
    date5 = cds[n*6+5].date_input('День 5', key = f'День 5 {n}', label_visibility = 'collapsed',format = 'DD/MM/YYYY')
    T = boxform.data_editor(df, column_config=column_config, hide_index=True,key=f't{n+1}')
    df2 = pd.DataFrame(T, dtype=float)
    
    dates = [date1, date2, date3, date4, date5]
    df2_date = df2.copy()
        
    dates_plus = ['Повторы']
    for y in range (0, len(dates)):
        dd = dates[y].strftime('%d.%m.%Y')
        dates_plus.append(f'{y+1}) {dd}')

    df2_date.columns = dates_plus
    Ts.append(df2)
    Ts_date.append(df2_date)

boxform.markdown('👇 После любых изменений нажмите кнопку Запуск вычислений. Иначе в сессии остаются предыдущие вычисления')
MC = boxform.form_submit_button('🚀 Запуск вычислений')

st.write('≽^• ˕ • ྀི≼  ฅ^>⩊<^ ฅ  ≽^•⩊•^≼  ≽(•⩊ •マ≼  ₍^ >⩊< ^₎Ⳋ  ≽^- ˕ -^≼  ≽(•⩊ •マ≼  ฅ^>⩊<^ ฅ ≽^• ˕ • ྀི≼  ฅ^>⩊<^ ฅ  ≽^•⩊•^≼  ≽(•⩊ •マ≼  ₍^ >⩊< ^₎Ⳋ  ≽^- ˕ -^≼  ≽(•⩊ •マ≼  ฅ^>⩊<^ ฅ')
#st.subheader('📝 Описательная статистика')

chs1 = []        # Заголовок
cs1 =[]          # данные
cs2 = []         # бокс-плот
csl1 =[]         # описательная статистика по дням
csl2 = []        # скаттер-плот


for c in range(0, snum):
    ch11 = st.container() 
    c11, c12 = st.columns(2)
    cl11, cl12 = st.columns(2)
    chs1.append(ch11)
    cs1.append(c11)
    cs2.append(c12)
    csl1.append(cl11)
    csl2.append(cl12)



# ------
# ГЕНЕРАТОР ОТЧЁТА .docx (вынесен на верхний уровень; данные принимает  через словарь R, который сохраняется в st.session_state)
# 
def build_docx_report(R):
    """Собирает отчёт в .docx из словаря результатов R. Возвращает io.BytesIO."""
    # Распаковка сохранённых в session_state результатов
    snum = R["snum"]; Ts = R["Ts"]; Ts_date = R["Ts_date"]
    anova_dict = R["anova_dict"]; grubbs_dict = R["grubbs_dict"]
    trueness_dict = R["trueness_dict"]; trueness_est = R["trueness_est"]
    ver_table_r1 = R["ver_table_r1"]; ver_table_r2 = R["ver_table_r2"]
    ver_table_wl1 = R["ver_table_wl1"]; ver_table_wl2 = R["ver_table_wl2"]
    mcvrs = R["mcvrs"]; mcvws = R["mcvws"]; levs = R["levs"]; spmeans = R["spmeans"]
    cvr_vn = R["cvr_vn"]; cva_vn = R["cva_vn"]; vntreb = R["vntreb"]
    spres = R["spres"]; trueness = R["trueness"]; specs_ok = R["specs_ok"]
    executor = R["executor"]; approver = R["approver"]
    #sexpand = R["sexpand"]
    # Поля формы отчёта (могут быть пустыми, если форма не заполнялась)
    sname = R["sname"]; sed = R["sed"]; analyzer = R["analyzer"]
    org = R["org"]; lab = R["lab"]
    CM = R["CM"]; sqc = R["sqc"]; slot = R["slot"]; srok = R["srok"]
    import io
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
    import datetime

    doc = Document()

    # --- Базовый стиль ---
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(10)

    def strip_table_header_numbering(table):
        """Постобработка готовой Word-таблицы: убирает из ячеек ПЕРВОЙ строки
        (шапки) нумерующий префикс вида "1) ", "2) " и т.п.
        Так в стримлите датафрейм остаётся с нумерацией (не ругается на
        одинаковые даты), а в отчёте шапка выглядит чисто: только дата."""
        import re
        for cell in table.rows[0].cells:
            new_text = re.sub(r'^\s*\d+\)\s*', '', cell.text)
            if new_text != cell.text:
                # Переписываем текст ячейки, сохраняя жирность шапки.
                for par in cell.paragraphs:
                    if par.runs:
                        par.runs[0].text = re.sub(r'^\s*\d+\)\s*', '', par.runs[0].text)
                        # Лишние ранчики после первого — обнуляем,
                        # чтобы не задвоить текст.
                        for run in par.runs[1:]:
                            run.text = ''

    def add_df_table(df, title):
        """Добавляет в документ заголовок и таблицу из pandas DataFrame
        (индекс DataFrame становится первым столбцом)."""
        if df is None or df.shape[0] == 0:
            return
        doc.add_heading(title, level=2)   # level = 2
        ncols = df.shape[1] + 1
        table = doc.add_table(rows=1, cols=ncols)
        table.style = 'Light Grid Accent 1'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        # Шапка
        hdr = table.rows[0].cells
        hdr[0].text = str(df.index.name) if df.index.name else ''
        for j, col in enumerate(df.columns):
            hdr[j + 1].text = str(col)
        # Жирная шапка
        for cell in hdr:
            for par in cell.paragraphs:
                for run in par.runs:
                    run.font.bold = True
        # Данные
        for idx, row in df.iterrows():
            cells = table.add_row().cells
            cells[0].text = str(idx)
            # Первый столбец — жирным
            if cells[0].paragraphs[0].runs:
                cells[0].paragraphs[0].runs[0].font.bold = True
            for j, val in enumerate(row):
                cells[j + 1].text = '' if val is None else str(val)
        # Центрируем текст во ВСЕХ ячейках: по горизонтали (выравнивание
        # абзаца) и по вертикали (выравнивание ячейки). table.alignment
        # центрирует только саму таблицу на странице, а не её содержимое.
        for trow in table.rows:
            for cell in trow.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                for par in cell.paragraphs:
                    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()
        return table

    # --- Титул ---
    #======================================================================================================
    # Шапка

    header = doc.add_table(rows=5, cols=3)
    header.style = 'Light Grid Accent 1'

    header.cell(0, 0).text = "Организация"
    header.cell(0, 1).merge(header.cell(0, 2))
    header.cell(0, 1).text = str(org)

    header.cell(1, 0).text = "Лаборатория / Отдел"
    header.cell(1, 1).merge(header.cell(1, 2))
    header.cell(1, 1).text = str(lab)

    header.cell(2, 0).text = "Выполнил"
    header.cell(2, 1).merge(header.cell(2, 2))
    header.cell(2, 1).text = str(executor)

    header.cell(3, 0).text = "Согласовал"
    header.cell(3, 1).merge(header.cell(3, 2))
    header.cell(3, 1).text = str(approver)

    header.cell(4, 0).text = "Дата"
    header.cell(4, 1).merge(header.cell(4, 2))
    header.cell(4, 1).text = datetime.date.today().strftime("%d.%m.%Y")

    doc.add_paragraph()
    

    h = doc.add_heading('ОТЧЁТ О ВЕРИФИКАЦИИ МЕТОДИКИ', level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph('по документу CLSI EP15-A3')
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.runs[0].font.size = Pt(13)
    sub.runs[0].font.bold = True
    doc.add_paragraph()

    if CM == 'Контрольный материал':
        header1 = doc.add_table(rows=9, cols=3)
        header1.style = 'Light Grid Accent 1'

        header1.cell(0, 0).text = "Тест"
        header1.cell(0, 1).merge(header1.cell(0, 2))
        header1.cell(0, 1).text = str(sname)

        header1.cell(1, 0).text = "Единицы измерения"
        header1.cell(1, 1).merge(header1.cell(1, 2))
        header1.cell(1, 1).text = str(sed)

        header1.cell(2, 0).text = "Анализатор"
        header1.cell(2, 1).merge(header1.cell(2, 2))
        header1.cell(2, 1).text = str(analyzer)

        header1.cell(3, 0).text = "Исследуемый материал:"
        header1.cell(3, 1).merge(header1.cell(3, 2))
        header1.cell(3, 1).text = str('Контроль')

        header1.cell(4, 0).text = "Название контрольного материала:"
        header1.cell(4, 1).merge(header1.cell(4, 2))
        header1.cell(4, 1).text = str(sqc)

        header1.cell(5, 0).text = "Лот контроля:"
        header1.cell(5, 1).merge(header1.cell(5, 2))
        header1.cell(5, 1).text = str(slot)

        header1.cell(6, 0).text = "Срок годности:"
        header1.cell(6, 1).merge(header1.cell(6, 2))
        header1.cell(6, 1).text = str(srok)
 
        header1.cell(7, 0).text = "Количество исследованных уровней"
        header1.cell(7, 1).merge(header1.cell(7, 2))
        header1.cell(7, 1).text = str(snum)

        header1.cell(8, 0).text = "Дизайн исследования"
        header1.cell(8, 1).merge(header1.cell(8, 2))
        header1.cell(8, 1).text = str("5 дней по 5 повторов")

    else:
        header1 = doc.add_table(rows=6, cols=3)
        header1.style = 'Light Grid Accent 1'

        header1.cell(0, 0).text = "Тест"
        header1.cell(0, 1).merge(header1.cell(0, 2))
        header1.cell(0, 1).text = str(sname)

        header1.cell(1, 0).text = "Единицы измерения"
        header1.cell(1, 1).merge(header1.cell(1, 2))
        header1.cell(1, 1).text = str(sed)

        header1.cell(2, 0).text = "Анализатор"
        header1.cell(2, 1).merge(header1.cell(2, 2))
        header1.cell(2, 1).text = str(analyzer)

        header1.cell(3, 0).text = "Исследуемый материал:"
        header1.cell(3, 1).merge(header1.cell(3, 2))
        header1.cell(3, 1).text = str('Проба пациента')

        header1.cell(4, 0).text = "Количество исследованных уровней"
        header1.cell(4, 1).merge(header1.cell(4, 2))
        header1.cell(4, 1).text = str(snum)

        header1.cell(5, 0).text = "Дизайн исследования"
        header1.cell(5, 1).merge(header1.cell(5, 2))
        header1.cell(5, 1).text = str("5 дней по 5 повторов")


   
    doc.add_paragraph()  

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



    #  Данные эксперимента и описательная статистика 
    doc.add_heading('1. Данные эксперимента', level=1)
    for i in range(0, snum):
        doc.add_heading(f'Уровень {i + 1}', level=2)
        # В отчёт идёт Ts_date как есть — с нумерованными датами ("1) дата"),
        # поэтому в стримлите датафрейм не ругается на одинаковые даты.
        # Колонка "Повторы" уходит в индекс и становится заголовком первого
        # столбца; номера повторов приводим к целым.
        df_data = Ts_date[i].copy()
        if 'Повторы' in df_data.columns:
            df_data = df_data.set_index('Повторы')
            try:
                df_data.index = df_data.index.astype(float).astype(int)
            except (ValueError, TypeError):
                pass
        data_table = add_df_table(df_data,
                                  f'Результаты измерений, уровень {i + 1}')
        # Постобработка готовой Word-таблицы: срезаем префикс "N) " из шапки,
        # чтобы в отчёте остались чистые даты (правка на уровне doc-таблицы,
        # а не датафрейма — датафрейм в стримлите сохраняет нумерацию).
        if data_table is not None:
            strip_table_header_numbering(data_table)
        Ms_, SDs_, CVs_, GM_, SDtot_, mins_, maxs_ = describe(Ts[i])
        ta_ = describe_table(Ms_, SDs_, CVs_, mins_, maxs_)
        add_df_table(ta_, f'Описательная статистика по дням, уровень {i + 1}')

    # ГРАФИКИ
    doc.add_heading('2. Графический анализ', level=1)
    for i in range(0, snum):
        doc.add_heading(f'Уровень {i + 1}', level=2)
        for fig, cap in [(plot_box(Ts[i]), 'График box-plot по дням'),
                         (plot_levey(Ts[i]), 'Результаты последовательных измерений по дням')]:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            p = doc.add_paragraph(cap)
            p.runs[0].font.bold = True
            doc.add_picture(buf, width=Cm(15))
            doc.add_paragraph()

    # Граббс и ANOVA
    doc.add_heading('3. Статистический анализ', level=1)
    gt_ = pd.DataFrame.from_dict(grubbs_dict, orient='index')
    if gt_.shape[0] > 1:
        gh = gt_.iloc[0]; gt_ = gt_[1:]; gt_.rename(columns=gh, inplace=True)
        add_df_table(gt_, 'Общая статистика и границы выбросов Граббса')
    at_ = pd.DataFrame.from_dict(anova_dict, orient='index')
    if at_.shape[0] > 1:
        ah = at_.iloc[0]; at_ = at_[1:]; at_.rename(columns=ah, inplace=True)
        add_df_table(at_, 'Результаты ANOVA и оценка непрецизионности')

    #  Верификация прецизионности 
    if spres and specs_ok:
        doc.add_heading('4. Верификация прецизионности', level=1)
        DFrs_, Frs_, UVLrs_, ps_, DFwls_, levels_, Fwls_, UVLwls_ = \
            specification_prepare(mcvrs, mcvws, levs, spmeans)
        spec_ = specification_table(mcvrs, mcvws, levels_, spmeans,
                                    DFrs_, Frs_, UVLrs_, ps_, DFwls_, Fwls_, UVLwls_)
        add_df_table(spec_, 'Расчёт верхней верификационной границы (UVL)')

        vtr_dict = ver_table_r1 if (vntreb and cvr_vn != 0) else ver_table_r2
        vtr_ = pd.DataFrame.from_dict(vtr_dict, orient='index')
        if vtr_.shape[0] > 1:
            vh = vtr_.iloc[0]; vtr_ = vtr_[1:]; vtr_.rename(columns=vh, inplace=True)
            add_df_table(vtr_, 'Результаты верификации повторяемости')

        vtwl_dict = ver_table_wl1 if (vntreb and cva_vn != 0) else ver_table_wl2
        vtwl_ = pd.DataFrame.from_dict(vtwl_dict, orient='index')
        if vtwl_.shape[0] > 1:
            wh = vtwl_.iloc[0]; vtwl_ = vtwl_[1:]; vtwl_.rename(columns=wh, inplace=True)
            add_df_table(vtwl_, 'Результаты верификации внутрилабораторной прецизионности')

    # Верификация правильности
    if trueness and len(trueness_dict['']) > 0:
        doc.add_heading('5. Верификация правильности (Trueness)', level=1)
        doc.add_paragraph(f'Источник целевого значения, сценарий по EP15-A3: {tradio}')
        tes = pd.DataFrame.from_dict(trueness_est, orient = 'index')
        tesn = tes.iloc[0]
        tes = tes[1:]
        tes.rename(columns=tesn, inplace =True)
        add_df_table(tes, 'Расчёт верификационного интервала')

        tt_ = pd.DataFrame.from_dict(trueness_dict, orient='index')
        th = tt_.iloc[0]; tt_ = tt_[1:]; tt_.rename(columns=th, inplace=True)
        add_df_table(tt_, 'Результаты оценки правильности')

        #doc.add_paragraph(
        #    'Верификация правильности пройдена, если среднее значение '
        #    'попадает в верификационный интервал ')
        

    # --- Подписи ---
    #if sexpand and (executor or approver):
    doc.add_paragraph()
    doc.add_paragraph()
    sigtab = doc.add_table(rows=1, cols=2)
    sc = sigtab.rows[0].cells
    sc[0].text = f'Выполнил: {executor}'
    sc[1].text = f'Согласовал: {approver}'

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out


# !
# ВЫЧИСЛЕНИЯ
# При нажатии "Запуск вычислений" считаем всё и складываем результаты в
# st.session_state. Отрисовки здесь нет — она отдельно, поэтому таблицы и
# графики не пропадают при последующих перезапусках (например, при нажатии
# кнопки скачивания отчёта).


if MC:
    anova_results = []
    # Спецификации считаются заполненными только если списки НЕ пустые
    # (Precision включён и введены значения) И ни одно значение не равно 0.
    # Без проверки на пустоту any() по [] возвращает False, из-за чего
    # specs_ok ошибочно становился True при выключенном Precision и далее
    # specification_prepare() возвращала пустые UVLrs/UVLwls → IndexError.
    specs_ok = bool(mcvrs) and bool(mcvws) and not any(
        x == 0 for x in (mcvrs + mcvws))
    # Словари наполняются заново при каждом запуске — на случай повторного
    # расчёта очищаем их от данных предыдущего прогона.
    for _d in (anova_dict, grubbs_dict, trueness_dict,
               ver_table_r1, ver_table_r2, ver_table_wl1, ver_table_wl2):
        for _k in _d:
            _d[_k].clear()

    calc_ok = True
    for i in range(0, snum):
        if spres and not specs_ok:
            calc_ok = False
            anova_results.append(None)
        else:
            if specs_ok:
                DFrs, Frs, UVLrs, ps, DFwls, levels, Fwls, UVLwls = \
                    specification_prepare(mcvrs, mcvws, levs, spmeans)
            else:
                UVLrs = [0.0] * snum
                UVLwls = [0.0] * snum
            # Страховка: гарантируем, что UVL-списки имеют длину >= snum,
            # даже если specification_prepare вернула короткий/пустой список
            # (например, при рассинхроне snum и заполненных уровней).
            if len(UVLrs) < snum:
                UVLrs = list(UVLrs) + [0.0] * (snum - len(UVLrs))
            if len(UVLwls) < snum:
                UVLwls = list(UVLwls) + [0.0] * (snum - len(UVLwls))
            res = anova(Ts[i], i, anova_dict, grubbs_dict,
                        mcvrs if mcvrs else [0.0] * snum,
                        mcvws if mcvws else [0.0] * snum,
                        UVLrs, UVLwls, cvr_vn, cva_vn)
            anova_results.append(res)
            # target_vals может оказаться короче snum, если уровни Trueness
            # не были заполнены или сценарий сменили на полпути — проверяем длину.
            if (trueness and res is not None
                    and i < len(target_vals) and target_vals[i] > 0):
                trueness_calc(res, target_vals[i], bias_lim, i, trueness_dict)

    if spres and not specs_ok:
        # Спецификации не заполнены — ничего не сохраняем, вылезет предупреждение.
        st.session_state.pop('results', None)
        st.warning('⚠️❗ Заполните спецификации производителя!')
    else:
        # Сохраняем ВСЁ необходимое для отрисовки и для отчёта.
        st.session_state['results'] = {
            'snum': snum,
            'Ts': Ts,
            'Ts_date': Ts_date,
            'anova_dict': anova_dict,
            'grubbs_dict': grubbs_dict,
            'trueness_est': trueness_est,
            'trueness_dict': trueness_dict,
            'ver_table_r1': ver_table_r1,
            'ver_table_r2': ver_table_r2,
            'ver_table_wl1': ver_table_wl1,
            'ver_table_wl2': ver_table_wl2,
            'mcvrs': mcvrs, 'mcvws': mcvws, 'levs': levs, 'spmeans': spmeans,
            'cvr_vn': cvr_vn, 'cva_vn': cva_vn, 'vntreb': vntreb,
            'spres': spres, 'trueness': trueness, 'specs_ok': specs_ok,
            #'sexpand': sexpand,
            'executor': executor if 'executor' in dir() else '',
            'approver': approver if 'approver' in dir() else '',
            # Поля формы отчёта — существуют только при включённом sexpand,
            # поэтому подставляем пустые значения по умолчанию.
            'sname': sname if 'sname' in dir() else '',
            'sed': sed if 'sed' in dir() else '',
            'analyzer': analyzer if 'analyzer' in dir() else '',
            'org': org if 'org' in dir() else '',
            'lab': lab if 'lab' in dir() else '',
            'CM': CM if 'CM' in dir() else 'Контрольный материал',
            'sqc': sqc if 'sqc' in dir() else '',
            'slot': slot if 'slot' in dir() else '',
            'srok': srok if 'srok' in dir() else '',
        }


#--------------
# ОТРИСОВКА
# Выполняется при КАЖДОМ перезапуске скрипта, если в сессии есть результаты.

if 'results' in st.session_state:
    R = st.session_state['results']
    snum = R['snum']
    Ts = R['Ts']
    specs_ok = R['specs_ok']

    #  Описательная статистика, графики 
   
    for i in range(0, snum):
        chs1[i].subheader(f'Уровень {i + 1}')
        cs1[i].markdown('**Данные эксперимента**')
        cs1[i].dataframe(R['Ts_date'][i], hide_index=True)
        Ms, SDs, CVs, GM, SDtot, mins, maxs = describe(Ts[i])
        ta = describe_table(Ms, SDs, CVs, mins, maxs)
        csl1[i].markdown(f'**Описательная статистика по дням для уровня {i + 1}**')
        csl1[i].dataframe(ta)
        # Графики перерисовываются из сохранённых данных (matplotlib-фигуры
        # в session_state не кладём — это ненадёжно).
        cs2[i].markdown(f'**График box-plot по дням для уровня {i + 1}**')
        cs2[i].pyplot(plot_box(Ts[i]))
        csl2[i].markdown(f'**Результаты последовательных измерений по дням для уровня {i + 1}**')
        csl2[i].pyplot(plot_levey(Ts[i]))
    
    st.subheader('📈 Верификация прецизионности')
    # --- Граббс ---
    st.markdown('**Общая статистика и границы выбросов Граббса**')
    gt = pd.DataFrame.from_dict(R['grubbs_dict'], orient='index')
    if gt.shape[0] > 1:
        gh = gt.iloc[0]; gt = gt[1:]; gt.rename(columns=gh, inplace=True)
        st.dataframe(gt)

    # --- ANOVA ---
    st.markdown('**Результаты ANOVA и оценка непрецизионности**')
    at = pd.DataFrame.from_dict(R['anova_dict'], orient='index')
    if at.shape[0] > 1:
        ah = at.iloc[0]; at = at[1:]; at.rename(columns=ah, inplace=True)
        st.dataframe(at)

    # --- UVL ---
    if specs_ok:
        st.markdown('**Расчёт верхней верификационной границы (UVL) для спецификаций '
                    'производителя по прецизионности**')
        DFrs, Frs, UVLrs, ps, DFwls, levels, Fwls, UVLwls = \
            specification_prepare(R['mcvrs'], R['mcvws'], R['levs'], R['spmeans'])
        spec_table = specification_table(R['mcvrs'], R['mcvws'], levels, R['spmeans'],
                                         DFrs, Frs, UVLrs, ps, DFwls, Fwls, UVLwls)
        st.dataframe(spec_table)

    # --- Верификация повторяемости ---
    if R['vntreb'] is False or R['cvr_vn'] == 0:
        st.markdown('**Результаты верификации повторяемости**')
        vtr = pd.DataFrame.from_dict(R['ver_table_r2'], orient='index')
    else:
        st.markdown('**Результаты верификации повторяемости и оценка соответствия '
                    'внутренним требованиям**')
        vtr = pd.DataFrame.from_dict(R['ver_table_r1'], orient='index')
    if vtr.shape[0] > 1:
        vh = vtr.iloc[0]; vtr = vtr[1:]; vtr.rename(columns=vh, inplace=True)
        st.dataframe(vtr)

    # --- Верификация внутрилабораторной прецизионности ---
    if R['vntreb'] is False or R['cva_vn'] == 0:
        st.markdown('**Результаты верификации внутрилабораторной прецизионности**')
        vtwl = pd.DataFrame.from_dict(R['ver_table_wl2'], orient='index')
    else:
        st.markdown('**Результаты верификации внутрилабораторной прецизионности и '
                    'оценка соответствия внутренним требованиям**')
        vtwl = pd.DataFrame.from_dict(R['ver_table_wl1'], orient='index')
    if vtwl.shape[0] > 1:
        wh = vtwl.iloc[0]; vtwl = vtwl[1:]; vtwl.rename(columns=wh, inplace=True)
        st.dataframe(vtwl)

    # Правильность
    if R['trueness_est'] and len(R['trueness_est']['']) > 0:
        st.subheader('🎯 Верификация правильности')
        st.markdown(f'***Источник целевого значения, сценарий по EP15-A3: {tradio}***')
        st.markdown('**Расчёт верификационного интервала для оценки правильности**')
        #tes = pd.DataFrame.from_dict(R['trueness_est'], orient='index')
        #tesh = tes.iloc[0]; tes = tes[1:]; tes.rename(columns=tesh, inplace=True)
        tesh = pd.DataFrame.from_dict(R['trueness_est'], orient = 'index')
        tesh_name = tesh.iloc[0]
        tesh = tesh[1:]
        tesh.rename(columns=tesh_name, inplace =True)
        st.dataframe(tesh)
    if R['trueness'] and len(R['trueness_dict']['']) > 0:
        st.markdown('**Результаты оценки правильности (Trueness)**')
        tt = pd.DataFrame.from_dict(R['trueness_dict'], orient='index')
        th = tt.iloc[0]; tt = tt[1:]; tt.rename(columns=th, inplace=True)
        st.dataframe(tt)
        #st.caption('Верификация пройдена, среднее попадает в ВИ')
    elif R['trueness']:
        st.warning('⚠️ Заполните целевые значения для оценки правильности!')

    # --- Выгрузка отчёта ---
    # download_button перезапускает скрипт, но т.к. отрисовка в Фазе 2
    # завязана на session_state, а не на MC, всё остаётся на экране. Из-за этой хуйни, конечно, все виснет, но пока так
    st.divider()
    st.markdown('### 📥 Выгрузка отчёта')
    try:
        report_buf = build_docx_report(R)
        fname = f'Отчёт_EP15_{datetime.date.today().strftime("%Y%m%d")}.docx'
        st.download_button(
            label='📄 Скачать отчёт в формате .docx',
            data=report_buf,
            file_name=fname,
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        st.error(f'Не удалось сформировать отчёт: {e}')
