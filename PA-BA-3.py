import streamlit as st 
import pandas as pd 
import numpy as np 
from scipy import stats 
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.optimize import curve_fit
from scipy.stats.mstats import hdquantiles
from sklearn.metrics import r2_score
#from tqdm import tqdm
from scipy.stats import t as student_t

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
 #   mean = (x + y) / 2 
 #   slovar = {'x': x, 'y': y, 'mean': mean}
 #   slovar_todf = pd.DataFrame(slovar)
 #   todf = slovar_todf.sort_values(by='mean')
    mean = (x + y) / 2 
    srt = np.argsort(mean)
    mean = mean[srt]
    xx = x[srt]
    yy = y[srt]
    if mode == "Absolute difference": 
        diff = yy - xx 
        ylabel = f'{b1} - {b2}'
        xlabel = 'Mean of methods' 
    elif mode == "Relative difference (%)": 
        diff = 100 * (yy - xx) / mean 
        ylabel = f"({b1} - {b2}) / Mean of methods (%)" 
        xlabel = 'Mean of methods'
    elif mode == "Relative difference": 
        diff = (yy - xx) / mean 
        ylabel = f"({b1} - {b2}) / Mean of methods"
        xlabel = 'Mean of methods' 
    elif mode == 'Rank (X+Y)/2 vs (X-Y)':
        
       # xx = todf['x']
       # yy = todf['y']
     
        diff = yy - xx
        ylabel = f'{b1} - {b2}'
        xlabel = 'Rank of mean of methods'
        mean = np.arange(1, len(x)+1, 1)
    elif mode == 'Rank (X+Y)/2 vs 100*(X-Y)/Mean':
        
    #    mm = mean
    #    xx = todf['x']
    #    yy = todf['y']
    #    mm = todf['mean']

        diff = 100 * (yy - xx) / mean 
        ylabel = f"({b1} - {b2}) / Mean of methods (%)"
        xlabel = 'Rank of mean of methods'
        mean = np.arange(1, len(x)+1, 1)
    elif mode == r'$ln(\sqrt{XY})\quad vs\quad ln(Y/X)$':
        mean = np.log(mean)
        #mean = np.log(np.sqrt(x*y))
        diff = np.log(yy/xx)
        xlabel = r'$ln(\sqrt{XY})$'
        ylabel = r'$ln(Y/X)$'    
#    elif mode == 'rolling BA, abs.':
#        rx = []
#        ry = []
#        okno = 40
#        for i in range(0,len(x)+1):
#            if i < okno:
#                srx = x[:okno]
    else: 
        raise ValueError("Unknown BA mode") 
    return mean, diff, ylabel, xlabel 

def bland_altman_analysis(x, y, alpha=0.05, mode="Absolute difference"): 
    mean, diff, ylabel, xlabel = bland_altman_prepare(x, y, mode)
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
            "xlabel": xlabel, 
            "md": md, "sd": sd, 
            "loa_upper": loa_upper, 
            "loa_lower": loa_lower, 
            "ci_md": ci_md, 
            "ci_upper": ci_upper, 
            "ci_lower": ci_lower, 
            "n": n, 
            "te": te, } 

