import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from itertools import combinations

st.set_page_config(layout="wide")

# -----------------------------
# Bland–Altman
# -----------------------------
def bland_altman_analysis(x, y, alpha=0.05):
    x = np.asarray(x)
    y = np.asarray(y)

    diff = x - y
    mean = (x + y) / 2

    n = len(diff)
    md = np.mean(diff)
    sd = np.std(diff, ddof=1)

    loa_upper = md + 1.96 * sd
    loa_lower = md - 1.96 * sd

    tval = stats.t.ppf(1 - alpha/2, df=n-1)

    # CI mean difference
    se_md = sd / np.sqrt(n)
    ci_md = (md - tval * se_md, md + tval * se_md)

    # CI LoA (строгая формула, Б-А 1999)
    se_loa = sd * np.sqrt(1/n + (1.96**2)/(2*(n-1)))
    ci_upper = (loa_upper - tval * se_loa, loa_upper + tval * se_loa)
    ci_lower = (loa_lower - tval * se_loa, loa_lower + tval * se_loa)

    return {
        "mean": mean,
        "diff": diff,
        "md": md,
        "sd": sd,
        "loa_upper": loa_upper,
        "loa_lower": loa_lower,
        "ci_md": ci_md,
        "ci_upper": ci_upper,
        "ci_lower": ci_lower,
        "n": n
    }
def plot_bland_altman(res, title):
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.scatter(res["mean"], res["diff"], alpha=0.6)

    ax.axhline(res["md"], color="black", linestyle="--")
    ax.axhline(res["loa_upper"], color="red", linestyle="--")
    ax.axhline(res["loa_lower"], color="red", linestyle="--")

    xmin, xmax = np.min(res["mean"]), np.max(res["mean"])
    alpha=0.05
    diff = x - y
    mean = (x + y) / 2

    n = len(diff)
    md = np.mean(diff)
    sd = np.std(diff, ddof=1)


    loa_upper = md + 1.96 * sd
    loa_lower = md - 1.96 * sd

    tval = stats.t.ppf(1 - alpha/2, df=n-1)

    # CI mean difference
    se_md = sd / np.sqrt(n)
    ci_md = (md - tval * se_md, md + tval * se_md)

    # CI LoA (строгая формула, Б-А 1999)
    se_loa = sd * np.sqrt(1/n + (1.96**2)/(2*(n-1)))
    ci_upper = (loa_upper - tval * se_loa, loa_upper + tval * se_loa)
    ci_lower = (loa_lower - tval * se_loa, loa_lower + tval * se_loa)

    # CI 
    left, right = ax.get_xlim()
    bottom, top = ax.get_ylim()
    # Set y-axis limits
    max_y = max(abs(bottom), abs(top))
    ax.set_ylim(-max_y * 1.1, max_y * 1.1)
    # Set x-axis limits
    domain = right - left
    ax.set_xlim(left, left + domain * 1.1)
    # Annotations
    ax.annotate('+LOA', (right, loa_upper), (0, 7), textcoords='offset pixels')
    ax.annotate(f'{loa_upper:+4.2f}', (right, loa_upper), (0, -25), textcoords='offset pixels')
    ax.annotate('Mean Bias', (right, md), (0, 7), textcoords='offset pixels')
    ax.annotate(f'{md:+4.2f}', (right, md), (0, -25), textcoords='offset pixels')
    ax.annotate('-LOA', (right, loa_lower), (0, 7), textcoords='offset pixels')
    ax.annotate(f'{loa_lower:+4.2f}', (right, loa_lower), (0, -25), textcoords='offset pixels')


    ax.set_title(title)
    ax.set_xlabel("Mean of methods")
    ax.set_ylabel("Difference")

    ax.grid(True, alpha=0.3)
    ax.legend()

    return fig

# Проходящий Баблок
def passing_bablok(x, y, alpha=0.05):
    x = np.asarray(x)
    y = np.asarray(y)

    slopes = []

    n = len(x)

    for i in range(n - 1):
        for j in range(i + 1, n):
            y_i, y_j, x_i, x_j = y[i], y[j], x[i], x[j]
            # исключаем идентичные точки
            if (y_i == y_j) and (x_i == x_j):
                continue
            # исключаем деление на нулевые ошибки
            if x_i == x_j:
                if y_i > y_j:
                    # +inf
                    grad = np.inf
                    slopes.append(grad)
                    continue
                else:
                    # -inf
                    grad = -np.inf
                    slopes.append(grad)
                    continue
            # градиент
            grad = (y_i - y_j) / (x_i - x_j)
            # игнорим градиент -1
            if np.isclose(grad,-1):
                continue
            # добавляем в список наклонов
            slopes.append(grad)
    slopes.sort()
    N = len(slopes)
    S = np.array(slopes)
    K = (S < -1).sum() 


    if N % 2 != 0:
        idx = (N + 1) / 2 + K
        idx = int(idx) - 1
        b = S[idx]
    else:
        idx = N / 2 + K
        idx = int(idx) - 1
        b = 0.5 * (S[idx] + S[idx + 1])
    
    a = np.median(y - b * x)

    C=0.95  #95 % доверительный
    #
    w = stats.norm.ppf(1-(1-C)/2)  
    # индексы градиентов, соответствующие доверительным интервалам 
    C_gamma = w * np.sqrt((n * (n - 1) * (2 * n + 5)) / 18)
    M_1 = np.round((N - C_gamma) / 2)
    M_2 = N - M_1 + 1

    b_L = S[int(M_1) + K - 1]
    b_U = S[int(M_2) + K - 1]

    a_L = np.median(y - b_U * x)
    a_U = np.median(y - b_L * x)

    slope_ci = (b_L, b_U)
    intercept_ci = (a_L,a_U)

    return {
        "slope": b,
        "intercept": a,
        "slope_ci": slope_ci,
        "intercept_ci": intercept_ci
    }

