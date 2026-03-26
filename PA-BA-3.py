import streamlit as st 
import pandas as pd 
import numpy as np 
from scipy import stats 
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

#=============================
#Utilities
#=============================
# TE = |bias| + z * SD (z=1.65 ~ 95% one-sided) 
def compute_total_error(mean_diff, sd, z=1.96): 
    return round(abs(mean_diff) + z * sd, 2)
#=============================
# Функция расчёта CI для r Пирсона
def pearson_ci(r, n, alpha=0.05):
    if abs(r) >= 1 or n <= 3:
        return (np.nan, np.nan)

    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    zcrit = stats.norm.ppf(1 - alpha / 2)

    pearson_ci_lo = np.tanh(z - zcrit * se)
    pearson_ci_hi = np.tanh(z + zcrit * se)

    return round(pearson_ci_lo,4), round(pearson_ci_hi,4)
#=============================
# Функция расчёта CI для p Спирмена
def spearman_ci(rho, n, alpha=0.05):
    if abs(rho) >= 1 or n <= 3:
        return (np.nan, np.nan)

    z = np.arctanh(rho)
    se = 1 / np.sqrt(n - 3)
    zcrit = stats.norm.ppf(1 - alpha / 2)

    spearman_ci_lo = np.tanh(z - zcrit * se)
    spearman_ci_hi = np.tanh(z + zcrit * se)

    return round(spearman_ci_lo,4), round(spearman_ci_hi,4)

#=============================
# Функция расчёта CI для tau Кендалля (Bootstrap)
def kendall_tau_ci(x, y, n_boot=2000, alpha=0.05, random_state=None):
    rng = np.random.default_rng(random_state)
    x = np.asarray(x)
    y = np.asarray(y)
    n = len(x)

    tau_boot = np.zeros(n_boot)

    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        tau_boot[i], _ = stats.kendalltau(x[idx], y[idx])

    kendall_tau_lo = np.percentile(tau_boot, 100 * alpha / 2)
    kendall_tau_hi = np.percentile(tau_boot, 100 * (1 - alpha / 2))

    return round(kendall_tau_lo,4), round(kendall_tau_hi,4)
#=============================
# CUSUM
def cusum_test_passing_bablok(x, y, a, b, n_sim=5000, random_state=None):
    x = np.asarray(x)
    y = np.asarray(y)
    n = len(x)

    # Считаем остатки
    y_hat = b * x + a
    residuals = y - y_hat

    n_pos = np.sum(residuals > 0)
    n_neg = np.sum(residuals < 0)

    if n_pos == 0 or n_neg == 0:
        raise ValueError("CUSUM test not defined: all residuals have same sign.")

    # Считаем r_i
    r = np.zeros(n)
    r[residuals > 0] = np.sqrt(n_neg / n_pos)
    r[residuals < 0] = -np.sqrt(n_pos / n_neg)
    # residuals == 0 → r_i = 0 (уже так)

    # Считаем distances d_i
    d = (y + x / b - a) / np.sqrt(1 + 1 / b**2)

    # Сортируем по D: sort r_i by d_i
    order = np.argsort(d)
    r_sorted = r[order]

    # cumulative sums
    c = np.cumsum(r_sorted)
    c_max = np.max(np.abs(c))

    # Вычисляем статистику H
    n_minus = min(n_pos, n_neg)
    h_obs = c_max / np.sqrt(n_minus + 1)

    # p-value approximation
    # usum_p = 2 * (1 - stats.norm.cdf(abs(h)))

    # Monte Carlo permutations
    h_sim = np.zeros(n_sim)

    for i in range(n_sim):
        rng = np.random.default_rng(random_state)
        r_perm = rng.permutation(r_sorted)
        c_perm = np.cumsum(r_perm)
        cmax_perm = np.max(np.abs(c_perm))
        h_sim[i] = cmax_perm / np.sqrt(n_minus + 1)

    # p-value -----
    cusum_p = (np.sum(h_sim >= h_obs) + 1) / (n_sim + 1)

    return cusum_p


#=============================
#Bland–Altman
#=============================
def bland_altman_prepare(x, y, mode="Absolute difference"): 
    x = np.asarray(x, dtype=float) 
    y = np.asarray(y, dtype=float)
    mean = (x + y) / 2 
    if mode == "Absolute difference": 
        diff = y - x 
        ylabel = f'{b1} - {b2}' 
    elif mode == "Relative difference (%)": 
        diff = 100 * (y - x) / mean 
        ylabel = f"({b1} - {b2}) / Mean of methods (%)" 
    elif mode == "Relative difference": 
        diff = (y - x) / mean 
        ylabel = f"({b1} - {b2}) / Mean of methods" 
    else: 
        raise ValueError("Unknown BA mode") 
    return mean, diff, ylabel 