# График Бланда-Альтмана
def plot_bland_altman(res, title, ba_check=False): 
    fig, ax = plt.subplots(figsize=(8, 6),dpi=200)
    ax.scatter(res["mean"], res["diff"], alpha=0.6) 
    ax.axhline(res["md"], color="black", linestyle="--" )      #, label="Mean diff") 
    ax.axhline(res["loa_upper"], color="red", linestyle="--")  #  , label="Upper LoA") 
    ax.axhline(res["loa_lower"], color="red", linestyle="--")  #, label="Lower LoA") 

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
    ax.set_xlabel(res["xlabel"]) 
    ax.set_ylabel(res["ylabel"]) 
    ax.grid(True, alpha=0.3) 

    # Добавлении линии регрессии в БА
    if ba_check:
        perdict = {'mean': res['mean'], 'diff': res['diff']}
        resdf = pd.DataFrame(perdict)
        X = sm.add_constant(resdf["mean"])          
        model_diff = sm.OLS(resdf['diff'], X).fit()
        ba0, ba1 = model_diff.params
        resdf['diff_pred'] = model_diff.predict(X)
        resdf_sorted = resdf.sort_values(by='mean')
        minus = "\u2212"
        sign = "+" if ba0>=0 else minus
        reg_line = f'y = {ba1:4.2f}x {sign} {abs(ba0):4.2f}'
        ax.plot(resdf_sorted['mean'], resdf_sorted['diff_pred'], color='brown', ls= '--',  label = reg_line)
        ax.legend() 

    #    resdf['resid'] = resdf['diff'] - model_diff.predict(X)
    #    resdf['abs_resid'] = np.abs(resdf['resid'])

    #    model_resid = sm.OLS(resdf['abs_resid'], X).fit()
    #    c0, c1 = model_resid.params
    #    factor = np.sqrt(np.pi / 2)            
    #    resdf['sd_pred'] = factor * model_resid.predict(X)

    #    resdf['loa_upper_reg'] = resdf['diff_pred'] + 1.96 * resdf['sd_pred']
    #    resdf['loa_lower_reg'] = resdf['diff_pred'] - 1.96 * resdf['sd_pred']

    #    resdf_sorted = resdf.sort_values(by='mean')
    #    ax.plot(resdf_sorted['mean'], resdf_sorted['diff_pred'], color='brown', label='Среднее смещение (регрессия)')
    #    ax.plot(resdf_sorted['mean'], resdf_sorted['loa_upper_reg'], color='purple', ls='--', lw=1.5, label='Верхний LoA (регр.)')
    #    ax.plot(resdf_sorted['mean'], resdf_sorted['loa_lower_reg'], color='purple', ls='--', lw=1.5, label='Нижний LoA (регр.)')
    
    return fig 

# Выбор регрессионной модели для BA
def ba_prepare_reg(x, y, ba_regression = 'Without regression'): 
    x = np.asarray(x, dtype=float) 
    y = np.asarray(y, dtype=float)
    mean = (x + y) / 2 
    srt = np.argsort(mean)
    mean = mean[srt]
    x = x[srt]
    y = y[srt]
    if ba_regression == "Regression for absolute difference": 
        diff = y - x 
        ylabel = f'{b1} - {b2}'
        xlabel = 'Mean of methods' 
    elif ba_regression == 'Regression for relative difference (%)': 
        diff = 100 * (y - x) / mean 
        ylabel = f"({b1} - {b2}) / Mean of methods (%)" 
        xlabel = 'Mean of methods'
    elif ba_regression == 'Regression in log-scale':
        mean = np.log(mean)
        diff = np.log(y/x)
        xlabel = r'$ln(\sqrt{XY})$'
        ylabel = r'$ln(Y/X)$'    
    elif ba_regression == 'Without regression':
        pass
    else: 
        raise ValueError("Unknown BA mode") 
    return mean, diff, ylabel, xlabel 