def plot_passing_bablok(x, y, res, title):
    fig, ax = plt.subplots(figsize=(8, 6))

    x = np.asarray(x)
    y = np.asarray(y)

    ax.scatter(x, y, alpha=0.6)

    slopes = []

    n = len(x)

    for i in range(n - 1):
        for j in range(i + 1, n):
            y_i, y_j, x_i, x_j = y[i], y[j], x[i], x[j]
            # исключаем идентичные точки
            if (y_i == y_j) and (x_i == x_j):
                continue
            # исключаем деление на нулевые ошибки
            if x_i == x_j:
                if y_i > y_j:
                    # +inf
                    grad = np.inf
                    slopes.append(grad)
                    continue
                else:
                    # -inf
                    grad = -np.inf
                    slopes.append(grad)
                    continue
            # gradient
            grad = (y_i - y_j) / (x_i - x_j)
            # игнорим градиент -1
            if np.isclose(grad,-1):
                continue
            # добавляем в список наклонов
            slopes.append(grad)


    slopes.sort()
    N = len(slopes)
    S = np.array(slopes)
    K = (S < -1).sum() 


    if N % 2 != 0:
        idx = (N + 1) / 2 + K
        idx = int(idx) - 1
        b = S[idx]
    else:
        idx = N / 2 + K
        idx = int(idx) - 1
        b = 0.5 * (S[idx] + S[idx + 1])
    
    a = np.median(y - b * x)

    C=0.95  #95 % доверительный
    #
    w = stats.norm.ppf(1-(1-C)/2)  
    # индексы градиентов, соответствующие доверительным интервалам 
    C_gamma = w * np.sqrt((n * (n - 1) * (2 * n + 5)) / 18)
    M_1 = np.round((N - C_gamma) / 2)
    M_2 = N - M_1 + 1

    b_L = S[int(M_1) + K - 1]
    b_U = S[int(M_2) + K - 1]

    a_L = np.median(y - b_U * x)
    a_U = np.median(y - b_L * x)

    slope_ci = (b_L, b_U)
    intercept_ci = (a_L,a_U)

    ax.set_xlabel('Method A')
    ax.set_ylabel('Method B')

    left, right = ax.get_xlim()
    bottom, top = ax.get_ylim()
    # Change axis limits
    ax.set_xlim(0, right)
    ax.set_ylim(0, top)
    # Reference line
    ax.plot([left, right], [left, right], c='grey', ls='--', label='Reference line')
    # Passing-Bablok regression line
    xx = np.array([left, right])
    yy = a + b * xx
    ax.plot(xx, yy, label=f'{b:4.2f}x + {a:4.2f}')
    # Passing-Bablok regression line - confidence intervals
    #x = np.array([left, right])
    y_L = a_L + b_L * xx
    y_U = a_U + b_U * xx
    label_uCI = f'Upper CI: {b_U:4.2f}x + {a_U:4.2f}'
    ax.plot(xx, y_U, c='tab:blue', alpha=0.2, label=label_uCI)
    label_lCI = f'Lower CI: {b_L:4.2f}x + {a_L:4.2f}'
    ax.plot(xx, y_L, c='tab:blue', alpha=0.2, label=label_lCI)
    ax.fill_between(xx, y_U, y_L, alpha=0.2)
    # Set aspect ratio
    #ax.set_aspect('equal')
    
    # Legend
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)
    ax.set_title(title)

    return fig

# -----------------------------
# UI
# -----------------------------
st.title("Сравнение методов: Bland–Altman + Passing–Bablok")

uploaded_file = st.file_uploader("Загрузите Excel файл", type=['xlsx','xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("Данные")
    st.dataframe(df.head())

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    st.sidebar.header("Выбор методов")

    bo1,bo2=st.sidebar.columns(2)

    b1=bo1.selectbox('Method A',df.columns)
    b2=bo2.selectbox('Method B',df.columns)

    
    run_btn = st.sidebar.button("Запустить анализ")

    if run_btn:
        #st.markdown(f"## {b1} vs {b2}")

        data = df[[b1, b2]].dropna()

        x = data[b2].values
        y = data[b1].values

        # ---- Bland–Altman ----
        ba_res = bland_altman_analysis(x, y)

        # ---- Passing–Bablok ----
        pb_res = passing_bablok(x, y)

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Bland–Altman")
            fig_ba = plot_bland_altman(ba_res, f"{b1} vs {b2}")
            st.pyplot(fig_ba)

            ba_table = pd.DataFrame({
                "Параметр": ["Mean diff", "LoA lower", "LoA upper"],
                "Значение": [ba_res["md"], ba_res["loa_lower"], ba_res["loa_upper"]],
                "CI lower": [ba_res["ci_md"][0], ba_res["ci_lower"][0], ba_res["ci_upper"][0]],
                "CI upper": [ba_res["ci_md"][1], ba_res["ci_lower"][1], ba_res["ci_upper"][1]]
            })

            st.table(ba_table)

        with c2:
            st.subheader("Passing–Bablok")
            fig_pb = plot_passing_bablok(x, y, pb_res, f"{b1} vs {b2}")
            st.pyplot(fig_pb)

            pb_table = pd.DataFrame({
                "Параметр": ["Slope", "Intercept"],
                "Значение": [pb_res["slope"], pb_res["intercept"]],
                "CI lower": [pb_res["slope_ci"][0], pb_res["intercept_ci"][0]],
                "CI upper": [pb_res["slope_ci"][1], pb_res["intercept_ci"][1]],
            })

            st.table(pb_table)

else:
    st.info("Загрузите Excel файл для начала работы.")
