import streamlit as st 
import pandas as pd 
import numpy as np 
from scipy import stats 
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

#=============================
#Utilities
#=============================
def compute_total_error(mean_diff, sd, z=1.65): 
    return abs(mean_diff) + z * sd
# Common lab definition: TE = |bias| + z * SD (z=1.65 ~ 95% one-sided) 
#=============================
#Bland–Altman
#=============================
def bland_altman_prepare(x, y, mode="absolute"): 
    x = np.asarray(x, dtype=float) 
    y = np.asarray(y, dtype=float)
    mean = (x + y) / 2 
    if mode == "absolute": 
        diff = x - y 
        ylabel = "Difference" 
    elif mode == "percent": 
        diff = 100 * (x - y) / mean 
        ylabel = "Difference (%)" 
    elif mode == "relative": 
        diff = (x - y) / mean 
        ylabel = "Relative difference" 
    else: 
        raise ValueError("Unknown BA mode") 
    return mean, diff, ylabel 

def bland_altman_analysis(x, y, alpha=0.05, mode="absolute"): 
    mean, diff, ylabel = bland_altman_prepare(x, y, mode)
    n = len(diff) 
    md = np.mean(diff) 
    sd = np.std(diff, ddof=1) 
    loa_upper = md + 1.96 * sd 
    loa_lower = md - 1.96 * sd 
    # t-quantile 
    tval = stats.t.ppf(1 - alpha / 2, df=n - 1) 
    se_md = sd / np.sqrt(n) 
    ci_md = (md - tval * se_md, md + tval * se_md) 
    # Strict SE for LoA (Bland–Altman 1999) 
    se_loa = sd * np.sqrt(1 / n + (1.96 ** 2) / (2 * (n - 1))) 
    ci_upper = (loa_upper - tval * se_loa, loa_upper + tval * se_loa) 
    ci_lower = (loa_lower - tval * se_loa, loa_lower + tval * se_loa) 
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

def plot_bland_altman(res, title): 
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(res["mean"], res["diff"], alpha=0.6) 
    ax.axhline(res["md"], color="black", linestyle="--", label="Mean diff") 
    ax.axhline(res["loa_upper"], color="red", linestyle="--", label="Upper LoA") 
    ax.axhline(res["loa_lower"], color="red", linestyle="--", label="Lower LoA") 

    xmin, xmax = np.min(res["mean"]), np.max(res["mean"]) 

    
    ax.fill_between([xmin, xmax], res["ci_upper"][0], res["ci_upper"][1], color="red", alpha=0.15) 
    ax.fill_between([xmin, xmax], res["ci_lower"][0], res["ci_lower"][1], color="red", alpha=0.15) 
    ax.fill_between([xmin, xmax], res["ci_md"][0], res["ci_md"][1], color="gray", alpha=0.2) 

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
    ax.legend() 
    
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
            
    # CUSUM linearity test (approximate) 
    residuals = y - (a + b * x) 
    cusum =np.cumsum(residuals) 
    cusum_stat = np.max(np.abs(cusum)) 
    cusum_p = np.exp(-2 * cusum_stat ** 2 / np.sum(residuals ** 2)) if np.sum(residuals ** 2) > 0 else np.nan 
        
    return { 
        "slope": b, 
        "intercept": a, 
        "slope_ci": (b_L, b_U), 
        "intercept_ci": (a_L, a_U), 
        "pearson": (pearson_r, pearson_p), 
        "spearman": (spearman_r, spearman_p), 
        "cusum_p": cusum_p, } 
    