# Скользящие квантили (метод скользящего окна для BA)
def sliding_quantile_ba(avg, diff, window_size=21, q_low=0.025, q_high=0.975, min_fraction=0.85):
    n = len(avg)
    half = window_size // 2
    min_points = int(window_size * min_fraction)
    
    # Считаем только полноценные окна
    centers = []
    medians = []
    lowers = []
    uppers = []
    
    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        
        if (end - start) < min_points:
            continue
            
        w = diff[start:end]
        qs = hdquantiles(w, prob=[0.5, q_low, q_high])
        
        centers.append(np.mean(avg[start:end]))
        medians.append(float(qs[0]))
        lowers.append(float(qs[1]))
        uppers.append(float(qs[2]))
    
    centers = np.array(centers)
    medians = np.array(medians)
    lowers  = np.array(lowers)
    uppers  = np.array(uppers)
    
    if len(centers) == 0:
        raise ValueError("Не удалось сформировать ни одного полноценного окна. Уменьшите window_size.")
    
    # Горизонтальное продление на краях
    avg_min = avg.min()
    avg_max = avg.max()
    
    # Левый край
    left_center = np.array([avg_min, centers[0]])
    left_med    = np.array([medians[0], medians[0]])
    left_lo     = np.array([lowers[0], lowers[0]])
    left_up     = np.array([uppers[0], uppers[0]])
    
    # Правый край
    right_center = np.array([centers[-1], avg_max])
    right_med    = np.array([medians[-1], medians[-1]])
    right_lo     = np.array([lowers[-1], lowers[-1]])
    right_up     = np.array([uppers[-1], uppers[-1]])
    
    # Объединяем
    full_center = np.concatenate([left_center, centers, right_center])
    full_med    = np.concatenate([left_med, medians, right_med])
    full_lo     = np.concatenate([left_lo, lowers, right_lo])
    full_up     = np.concatenate([left_up, uppers, right_up])
    
    # Убираем возможные дубликаты на стыках
    _, unique_idx = np.unique(full_center, return_index=True)
    unique_idx = np.sort(unique_idx)
    
    return (full_center[unique_idx],
            full_med[unique_idx],
            full_lo[unique_idx],
            full_up[unique_idx])


def ba_reg_anal(x, y, WINDOW, mode="Absolute difference"): 
    mean, diff, ylabel, xlabel = bland_altman_prepare(x, y, mode)
    #mean, diff, ylabel, xlabel = ba_prepare_reg(x, y, ba_regression)
    n = len(diff) 
    #WINDOW = 51
    FRAC = 0.32

    center, med, lo, up = sliding_quantile_ba(mean, diff, WINDOW)

    smooth_med = lowess(med, center, frac=FRAC, return_sorted=False)
    smooth_lo  = lowess(lo,  center, frac=FRAC, return_sorted=False)
    smooth_up  = lowess(up,  center, frac=FRAC, return_sorted=False)

    def linear(x, a, b):
        return a + b * x

    def lin_hyp(x, a, b, c):
        """a + b*x + c/x"""
        return a + b * x + c / x

    def hyperbola(x, a, b, c):
        """a + b / (x + c)"""
        return a + b / (x + c)

    def lin_log(x, a, b, c):
        """a + b*x + c*ln(x)"""
        return a + b * x + c * np.log(x)

    def hyp_log(x, a, b, c):
        """a + b/x + c*ln(x)"""
        return a + b / x + c * np.log(x)

    def lin_sqrt(x, a, b, c):
        """a + b*x + c*sqrt(x)"""
        return a + b * x + c * np.sqrt(x)

    def rational(x, a, b, c):
        """a + b*x / (x + c)"""
        return a + b * x / (x + c)

    models = {
        'Линейная':               (linear,    [0.0, 0.0],           (-np.inf, np.inf)),
        'a + bx + c/x':           (lin_hyp,   [0.0, 0.0, 10.0],     (-np.inf, np.inf)),
        'Гипербола a+b/(x+c)':    (hyperbola, [0.0, 20.0, 15.0],    ([-np.inf, -np.inf, 1.0], [np.inf, np.inf, np.inf])),
        'a + bx + c·ln(x)':       (lin_log,   [0.0, 0.0, 0.0],      (-np.inf, np.inf)),
        'a + b/x + c·ln(x)':      (hyp_log,   [0.0, 20.0, 0.0],     (-np.inf, np.inf)),
        'a + bx + c·√x':          (lin_sqrt,  [0.0, 0.0, 0.0],      (-np.inf, np.inf)),
        'Рациональная a+bx/(x+c)':(rational,  [0.0, 1.0, 20.0],     ([-np.inf, -np.inf, 1.0], [np.inf, np.inf, np.inf])),}




    return { "mean": mean, 
            "diff": diff, 
            "ylabel": ylabel,
            "xlabel": xlabel,
            "center": center, 
            "smooth_med": smooth_med, 
            "smooth_lo": smooth_lo,
            "smooth_up": smooth_up, }
