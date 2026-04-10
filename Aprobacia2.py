import streamlit as st
import pandas as pd
import numpy as np
from sklearn.utils import resample
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint
from scipy.stats import chi2

st.set_page_config(layout="wide")

st.title("Диагностическое согласие методов.")

uploaded_file = st.sidebar.file_uploader("Загрузите Excel", type=["xlsx", "xls"])

st.sidebar.write("===============⎛⎝ ≽ > ⩊ < ≼ ⎠⎞================")

minus = "\u2212"
# ФУНКЦИИ
# Предобработка входных данных
def prepare_pair(df, aa, bb, p1, p2):

    dfs = df[[aa,bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs["m1_bin"] = np.where(dfs[aa] >= p1, 1, 0)
    dfs["m2_bin"] = np.where(dfs[bb] >= p2, 1, 0)

    a = np.sum((dfs["m1_bin"]==0) & (dfs["m2_bin"]==0))
    b = np.sum((dfs["m1_bin"]==0) & (dfs["m2_bin"]==1))
    c = np.sum((dfs["m1_bin"]==1) & (dfs["m2_bin"]==0))
    d = np.sum((dfs["m1_bin"]==1) & (dfs["m2_bin"]==1))

    return a,b,c,d,dfs

# KAPPA
def compute_kappa(a,b,c,d):
    n = a+b+c+d
    Po = (a+d)/n
    Pe = ((a+b)*(a+c)+(c+d)*(b+d))/n**2
    if (1-Pe)==0:
        return np.nan
    return (Po-Pe)/(1-Pe)


# Bootstrap CI for kappa
def bootstrap_kappa(dfs, B=2000):
    boot = []
    for _ in range(B):
        sample = resample(dfs, replace=True)

        a = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==0))
        b = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==1))
        c = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==0))
        d = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==1))
        
        k = compute_kappa(a,b,c,d)
        if not np.isnan(k):
            boot.append(k)
    return np.percentile(boot, [2.5,97.5])

# Рассчёт PPA и NPA
def compute_ppa_npa(a,b,c,d):
    PPA = round(100*d/(d+b),2) if (d+b)>0 else np.nan
    NPA = round(100*a/(a+c),2) if (a+c)>0 else np.nan
    return PPA, NPA

def ci_binomial(x, n, alpha=0.05, method="wilson"):
    return proportion_confint(x, n, alpha=alpha, method=method)

# Prevalence adjusted bias adjusted kappa (PABAK)
def pabak(a,b,c,d):
    n = a+b+c+d
    Po = (a+d)/n
    PABAK = 2*Po - 1
    return PABAK

def pabak_ci_funk(a,b,c,d):
    Po = (a+d)/(a+b+c+d)
    Po_ci = ci_binomial(a+d, a+b+c+d)

    pabak_ci_low = 2*Po_ci[0]-1 
    pabak_ci_high = 2*Po_ci[1]-1
    return pabak_ci_low, pabak_ci_high

# тест МакНемара
def mcnemar_result(a,b,c,d):
    mc_table = [[a,b],[c,d]]
    mc_res = mcnemar(mc_table, exact=True)
    if mc_res.pvalue < 0.05:
        mc_answer = "Методы систематически отличаются"
    else:
        mc_answer = "Нет систематического различия"
    return mc_answer, mc_res.pvalue

# Gwet's AC1
def gwet_ac1(a,b,c,d):
    n = a+b+c+d
    Po = (a+d)/n
    p1 = (a+b)/n
    p2 = (a+c)/n
    p = (p1 + p2)/2
    Pe = 2*p*(1-p)
    if (1-Pe)==0:
        return np.nan
    return (Po - Pe)/(1 - Pe)

# Bootstrap CI for Gwet's AC1
def bootstrap_ac1(dfs, B=2000):
    boot = []
    for _ in range(B):
        sample = resample(dfs, replace=True)
        a = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==0))
        b = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==1))
        c = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==0))
        d = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==1))
        ac1 = gwet_ac1(a,b,c,d)
        if not np.isnan(ac1):
            boot.append(ac1)
    return np.percentile(boot,[2.5,97.5])