def plot_passing_bablok(x, y, res, title, from_zero=False): 
    fig, ax = plt.subplots(figsize=(8, 6))
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
    ax.plot(xx, yy, label="Passing–Bablok") 
    
    yL = res["intercept_ci"][0] + res["slope_ci"][0] * xx 
    yU = res["intercept_ci"][1] + res["slope_ci"][1] * xx 
    ax.plot(xx, yL, c="gray", alpha=0.5) 
    ax.plot(xx, yU, c="gray", alpha=0.5) 
    ax.fill_between(xx, yL, yU, color="gray", alpha=0.2, label="95% CI") 
    ax.plot(xx, xx, c="black", ls="--", alpha=0.5, label="y = x") 
    ax.set_title(title) 
    ax.set_xlabel("Method X") 
    ax.set_ylabel("Method Y") 
    ax.grid(True, alpha=0.3) 
    ax.legend() 
    
    return fig 
#=============================
#UI
#=============================
st.title("Method comparison: Bland–Altman & Passing–Bablok (extended)")
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

if uploaded_file: 
    df = pd.read_excel(uploaded_file) 
    st.dataframe(df.head())
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist() 

    if "pairs" not in st.session_state: st.session_state.pairs = [(numeric_cols[0], numeric_cols[1])] if len(numeric_cols) >= 2 else [] 

    st.sidebar.header("Method pairs") 

    new_pairs = [] 

    for i, (c1, c2) in enumerate(st.session_state.pairs): 
        col1, col2 = st.sidebar.columns(2) 
        a = col1.selectbox(f"Method A #{i+1}", numeric_cols, index=numeric_cols.index(c1)) 
        b = col2.selectbox(f"Method B #{i+1}", numeric_cols, index=numeric_cols.index(c2)) 
        new_pairs.append((a, b)) 
    
    st.session_state.pairs = new_pairs 

    if st.sidebar.button("+ Add pair"): 
        if len(numeric_cols) >= 2: 
            st.session_state.pairs.append((numeric_cols[0], numeric_cols[1])) 
        
    ba_mode = st.sidebar.selectbox("Bland–Altman mode", ["absolute", "percent", "relative"]) 
    pb_zero = st.sidebar.checkbox("PB axis from zero", value=False) 

    if st.sidebar.button("Run analysis"): 
        for (b1, b2) in st.session_state.pairs: 
            data = df[[b1, b2]].dropna() 
            x = data[b2].values 
            y = data[b1].values 
        
            st.markdown(f"## {b1} vs {b2}") 
        
            ba_res = bland_altman_analysis(x, y, mode=ba_mode) 
            pb_res = passing_bablok(x, y) 
            c1, c2 = st.columns(2) 
        
            with c1: 
                st.subheader("Bland–Altman") 
                st.pyplot(plot_bland_altman(ba_res, f"{b1} vs {b2}")) 
            
                ba_table = pd.DataFrame({ 
                    "Metric": ["Mean diff", "LoA lower", "LoA upper", "Total Error"], 
                    "Value": [ba_res["md"], ba_res["loa_lower"], ba_res["loa_upper"], ba_res["te"]], 
                    "CI lower": [ba_res["ci_md"][0], ba_res["ci_lower"][0], ba_res["ci_upper"][0], np.nan], 
                    "CI upper": [ba_res["ci_md"][1], ba_res["ci_lower"][1], ba_res["ci_upper"][1], np.nan], }) 
            
                st.dataframe(ba_table, hide_index=True) 
            
            with c2: 
                st.subheader("Passing–Bablok") 
                st.pyplot(plot_passing_bablok(x, y, pb_res, f"{b1} vs {b2}", from_zero=pb_zero)) 
            
                pb_table = pd.DataFrame({ 
                    "Metric": ["Slope", "Intercept", "Pearson r", "Spearman r", "CUSUM p"], 
                    "Value": [pb_res["slope"], pb_res["intercept"], pb_res["pearson"][0], pb_res["spearman"][0], pb_res["cusum_p"]], 
                    "CI lower": [pb_res["slope_ci"][0], pb_res["intercept_ci"][0], np.nan, np.nan, np.nan], 
                    "CI upper": [pb_res["slope_ci"][1], pb_res["intercept_ci"][1], np.nan, np.nan, np.nan], }) 
            
                st.dataframe(pb_table, hide_index=True) 
else: 
    st.info("Upload Excel file to start")