def bland_altman_analysis(x, y, alpha=0.05, mode="Absolute difference"): 
    mean, diff, ylabel = bland_altman_prepare(x, y, mode)
    n = len(diff) 
    md = np.mean(diff) 
    sd = np.std(diff, ddof=1) 
    loa_upper = md + 1.96 * sd 
    loa_lower = md - 1.96 * sd 
    # t-quantile 
    tval = stats.t.ppf(1 - alpha / 2, df=n - 1) 
    se_md = sd / np.sqrt(n) 
    ci_md = (round(md - tval * se_md,4), round(md + tval * se_md,4)) 
    # Strict SE for LoA (Bland–Altman 1999) 
    se_loa = sd * np.sqrt(1 / n + (1.96 ** 2) / (2 * (n - 1))) 
    ci_upper = (round(loa_upper - tval * se_loa,4), round(loa_upper + tval * se_loa,4))
    ci_lower = (round(loa_lower - tval * se_loa,4), round(loa_lower + tval * se_loa,4))
    te = compute_total_error(md, sd) 
    
    return { "mean": mean, 
            "diff": diff, 
            "ylabel": ylabel, 
            "md": md, "sd": sd, 
            "loa_upper": loa_upper, 
            "loa_lower": loa_lower, 
            "ci_md": ci_md, 
            "ci_upper": ci_upper, 
            "ci_lower": ci_lower, 
            "n": n, 
            "te": te, } 

# График Бланда-Альтмана
def plot_bland_altman(res, title): 
    fig, ax = plt.subplots(figsize=(8, 6),dpi=200)
    ax.scatter(res["mean"], res["diff"], alpha=0.6) 
    ax.axhline(res["md"], color="black", linestyle="--", label="Mean diff") 
    ax.axhline(res["loa_upper"], color="red", linestyle="--", label="Upper LoA") 
    ax.axhline(res["loa_lower"], color="red", linestyle="--", label="Lower LoA") 

    xmin, xmax = np.min(res["mean"]), np.max(res["mean"]) 

    # CI 
    left, right = ax.get_xlim()
    bottom, top = ax.get_ylim()
    # Set y-axis limits
    max_y = max(abs(bottom), abs(top))
    #ax.set_ylim(-max_y * 1.1, max_y * 1.1)
    # Set x-axis limits
    domain = right - left
    ax.set_xlim(left, left + domain * 1.15)

    ax.fill_between([xmin, left + domain * 1.13], res["ci_upper"][0], res["ci_upper"][1], color="red", alpha=0.15) 
    ax.fill_between([xmin, left + domain * 1.13], res["ci_lower"][0], res["ci_lower"][1], color="red", alpha=0.15) 
    ax.fill_between([xmin, left + domain * 1.13], res["ci_md"][0], res["ci_md"][1], color="gray", alpha=0.2) 

    # Annotations
    ax.annotate('+LOA', (right, res["loa_upper"]), (0, 7), textcoords='offset pixels')
    ax.annotate(f'{res["loa_upper"]:+4.2f}', (right, res["loa_upper"]), (0, -25), textcoords='offset pixels')
    ax.annotate('Mean Bias', (right, res["md"]), (0, 7), textcoords='offset pixels')
    ax.annotate(f'{res["md"]:+4.2f}', (right, res["md"]), (0, -25), textcoords='offset pixels')
    ax.annotate('-LOA', (right, res["loa_lower"]), (0, 7), textcoords='offset pixels')
    ax.annotate(f'{res["loa_lower"]:+4.2f}', (right, res["loa_lower"]), (0, -25), textcoords='offset pixels')

    ax.set_title(title) 
    ax.set_xlabel("Mean of methods") 
    ax.set_ylabel(res["ylabel"]) 
    ax.grid(True, alpha=0.3) 
    #ax.legend() 
    
    return fig 
#=============================
#Passing–Bablok (Rowan-compatible)
#=============================
def passing_bablok(x, y, alpha=0.05): 
    x = np.asarray(x, dtype=float) 
    y = np.asarray(y, dtype=float)
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
    slopes = np.array(slopes)
    K = (slopes < -1).sum() 


    if N % 2 != 0:
        idx = (N + 1) / 2 + K
        idx = int(idx) - 1
        b = slopes[idx]
    else:
        idx = N / 2 + K
        idx = int(idx) - 1
        b = 0.5 * (slopes[idx] + slopes[idx + 1])
    
    a = np.median(y - b * x)

              
    # CI for slope 
    z = stats.norm.ppf(1 - alpha / 2) 
    C_gamma = z * np.sqrt((n * (n - 1) * (2 * n + 5)) / 18) 
    M_1 = np.round((N - C_gamma) / 2) 
    M_2 = N - M_1 + 1 
            
    b_L = slopes[int(M_1) + K - 1] 
    b_U = slopes[int(M_2) + K - 1] 
            
    a_L = np.median(y - b_U * x) 
    a_U = np.median(y - b_L * x) 
            
    # Correlations 
    pearson_r, pearson_p = stats.pearsonr(x, y) 
    spearman_r, spearman_p = stats.spearmanr(x, y)
    kendall_tau, kendall_p = stats.kendalltau(x, y) 

    if pearson_p < 0.0001:
        pearson_p = '< 0.0001'
    else:
        pearson_p = round(pearson_p, 4)

    if spearman_p < 0.0001:
        spearman_p = '< 0.0001'
    else:
        spearman_p = round(spearman_p, 4)
    
    if kendall_p < 0.0001:
        kendall_p = '< 0.0001'
    else:
        kendall_p = round(kendall_p, 4)


    pearson_ci_lo, pearson_ci_hi = pearson_ci(pearson_r, n)
    spearman_ci_lo, spearman_ci_hi = spearman_ci(spearman_r, n)
    kendall_tau_lo, kendall_tau_hi = kendall_tau_ci(x,y)


    # CUSUM linearity test
    # 
    cusum_p = cusum_test_passing_bablok(x,y,a,b)

  

    return { 
        "slope": b, 
        "intercept": a, 
        "slope_ci": (round(b_L,4), round(b_U,4)), 
        "intercept_ci": (round(a_L,4), round(a_U,4)), 
        "pearson": (pearson_r, pearson_p, pearson_ci_lo, pearson_ci_hi), 
        "spearman": (spearman_r, spearman_p, spearman_ci_lo, spearman_ci_hi), 
        "cusum_p": cusum_p,
         "kendall": (kendall_tau, kendall_p,kendall_tau_lo,kendall_tau_hi) } 