#            "bias_ci_lo": bias_ci_lo, 
#            "bias_ci_hi": bias_ci_hi, 
#            "lo_ci_lo": lo_ci_lo, 
#            "lo_ci_hi": lo_ci_hi, 
#            "up_ci_lo": up_ci_lo, 
#            "up_ci_hi": up_ci_hi, 
#            "bias_fit": bias_fit, 
#            "lo_fit": lo_fit,
#            "up_fit": up_fit,
#            "n": n,   
#            "Bias(A)": format_eq(bias_name, bias_params),
#            "Lower(A)": format_eq(lo_name, lo_params),
#            "Upper(A)": format_eq(up_name, up_params),} 

# BA regрессия
def ba_reg_plot(ba_reg_res):
    fig, ax = plt.subplots(figsize=(8, 6),dpi=200)
    mean = ba_reg_res["mean"]
    diff = ba_reg_res['diff']
    ylabel = ba_reg_res["ylabel"]
    xlabel = ba_reg_res["xlabel"] 
    center = ba_reg_res["center"]  
    smooth_med = ba_reg_res["smooth_med"] 
    smooth_lo = ba_reg_res["smooth_lo"] 
    smooth_up  = ba_reg_res["smooth_up"] 
#    bias_ci_lo  = ba_reg_res["bias_ci_lo"] 
#    bias_ci_hi  = ba_reg_res["bias_ci_hi"]
#    lo_ci_lo = ba_reg_res["lo_ci_lo"] 
#    lo_ci_hi  = ba_reg_res["lo_ci_hi"] 
 #   up_ci_lo  = ba_reg_res["up_ci_lo"] 
 #   up_ci_hi = ba_reg_res["up_ci_hi"] 
 #   bias_fit  = ba_reg_res["bias_fit"] 
#    lo_fit = ba_reg_res["lo_fit"]
 #   up_fit = ba_reg_res["up_fit"]
#    n = ba_reg_res["n"]
 #   eq_bias = ba_reg_res["Bias(A)"] 
#    eq_loa = ba_reg_res["Lower(A)"]
#    eq_up =  ba_reg_res["Upper(A)"] 
    A_grid = np.linspace(mean.min() , mean.max(), 160)

    ax.scatter(mean, diff, alpha=0.5, color='steelblue', zorder=1)  #alpha=0.32, s=16,

    # Lowess (непараметрика)
    ax.plot(center, smooth_med, color='orange', lw=2.2, alpha=0.85, label='Lowess Bias')
    ax.plot(center, smooth_lo,  color='r',  lw=1.8, ls='--', alpha=0.75, label='Lowess LoA')
    ax.plot(center, smooth_up,  color='r',    lw=1.8, ls='--', alpha=0.75)

    # Параметрические модели + CI
#    ax.fill_between(A_grid, bias_ci_lo, bias_ci_hi, color='darkorange', alpha=0.20, label='95% CI смещения')
#    ax.fill_between(A_grid, lo_ci_lo, lo_ci_hi, color='darkgreen', alpha=0.18, label='95% CI нижнего LoA')
#    ax.fill_between(A_grid, up_ci_lo, up_ci_hi, color='darkred', alpha=0.18, label='95% CI верхнего LoA')