def bootstrap_npa_ppa(dfs, B=2000):
    ppa_boot = []
    npa_boot = []
    for _ in range(B):
        sample = resample(dfs, replace=True)
        a = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==0))
        b = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==1))
        c = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==0))
        d = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==1))
        PPA, NPA = compute_ppa_npa(a,b,c,d)
        ppa_boot.append(PPA)
        npa_boot.append(NPA)
    return np.percentile(ppa_boot,[2.5,97.5]), np.percentile(npa_boot,[2.5,97.5])

# PI + BI
def prevalence_bias_index(a,b,c,d):
    n = a+b+c+d
    PI = abs(a-d)/n
    BI = abs(b-c)/n
    return PI, BI

def plot_scatter_with_cutoff(dfs, aa, bb, p1, p2):
    x = dfs[aa]
    y = dfs[bb]
    x = x.replace(0,0.0001)
    m1_bin = x >= p1
    m2_bin = y >= p2
    concordant = m1_bin == m2_bin
    fig, ax = plt.subplots()
    ax.scatter(x[concordant], y[concordant], alpha=0.6)
    ax.scatter(x[~concordant], y[~concordant], alpha=0.6)
    ax.axvline(p1, ls = '--', color= 'black', label = 'cut-off A', alpha = 0.6)
    ax.axhline(p2, color= 'black', label = 'cut-off B', alpha = 0.8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(f"Метод А ({aa})")
    ax.set_ylabel(f"Метод B ({bb})")
    ax.set_title("Диаграмма рассеяния (логарифмическая шкала)")
    ax.legend()
    return fig

# МАТРИЦА 
def plot_confusion_matrix(a, b, c, d):
    matrix = np.array([[a, b],
                       [c, d]])
    fig, ax = plt.subplots()
    
    cmap = plt.cm.PuBuGn
    # создаём модифицированную cmap
    colors = cmap(np.linspace(0, 1, 256))
    gamma = 0.4  
    colors[:, :3] = colors[:, :3] ** gamma
    new_cmap = mcolors.ListedColormap(colors)

    im = ax.imshow(matrix, cmap=new_cmap)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, matrix[i, j],
                    ha="center", va="center")
    ax.set_xticks([0,1])
    ax.set_yticks([0,1])
    ax.set_yticklabels([f"Метод A {minus}", "Метод A +"])
    ax.set_xticklabels([f"Метод B {minus}", "Метод B +"])
    ax.set_title("Таблица сопряженности 2x2")
    fig.colorbar(im)
    return fig

# столбики
def plot_agreement_bar(a,b,c,d):
    labels = [f"A{minus}B{minus}",f"A{minus}B+",f"A+B{minus}","A+B+"]
    values = [a,b,c,d] 
    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title("Структура сопряженности")
    ax.set_ylabel("Количество")
    return fig

# NPA/PPA
def ppa_npa_curve(dfs):
    ppa_list = []
    npa_list = []
    pr_list = []
    spisok = sorted(list(dfs[aa]))
    for i in spisok:
        a,b,c,d,dfs = prepare_pair(df,aa,bb,i,p2)
        npa = 100* a/(a+c) if (a+c)>0 else np.nan  #TN
        ppa = 100* d/(d+b) if (d+b)>0 else np.nan  #TP
        precision = 100* d/(d+c) if (d+c)>0 else np.nan
        ppa_list.append(ppa)
        npa_list.append(npa)
        pr_list.append(precision)

    return np.array(ppa_list), np.array(npa_list), np.array(pr_list)

# График NPA/PPA
def plot_ppa_npa(ppa_list, npa_list):
    fig, ax = plt.subplots()
    ax.plot(npa_list, ppa_list)
    ax.set_xlabel("NPA (%)")
    ax.set_ylabel("PPA (%)")
    ax.invert_xaxis()
    ax.set_title("Кривая согласия (PPA vs NPA)")
    ax.plot([0,100],[100,0],'--')
    return fig

def plot_pr_curve(ppa_list, pr_list):
    fig, ax = plt.subplots()
    ax.plot(ppa_list, pr_list)
    ax.set_xlabel("PPA (%)")
    ax.set_ylabel("Precision (%)")
    ax.set_title("Precision-Recall относительно референсного метода")
    return fig