# Функция, рисующая регрессию Пассинга-Баблока    
def plot_passing_bablok(x, y, res, title, from_zero=False): 
    fig, ax = plt.subplots(figsize=(8, 6),dpi=200)
    ax.scatter(x, y, alpha=0.6) 
    xmin, xmax = np.min(x), np.max(x) 
    ymin, ymax = np.min(y), np.max(y) 
    if from_zero: 
        xmin, ymin = 0, 0 
        
    pad_x = 0.05 * (xmax - xmin) 
    pad_y = 0.05 * (ymax - ymin) 

    ax.set_xlim(xmin - pad_x, xmax + pad_x) 
    ax.set_ylim(ymin - pad_y, ymax + pad_y) 

    xx = np.array([ax.get_xlim()[0], ax.get_xlim()[1]]) 
    yy = res["intercept"] + res["slope"] * xx

    b=res['slope']
    a=res['intercept']
    
    minus = "\u2212"
    sign = "+" if a>=0 else minus
    pb_line = f'y = {b:4.2f}x {sign} {abs(a):4.2f}'
    ax.plot(xx, yy, label=pb_line)

    b_U = res["slope_ci"][1]
    a_U = res["intercept_ci"][1]
    b_L = res["slope_ci"][0]
    a_L = res["intercept_ci"][0]
    
    yL = res["intercept_ci"][0] + res["slope_ci"][0] * xx 
    yU = res["intercept_ci"][1] + res["slope_ci"][1] * xx 
    ax.plot(xx, yL, c="gray", alpha=0.5,label = f'Lower CI: {b_L:4.2f}x {sign} {abs(a_L):4.2f}') 
    ax.plot(xx, yU, c="gray", alpha=0.5,label=f'Upper CI: {b_U:4.2f}x {sign} {abs(a_U):4.2f}') 
    ax.fill_between(xx, yL, yU, color="gray", alpha=0.2, label="95% CI") 
    ax.plot(xx, xx, c="black", ls="--", alpha=0.5, label="Reference line") 
    ax.set_title(title) 
    ax.set_xlabel(f"{b2}") 
    ax.set_ylabel(f"{b1}") 
    ax.grid(True, alpha=0.3) 
    ax.legend(loc="upper left")
 
    #ax.legend(frameon=False)
    
    return fig 
# График осатков Passing-Bablok
def plot_pb_residuals_rank(x, y, res, title):
    x = np.asarray(x)
    y = np.asarray(y)

    b=res['slope']
    a=res['intercept']

    residuals = y - (b * x + a)

    d = (y + x / b - a) / np.sqrt(1 + 1 / b**2)
    order = np.argsort(d)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
    ax.scatter(
        np.arange(1, len(x) + 1),
        residuals[order],
        alpha=0.7
    )
    ax.axhline(0, linestyle="--")

    ax.set_xlabel("Rank(x,y)")
    ax.set_ylabel("Residuals (y − ŷ)")
    ax.grid(True, alpha=0.3) 
    ax.set_title(title)

    return fig

# ДЁЁЁЁЁЁЁЁМИНГ!!!!
# ЛИНИЯ регрессии Дёминга
def deming_regression(x, y, lambda_):
    x = np.asarray(x)
    y = np.asarray(y)

    if x.size != y.size:
        raise ValueError("x and y must have the same length")

    x_mean = np.mean(x)
    y_mean = np.mean(y)

    x_cent = x - x_mean
    y_cent = y - y_mean

    s_xx = np.mean(x_cent ** 2)
    s_yy = np.mean(y_cent ** 2)
    s_xy = np.mean(x_cent * y_cent)

    numerator = s_yy - lambda_ * s_xx
    delta = np.sqrt(numerator**2 + 4 * lambda_ * s_xy**2)

    dslope = (numerator + delta) / (2 * s_xy)
    dintercept = y_mean - dslope * x_mean

    return {
        "slope": round(dslope,4), 
        "intercept": round(dintercept,4)}

