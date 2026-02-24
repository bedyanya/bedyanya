import streamlit as st
import pandas as pd
import numpy as np
from sklearn.utils import resample
import matplotlib.pyplot as plt
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint

st.set_page_config(layout="wide")

st.title("Диагностическое согласие методов. Сравнение полуколичественных и качественных методов.")

uploaded_file = st.file_uploader("Загрузите Excel", type=["xlsx", "xls"])


# ФУНКЦИИ
# Предобработка входных данных
def prepare_pair(df, aa, bb, p1, p2):

    dfs = df[[aa,bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs["m1_bin"] = np.where(dfs[aa] >= p1, 1, 0)
    dfs["m2_bin"] = np.where(dfs[bb] >= p2, 1, 0)

    a = np.sum((dfs["m1_bin"]==1) & (dfs["m2_bin"]==1))
    b = np.sum((dfs["m1_bin"]==1) & (dfs["m2_bin"]==0))
    c = np.sum((dfs["m1_bin"]==0) & (dfs["m2_bin"]==1))
    d = np.sum((dfs["m1_bin"]==0) & (dfs["m2_bin"]==0))

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

        a = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==1))
        b = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==0))
        c = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==1))
        d = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==0))
        
        k = compute_kappa(a,b,c,d)
        if not np.isnan(k):
            boot.append(k)
    return np.percentile(boot, [2.5,97.5])

# Рассчёт PPA и NPA
def compute_ppa_npa(a,b,c,d):
    # тут исправил в соответствии с таблицей
    PPA = a/(a+c) if (a+b)>0 else np.nan
    NPA = d/(b+d) if (c+d)>0 else np.nan

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
        mc_answer = "Метод систематически отличается"
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

        a = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==1))
        b = np.sum((sample["m1_bin"]==1) & (sample["m2_bin"]==0))
        c = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==1))
        d = np.sum((sample["m1_bin"]==0) & (sample["m2_bin"]==0))

        ac1 = gwet_ac1(a,b,c,d)
        if not np.isnan(ac1):
            boot.append(ac1)

    return np.percentile(boot,[2.5,97.5])

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
    ax.scatter(x[~concordant], y[~concordant], alpha=0.8)
    ax.axvline(p1)
    ax.axhline(p2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(aa)
    ax.set_ylabel(bb)
    ax.set_title("Scatter plot (log-scale)")
    return fig


def plot_confusion_matrix(a, b, c, d):
    matrix = np.array([[a, b],
                       [c, d]])
    fig, ax = plt.subplots()
    im = ax.imshow(matrix, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, matrix[i, j],
                    ha="center", va="center")
    ax.set_xticks([0,1])
    ax.set_yticks([0,1])
    ax.set_xticklabels(["Метод B +", "Метод B -"])
    ax.set_yticklabels(["Метод A +", "Метод A -"])
    ax.set_title("Таблица сопряженности 2x2")
    fig.colorbar(im)
    return fig

def plot_agreement_bar(a,b,c,d):
    labels = ["++","+-","-+","--"]
    values = [a,b,c,d]
    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title("Структура согласованности")
    ax.set_ylabel("Количество")
    return fig

def plot_mosaic(a,b,c,d):
    n = a+b+c+d
    row1 = a+b
    row2 = c+d
    fig, ax = plt.subplots()
    ax.bar([0], [a/row1], width=row1/n)
    ax.bar([0], [b/row1], bottom=[a/row1], width=row1/n)
    ax.bar([1], [c/row2], width=row2/n)
    ax.bar([1], [d/row2], bottom=[c/row2], width=row2/n)
    ax.set_title("Mosaic Plot")
    return fig

# UI:
if uploaded_file: 
    df = pd.read_excel(uploaded_file) 
    st.dataframe(df.head())
    numeric_cols=df.columns.to_list()

    # sidebar
    radio_type = st.sidebar.radio("Выбери тип сравнения",['Diagnostic agreement',
                                                        "Categorical / Ordinal agreement"])

    if radio_type == 'Diagnostic agreement':
        st.subheader("Диагностическое согласие после бинаризации количественных методов.")
        st.write("Данный раздел подойдет для сравнения полуколичественных методов с порогом отсечки на положительных и отрицательных." \
        "Например, сравнение ИФА, ИХЛА - методов для диагностики инфекционных заболеваний." \
        " Также можно провести анализ согласия количественных методов относительно уровня cut-off.")
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
            ppa_ci = ci_binomial(a, a+c)
            npa_ci = ci_binomial(d, b+d)
            PABAK = pabak(a,b,c,d)
            pabak_ci_low, pabak_ci_high = pabak_ci_funk(a,b,c,d)
            mc_answer, mcnemar_pval = mcnemar_result(a,b,c,d)
            AC1 = gwet_ac1(a,b,c,d)
            ci_ac1_low, ci_ac1_high = bootstrap_ac1(dfs)
            PI, BI = prevalence_bias_index(a,b,c,d)

            results22 = {"": ["Метод A +","Метод A -"],
                        "Метод B +": [a,c],
                        "Метод B -": [b,d]}

            pibi_table = {"Prevalence Index": round(PI,4),
                          "Bias Index": round(BI,4)} 

            kappa_table = {"": ["kappa", 
                                "PPA", 
                                "NPA",
                                "PABAK",
                                "Gwet's AC1"],
                           "Value": [round(kappa,4), 
                                    round(PPA,4), 
                                    round(NPA,4),
                                    round(PABAK,4), 
                                    round(AC1,4)],
                            "95% CI":[ f'от {round(ci_low,4)} до {round(ci_high,4)}',
                                    f'от {round(ppa_ci[0],4)} до {round(ppa_ci[1],4)}',
                                    f'от {round(npa_ci[0],4)} до {round(npa_ci[1],4)}',
                                    f'от {round(pabak_ci_low,4)} до {round(pabak_ci_high,4)}',
                                    f'от  {round(ci_ac1_low,4)} до {round(ci_ac1_high,4)}']}
        
            mcnemar_table = {"p-value": [round(mcnemar_pval,4)],
                            "Интерпретация" : [mc_answer] }
        
            c1,c2,c3 = st.columns(3)
            c11,c22 = st.columns(2)
            c111,c222 = st.columns(2)
        
            c1.markdown("Таблица сопряженности 2х2")
            c1.dataframe(results22)
            c1.dataframe(pibi_table)
            c2.markdown("Согласованность")
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
                ax.set_xlabel("Cut-off Метода А")
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

    else:
        st.subheader("Тута пока ничего нет. Выберите Diagnostic agreement")    

else:
    st.info("В загруженном файле результаты должны располагаться в столбцах и иметь заголовки")        