#======================================================================
# Чтобы замутить всё с неопределенностью вместе:
def prepare_pair2(df, aa, bb):
    dfs = df[[aa,bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    return dfs[aa], dfs[bb]

# Функция определения границ серой зоны
def gray_zone_from_cv(cutoff, cv, z=1.96):
    sigma = cv * cutoff/100
    delta = z * sigma
    return cutoff - delta, cutoff + delta

# функция категоризации данных
def categorize(x, c_low, c_high):
    return np.where(x < c_low, 0,
           np.where(x > c_high, 2, 1))

# строим таблицу 3х3 (с учётом серой зоны)
def build_3x3_table(x1, x2, c1_low, c1_high, c2_low, c2_high):
    y1 = categorize(x1, c1_low, c1_high)
    y2 = categorize(x2, c2_low, c2_high)

        
    a = np.sum((y1==0)&(y2==0))
    b = np.sum((y1==0)&(y2==1))
    c = np.sum((y1==0)&(y2==2))
    d = np.sum((y1==1)&(y2==0))
    e = np.sum((y1==1)&(y2==1))
    f = np.sum((y1==1)&(y2==2))
    g = np.sum((y1==2)&(y2==0))
    h = np.sum((y1==2)&(y2==1))
    i = np.sum((y1==2)&(y2==2))
    
    table = np.array([[a, b, c], 
                  [d, e, f], 
                  [g, h, i]])

    return table , a,b,c,d,e,f,g,h,i


# Подсчёт долей каждой категории согласия
#def agreement_components(table):
#    N = table.sum()
#    a,e,i = table[0,0], table[1,1], table[2,2]
#    strict = (a + e + i) / N
#    partial = (table[0,1] + table[1,0] + table[1,2] + table[2,1]) / N
#    extreme = (table[0,2] + table[2,0]) / N
#    return strict, partial, extreme


# ВЕСА
def make_weights(k=3, scheme= 'Линейные весы'):
    W = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if scheme == 'Линейные весы':
                W[i, j] = 1 - abs(i - j) / (k - 1)
            elif scheme == 'Квадратичные весы':
                W[i, j] = 1- ((i - j) / (k - 1))**2
            else:
                raise ValueError("Unknown scheme")
            #W = np.flip(W, axis=1)
    return W


# ВЗВЕШЕННАЯ каппа
def weighted_kappa(table, W):
    table = np.array(table)
    N = table.sum()
    P = table / N
    Po = np.sum(W * P)
    row_marg = P.sum(axis=1)
    col_marg = P.sum(axis=0)
    Pe = np.sum(W * np.outer(row_marg, col_marg))
    return (Po - Pe) / (1 - Pe)


# AC2/ (взвешенная)
def gwet_ac2(table, W):
    table = np.array(table)
    N = table.sum()
    P = table / N
    #наблюдаемое взвешенное согласие
    Po = np.sum(W * P)    
    # маргинальные суммы                  
    row_sum = np.sum(table, axis=1)
    col_sum = np.sum(table, axis=0)
    pi = (row_sum + col_sum) / (2*N)          
    #Pe = np.sum(W * np.outer(pi, pi))
    Pe = np.sum(pi*(1-pi))
    if np.isclose(Pe,1):
        if np.isclose(Po,1):
            return 1.0
        else:
            return np.nan
    return (Po - Pe) / (1 - Pe)
  

# BOOTSTRAP CI
def bootstrap_ci(df, func, W,
                 c1_low, c1_high,
                 c2_low, c2_high,
                 n_boot=2000):
    dfs = df[[aa,bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    stats = []
    for _ in range(n_boot):
        dfboot = resample(dfs, replace=True)
        t , a,b,c,d,e,f,g,h,i = build_3x3_table(
            dfboot[aa], dfboot[bb],
            c1_low, c1_high,
            c2_low, c2_high)
        stats.append(func(t, W))
    return np.round(np.percentile(stats, [2.5, 97.5]), 4)


# БоУКЕРтест
def bowker_test(table, b,d,c,g,f,h):
    table = np.array(table)
    k = table.shape[0]
    B = 0
    if b+d > 0:
        B += (d-b)**2/(d+b)
    if c+g > 0:
        B += (g-c)**2/(g+c)
    if f+h > 0:
        B += (h-f)**2/(h+f)
    df = k * (k - 1) / 2
    p = 1 - chi2.cdf(B, df)
    if p < 0.05:
        interpretation = "Методы систематически отличаются"
    else:
         interpretation = "Нет систематического отличия"

    if p < 0.0001:
        p = "<0.0001"
    return B, p , interpretation


# ТАБЛИЦА 3х3
def plot_3x3_agreement(table):
    fig, ax = plt.subplots(figsize=(8, 8), dpi=200)
    cmap = plt.cm.PuBuGn
    # создаём модифицированную cmap
    colors = cmap(np.linspace(0, 1, 256))
    gamma = 0.4  
    colors[:, :3] = colors[:, :3] ** gamma
    new_cmap = mcolors.ListedColormap(colors)

    im = ax.imshow(table, cmap=new_cmap)
    labels = [f"{minus}", "СЗ", "+"]
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Метод B ({bb})")
    ax.set_ylabel(f"Метод A ({aa})")
    # подписи чисел
    for i in range(3):
        for j in range(3):
            ax.text(j, i, int(table[i, j]),
                    ha="center", va="center")
    ax.set_title("Таблица сопряженности 3х3 (тепловая карта)")
    fig.colorbar(im)
    return fig

#серозон, логарифмическая шкала
def plot_scatter_gray_zone(
    x1, x2,
    c1_low, c1_high,
    c2_low, c2_high,
    log_scale=True):
    
    b1 = []
    b2 = []
    b3 = []
    b4 = []
    b5 = []
    b6 = []
    x1 = x1.tolist()
    x2 = x2.tolist()
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
    for n in range(0,len(x1)):
        if x1[n]<c1_low:
            if x2[n]<c2_low:
                b1.append(x1[n])
                b2.append(x2[n])
            if (x2[n]>c2_high):
                b3.append(x1[n])
                b4.append(x2[n])
            if x2[n]>c2_low and x2[n]<c2_high:
                b5.append(x1[n])
                b6.append(x2[n])
        if x1[n]>c1_high:
            if x2[n]>c2_high:
                b1.append(x1[n])
                b2.append(x2[n])
            if (x2[n]<c2_low):
                b3.append(x1[n])
                b4.append(x2[n])
            if x2[n]>c2_low and x2[n]<c2_high:
                b5.append(x1[n])
                b6.append(x2[n])
        if x1[n]>=c1_low and x1[n]<=c1_high:
            if x2[n]>=c2_low and x2[n]<=c2_high:
                b1.append(x1[n])
                b2.append(x2[n])
            if x2[n]>=c2_high or x2[n]<=c2_low:
                b5.append(x1[n])
                b6.append(x2[n])
    # точки
    ax.scatter(b1,b2, alpha=0.6, color = 'blue')
    ax.scatter(b3,b4, alpha=0.8, color = 'orange')
    ax.scatter(b5,b6, alpha=0.8, color = 'gray')
    # линии метода 1 (вертикальные)
    ax.axvline(c1_low, linestyle='--', color = 'black', alpha = 0.6, label = 'Серая зона A')
    ax.axvline(c1_high, linestyle='--', color = 'black', alpha = 0.6)
    # линии метода 2 (горизонтальные)
    ax.axhline(c2_low, linestyle='--', color = 'purple', alpha = 0.6, label = 'Серая зона B')
    ax.axhline(c2_high, linestyle='--', color = 'purple', alpha = 0.6)
    # лог шкала
    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
    ax.set_xlabel(f"Метод A ({aa})")
    ax.set_ylabel(f"Метод B ({bb})")
    ax.legend()
    ax.set_title("Диаграмма рассеяния (логарифмическая шкала)")
    return fig



# Ещё одна таблица сопряженности
def plot_agreement_pattern(table):
    fig, ax = plt.subplots(figsize=(8, 8), dpi=200)
    category_map = np.zeros_like(table)
    # strict = 2
    for i in range(3):
        category_map[i, i] = -5
    # agreement = -1
    category_map[0,2] = 1
    category_map[2,0] = 1
    # partial = 1
    for i in range(3):
        for j in range(3):
            if i != j and category_map[i,j] == 0:
                category_map[i,j] = 20
    category_map[1,1] = -5
    im = ax.imshow(category_map, cmap = 'tab20c')
    labels = [f"{minus}", "СЗ", "+"]
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Метод B ({bb})")
    ax.set_ylabel(f"Метод A ({aa})")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, int(table[i, j]), ha="center", va="center")
    ax.set_title("Таблица сопряженности 3х3")
    return fig




#================================
# UI:
if uploaded_file:
    st.info("""В загруженном файле результаты должны располагаться в столбцах и иметь заголовки.  
            Строки с отсутствующими данными автоматически удаляются и не принимают участия в расчётах.  
             Для количественных тестов следующие знаки автоматически удаляются: &gt;l < >""")
    st.info ("""***Количественные в бинарные***: деление производится автоматически по введенным уровням cut-off  
             ***Количественные в бинарные + неопределенность***: деление производится автоматически с учётом уровней cut-off и CV методов""") 
    df = pd.read_excel(uploaded_file) 
    st.dataframe(df.head())
    numeric_cols=df.columns.to_list()

    # sidebar
    radio_type = st.sidebar.radio("Выбери тип данных для сравнения",['Количественные в бинарные',
                                                          'Количественные в бинарные + неопределенность'])

    if radio_type == 'Количественные в бинарные':
        st.subheader("Диагностическое согласие после бинаризации количественных методов.")
        st.info("Данный раздел подойдет для сравнения полуколичественных методов с порогом отсечки на положительных и отрицательных." \
        "Например, сравнение ИФА, ИХЛА - методов для диагностики инфекционных заболеваний." \
        " Анализ согласия количественных методов относительно уровня cut-off.")
        st.write("=================================================================================================================")
    
        st.sidebar.header("Пара методов") 
        # пара
        col1, col2 = st.sidebar.columns(2) 
    
        aa = col1.selectbox(f"Метод A (Новый)", numeric_cols) 
        bb = col2.selectbox(f"Метод B (Референтный)", numeric_cols) 
        p1 = col1.number_input("Порог метода А", value=1.0)
        p2 = col2.number_input("Порог метода В", value=1.0)
       
        cut_off_input = st.sidebar.number_input("Введите максимальное значение cut-off Метода А для построения графика зависимости " \
        " коэффициентов согласованности от cut-off в диапазоне от 0 до введенного значения",value=3)

        push = st.sidebar.button("Запуск вычислений")
        if push:

            a,b,c,d,dfs = prepare_pair(df,aa,bb,p1,p2)
            kappa = compute_kappa(a,b,c,d)
            ci_low, ci_high = bootstrap_kappa(dfs)
            PPA, NPA = compute_ppa_npa(a,b,c,d)
            #ppa_ci =  ci_binomial(a, a+c)
            #npa_ci =  ci_binomial(d, b+d)
            ppa_ci, npa_ci = bootstrap_npa_ppa(dfs, B=2000)

            PABAK = pabak(a,b,c,d)
            pabak_ci_low, pabak_ci_high = pabak_ci_funk(a,b,c,d)
            mc_answer, mcnemar_pval = mcnemar_result(a,b,c,d)
            AC1 = gwet_ac1(a,b,c,d)
            ci_ac1_low, ci_ac1_high = bootstrap_ac1(dfs)
            PI, BI = prevalence_bias_index(a,b,c,d)
            ppa_list, npa_list, pr_list = ppa_npa_curve(dfs)

            results22 = {"": [f"Метод A {minus}","Метод A +"],
                        f"Метод B {minus}": [a,c],
                        "Метод B +": [b,d]}

            pibi_table = {"Prevalence Index": round(PI,4),
                          "Bias Index": round(BI,4)} 

            kappa_table = {"": ["kappa", 
                                "PPA, %", 
                                "NPA, %",
                                "PABAK",
                                "AC1 Гвета"],
                           "Значение": [round(kappa,4), 
                                    round(PPA,2), 
                                    round(NPA,2),
                                    round(PABAK,4), 
                                    round(AC1,4)],
                            "95% CI":[ f'от {round(ci_low,4)} до {round(ci_high,4)}',
                                    f'от {round(ppa_ci[0],2)} до {round(ppa_ci[1],2)}',
                                    f'от {round(npa_ci[0],2)} до {round(npa_ci[1],2)}',
                                    f'от {round(pabak_ci_low,4)} до {round(pabak_ci_high,4)}',
                                    f'от  {round(ci_ac1_low,4)} до {round(ci_ac1_high,4)}']}
        
            mcnemar_table = {"p-value": [round(mcnemar_pval,4)],
                            "Интерпретация" : [mc_answer] }
        
            c1,c2,c3 = st.columns(3)
            c11,c22 = st.columns(2)
            c111,c222 = st.columns(2)
        
            c1.markdown("Таблица сопряженности 2х2")
            c1.dataframe(results22)
            #c1.dataframe(pibi_table)
            c2.markdown("Показатели согласованности")
            c2.dataframe(kappa_table) 
            c3.markdown("Критерий Макнемара")
            c3.dataframe(mcnemar_table)

            # График зависимости kappa от порога метода А
            def plot_k():
                ks = []
                pabaks = []
                ac1s = []
                porogs = []
                for i in np.linspace(0,cut_off_input,100):
                    a,b,c,d,dfs = prepare_pair(df,aa,bb,i,p2)
                    k = compute_kappa(a,b,c,d)
                    ks.append(k)
                    pabak_i = pabak(a,b,c,d)
                    pabaks.append(pabak_i)
                    ac1_i = gwet_ac1(a,b,c,d)
                    ac1s.append(ac1_i)
                    porogs.append(i)
                fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
                ax.set_xlabel(f"Cut-off Метода А ({aa})")
                ax.set_ylabel("Коэффициент согласованности")
                ax.plot(porogs,ks,label = "kappa")
                ax.plot(porogs,pabaks, label = "PABAK")
                ax.plot(porogs,ac1s, label = "AC1")
                ax.legend()
                ax.set_title("Зависимость согласованности от cut-off Метода А")

                return fig
        
            matrix = plot_confusion_matrix(a,b,c,d)
            c11.pyplot(matrix)
            aggrement_bar = plot_agreement_bar(a,b,c,d)
            c22.pyplot(aggrement_bar)
                
            c111.pyplot(plot_k())
            plot_scatter = plot_scatter_with_cutoff(dfs,aa,bb,p1,p2)
            c222.pyplot(plot_scatter)
            npa_ppa_plot = plot_ppa_npa(ppa_list, npa_list)
            c111.pyplot(npa_ppa_plot)
            pr_curve = plot_pr_curve(ppa_list, pr_list)
            c222.pyplot(pr_curve)
            

    # С учётом неопределенности после бинаризации всегда будет таблица 3х3:
    if radio_type == 'Количественные в бинарные + неопределенность':
         st.info("В этом разделе проводится согласие двух методов после бинаризации количественных данных, " \
         "учитывая неопределенность измерения в области cut-off (серой зоне).")
         st.write("=================================================================================================================")
  
         st.sidebar.header("Пара методов") 
         col1, col2 = st.sidebar.columns(2) 
    
         aa = col1.selectbox(f"Метод A (Новый)", numeric_cols) 
         bb = col2.selectbox(f"Метод B (Референтный)", numeric_cols) 
         p1 = col1.number_input("Порог метода А", value=1.0)
         p2 = col2.number_input("Порог метода В", value=1.0)
         cv1 = col1.number_input("CV метода A", step=0.01)
         cv2 = col2.number_input("CV метода B", step=0.01)
       
         cut_off_input = st.sidebar.number_input("Введите максимальное значение cut-off Метода А для построения графика зависимости " \
        " коэффициентов согласованности от cut-off в диапазоне от 0 до введенного значения",value=3)
         
         weights = st.sidebar.radio("Взвешенный коэффициент согласованности", ['Линейные весы', 'Квадратичные весы'])

         push_u = st.sidebar.button("Запуск вычислений")
         if push_u:
             c1_low, c1_high = gray_zone_from_cv(p1, cv1)
             c2_low, c2_high = gray_zone_from_cv(p2, cv2)
             x1, x2 = prepare_pair2(df, aa, bb)

             table, a,b,c,d,e,f,g,h,i = build_3x3_table(x1, x2, c1_low, c1_high, c2_low, c2_high)
             W = make_weights(k=3, scheme = weights)
             wk = weighted_kappa(table,W)
             ac2 = gwet_ac2(table,W)
             wk_ci_low, wk_ci_high = bootstrap_ci(df, weighted_kappa, W, c1_low, c1_high, c2_low, c2_high)
             ac2_ci_low, ac2_ci_high = bootstrap_ci(df, gwet_ac2, W, c1_low, c1_high, c2_low, c2_high)
             bt_stat, bt_pval, interpretation = bowker_test(table, b,d,c,g,f,h)
 
             results33 = {"": ["Метод A -","Серая зона A","Метод A +"],
                         "Метод B -": [a,d,g],
                         "Серая зона B": [b,e,h],
                         "Метод B +": [c,f,i]}


             Agr_table = {"": ["Взвешенная kappa", 
                              "AC2 Гвета"],
                            "Значение": [round(wk,4), 
                                     round(ac2,4)],
                             "95% CI": [f"от {wk_ci_low} до {wk_ci_high}", f"от {ac2_ci_low} до {ac2_ci_high}"]}
                                    
             bowker_T = {"Статистика критерия": [bt_stat],
                             "p-value" : [bt_pval],
                              "Интерпретация": [interpretation] }
        
             c1,c2 = st.columns(2)
             c11,c22 = st.columns(2)
             c111,c222 = st.columns(2)
        
 
             # График зависимости взвешенной kappa и АС2 от порога метода А
             def plot_wk(table,W):
                 wks = []
                 ac2s = []
                 porogs = []
                 for i in np.linspace(0,cut_off_input,100):
                     c1_low, c1_high = gray_zone_from_cv(i, cv1)
                     c2_low, c2_high = gray_zone_from_cv(p2, cv2)
                     x1, x2 = prepare_pair2(df, aa, bb)
                     table, a,b,c,d,e,f,g,h,ii = build_3x3_table(x1, x2, c1_low, c1_high, c2_low, c2_high)
                     W = make_weights(k=3, scheme = weights)
                     wk = weighted_kappa(table,W)
                     wks.append(wk)
                     ac2 = gwet_ac2(table,W)
                     ac2s.append(ac2)
                     porogs.append(i)
                 fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
                 ax.set_xlabel(f"Cut-off Метода А ({aa})")
                 ax.set_ylabel("Коэффициент согласованности")
                 ax.plot(porogs,wks,label = "взвешенная kappa")
                 ax.plot(porogs,ac2s, label = "AC2")
                 ax.legend()
                 ax.set_title("Зависимость согласованности от cut-off Метода А")
                 return fig

             c1.markdown("Таблица сопряженности 3х3 с серой зоной")
             c1.dataframe(results33)
             c2.markdown("Показатели согласия")
             c2.dataframe(Agr_table)
             c2.markdown("Критерий Макнемара - Боукера")
             c2.dataframe(bowker_T)
             #st.write(W)

             plot3x3 = plot_3x3_agreement(table)
             c11.pyplot(plot3x3)
             plot_cutoff = plot_wk(table,W)
             c111.pyplot(plot_cutoff)
             plot_AP = plot_agreement_pattern(table)
             c22.pyplot(plot_AP)
             plot_sgz = plot_scatter_gray_zone(x1, x2, c1_low, c1_high, c2_low, c2_high)
             c222.pyplot(plot_sgz)

else:
    st.info("""В загруженном файле результаты должны располагаться в столбцах и иметь заголовки.  
            Строки с отсутствующими данными автоматически удаляются и не принимают участия в расчётах.  
             Для количественных тестов следующие знаки автоматически удаляются: &gt;l < >""")
    st.info ("""***Количественные в бинарные***: деление производится автоматически по введенным уровням cut-off  
             ***Количественные в бинарные + неопределенность***: деление производится автоматически с учётом уровней cut-off и CV методов""")         