# CI для Дёминга
def deming_bootstrap_ci(
    x,
    y,
    lambda_,
    n_boot=5000,
    alpha=0.05,
    seed=None
):
    x = np.asarray(x)
    y = np.asarray(y)
    n = len(x)

    rng = np.random.default_rng(seed)

    slopes = np.empty(n_boot)
    intercepts = np.empty(n_boot)

    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        x_b = x[idx]
        y_b = y[idx]

        dres = deming_regression(x_b, y_b, lambda_)
        slopes[i] = dres["slope"]
        intercepts[i] = dres["intercept"]

    lower = alpha / 2
    upper = 1 - alpha / 2

    dslope_ci = np.percentile(slopes, [100 * lower, 100 * upper])
    dintercept_ci = np.percentile(intercepts, [100 * lower, 100 * upper])

    return {"slope_ci": (round(dslope_ci[0],4), round(dslope_ci[1],4)), 
            "intercept_ci": (round(dintercept_ci[0],4), round(dintercept_ci[1],4))}

# Функция, рисующая регрессию Дёминга    
def plot_deming(x, y, dres, dres_ci, title, from_zero=False): 
    fig, ax = plt.subplots(figsize=(8, 6),dpi=200)
    ax.scatter(x, y, alpha=0.6,color="purple") 
    xmin, xmax = np.min(x), np.max(x) 
    ymin, ymax = np.min(y), np.max(y) 
    if from_zero: 
        xmin, ymin = 0, 0 
        
    pad_x = 0.05 * (xmax - xmin) 
    pad_y = 0.05 * (ymax - ymin) 

    ax.set_xlim(xmin - pad_x, xmax + pad_x) 
    ax.set_ylim(ymin - pad_y, ymax + pad_y) 

    xx = np.array([ax.get_xlim()[0], ax.get_xlim()[1]]) 
    yy = dres["intercept"] + dres["slope"] * xx

    b=dres['slope']
    a=dres['intercept']
    
    minus = "\u2212"
    sign = "+" if a>=0 else minus
    pb_line = f'y = {b:4.2f}x {sign} {abs(a):4.2f}'
    ax.plot(xx, yy, label=pb_line)

    b_U = dres_ci["slope_ci"][1]
    a_U = dres_ci["intercept_ci"][1]
    b_L = dres_ci["slope_ci"][0]
    a_L = dres_ci["intercept_ci"][0]
    
    yL = dres_ci["intercept_ci"][0] + dres_ci["slope_ci"][0] * xx 
    yU = dres_ci["intercept_ci"][1] + dres_ci["slope_ci"][1] * xx 
    ax.plot(xx, yL, c="gray", alpha=0.5,label = f'Lower CI: {b_L:4.2f}x {sign} {abs(a_L):4.2f}') 
    ax.plot(xx, yU, c="gray", alpha=0.5,label=f'Upper CI: {b_U:4.2f}x {sign} {abs(a_U):4.2f}') 
    ax.fill_between(xx, yL, yU, color="yellow", alpha=0.2, label="95% CI") 
    ax.plot(xx, xx, c="black", ls="--", alpha=0.5, label="Reference line") 
    ax.set_title(title) 
    ax.set_xlabel(f"{b2}") 
    ax.set_ylabel(f"{b1}") 
    ax.grid(True, alpha=0.3) 
    ax.legend()
 
    #ax.legend(frameon=False)
    
    return fig 

# График остатков (регрессия Деминга)
def plot_deming_residuals(x, y, dres,title):
    
    b=dres['slope']
    a=dres['intercept']
    
    residuals = (y - a - b * x) / np.sqrt(1 + b**2)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
    ax.scatter(x,residuals, color="purple", alpha=0.7)
    
    ax.axhline(0, linestyle="--")

    ax.set_xlabel(f"{b2}")
    ax.set_ylabel("Residuals (y − ŷ)")
    ax.grid(True, alpha=0.3) 
    ax.set_title(title)

    return fig

# ГОРА (Mountain plot)
def mountain_plot(x, y, title):
    x = np.asarray(x)
    y = np.asarray(y)

    # 1. разности
    diff = y - x

    # 2. сортировка
    diff_sorted = np.sort(diff)
    n = len(diff_sorted)

    # 3. эмпирическая CDF
    cdf = np.arange(1, n + 1) / n

    # 4. Folded CDF (гора)
    mountain = 100 * (0.5 - np.abs(cdf - 0.5))

    # 5. график
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)

    ax.plot(diff_sorted, mountain)
    ax.axvline(np.median(diff), linestyle="--")
    ax.set_xlabel(f'{b1} - {b2}')
    ax.set_ylabel("Folded cumulative frequency (%)")
    ax.grid(True, alpha=0.3)
    ax.set_title(title)

    return fig
#=============================
#UI
#=============================
st.title("Сравнение методов: Bland–Altman & Passing–Bablok")
uploaded_file = st.file_uploader("Выберете Excel-файл", type=["xlsx", "xls"])