#    ax.plot(A_grid, bias_fit, color='darkorange', lw=2.8, label = eq_bias)
#    ax.plot(A_grid, lo_fit,   color='darkgreen',  lw=2.5, label= eq_loa)
#    ax.plot(A_grid, up_fit,   color='darkred',    lw=2.5, label= eq_up)

    ax.axhline(0, color='gray', lw=0.8)
    ax.set_xlabel(xlabel = xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title('Скользящие квантили + Lowess')
    ax.legend(loc='best', fontsize=8.5)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(diff.min()*1.2, diff.max()*1.2)

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

    sign_L = "+" if a_L>=0 else minus
    sign_U = "+" if a_U>=0 else minus
    
    yL = res["intercept_ci"][0] + res["slope_ci"][0] * xx 
    yU = res["intercept_ci"][1] + res["slope_ci"][1] * xx 
    ax.plot(xx, yL, c="gray", alpha=0.5,label = f'Lower CI: {b_L:4.2f}x {sign_L} {abs(a_L):4.2f}') 
    ax.plot(xx, yU, c="gray", alpha=0.5,label=f'Upper CI: {b_U:4.2f}x {sign_U} {abs(a_U):4.2f}') 
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

    sign_L = "+" if a_L>=0 else minus
    sign_U = "+" if a_U>=0 else minus        
    
    yL = dres_ci["intercept_ci"][0] + dres_ci["slope_ci"][0] * xx 
    yU = dres_ci["intercept_ci"][1] + dres_ci["slope_ci"][1] * xx 
    ax.plot(xx, yL, c="gray", alpha=0.5,label = f'Lower CI: {b_L:4.2f}x {sign_L} {abs(a_L):4.2f}') 
    ax.plot(xx, yU, c="gray", alpha=0.5,label=f'Upper CI: {b_U:4.2f}x {sign_U} {abs(a_U):4.2f}') 
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
                                                      "Relative difference",
                                                      'Rank (X+Y)/2 vs (X-Y)',
                                                      'Rank (X+Y)/2 vs 100*(X-Y)/Mean',
                                                      r'$ln(\sqrt{XY})\quad vs\quad ln(Y/X)$'])
    ba_check = st.sidebar.checkbox('Добавить линию регрессии на график БА', value=False)
#    ba_regression = st.sidebar.radio('Bland-Altman regression model', ['Without regression', 
#                                                                       'Regression for absolute difference',
#                                                                       'Regression for relative difference (%)',
 #                                                                      'Regression in log-scale'])
    advanced_ba = st.sidebar.checkbox('Добавить исследовательский график БА (Локальный БА в скользящем окне + lowess)', value=False)
    if advanced_ba:
        okno = st.sidebar.number_input('Размер окна', min_value=21, max_value=61, value=41,step=1)
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
            st.pyplot(plot_bland_altman(ba_res, f"{b1} vs {b2}   (n = {len(x)})", ba_check)) 
            
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

        def BA_reg_show(ba_mode):
            st.subheader("Bland–Altman: moving window + lowess") 
            baregres = ba_reg_anal(x, y, okno, ba_mode) 
            st.pyplot(ba_reg_plot(baregres))
        
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
            #c_reg, c_reg2 = st.columns(2)
            c21, c22 = st.columns(2)
            c_reg, c_reg2 = st.columns(2)
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
                with c_reg:
                    if advanced_ba:
                        BA_reg_show(ba_mode)
                    else:
                        pass
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
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    TE_show()
                    TE_sum_show(te_summary_data)
                with c2:
                    if advanced_ba:
                        BA_reg_show(ba_mode)
                    else:
                        pass
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
                with c_reg:
                    if advanced_ba:
                        BA_reg_show(ba_mode)
                    else:
                        pass
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
                    if advanced_ba:
                        BA_reg_show(ba_mode)
                    else:
                        pass
                with c_reg:
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
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    TE_show()
                    TE_sum_show(te_summary_data)
                with c2:
                    if advanced_ba:
                        BA_reg_show(ba_mode)
                    else:
                        pass
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
                    if advanced_ba:
                        BA_reg_show(ba_mode)
                    else:
                        pass
                with c_reg:
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
                    ba_res = bland_altman_analysis(x, y, mode='Absolute difference')
                    BA_show()
                with c_reg:
                    if advanced_ba:
                        BA_reg_show(ba_mode='Absolute difference')
                    else:
                        pass
                with c21:
                    BA_table_show()
                    BA_sum(ba_summary_data)
                    #TE_show()
                    #TE_sum_show(te_summary_data)
                with c2:
                    ba_res = bland_altman_analysis(x, y, mode="Relative difference (%)")
                    BA_show()
                with c_reg2:
                    if advanced_ba:
                        BA_reg_show(ba_mode="Relative difference (%)")
                    else:
                        pass
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
    st.image('blindaltmanpassingbablok.jpg')