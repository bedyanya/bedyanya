import streamlit as st
import pandas as pd
import numpy as np
from sklearn.utils import resample
from sklearn.metrics import auc
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint
from scipy.stats import chi2
import seaborn as sns

st.set_page_config(layout="wide")

st.title("Диагностическое согласие методов. 👻")

uploaded_file = st.sidebar.file_uploader("Загрузите Excel", type=["xlsx", "xls"])

st.sidebar.write("⎛⎝ ≽ > ⩊ < ≼ ⎠⎞")

minus = "\u2212"

# =====================================================================
# ФУНКЦИИ
# =====================================================================

def prepare_pair(df, aa, bb, p1, p2):
    dfs = df[[aa, bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs["m1_bin"] = np.where(dfs[aa] >= p1, 1, 0)
    dfs["m2_bin"] = np.where(dfs[bb] >= p2, 1, 0)
    a = np.sum((dfs["m1_bin"] == 0) & (dfs["m2_bin"] == 0))
    b = np.sum((dfs["m1_bin"] == 0) & (dfs["m2_bin"] == 1))
    c = np.sum((dfs["m1_bin"] == 1) & (dfs["m2_bin"] == 0))
    d = np.sum((dfs["m1_bin"] == 1) & (dfs["m2_bin"] == 1))
    return a, b, c, d, dfs


def compute_kappa(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return np.nan
    Po = (a + d) / n
    Pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n ** 2
    if (1 - Pe) == 0:
        return np.nan
    return (Po - Pe) / (1 - Pe)


def bootstrap_kappa(dfs, B=2000):
    boot = []
    for _ in range(B):
        sample = resample(dfs, replace=True)
        a = np.sum((sample["m1_bin"] == 0) & (sample["m2_bin"] == 0))
        b = np.sum((sample["m1_bin"] == 0) & (sample["m2_bin"] == 1))
        c = np.sum((sample["m1_bin"] == 1) & (sample["m2_bin"] == 0))
        d = np.sum((sample["m1_bin"] == 1) & (sample["m2_bin"] == 1))
        k = compute_kappa(a, b, c, d)
        if not np.isnan(k):
            boot.append(k)
    if len(boot) < 10:
        return np.nan, np.nan
    return np.percentile(boot, [2.5, 97.5])


def compute_ppa_npa(a, b, c, d):
    PPA = round(100 * d / (d + b), 2) if (d + b) > 0 else np.nan
    NPA = round(100 * a / (a + c), 2) if (a + c) > 0 else np.nan
    return PPA, NPA


def ci_binomial(x, n, alpha=0.05, method="wilson"):
    return proportion_confint(x, n, alpha=alpha, method=method)


def pabak(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return np.nan
    return 2 * (a + d) / n - 1


def pabak_ci_funk(a, b, c, d):
    Po_ci = ci_binomial(a + d, a + b + c + d)
    return 2 * Po_ci[0] - 1, 2 * Po_ci[1] - 1


def mcnemar_result(a, b, c, d):
    mc_res = mcnemar([[a, b], [c, d]], exact=True)
    answer = "Методы систематически отличаются" if mc_res.pvalue < 0.05 else "Нет систематического различия"
    return answer, mc_res.pvalue


def gwet_ac1(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return np.nan
    Po = (a + d) / n
    p = ((a + b) / n + (a + c) / n) / 2
    Pe = 2 * p * (1 - p)
    if (1 - Pe) == 0:
        return np.nan
    return (Po - Pe) / (1 - Pe)


def bootstrap_ac1(dfs, B=2000):
    boot = []
    for _ in range(B):
        sample = resample(dfs, replace=True)
        a = np.sum((sample["m1_bin"] == 0) & (sample["m2_bin"] == 0))
        b = np.sum((sample["m1_bin"] == 0) & (sample["m2_bin"] == 1))
        c = np.sum((sample["m1_bin"] == 1) & (sample["m2_bin"] == 0))
        d = np.sum((sample["m1_bin"] == 1) & (sample["m2_bin"] == 1))
        ac1 = gwet_ac1(a, b, c, d)
        if not np.isnan(ac1):
            boot.append(ac1)
    if len(boot) < 10:
        return np.nan, np.nan
    return np.percentile(boot, [2.5, 97.5])


def bootstrap_npa_ppa(dfs, B=2000):
    ppa_boot, npa_boot = [], []
    for _ in range(B):
        sample = resample(dfs, replace=True)
        a = np.sum((sample["m1_bin"] == 0) & (sample["m2_bin"] == 0))
        b = np.sum((sample["m1_bin"] == 0) & (sample["m2_bin"] == 1))
        c = np.sum((sample["m1_bin"] == 1) & (sample["m2_bin"] == 0))
        d = np.sum((sample["m1_bin"] == 1) & (sample["m2_bin"] == 1))
        PPA, NPA = compute_ppa_npa(a, b, c, d)
        ppa_boot.append(PPA)
        npa_boot.append(NPA)
    return np.percentile(ppa_boot, [2.5, 97.5]), np.percentile(npa_boot, [2.5, 97.5])


def plot_scatter_with_cutoff(dfs, aa, bb, p1, p2):
    x = dfs[aa].replace(0, 0.0001)
    y = dfs[bb]
    m1_bin = x >= p1
    m2_bin = y >= p2
    concordant = m1_bin == m2_bin
    fig, ax = plt.subplots()
    ax.scatter(x[concordant], y[concordant], alpha=0.6, label="Согласны")
    ax.scatter(x[~concordant], y[~concordant], alpha=0.6, label="Не согласны")
    ax.axvline(p1, ls="--", color="black", label="cut-off A", alpha=0.6)
    ax.axhline(p2, color="black", label="cut-off B", alpha=0.8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(f"Метод А ({aa})")
    ax.set_ylabel(f"Метод B ({bb})")
    ax.set_title("Диаграмма рассеяния (логарифмическая шкала)")
    ax.legend()
    return fig


def plot_confusion_matrix(a, b, c, d):
    matrix = np.array([[a, b], [c, d]])
    fig, ax = plt.subplots()
    cmap = plt.cm.PuBuGn
    colors = cmap(np.linspace(0, 1, 256))
    colors[:, :3] = colors[:, :3] ** 0.4
    new_cmap = mcolors.ListedColormap(colors)
    im = ax.imshow(matrix, cmap=new_cmap)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, matrix[i, j], ha="center", va="center")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticks(np.arange(-0.5, 2, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 2, 1), minor=True)
    ax.grid(color="black", which="minor")
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.set_yticklabels([f"Метод A {minus}", "Метод A +"])
    ax.set_xticklabels([f"Метод B {minus}", "Метод B +"])
    ax.set_title("Таблица сопряженности 2x2")
    fig.colorbar(im)
    return fig


def plot_agreement_bar(a, b, c, d):
    labels = [f"A{minus}B{minus}", f"A{minus}B+", f"A+B{minus}", "A+B+"]
    fig, ax = plt.subplots()
    ax.bar(labels, [a, b, c, d])
    ax.set_title("Структура сопряженности")
    ax.set_ylabel("Количество")
    return fig


def ppa_npa_curve(dfs, aa, bb, p2, df):
    ppa_list, npa_list, pr_list = [], [], []
    for i in sorted(dfs[aa].unique()):
        a, b, c, d, _ = prepare_pair(df, aa, bb, i, p2)
        npa = 100 * a / (a + c) if (a + c) > 0 else np.nan
        ppa = 100 * d / (d + b) if (d + b) > 0 else np.nan
        precision = 100 * d / (d + c) if (d + c) > 0 else np.nan
        ppa_list.append(ppa)
        npa_list.append(npa)
        pr_list.append(precision)
    return np.array(ppa_list), np.array(npa_list), np.array(pr_list)


def plot_ppa_npa(ppa_list, npa_list):
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    order = np.argsort(npa_list)[::-1]
    npa_s, ppa_s = npa_list[order], ppa_list[order]
    mask = ~(np.isnan(npa_s) | np.isnan(ppa_s))
    npa_s, ppa_s = npa_s[mask], ppa_s[mask]
    auc_val = np.nan
    if len(npa_s) > 1:
        auc_val = auc(npa_s / 100.0, ppa_s / 100.0)
        ax.plot(npa_s, ppa_s, "b-", lw=2, label="Кривая согласия")
        ax.fill_between(npa_s, ppa_s, alpha=0.15)
        ax.text(0.05, 0.15, f"AUC = {auc_val:.3f}", transform=ax.transAxes,
                fontsize=12, bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    ax.set_xlabel("NPA (%)")
    ax.set_ylabel("PPA (%)")
    ax.invert_xaxis()
    ax.set_xlim(105, 0)
    ax.set_ylim(0, 105)
    ax.set_title("Кривая согласия (PPA vs NPA)")
    ax.plot([0, 100], [100, 0], "--", color="gray", alpha=0.5)
    ax.legend(loc="lower left")
    ax.grid(True, alpha=0.3)
    return fig, auc_val


def plot_pr_curve(ppa_list, pr_list):
    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    order = np.argsort(ppa_list)
    ppa_s, pr_s = ppa_list[order], pr_list[order]
    mask = ~(np.isnan(ppa_s) | np.isnan(pr_s))
    ppa_s, pr_s = ppa_s[mask], pr_s[mask]
    auc_val = np.nan
    if len(ppa_s) > 1:
        auc_val = auc(ppa_s / 100.0, pr_s / 100.0)
        ax.plot(ppa_s, pr_s, "g-", lw=2, label="PR-кривая")
        ax.fill_between(ppa_s, pr_s, alpha=0.15, color="green")
        ax.text(0.05, 0.15, f"AUC-PR = {auc_val:.3f}", transform=ax.transAxes,
                fontsize=12, bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8))
    ax.set_xlabel("PPA / Recall (%)")
    ax.set_ylabel("Precision (%)")
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)
    ax.set_title("Precision-Recall относительно референсного метода")
    ax.legend(loc="lower left")
    ax.grid(True, alpha=0.3)
    return fig, auc_val


# -------------------- серая зона --------------------

def prepare_pair2(df, aa, bb):
    dfs = df[[aa, bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    return dfs[aa], dfs[bb]


def gray_zone_from_cv(cutoff, cv, z=1.96):
    sigma = cv * cutoff / 100
    delta = z * sigma
    return cutoff - delta, cutoff + delta


def categorize(x, c_low, c_high):
    return np.where(x < c_low, 0, np.where(x > c_high, 2, 1))


def build_3x3_table(x1, x2, c1_low, c1_high, c2_low, c2_high):
    y1 = categorize(x1, c1_low, c1_high)
    y2 = categorize(x2, c2_low, c2_high)
    a = np.sum((y1 == 0) & (y2 == 0))
    b = np.sum((y1 == 0) & (y2 == 1))
    c = np.sum((y1 == 0) & (y2 == 2))
    d = np.sum((y1 == 1) & (y2 == 0))
    e = np.sum((y1 == 1) & (y2 == 1))
    f = np.sum((y1 == 1) & (y2 == 2))
    g = np.sum((y1 == 2) & (y2 == 0))
    h = np.sum((y1 == 2) & (y2 == 1))
    i = np.sum((y1 == 2) & (y2 == 2))
    table = np.array([[a, b, c], [d, e, f], [g, h, i]])
    return table, a, b, c, d, e, f, g, h, i


def make_weights(k=3, scheme="Линейные весы"):
    W = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if k == 1:
                W[i, j] = 1.0
            elif scheme == "Линейные весы":
                W[i, j] = 1 - abs(i - j) / (k - 1)
            else:
                W[i, j] = 1 - ((i - j) / (k - 1)) ** 2
    return W


def weighted_kappa(table, W):
    table = np.asarray(table, dtype=float)
    N = table.sum()
    if N == 0:
        return np.nan
    P = table / N
    Po = np.sum(W * P)
    Pe = np.sum(W * np.outer(P.sum(1), P.sum(0)))
    if np.isclose(1 - Pe, 0):
        return np.nan
    return (Po - Pe) / (1 - Pe)


def gwet_ac2(table, W):
    table = np.asarray(table, dtype=float)
    N = table.sum()
    if N == 0:
        return np.nan
    P = table / N
    Po = np.sum(W * P)
    pi = (table.sum(1) + table.sum(0)) / (2 * N)
    Pe = np.sum(pi * (1 - pi))
    if np.isclose(Pe, 1):
        return 1.0 if np.isclose(Po, 1) else np.nan
    return (Po - Pe) / (1 - Pe)


def bootstrap_ci_kxk(df, aa, bb, func, W, cuts1, cuts2, n_boot=2000):
    dfs = df[[aa, bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    stats = []
    for _ in range(n_boot):
        dfboot = resample(dfs, replace=True)
        t = build_kxk_table(dfboot[aa].values, dfboot[bb].values, cuts1, cuts2)
        val = func(t, W)
        if not np.isnan(val):
            stats.append(val)
    if len(stats) < 10:
        return np.nan, np.nan
    return np.round(np.percentile(stats, [2.5, 97.5]), 4)


def bowker_test(table):
    table = np.asarray(table)
    k = table.shape[0]
    B = 0.0
    for i in range(k):
        for j in range(i + 1, k):
            nij, nji = table[i, j], table[j, i]
            if nij + nji > 0:
                B += (nij - nji) ** 2 / (nij + nji)
    df = k * (k - 1) / 2
    p = 1 - chi2.cdf(B, df)
    interp = "Методы систематически отличаются" if p < 0.05 else "Нет систематического отличия"
    if p < 0.0001:
        p = "<0.0001"
    return B, p, interp


def plot_3x3_agreement(table, aa, bb):
    fig, ax = plt.subplots(figsize=(8, 8), dpi=200)
    cmap = plt.cm.PuBuGn
    colors = cmap(np.linspace(0, 1, 256))
    colors[:, :3] = colors[:, :3] ** 0.4
    new_cmap = mcolors.ListedColormap(colors)
    im = ax.imshow(table, cmap=new_cmap)
    labels = [f"{minus}", "СЗ", "+"]
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
    ax.grid(color="black", which="minor")
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Метод B ({bb})")
    ax.set_ylabel(f"Метод A ({aa})")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, int(table[i, j]), ha="center", va="center")
    ax.set_title("Таблица сопряженности 3х3")
    fig.colorbar(im)
    return fig


def plot_scatter_gray_zone(x1, x2, c1_low, c1_high, c2_low, c2_high, aa, bb, log_scale=True):
    # упрощённая версия (согласованные / несогласованные / серые)
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
    ax.scatter(x1, x2, alpha=0.5, s=20, c="steelblue")
    ax.axvline(c1_low, ls="--", color="black", alpha=0.6, label="Серая зона A")
    ax.axvline(c1_high, ls="--", color="black", alpha=0.6)
    ax.axhline(c2_low, ls="--", color="purple", alpha=0.6, label="Серая зона B")
    ax.axhline(c2_high, ls="--", color="purple", alpha=0.6)
    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
    ax.set_xlabel(f"Метод A ({aa})")
    ax.set_ylabel(f"Метод B ({bb})")
    ax.legend()
    ax.set_title("Диаграмма рассеяния (серая зона)")
    return fig


def plot_agreement_pattern(table, aa, bb):
    fig, ax = plt.subplots(figsize=(8, 8), dpi=200)
    category_map = np.zeros_like(table)
    for i in range(3):
        category_map[i, i] = -5
    category_map[0, 2] = category_map[2, 0] = 1
    for i in range(3):
        for j in range(3):
            if i != j and category_map[i, j] == 0:
                category_map[i, j] = 20
    im = ax.imshow(category_map, cmap="tab20c")
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


# -------------------- многокатегориальный режим --------------------

def categorize_multi(x, cuts):
    return np.digitize(x, np.asarray(cuts, dtype=float), right=False)


def build_kxk_table(x1, x2, cuts1, cuts2):
    y1 = categorize_multi(x1, cuts1)
    y2 = categorize_multi(x2, cuts2)
    k = len(cuts1) + 1
    table = np.zeros((k, k), dtype=int)
    for i in range(k):
        for j in range(k):
            table[i, j] = np.sum((y1 == i) & (y2 == j))
    return table


def unweighted_kappa(table, W=None):
    table = np.asarray(table, dtype=float)
    N = table.sum()
    if N == 0:
        return np.nan
    Po = np.trace(table) / N
    Pe = np.sum((table.sum(1) / N) * (table.sum(0) / N))
    if np.isclose(1 - Pe, 0):
        return np.nan
    return (Po - Pe) / (1 - Pe)


def category_ppa_npa(table):
    k = table.shape[0]
    results = []
    for cat in range(k):
        tp = table[cat, cat]
        ref_pos = table[:, cat].sum()
        ppa = 100 * tp / ref_pos if ref_pos > 0 else np.nan
        tn = table.sum() - table[cat, :].sum() - table[:, cat].sum() + tp
        ref_neg = table.sum() - ref_pos
        npa = 100 * tn / ref_neg if ref_neg > 0 else np.nan
        results.append({
            "Категория": f"Кат. {cat + 1}",
            "PPA, %": round(ppa, 2) if not np.isnan(ppa) else np.nan,
            "NPA, %": round(npa, 2) if not np.isnan(npa) else np.nan,
            "n (реф. +)": int(ref_pos),
            "n (реф. −)": int(ref_neg)
        })
    return results


def bootstrap_category_ppa_npa(df, aa, bb, cuts1, cuts2, n_boot=2000):
    dfs = df[[aa, bb]].dropna()
    dfs[aa] = dfs[aa].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    dfs[bb] = dfs[bb].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>*'})))
    k = len(cuts1) + 1
    ppa_boots = [[] for _ in range(k)]
    npa_boots = [[] for _ in range(k)]
    for _ in range(n_boot):
        dfboot = resample(dfs, replace=True)
        t = build_kxk_table(dfboot[aa].values, dfboot[bb].values, cuts1, cuts2)
        for cat in range(k):
            tp = t[cat, cat]
            ref_pos = t[:, cat].sum()
            ppa = 100 * tp / ref_pos if ref_pos > 0 else np.nan
            tn = t.sum() - t[cat, :].sum() - t[:, cat].sum() + tp
            ref_neg = t.sum() - ref_pos
            npa = 100 * tn / ref_neg if ref_neg > 0 else np.nan
            if not np.isnan(ppa):
                ppa_boots[cat].append(ppa)
            if not np.isnan(npa):
                npa_boots[cat].append(npa)
    cis = []
    for cat in range(k):
        ppa_ci = np.percentile(ppa_boots[cat], [2.5, 97.5]) if len(ppa_boots[cat]) >= 10 else (np.nan, np.nan)
        npa_ci = np.percentile(npa_boots[cat], [2.5, 97.5]) if len(npa_boots[cat]) >= 10 else (np.nan, np.nan)
        cis.append({
            "Категория": f"Кат. {cat + 1}",
            "PPA 95% CI": f"от {ppa_ci[0]:.2f} до {ppa_ci[1]:.2f}" if not np.isnan(ppa_ci[0]) else "—",
            "NPA 95% CI": f"от {npa_ci[0]:.2f} до {npa_ci[1]:.2f}" if not np.isnan(npa_ci[0]) else "—"
        })
    return cis


def plot_kxk_heatmap(table, labels, aa, bb, title="Таблица сопряженности"):
    size = max(6, table.shape[0] * 1.3)
    fig, ax = plt.subplots(figsize=(size, size), dpi=200)
    cmap = plt.cm.PuBuGn
    colors = cmap(np.linspace(0, 1, 256))
    colors[:, :3] = colors[:, :3] ** 0.4
    new_cmap = mcolors.ListedColormap(colors)
    im = ax.imshow(table, cmap=new_cmap)
    ax.set_xticks(range(table.shape[1]))
    ax.set_yticks(range(table.shape[0]))
    ax.set_xticks(np.arange(-0.5, table.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, table.shape[0], 1), minor=True)
    ax.grid(color="black", which="minor")
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel(f"Метод B ({bb})")
    ax.set_ylabel(f"Метод A ({aa})")
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            ax.text(j, i, int(table[i, j]), ha="center", va="center")
    ax.set_title(title)
    fig.colorbar(im)
    return fig


def plot_scatter_multi(x1, x2, cuts1, cuts2, aa, bb, log_scale=True):
    """
    Согласованные точки — синие.
    Несогласованные окрашены по |catA − catB|: чем больше расхождение, тем краснее.
    """
    y1 = categorize_multi(x1, cuts1)
    y2 = categorize_multi(x2, cuts2)
    disagreement = np.abs(y1 - y2)

    fig, ax = plt.subplots(figsize=(9, 7), dpi=200)

    # согласованные
    mask_agree = disagreement == 0
    ax.scatter(x1[mask_agree], x2[mask_agree],
               c="steelblue", alpha=0.55, s=28, label="Согласны (Δ=0)", edgecolors="none")


    # несогласованные
    mask_dis = disagreement > 0
    if np.any(mask_dis):
        max_dis = max(1, int(disagreement.max()))
        colors_dis = disagreement[mask_dis] / max_dis
        sc = ax.scatter(x1[mask_dis], x2[mask_dis],
                        c=colors_dis, cmap="Reds", alpha=0.85, s=42,
                        vmin=0, vmax=1, edgecolors="k", linewidths=0.3,
                        label="Не согласны")
        cbar = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.02)
        cbar.set_label("|категория A − категория B|", fontsize=9)
        ticks = np.linspace(0, 1, min(5, max_dis + 1))
        cbar.set_ticks(ticks)
        cbar.set_ticklabels([f"{v * max_dis:.0f}" for v in ticks])

    for idx, c in enumerate(cuts1):
        ax.axvline(c, ls="--", color="black", alpha=0.65, label="Границы A" if idx == 0 else None)
    for idx, c in enumerate(cuts2):
        ax.axhline(c, color="purple", alpha=0.65, label="Границы B" if idx == 0 else None)

    if log_scale and ((x1 > 0) & (x2 > 0)).mean() > 0.5:
        ax.set_xscale("log")
        ax.set_yscale("log")

    ax.set_xlabel(f"Метод A ({aa})")
    ax.set_ylabel(f"Метод B ({bb})")
    ax.set_title("Диаграмма рассеяния: цвет = степень несогласия категорий")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.25)
    return fig


# =====================================================================
# UI
# =====================================================================

if uploaded_file:
    st.info("""В загруженном файле результаты должны располагаться в столбцах и иметь заголовки.  
            Строки с отсутствующими данными автоматически удаляются.  
            Для количественных тестов автоматически удаляются знаки: &gt;l < >""")
    st.info("""*Количественные в бинарные* · *+ неопределенность* · *Категориальные (произвольное k)*""")

    df = pd.read_excel(uploaded_file)
    st.dataframe(df.head())
    numeric_cols = df.columns.to_list()

    radio_type = st.sidebar.radio(
        "Выбери тип данных для сравнения",
        ["Количественные в бинарные",
         "Количественные в бинарные + неопределенность",
         "Количественные в категориальные (произвольное k)"]
    )

    # ===================== 1. Бинарный =====================
    if radio_type == "Количественные в бинарные":
        st.subheader("Диагностическое согласие после бинаризации")
        st.sidebar.header("Пара методов")
        col1, col2 = st.sidebar.columns(2)
        aa = col1.selectbox("Метод A (Новый)", numeric_cols)
        bb = col2.selectbox("Метод B (Референтный)", numeric_cols)
        p1 = col1.number_input("Порог метода А", value=1.0)
        p2 = col2.number_input("Порог метода В", value=1.0)
        cut_off_input = st.sidebar.number_input("Макс. cut-off A для графика", value=3.0)

        if st.sidebar.button("Запуск вычислений ▶️"):
            a, b, c, d, dfs = prepare_pair(df, aa, bb, p1, p2)
            kappa = compute_kappa(a, b, c, d)
            ci_low, ci_high = bootstrap_kappa(dfs)
            PPA, NPA = compute_ppa_npa(a, b, c, d)
            ppa_ci, npa_ci = bootstrap_npa_ppa(dfs)
            PABAK = pabak(a, b, c, d)
            pabak_l, pabak_h = pabak_ci_funk(a, b, c, d)
            mc_ans, mc_p = mcnemar_result(a, b, c, d)
            AC1 = gwet_ac1(a, b, c, d)
            ac1_l, ac1_h = bootstrap_ac1(dfs)
            ppa_list, npa_list, pr_list = ppa_npa_curve(dfs, aa, bb, p2, df)

            c1, c2, c3 = st.columns(3)
            c1.markdown("Таблица 2×2")
            c1.dataframe({"": [f"Метод A {minus}", "Метод A +"],
                          f"Метод B {minus}": [a, c], "Метод B +": [b, d]})
            c2.markdown("Показатели")
            c2.dataframe({
                "": ["kappa", "PPA, %", "NPA, %", "PABAK", "AC1"],


                "Значение": [round(kappa, 4), round(PPA, 2), round(NPA, 2), round(PABAK, 4), round(AC1, 4)],
                "95% CI": [f"от {ci_low:.4f} до {ci_high:.4f}",
                           f"от {ppa_ci[0]:.2f} до {ppa_ci[1]:.2f}",
                           f"от {npa_ci[0]:.2f} до {npa_ci[1]:.2f}",
                           f"от {pabak_l:.4f} до {pabak_h:.4f}",
                           f"от {ac1_l:.4f} до {ac1_h:.4f}"]
            })
            c3.markdown("МакНемар")
            c3.dataframe({"p-value": [round(mc_p, 4)], "Интерпретация": [mc_ans]})

            c11, c22 = st.columns(2)
            c111, c222 = st.columns(2)
            c11.pyplot(plot_confusion_matrix(a, b, c, d))
            c22.pyplot(plot_agreement_bar(a, b, c, d))
            c111.pyplot(plot_scatter_with_cutoff(dfs, aa, bb, p1, p2))
            fig_k, ax = plt.subplots(figsize=(8, 6), dpi=200)
            ks, pabaks, ac1s, porogs = [], [], [], []
            for i in np.linspace(0, cut_off_input, 100):
                aa_, bb_, cc_, dd_, _ = prepare_pair(df, aa, bb, i, p2)
                ks.append(compute_kappa(aa_, bb_, cc_, dd_))
                pabaks.append(pabak(aa_, bb_, cc_, dd_))
                ac1s.append(gwet_ac1(aa_, bb_, cc_, dd_))
                porogs.append(i)
            ax.plot(porogs, ks, label="kappa")
            ax.plot(porogs, pabaks, label="PABAK")
            ax.plot(porogs, ac1s, label="AC1")
            ax.set_xlabel(f"Cut-off A ({aa})")
            ax.set_ylabel("Коэффициент")
            ax.legend()
            ax.set_title("Зависимость от cut-off A")
            c222.pyplot(fig_k)
            npa_ppa_plot, auc_ppa = plot_ppa_npa(ppa_list, npa_list)
            c111.pyplot(npa_ppa_plot)
            pr_plot, auc_pr = plot_pr_curve(ppa_list, pr_list)
            c222.pyplot(pr_plot)
            if not np.isnan(auc_ppa):
                st.markdown(f"AUC PPA-NPA: {auc_ppa:.3f}")
            if not np.isnan(auc_pr):
                st.markdown(f"AUC-PR: {auc_pr:.3f}")

    # ===================== 2. Серая зона =====================
    if radio_type == "Количественные в бинарные + неопределенность":
        st.subheader("Согласие с серой зоной (CV)")
        st.sidebar.header("Пара методов")
        col1, col2 = st.sidebar.columns(2)
        aa = col1.selectbox("Метод A", numeric_cols, key="u_aa")
        bb = col2.selectbox("Метод B", numeric_cols, key="u_bb")
        p1 = col1.number_input("Порог A", value=1.0, key="u_p1")
        p2 = col2.number_input("Порог B", value=1.0, key="u_p2")
        cv1 = col1.number_input("CV A", step=0.01, key="u_cv1")
        cv2 = col2.number_input("CV B", step=0.01, key="u_cv2")
        weights = st.sidebar.radio("Веса", ["Линейные весы", "Квадратичные весы"], key="u_w")
        cut_off_input = st.sidebar.number_input("Макс. cut-off A", value=3.0, key="u_cut")

        if st.sidebar.button("Запуск вычислений ▶️", key="push_u"):
            c1l, c1h = gray_zone_from_cv(p1, cv1)
            c2l, c2h = gray_zone_from_cv(p2, cv2)
            x1, x2 = prepare_pair2(df, aa, bb)
            table, a, b, c, d, e, f, g, h, i = build_3x3_table(x1, x2, c1l, c1h, c2l, c2h)
            W = make_weights(3, weights)
            wk = weighted_kappa(table, W)
            ac2 = gwet_ac2(table, W)
            wk_ci = bootstrap_ci_kxk(df, aa, bb, weighted_kappa, W, [c1l, c1h], [c2l, c2h])
            ac2_ci = bootstrap_ci_kxk(df, aa, bb, gwet_ac2, W, [c1l, c1h], [c2l, c2h])
            bt_stat, bt_p, inter = bowker_test(table)

            c1, c2 = st.columns(2)
            c1.dataframe({"": ["A−", "СЗ A", "A+"],
                          "B−": [a, d, g], "СЗ B": [b, e, h], "B+": [c, f, i]})
            c2.dataframe({
                "": ["Взвеш. κ", "AC2"],
                "Значение": [round(wk, 4), round(ac2, 4)],
                "95% CI": [f"от {wk_ci[0]} до {wk_ci[1]}", f"от {ac2_ci[0]} до {ac2_ci[1]}"]
            })
            c2.dataframe({"Стат.": [bt_stat], "p": [bt_p], "Интерп.": [inter]})


            c11, c22 = st.columns(2)
            c11.pyplot(plot_3x3_agreement(table, aa, bb))
            c22.pyplot(plot_agreement_pattern(table, aa, bb))
            c111, c222 = st.columns(2)
            c222.pyplot(plot_scatter_gray_zone(x1, x2, c1l, c1h, c2l, c2h, aa, bb))

    # ===================== 3. Произвольное k =====================
    if radio_type == "Количественные в категориальные (произвольное k)":
        st.subheader("Многокатегориальное согласие (произвольное k)")
        st.info("PPA/NPA по категориям + bootstrap CI. На scatter несогласованные точки краснеют пропорционально |Δ категории|.")

        st.sidebar.header("Пара методов")
        col1, col2 = st.sidebar.columns(2)
        aa = col1.selectbox("Метод A (Новый)", numeric_cols, key="m_aa")
        bb = col2.selectbox("Метод B (Референтный)", numeric_cols, key="m_bb")

        n_cat = st.sidebar.number_input("Число категорий (k)", min_value=2, max_value=10, value=3, step=1)

        st.sidebar.markdown(f"Границы A ({int(n_cat)-1} шт.)")
        cuts_a = [st.sidebar.number_input(f"A: {i+1}→{i+2}", value=float(i+1), key=f"ca{i}_{n_cat}")
                  for i in range(int(n_cat)-1)]
        st.sidebar.markdown(f"Границы B ({int(n_cat)-1} шт.)")
        cuts_b = [st.sidebar.number_input(f"B: {i+1}→{i+2}", value=float(i+1), key=f"cb{i}_{n_cat}")
                  for i in range(int(n_cat)-1)]

        weights = st.sidebar.radio("Веса", ["Линейные весы", "Квадратичные весы"], key="m_w")
        n_boot = st.sidebar.number_input("Bootstrap реплик", 500, 5000, 2000, 500)
        use_log = st.sidebar.checkbox("Лог. шкала на scatter", True)

        if st.sidebar.button("Запуск вычислений ▶️", key="push_m"):
            cuts_a = sorted(map(float, cuts_a))
            cuts_b = sorted(map(float, cuts_b))
            n_cat = int(n_cat)

            if len(cuts_a) != n_cat - 1 or len(cuts_b) != n_cat - 1:
                st.error("Число границ ≠ k−1")
            else:
                x1, x2 = prepare_pair2(df, aa, bb)
                table = build_kxk_table(x1.values, x2.values, cuts_a, cuts_b)
                W = make_weights(n_cat, weights)

                kappa_uw = unweighted_kappa(table)
                kappa_w = weighted_kappa(table, W)
                ac2 = gwet_ac2(table, W)
                Po = np.trace(table) / table.sum() if table.sum() else np.nan
                # 95% CI для Po (Wilson)
                n_agree = int(np.trace(table))
                N_total = int(table.sum())
                if N_total > 0:
                    po_ci_low, po_ci_high = proportion_confint(n_agree, N_total, alpha=0.05, method="wilson")
                    po_ci_str = f"от {po_ci_low:.4f} до {po_ci_high:.4f}"
                else:
                    po_ci_str = "—"

                with st.spinner("Bootstrap κ / AC2..."):
                    ku_ci = bootstrap_ci_kxk(df, aa, bb, unweighted_kappa, W, cuts_a, cuts_b, n_boot)
                    kw_ci = bootstrap_ci_kxk(df, aa, bb, weighted_kappa, W, cuts_a, cuts_b, n_boot)
                    ac_ci = bootstrap_ci_kxk(df, aa, bb, gwet_ac2, W, cuts_a, cuts_b, n_boot)

                bt_stat, bt_p, inter = bowker_test(table)
                cat_ppa = category_ppa_npa(table)

                with st.spinner("Bootstrap PPA/NPA..."):
                    cat_cis = bootstrap_category_ppa_npa(df, aa, bb, cuts_a, cuts_b, n_boot)

                cat_full = pd.DataFrame(cat_ppa).merge(pd.DataFrame(cat_cis), on="Категория")

                labels = [f"Кат. {i+1}" for i in range(n_cat)]
                res = {"": labels}
                for j, lab in enumerate(labels):
                    res[f"B · {lab}"] = table[:, j].tolist()

                c1, c2 = st.columns(2)
                c1.markdown(f"Таблица {n_cat}×{n_cat}")
                c1.dataframe(res)
                c2.markdown("Показатели согласия")
                c2.dataframe({
                    "": ["Невзвеш. κ", "Взвеш. κ", "AC2", "Po"],
                    "Значение": [round(kappa_uw, 4) if not np.isnan(kappa_uw) else "—",
                                 round(kappa_w, 4) if not np.isnan(kappa_w) else "—",
                                 round(ac2, 4) if not np.isnan(ac2) else "—",


                                 round(Po, 4) if not np.isnan(Po) else "—"],
                    "95% CI": [f"от {ku_ci[0]} до {ku_ci[1]}" if not np.isnan(ku_ci[0]) else "—",
                               f"от {kw_ci[0]} до {kw_ci[1]}" if not np.isnan(kw_ci[0]) else "—",
                               f"от {ac_ci[0]} до {ac_ci[1]}" if not np.isnan(ac_ci[0]) else "—",  #]})
                               po_ci_str]})

                c2.dataframe({"Стат. Боукера": [bt_stat], "p": [bt_p], "Интерп.": [inter]})

                st.markdown("### PPA / NPA по категориям + bootstrap 95 % CI")
                st.dataframe(cat_full)
                st.caption("PPA — согласие на категории k при референсе = k; NPA — согласие на «не k».")

                c11, c22 = st.columns(2)
                c11.pyplot(plot_kxk_heatmap(table, labels, aa, bb, f"Таблица {n_cat}×{n_cat}"))
                c22.pyplot(plot_scatter_multi(x1, x2, cuts_a, cuts_b, aa, bb, use_log))

                st.write(f"Границы A ({aa}): {cuts_a}")
                st.write(f"Границы B ({bb}): {cuts_b}")
                st.caption("Синие точки — полное согласие категорий. Оттенки красного — |Δ категории|.")

else:
    st.info("Загрузите Excel-файл со столбцами результатов.")