if uploaded_file: 
    df = pd.read_excel(uploaded_file) 
    st.dataframe(df.head())
    #numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    numeric_cols=df.columns.to_list()

    current_file = uploaded_file.name

    # session_state

    if "current_file" not in st.session_state:
        st.session_state.current_file = None

    if st.session_state.current_file != current_file:
        st.session_state.current_file = current_file
        st.session_state.pairs = []

    if not st.session_state.pairs and len(numeric_cols) >= 2:
        st.session_state.pairs = [(numeric_cols[0], numeric_cols[1])]


    # sidebar
    st.sidebar.header("Пары методов") 
    # пары
    new_pairs = [] 
    # две колонки с парами и сессии с добавлением/удалением пар
    for i, (c1, c2) in enumerate(st.session_state.pairs): 
        col1, col2 = st.sidebar.columns(2) 
        a = col1.selectbox(f"Method A {i+1}", numeric_cols, index=numeric_cols.index(c1)) 
        b = col2.selectbox(f"Method B (Reference){i+1}", numeric_cols, index=numeric_cols.index(c2)) 
        new_pairs.append((a, b)) 
    
    st.session_state.pairs = new_pairs

    col_add, col_remove = st.sidebar.columns(2)

    if col_add.button("+ Добавить пару"):
        st.session_state.pairs.append(
            (numeric_cols[0], numeric_cols[1])
        )
        st.rerun()

    if col_remove.button("− Удалить пару"):
        if len(st.session_state.pairs) > 1:
            st.session_state.pairs.pop()
            st.rerun() 


    # выбор методов построения    
    ba_mode = st.sidebar.radio("Bland–Altman метод", ["Absolute difference", 
                                                      "Relative difference (%)", 
                                                      "Relative difference"])
    report_mode = st.sidebar.radio("Выбери вариант отчёта", ["BA+PB",
                                                             "BA+PB+residuals (var1)", 
                                                             "BA+PB+residuals (var2)",
                                                             "BA+Mountain+PB+residuals",
                                                             "BA(abs diff)+BA(relative diff)+PB+residuals",
                                                             "BA+Deming",
                                                             "BA+Mountain+Deming"]) 
    pb_zero = st.sidebar.checkbox("График регрессии от 0", value=False)
    lam = 1
    lambdas = []
    if report_mode =="BA+Deming" or report_mode =="BA+Mountain+Deming":
        for i in range (0,len(st.session_state.pairs)):
            lam = st.sidebar.number_input(f"Введите значение λ для пары {i+1}", value=1.0)
            #st.session_state['lambdas'] = lambdas
            lambdas.append(lam)
    st.session_state.lambdas = lambdas

    

    # Графики и результаты:
    if st.sidebar.button("Запустить анализ"):
        # Для summary table:
        ba_summary_data = pd.DataFrame(columns=["Methods",
                                            "Mean Bias, (95% CI)",
                                            "LoA lower, (95% CI)",
                                            "LoA upper, (95% CI)"])
        te_summary_data = pd.DataFrame(columns=["Methods","Total Error (TE)"])
        pb_summary_data = pd.DataFrame(columns = ["Methods",
                                            "Equation",
                                            "Slope, (95% CI)",
                                            "intercept, (95% CI)",
                                            "CUSUM"] )
        cor_summary_data = pd.DataFrame(columns=["Methods",
                                             "Pearson's r",
                                             "Spearman's p",
                                             "Kendall's tau"])
        deming_summary_data = pd.DataFrame(columns = ["Methods",
                                            "Equation",
                                            "Slope",
                                            "intercept"])

        st.session_state["ba_summary_data"] = ba_summary_data
        if ba_summary_data in st.session_state:
            st.dataframe(st.session_state["ba_summary_data"])
        
        st.session_state["te_summary_data"] = te_summary_data
        if te_summary_data in st.session_state:
            st.dataframe(st.session_state["te_summary_data"])
        
        st.session_state["pb_summary_data"] = pb_summary_data
        if pb_summary_data in st.session_state:
            st.dataframe( st.session_state["pb_summary_data"])
        
        st.session_state["cor_summary_data"] = cor_summary_data
        if cor_summary_data in st.session_state:
            st.dataframe( st.session_state["cor_summary_data"])
        
        st.session_state["deming_summary_data"] = deming_summary_data
        if deming_summary_data in st.session_state:
            st.dataframe( st.session_state["deming_summary_data"])
        
        def BA_show(): 
            st.subheader("Bland–Altman") 
            st.pyplot(plot_bland_altman(ba_res, f"{b1} vs {b2}   (n = {len(x)})")) 
            
        def BA_table_show():
            ba_table = pd.DataFrame({ 
                    " ": ["Mean Bias", "LoA lower", "LoA upper"], 
                    "Value": [ba_res["md"], ba_res["loa_lower"], ba_res["loa_upper"]],
                    "95% CI" : [f'от  {ba_res["ci_md"][0]}  до  {ba_res["ci_md"][1]}',
                                 f'от  {ba_res["ci_lower"][0]}  до  {ba_res["ci_lower"][1]}',
                                 f'от  {ba_res["ci_upper"][0]}  до  {ba_res["ci_upper"][1]}']})
                
            st.markdown('**Bland-Altman analysis**')
            st.dataframe(ba_table, hide_index=True) 
            
        def TE_show():
            if ba_mode == "Relative difference (%)":
                st.markdown(f'**Total Error (TE %):**  {ba_res["te"]}')
            else:
                st.markdown(f'**Total Error (TE):**  {ba_res["te"]}')
            
        def BA_sum(ba_summary_data):    
            # Добавим строку в summary table BA:
            ba_table2 = pd.DataFrame({
                    "Methods":[f"{b1} vs {b2}"],
                    "Mean Bias, (95% CI)": [f'{round(ba_res["md"],4)} (от {ba_res["ci_md"][0]} до {ba_res["ci_md"][1]})'],
                    "LoA lower, (95% CI)": [f'{round(ba_res["loa_lower"],4)} (от {ba_res["ci_lower"][0]} до {ba_res["ci_lower"][1]})'],
                    "LoA upper, (95% CI)": [f'{round(ba_res["loa_upper"],4)}  (от {ba_res["ci_upper"][0]} до {ba_res["ci_upper"][1]})'],
                })
            ba_summary_data = pd.concat([st.session_state["ba_summary_data"], ba_table2], ignore_index=True)
            st.session_state["ba_summary_data"] = ba_summary_data
            return st.session_state["ba_summary_data"]

        def TE_sum_show(te_summary_data=te_summary_data): 
            ba_te2 = pd.DataFrame({
                "Methods":[f"{b1} vs {b2}"],
                "Total Error (TE)" : [ba_res["te"]]
                })
            te_summary_data = pd.concat([st.session_state["te_summary_data"],ba_te2],ignore_index=True)
            st.session_state["te_summary_data"] = te_summary_data
            return st.session_state["te_summary_data"]

        def PB_show(): 
            st.subheader("Passing–Bablok")
            fig_pb = plot_passing_bablok(x, y, pb_res, f"{b1} vs {b2}  (n = {len(x)})", from_zero=pb_zero)
            st.pyplot(fig_pb)

        def PB_table_show():    
            st.markdown('**Passing-Bablok regression**')

            minus = "\u2212"
            sign = "+" if pb_res["intercept"]>=0 else minus
            pb_line = f'y = {round(pb_res["slope"],2)}x {sign} {round(abs(pb_res["intercept"]),2)}'
            st.markdown(pb_line)
            pb_table = pd.DataFrame({ 
                    " ": ["Slope", "Intercept"], 
                    "Value": [pb_res["slope"], pb_res["intercept"]], 
                    "95% CI": [f'от  {pb_res["slope_ci"][0]}  до  {pb_res["slope_ci"][1]}',
                               f'от  {pb_res["intercept_ci"][0]}  до  {pb_res["intercept_ci"][1]}'] })
            st.dataframe(pb_table, hide_index=True)
            
        def PB_sum(pb_summary_data):
            if pb_res["cusum_p"]<0.05:
                significant = f'Статистически значимое отклонение от линейности'
            else:
                significant = f'Нет статистически значимого отклонения от линейности'
            minus = "\u2212"
            sign = "+" if pb_res["intercept"]>=0 else minus
            pb_line = f'y = {round(pb_res["slope"],2)}x {sign} {round(abs(pb_res["intercept"]),2)}'

            # Добавим строку в summary table PB:
            pb_sum_table2 = pd.DataFrame({
                "Methods":[f"{b1} vs {b2}"],
                "Equation":[pb_line],
                "Slope, (95% CI)":[f'{round(pb_res["slope"],4)} (от {pb_res["slope_ci"][0]} до {pb_res["slope_ci"][1]})'],
                "intercept, (95% CI)":[f'{round(pb_res["intercept"],4)} (от {pb_res["intercept_ci"][0]} до {pb_res["intercept_ci"][1]})'],
                "CUSUM": [f'{significant}  (p_value = {round(pb_res["cusum_p"],4)})']
            })
            pb_summary_data = pd.concat([st.session_state["pb_summary_data"], pb_sum_table2], ignore_index=True)
            st.session_state["pb_summary_data"] = pb_summary_data
            return st.session_state["pb_summary_data"]

        def corr_show():
            corr_table = pd.DataFrame({
                    " ":["Pearson's r", "Spearman's p", "Kendall's tau"],
                    "Coefficient":[pb_res["pearson"][0],pb_res["spearman"][0],pb_res["kendall"][0]],
                    "95% CI": [f'от  {pb_res["pearson"][2]}  до  {pb_res["pearson"][3]}',
                               f'от  {pb_res["spearman"][2]}  до  {pb_res["spearman"][3]}',
                               f'от  {pb_res["kendall"][2]}  до  {pb_res["kendall"][3]}'],
                    "p-value":[pb_res["pearson"][1],pb_res["spearman"][1], pb_res["kendall"][1]]
                })
            st.markdown("**Correlations**") 
            st.dataframe(corr_table,hide_index=True)

        def corr_sum(cor_summary_data):
            # Добавим строку в summary table для корреляций
            cor_sum_table = pd.DataFrame({
                    "Methods":[f"{b1} vs {b2}","",""],
                    "Pearson's r":[round(pb_res["pearson"][0],4), f'95% CI: от  {pb_res["pearson"][2]}  до  {pb_res["pearson"][3]}', f'p-value: {pb_res["pearson"][1]}'],
                    "Spearman's p":[round(pb_res["spearman"][0],4), f'95% CI: от  {pb_res["spearman"][2]}  до  {pb_res["spearman"][3]}', f'p-value: {pb_res["spearman"][1]}'],
                    "Kendall's tau":[round(pb_res["kendall"][0],4), f'95% CI: от  {pb_res["kendall"][2]}  до  {pb_res["kendall"][3]}', f'p-value: {pb_res["kendall"][1]}']
                })
            cor_summary_data = pd.concat([st.session_state["cor_summary_data"],cor_sum_table],ignore_index=True)
            st.session_state["cor_summary_data"] = cor_summary_data
            return  st.session_state["cor_summary_data"]

        def CUSUM_show():
            st.markdown("**CUSUM test for deviation from linearity (Passing-Bablok):**")
            #               ***p-value obtained by Monte Carlo permutation***:")
            if pb_res["cusum_p"]<0.05:
                st.markdown(f'Статистически значимое отклонение от линейности ***(p-value = {round(pb_res["cusum_p"],4)})***')
            else:
                st.markdown(f'Нет статистически значимого отклонения от линейности ***(p-value = {round(pb_res["cusum_p"],4)})***')
                            
        def PB_res_show():
            st.subheader("Passing-Bablok residuals plot")
            fig_res = plot_pb_residuals_rank(x, y, pb_res, title= f"{b1} vs {b2}  (n = {len(x)})")
            st.pyplot(fig_res)
           
        def mountain_show():
            st.subheader("Mountain plot")
            fig_mountain = mountain_plot(x,y,title= f"{b1} vs {b2}  (n = {len(x)})")
            st.pyplot(fig_mountain)

        def Deming_show():
            st.subheader("Deming regression")
            dres = deming_regression(x, y, lambda_= lam)
            dres_ci = deming_bootstrap_ci(x,y,lambda_=lam)
            fig_deming = plot_deming(x, y, dres, dres_ci, title= f"{b1} vs {b2}  (n = {len(x)})", from_zero=pb_zero)
            st.pyplot(fig_deming)
                    
        def Deming_table_show(dres, dres_ci):
            st.markdown('**Deming regression**')

            minus = "\u2212"
            sign = "+" if dres["intercept"]>=0 else minus
            dem_line = f'y = {round(dres["slope"],2)}x {sign} {round(abs(dres["intercept"]),2)}'
            st.markdown(dem_line)
            dem_table = pd.DataFrame({ 
                        " ": ["Slope", "Intercept"], 
                        "Value": [dres["slope"], dres["intercept"]], 
                        "95% CI": [f'от  {dres_ci["slope_ci"][0]}  до  {dres_ci["slope_ci"][1]}',
                        f'от  {dres_ci["intercept_ci"][0]}  до  {dres_ci["intercept_ci"][1]}'] })
            st.dataframe(dem_table, hide_index=True)

        def Deming_res_show(dres):
            st.subheader("Deming regression residuals plot")
            res_deming = plot_deming_residuals(x,y,dres, title= f"{b1} vs {b2}  (n = {len(x)})")
            st.pyplot(res_deming)

        def Deming_sum(dres, dres_ci, deming_summary_data):
            minus = "\u2212"
            sign = "+" if dres["intercept"]>=0 else minus
            dem_line = f'y = {round(dres["slope"],2)}x {sign} {round(abs(dres["intercept"]),2)}'
            # Добавим строку в summary table PB:
            dem_sum_table2 = pd.DataFrame({
                "Methods":[f"{b1} vs {b2}",""],
                "Equation":[dem_line, ""],
                "Slope":[round(dres["slope"],4), f'95% CI: от  {dres_ci["slope_ci"][0]}  до  {dres_ci["slope_ci"][1]}'],
                "intercept":[round(dres["intercept"],4), f'95% CI: от  {dres_ci["intercept_ci"][0]}  до  {dres_ci["intercept_ci"][1]}']
            })
            deming_summary_data = pd.concat([st.session_state["deming_summary_data"], dem_sum_table2], ignore_index=True)
            st.session_state["deming_summary_data"] = deming_summary_data
            return st.session_state["deming_summary_data"]

                
        # Собственно запуск анализа:
        for m, (b1, b2) in enumerate(st.session_state.pairs): 
            data = df[[b1, b2]].apply(pd.to_numeric, errors='coerce').dropna()
            #наоборот должна быть лямбда
            if report_mode =="BA+Deming" or report_mode =="BA+Mountain+Deming":
                lam = 1/lambdas[m]
  
            x = data[b2].values 
            y = data[b1].values 
        
            st.markdown(f"## {b1} vs {b2}") 
        
            ba_res = bland_altman_analysis(x, y, mode=ba_mode) 
            pb_res = passing_bablok(x, y)
            dres = deming_regression(x, y, lambda_= lam)
            dres_ci = deming_bootstrap_ci(x,y,lambda_=lam) 
            c1, c2 = st.columns(2) 
            c21, c22 = st.columns(2)
            c31, c32 = st.columns(2)
            c41, c42 = st.columns(2)
            
                          
            #report_mode = st.sidebar.radio("Выбери вариант отчёта", ["BA+PB","BA+PB+residuals","BA+Mountain+PB+residuals","BA+Deming","BA+Mountain+Deming"])
            if report_mode == "BA+PB":
                with c1:
                    BA_show()
                    BA_table_show()
                    TE_show()
                    TE_sum_show(te_summary_data)
                    BA_sum(ba_summary_data)
                with c2:
                    PB_show()
                    PB_table_show()
                    PB_sum(pb_summary_data)
                    CUSUM_show()
                    corr_show()
                    corr_sum(cor_summary_data)

            if report_mode == "BA+PB+residuals (var1)":
                with c1:
                    BA_show()
                with c2:
                    st.write("")
                    st.write("")
                    st.write("")
                    st.write("")
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    TE_show()
                    TE_sum_show(te_summary_data)
                with c21:
                    PB_show()
                with c22:
                    PB_res_show()
                with c31:
                    PB_table_show()
                    PB_sum(pb_summary_data)
                    CUSUM_show()
                with c32:
                    corr_show()
                    corr_sum(cor_summary_data)
            
            if report_mode == "BA+PB+residuals (var2)":
                with c1:
                    BA_show()
                with c2:
                    PB_show()
                with c21:
                    BA_table_show()
                    TE_show()
                    TE_sum_show(te_summary_data)
                    BA_sum(ba_summary_data)
                with c22:
                    PB_res_show()
                with c31:
                    corr_show()
                    corr_sum(cor_summary_data)
                with c32:
                    PB_table_show()
                    PB_sum(pb_summary_data)
                    CUSUM_show()

            if report_mode == "BA+Mountain+PB+residuals":
                with c1:
                    BA_show()
                with c2:
                    mountain_show()
                with c21:
                    BA_table_show()
                    BA_sum(ba_summary_data)
                with c22:
                    TE_show()
                    TE_sum_show(te_summary_data)
                with c31:
                    PB_show()
                with c32:
                    PB_res_show()
                with c41:
                    PB_table_show()
                    PB_sum(pb_summary_data)
                    CUSUM_show()
                with c42:
                    corr_show()
                    corr_sum(cor_summary_data)
                   
            if report_mode == "BA+Deming":
                with c1:
                    BA_show()
                with c2:
                    st.write("")
                    st.write("")
                    st.write("")
                    st.write("")
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    TE_show()
                    TE_sum_show(te_summary_data)
                with c21:
                    Deming_show()
                    Deming_table_show(dres, dres_ci)
                    Deming_sum(dres, dres_ci, deming_summary_data)
                with c22:
                    Deming_res_show(dres)
                    corr_show()
                    corr_sum(cor_summary_data)
            
            if report_mode == "BA+Mountain+Deming":
                with c1:
                    BA_show()
                with c2:
                    mountain_show()
                with c21:
                    BA_table_show()
                    BA_sum(ba_summary_data)
                with c22:    
                    TE_show()
                    TE_sum_show(te_summary_data)
                with c31:
                    Deming_show()
                    Deming_table_show(dres, dres_ci)
                    Deming_sum(dres, dres_ci, deming_summary_data)
                with c32:
                    Deming_res_show(dres)
                    corr_show()
                    corr_sum(cor_summary_data)

            if report_mode == "BA(abs diff)+BA(relative diff)+PB+residuals":
                with c1:
                    BA_show()
                with c21:
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    #TE_show()
                    #TE_sum_show(te_summary_data)
                with c2:
                    ba_res = bland_altman_analysis(x, y, mode="Relative difference (%)")
                    BA_show()
                with c22:
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    #TE_show()
                    #TE_sum_show(te_summary_data)
                with c31:
                    PB_show()
                with c32:
                    PB_res_show()
                with c41:
                    PB_table_show()
                    PB_sum(pb_summary_data)
                    CUSUM_show()
                with c42:
                    corr_show()
                    corr_sum(cor_summary_data)

            



            


            st.subheader("================================================================")

        st.subheader("Summary data")
        st.markdown("**Bland-Altman analysis: summary table for methods**")
        st.dataframe(st.session_state["ba_summary_data"],hide_index=True)
        
        if report_mode in ["BA+PB","BA+PB+residuals (var1)","BA+PB+residuals (var2)","BA+Mountain+PB+residuals"]:
            st.markdown("**Total errors (TE). Summary table**")
            st.dataframe(st.session_state["te_summary_data"],hide_index=True)

        #if report_mode in ["BA+PB","BA+PB+residuals (var1)","BA+PB+residuals (var2)","BA+Mountain+PB+residuals"]:
        st.markdown("**Passing-Bablok regression: summary table for methods**")
        st.dataframe(st.session_state["pb_summary_data"],hide_index=True)
        
        if report_mode in ["BA+Deming","BA+Mountain+Deming"]:
            st.markdown("**Deming regression: summary table for methods**")
            st.dataframe(st.session_state["deming_summary_data"],hide_index=True)

        st.markdown("**Summary table for correlations**")
        st.dataframe(st.session_state["cor_summary_data"],hide_index=True)

else: 
    st.info("Загрузите excel-файл")
    st.info("Данные должны располагаться в столбцах и иметь заголовки. \
               Можно запустить анализ сразу нескольких методов.")
