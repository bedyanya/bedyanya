import streamlit as st 
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
import math

st.set_page_config(layout="wide")

st.title("Калькуляторы")


mainform = st.container(border=True)
z1, z2, z3 = mainform.columns([3,1,1])
z1.subheader('Общие параметры (SCORE2 / SCORE2-OP / SCORE2-Diabetes)')
mcol1, mcol2, mcol3, mcol4, mcol5 = mainform.columns([2.9,2.9,2.9,2.9,1.4])
sex = mcol2.selectbox('Пол', options=['Мужской', 'Женский'])
age = mcol2.number_input('Возраст',min_value=40, step=1, max_value=110)
region = mcol1.selectbox('Регион риска', options=['Очень высокий', 'Высокий', 'Средний', 'Низкий'], help='Россия — регион очень высокого риска 😬')
smoke = mcol3.selectbox('Курение в настоящий момент', options=['Нет','Да'])
sbp = mcol3.number_input('Систолическое АД (мм.рт.ст.)', min_value=60, max_value=300, step=1, value=120)
total_chol = mcol4.number_input('Общий холестерин (ммоль/л)', min_value=0.00, step=0.01)
hdl = mcol4.number_input('ЛПВП (ммоль/л)', min_value=0.00, step=0.01)
z21 , z22, z23 = mainform.columns([3,1,1])
z21.subheader('Дополнительные параметры')
z31, z32, z33, z34 = mainform.columns([2.9,2.9,2.9,4.3])
zb31 = z31.container(border=True)
zb32 = z32.container(border=True)
zb33 = z33.container(border=True)
zb34 = z34.container(border=True)
zb31.markdown('**SCORE2-OP (возраст > 70 лет)**')
zb32.markdown('**SCORE2-Diabetes (возраст 40-69 лет)**')
zb33.markdown('**EHR + Lp(a)**  (Fan et al. 2025)', help='Тестовая реализация')
zb34.markdown('**Дополнительные тесты**', help='Оставьте нули, если не используются')

diabetes_op = zb31.selectbox('Диабет', options=['Нет','Есть'], key='OP')
diabetes_d = zb32.selectbox('Диабет', options=['Нет','Есть'], key = 'Diabetes')

if diabetes_d == 'Есть':
    d_age = zb32.number_input('Возраст диагностики диабета', min_value=40, max_value=age, step=1, help='Не может превышать возраст пациента')
    hba1c = zb32.number_input('HbA1c (%)', min_value=0.00 , step=0.01, max_value= 20.00)
    eGFR = zb32.number_input('СКФ (мм/мин/1.73 м²)', min_value=0 , step=1, max_value=160) 
diabetes_ehr = zb33.selectbox('Диабет', options=['Нет','Есть'], key = 'Diabetes EHR')
race = zb33.selectbox('Раса', options=['Белая','Черная'])
aht = zb33.selectbox('Прием антигипертензивных препаратов', options=['Нет', 'Да'])
zb33.markdown('Внесите результат Lp(a) в мг/дл ╰┈➤')
zbz341, zbz342 = zb34.columns([3,1])
lpa = zbz341.number_input('Lp(a)', min_value=0.00, step = 0.01)
hs_crp = zbz341.number_input('СРБ высокочувствительный (мг/л)', min_value=0.00, step = 0.01)
hcy = zbz341.number_input('Гомоцистеин (мкмоль/л)', min_value=0.00, step = 0.01)
lpa_unit = zbz342.selectbox('Единицы Lp(a)', options=['мг/дл', 'нмоль/л'])


# Основные функции
# =========================================================================
def _calibrate(uncalibrated: float, scale1: float, scale2: float) -> float:
    #Калибровка complementary log-log
    uncalibrated = max(min(uncalibrated, 0.9999), 1e-10)
    return 1 - math.exp(-math.exp(scale1 + scale2 * math.log(-math.log(1 - uncalibrated))))

#SCORE2 (40–69 лет, без диабета)
def score2(sex = sex, 
           age = age, 
           smoke = smoke, 
           sbp = sbp,
           total_chol = total_chol, 
           hdl = hdl, 
           region = region) -> float:
    
    if smoke == 'Да':
        smoking = 1
    else:
        smoking = 0

    cage   = (age - 60) / 5
    csbp   = (sbp - 120) / 20
    ctchol = (total_chol - 6) / 1
    chdl   = (hdl - 1.3) / 0.5
    diabetes = 0  # для SCORE2 всегда 0

    if sex == "Мужской":
        lp = (0.3742 * cage + 0.6012 * smoking + 0.2777 * csbp +
              0.6457 * diabetes + 0.1458 * ctchol + (-0.2698) * chdl +
              (-0.0755) * cage * smoking + (-0.0255) * cage * csbp +
              (-0.0281) * cage * ctchol + 0.0426 * cage * chdl +
              (-0.0983) * cage * diabetes)
        baseline = 0.9605
        scales = {
            "Низкий": (-0.5699, 0.7476), "Средний": (-0.1565, 0.8009),
            "Высокий": (0.3207, 0.9360), "Очень высокий": (0.5836, 0.8294)
        }
    else:
        lp = (0.4648 * cage + 0.7744 * smoking + 0.3131 * csbp +
              0.8096 * diabetes + 0.1002 * ctchol + (-0.2606) * chdl +
              (-0.1088) * cage * smoking + (-0.0277) * cage * csbp +
              (-0.0226) * cage * ctchol + 0.0613 * cage * chdl +
              (-0.1272) * cage * diabetes)
        baseline = 0.9776
        scales = {
            "Низкий": (-0.7380, 0.7019), "Средний": (-0.3143, 0.7701),
            "Высокий": (0.5710, 0.9369), "Очень высокий": (0.9412, 0.8329)}

    uncal = 1 - baseline ** math.exp(lp)
    scale1, scale2 = scales[region]
    return round(_calibrate(uncal, scale1, scale2) * 100, 2)

#SCORE2-OP (70–89 лет)
def score2_op2(sex = sex, 
               age = age, 
               smoke = smoke, 
               sbp = sbp, 
               total_chol = total_chol, 
               hdl = hdl, 
               region = region, 
               diabetes_op = diabetes_op) -> float:

    if smoke == 'Да':
        smoking = 1
    else:
        smoking = 0

    if diabetes_op == 'Есть':
        diabetes = 1
    else:
        diabetes = 0
   
    # Центрирование (как в оригинале SCORE2-OP)
    cage   = age - 73
    csbp   = sbp - 150          
    ctchol = total_chol - 6
    chdl   = hdl - 1.4

    if sex == "Мужской":
        # Коэффициенты (log subdistribution HR)
        lp = (
            0.0634 * cage +
            0.4245 * diabetes +
            0.3524 * smoking +
            0.0094 * csbp +               # 0.094 на 10 мм рт.ст. → 0.0094 на 1 мм
            0.0850 * ctchol +
            (-0.3564) * chdl +
            (-0.0174) * cage * diabetes +
            (-0.0247) * cage * smoking +
            (-0.0005) * cage * csbp +
            0.0073  * cage * ctchol +
            0.0091  * cage * chdl )
        baseline_survival = 0.7576
        mean_lp = 0.0929

        # Точные scale-факторы из SCORE2-OP
        scales = {
            "Низкий":       (-0.34, 1.19),
            "Средний":  ( 0.01, 1.25),
            "Высокий":      ( 0.08, 1.15),
            "Очень высокий": ( 0.05, 0.70)}

    else:  # бабы
        lp = (
            0.0789 * cage +
            0.6010 * diabetes +
            0.4921 * smoking +
            0.0102 * csbp +               # 0.102 на 10 мм рт.ст.
            0.0605 * ctchol +
            (-0.3040) * chdl +
            (-0.0107) * cage * diabetes +
            (-0.0255) * cage * smoking +
            (-0.0004) * cage * csbp +
            (-0.0009) * cage * ctchol +
            0.0154  * cage * chdl  )
        baseline_survival = 0.8082
        mean_lp = 0.2290

        scales = {
            "Низкий":       (-0.52, 1.01),
            "Средний":  (-0.10, 1.10),
            "Высокий":      ( 0.38, 1.09),
            "Очень высокий": ( 0.38, 0.69)}

    # Некалиброванный риск (с вычитанием среднего LP)
    uncalibrated = 1 - baseline_survival ** math.exp(lp - mean_lp)

    # Калибровка
    scale1, scale2 = scales[region]
    uncalibrated = max(min(uncalibrated, 0.9999), 1e-10)
    calibrated = 1 - math.exp(-math.exp(scale1 + scale2 * math.log(-math.log(1 - uncalibrated))))

    return round(calibrated * 100, 2)


#SCORE2-Diabetes (40–69 лет, сахарный диабет 2 типа)
def score2_diabetes(sex = sex, 
                    age = age, 
                    smoke = smoke, 
                    sbp = sbp, 
                    total_chol = total_chol, 
                    hdl = hdl, 
                    region = region, 
                    diabetes_d = diabetes_d,
                    hba1c = 0,
                    egfr = 0) -> float:

    if smoke == 'Да':
        smoking = 1
    else:
        smoking = 0
    
    if diabetes_d == 'Есть':
        diabetes = 1
        diabetes_age = d_age
    else:
        diabetes = 0
        diabetes_age = 50

    # пересчёт единиц HbA1c из % в ммоль/моль
    hba1c = (hba1c - 2.15) * 10.93

    cage     = (age - 60) / 5
    csbp     = (sbp - 120) / 20
    ctchol   = (total_chol - 6) / 1
    chdl     = (hdl - 1.3) / 0.5
    cagediab = (diabetes_age - 50) / 5
    chba1c   = (hba1c - 31) / 9.34
    clnegfr  = (math.log(egfr) - 4.5) / 0.15
    diabetes = 1

    if sex == "Мужской":
        lp = (0.5368 * cage +
              0.4774 * smoking +
              0.1322 * csbp +
              0.6457 * diabetes +
              0.1102 * ctchol +
              (-0.1087) * chdl +
              (-0.0672) * cage * smoking +
              (-0.0268) * cage * csbp +
              (-0.0983) * cage * diabetes +
              (-0.0181) * cage * ctchol +
              0.0095 * cage * chdl +
              # для диабета:
              (-0.0998) * diabetes * cagediab +
              0.0955 * chba1c +
              (-0.0591) * clnegfr +
              0.0058 * clnegfr * clnegfr +
              (-0.0134) * chba1c * cage +
              0.0115 * clnegfr * cage)
        baseline = 0.9605
    else:
        lp = (0.6624 * cage +
              0.6139 * smoking +
              0.1421 * csbp +
              0.8096 * diabetes +
              0.1127 * ctchol +
              (-0.1568) * chdl +
              (-0.1122) * cage * smoking +
              (-0.0167) * cage * csbp +
              (-0.1272) * cage * diabetes +
              (-0.0200) * cage * ctchol +
              0.0186 * cage * chdl +
              # для диабета:
              (-0.1180) * diabetes * cagediab +
              0.1173 * chba1c +
              (-0.0640) * clnegfr +
              0.0062 * clnegfr * clnegfr +
              (-0.0196) * chba1c * cage +
              0.0169 * clnegfr * cage)
        baseline = 0.9776

    # Те же scale-факторы, что и у SCORE2
    scales = {"Мужской": {
            "Низкий": (-0.5699, 0.7476), "Средний": (-0.1565, 0.8009),
            "Высокий": (0.3207, 0.9360), "Очень высокий": (0.5836, 0.8294) },
        "Женский": {
            "Низкий": (-0.7380, 0.7019), "Средний": (-0.3143, 0.7701),
            "Высокий": (0.5710, 0.9369), "Очень высокий": (0.9412, 0.8329)}}

    uncal = 1 - baseline ** math.exp(lp)
    scale1, scale2 = scales[sex][region]
    return round(_calibrate(uncal, scale1, scale2) * 100, 2)

# Байесовское обновление рисков:
def bayesian_update_score(prior_risk_percent,
    hs_crp = hs_crp,
    homocysteine = hcy,
    lpa = lpa,
    lpa_unit = lpa_unit): 

    prior = max(min(prior_risk_percent / 100.0, 0.999), 0.001)
    prior_odds = prior / (1 - prior)

    def lr_crp(v):
        if v < 1: return 0.88
        if v < 2: return 1.05
        if v < 3: return 1.22
        return 1.35

    def lr_hcy(v):
        if v < 10: return 0.92
        if v < 15: return 1.10
        return 1.25

    #def lr_lpa(v, unit):
        #if unit.lower() in ("mg", "mg/dl"):
        #    v *= 2.5
        #if v < 75: return 0.95
        #if v < 125: return 1.15
        #if v < 200: return 1.30
        #return 1.45
    #    if v < 25: return 0.8625
    #    if v < 50: return 1.27
    #    if v < 100: return 1.67
    #    return 1.88
    
    def lr_lpa(lpa = lpa, lpa_unit = lpa_unit):
        ln_1_11 = math.log(1.174)
        if lpa_unit == 'мг/дл':
            lr = math.exp(ln_1_11 * (lpa/25))
            # мг/дл
            #ref = 25 
            #beta = 0.0112
            #delta = lpa - ref
            #lr = math.exp(beta * delta)
        else:
            lr = math.exp(ln_1_11 * (lpa/50))
            # нмоль/л
            #ref = 62.5
            #beta = 0.00255
            #delta = lpa - ref
            #lr = math.exp(beta * delta)
        # Мягкие границы
        #return max(0.82, min(lr, 3.8))
        return max(0.85, min(lr, 4.5))

    used = {}
    posterior_odds = prior_odds

    if hs_crp !=0:
        lr = lr_crp(hs_crp)
        posterior_odds *= lr
        used["hs_crp"] = lr

    if homocysteine !=0:
        lr = lr_hcy(homocysteine)
        posterior_odds *= lr
        used["homocysteine"] = lr

    if lpa !=0:
        lr = lr_lpa(lpa, lpa_unit)
        posterior_odds *= lr
        used["lpa"] = lr

    posterior = posterior_odds / (1 + posterior_odds)
    posterior_percent = round(posterior * 100, 2)

    #result = {
    #    "prior_percent": round(prior_risk_percent, 2),
    #    "posterior_percent": posterior_percent,
    #    "absolute_change": round(posterior_percent - prior_risk_percent, 2),
    #    "relative_change_percent": round((posterior / prior - 1) * 100, 1),
    #    "used_likelihood_ratios": used}

    return round(posterior_percent, 2)

# ==============================================================================
# EHR + Lp(a) модель
def lpa_risk_calculator(
    age = age,
    sex = sex,
    race = race,
    sbp = sbp,
    total_chol = total_chol,
    hdl = hdl,
    diabetes_ehr = diabetes_ehr,
    smoke = smoke,
    on_htn_meds = aht,
    lpa_mg = lpa):

    # Пересчёт единиц измерения ХС и ЛПВП в мг/дл
    hdle = hdl*38.67
    total_chole = total_chol*38.67

    if smoke == 'Да':
        smoker = True
    else:
        smoker = False

    if race == 'Черная':
        black = True
    else:
        black = False

    if diabetes_ehr == 'Есть':
        diabetes = True
    else:
        diabetes = False

    if aht == 'Да':
        on_htn_meds = True
    else:
        on_htn_meds = False

    if sex == 'Женский':
        female = True
    else:
        female = False

    # Коэффициенты (таблица 2)
    models = {
    "ASCVD": {
    "coef": {
    "lpa_per_25": 0.20348,
    "age": 0.02471,
    "female": -0.18778,
    "black": 0.42074,
    "sbp": 0.00354,
    "total_chole": -0.00052,
    "hdle": -0.00506,
    "diabetes": 0.93127,
    "smoker": 0.42402,
    "htn_meds": 1.00751,
    },
    "S0": 0.9182
    },
    "MI": {
    "coef": {
    "lpa_per_25": 0.10698,
    "age": 0.02305,
     "female": -0.31152,
    "black": 0.53055,
    "sbp": 0.00105,
    "total_chole": -0.00004,
    "hdle": -0.00566,
    "diabetes": 0.85799,
    "smoker": 0.47055,
    "htn_meds": 1.19230,
    },
    "S0": 0.9460
    },
    "Stroke": {
    "coef": {
    "lpa_per_25": 0.28789,
    "age": 0.02749,
    "female": 0.03365,
    "black": 0.09813,
    "sbp": -0.00114,
    "total_chole": -0.00093,
    "hdle": -0.00336,
    "diabetes": 0.98347,
    "smoker": 0.34732,
    "htn_meds": 0.88005,
    },
    "S0": 0.9644
    }
    }

    # Средние значения (одинаковые для всех моделей)
    means = {
    "lpa_per_25": 1.70,
    "age": 48.74,
    "female": 0.51,
    "black": 0.08,
    "sbp": 126.71,
    "total_chole": 221.53,
    "hdle": 49.23,
    "diabetes": 0.09,
    "smoker": 0.31,
    "htn_meds": 0.56,
    }

    results = {}

    for outcome, model in models.items():
        coef = model["coef"]
        S0 = model["S0"]

        # Линейный предиктор индивида
        r_ind = (
            coef["lpa_per_25"] * (lpa_mg / 25.0) +
            coef["age"] * age +
            coef["female"] * (1.0 if female else 0.0) +
            coef["black"] * (1.0 if black else 0.0) +
            coef["sbp"] * sbp +
            coef["total_chole"] * total_chol +
            coef["hdle"] * hdl +
            coef["diabetes"] * (1.0 if diabetes else 0.0) +
            coef["smoker"] * (1.0 if smoker else 0.0) +
            coef["htn_meds"] * (1.0 if on_htn_meds else 0.0)
               )

        # Средний линейный предиктор
        r_mean = sum(coef[k] * means[k] for k in coef)

        # Абсолютный 10-летний риск
        risk = 1.0 - (S0 ** math.exp(r_ind - r_mean))
        results[f"{outcome}"] = round(risk * 100, 2)

    return results


# ==============================================================================
#cr1, cr2, cr3, cr4 = st.columns(4)
if total_chol !=0 and hdl !=0:
    res_box = st.container(border=True)
    cr1, cr2, cr3, cr4 = res_box.columns([3.5,3.5,3.5,5.2])
    if age < 70:
        crb1 = cr1.container(border=True, horizontal_alignment='center')
        crb4 = cr4.container(border=True, horizontal_alignment='center')
        crb1.subheader('SCORE2:', divider='blue')
        score2_res = score2(sex = sex, age = age, smoke = smoke, sbp = sbp, total_chol = total_chol, hdl = hdl, region = region)
        crb1.subheader(f'{score2_res} %')
        crb4.subheader('Тестовый калькулятор', divider='blue')
        crb4.subheader('Обновленный SCORE2:')
        crb4.subheader(f'{bayesian_update_score(score2_res, hs_crp, hcy, lpa, lpa_unit)} %')
        if diabetes_d == 'Есть' and hba1c !=0 and eGFR !=0:
            crb2 = cr2.container(border=True, horizontal_alignment='center')
            crb2.subheader('SCORE2-Diabetes:', divider='blue')
            score2_d = score2_diabetes(sex=sex, age=age, smoke=smoke, sbp=sbp, total_chol=total_chol, hdl=hdl, region=region, diabetes_d=diabetes_d, hba1c=hba1c, egfr=eGFR)
            crb2.subheader(f'{score2_d} %')
            crb4.subheader('Обновленный SCORE2-Diabetes:')
            crb4.subheader(f'{bayesian_update_score(score2_d, hs_crp, hcy, lpa, lpa_unit)} %')
    else:
        crb1 = cr1.container(border=True, horizontal_alignment='center')
        crb4 = cr4.container(border=True, horizontal_alignment='center')
        crb1.subheader('SCORE2-OP:', divider='blue')
        score2_op_res = score2_op2(sex=sex, age=age, smoke=smoke, sbp=sbp, total_chol=total_chol, hdl=hdl, region=region, diabetes_op=diabetes_op)
        crb1.subheader(f'{score2_op_res} %')
        crb4.subheader('Тестовый калькулятор', divider='blue', help='Обновленные SCORE с учётом новых тестов')
        crb4.subheader('Обновленный SCORE2-OP:')
        crb4.subheader(f'{bayesian_update_score(score2_op_res, hs_crp, hcy, lpa, lpa_unit)} %')
    if lpa !=0 and lpa_unit == 'мг/дл':
        crb3 = cr3.container(border=True, horizontal_alignment='center')
        crb3.subheader('Модель EHR + Lp(a)', divider='blue')
        ehr_res = lpa_risk_calculator(age = age,sex=sex, race=race, sbp=sbp, total_chol=total_chol, hdl=hdl, diabetes_ehr=diabetes_ehr, smoke=smoke, on_htn_meds=aht, lpa_mg=lpa)
        crb3.subheader(f'ASCVD: {ehr_res['ASCVD']} %')
        crb3.subheader(f'MI: {ehr_res['MI']} %')
        crb3.subheader(f'Stroke: {ehr_res['Stroke']} %')

if total_chol !=0 and hdl !=0:
    pic1, pic2 = st.columns([1,3])
    pbox1 = pic1.container(border=True, gap='xsmall')
    che1,che2,che3,che4,che5 = pic2.columns(5)
    if age < 70:
        check_score2 = che2.toggle('SCORE2', value=True)
        check_score2_d = che3.toggle('SCORE2-Diabetes',value=True)
        check_bayes = che4.toggle('Тестовый SCORE2 ✚', value=True)
        check_bayes_d = che5.toggle('Тестовый SCORE2-Diabetes ✚',value=True)
    else:
        check_score2_op = che2.toggle('SCORE2-OP', value=True)
        check_bayes_op = che3.toggle('Тестовый SCORE2-OP ✚',value=True)
    if smoke == 'Нет':
        kur = pbox1.toggle('Курение', value=False)
    else:
        kur = pbox1.toggle('Курение', value=True)
    if kur:
        kur_str = 'Да'
    else:
        kur_str = 'Нет'

    sad = pbox1.slider('САД (мм.рт.ст.)', min_value=60, max_value=200, value=sbp, step=1)
    chol_slide = pbox1.slider('Общий холестерин (ммоль/л)', min_value=0.00, max_value=20.00, value=total_chol, step=0.01)
    hdl_slide = pbox1.slider('ЛПВП (ммоль/л)', min_value=0.00, max_value=8.00, value=hdl, step=0.01)
    
    #if  hba1c and eGFR and hba1c !=0 and eGFR !=0:
    if age < 70:
        pbox2 = pic1.container(border=True, gap='xxsmall')
        pbox2.caption('Только для SCORE2-Diabetes')
        if diabetes_d == 'Есть':
            hba1c_slide = pbox2.slider('HbA1c (%)', min_value=3.00, max_value=20.00, value=hba1c, step=0.01)
            egf_slide = pbox2.slider('СКФ (мм/мин/1.73 м²)', min_value=0, max_value=160, value=eGFR, step=1)
        else:
            hba1c_slide = pbox2.slider('HbA1c (%)', min_value=3.00, max_value=20.00, value=0.00, step=0.01)
            egf_slide = pbox2.slider('СКФ (мм/мин/1.73 м²)', min_value=0, max_value=160, value=0, step=1)

    pbox3 = pic1.container(border=True, gap='xxsmall')
    pbox3.caption('Дополнительные параметры ✚') 
    if lpa_unit=='мг/дл':
        lpaslide = pbox3.slider(f'Lp(a) ({lpa_unit})', min_value=0.00, max_value=300.00, value=lpa, step=0.01)
    else:
        lpaslide = pbox3.slider(f'Lp(a) ({lpa_unit})', min_value=0.00, max_value=500.00, value=lpa, step=0.01)

    crp_slide = pbox3.slider('СРБ высокочувствительный (мг/л)', min_value=0.00, max_value=50.00, value=hs_crp, step=0.01)
    hcy_slide = pbox3.slider('Гомоцистеин (мкмоль/л)', min_value=0.00, max_value=50.00, value=hcy, step=0.01)

    def visual():
        x = range(age,89)
        x2 = range(age,101)

        SCORES_NOW = []
        SCORES = []
        SCORESOP_NOW = []
        SCORESOP = []
        SCORESD_NOW = []
        SCORESD = []
        BAYESIAN_NOW = []
        BAYESIAN = []
        BAYESIAN_D_NOW = []
        BAYESIAN_D = []
        BAYESIAN_OP_NOW = []
        BAYESIAN_OP = []
        fig, ax = plt.subplots(figsize=(8, 4.3),dpi=200)

        if age < 70:
            for n in range(age,89):
                sco_now = score2(sex = sex, age = n, smoke = smoke, sbp = sbp, total_chol = total_chol, hdl = hdl, region = region)
                sco2 = score2(sex = sex, age = n, smoke = kur_str, sbp = sad, total_chol = chol_slide, hdl = hdl_slide, region = region)
                if  diabetes_d == 'Есть' and hba1c !=0 and eGFR !=0:
                    scod_now = score2_diabetes(sex=sex, age=n, smoke=smoke, sbp=sbp, total_chol=total_chol, hdl=hdl, region=region, diabetes_d=diabetes_d, hba1c=hba1c, egfr=eGFR)
                    SCORESD_NOW.append(scod_now)
                    if lpaslide !=0 or chol_slide !=0 or crp_slide !=0:
                        bayes_d_now = bayesian_update_score(scod_now, hs_crp, hcy, lpa, lpa_unit)
                        BAYESIAN_D_NOW.append(bayes_d_now)
                if  hba1c_slide !=0 and egf_slide !=0:
                    diabetes_d_tut = ['Есть']
                    scod = score2_diabetes(sex=sex, age=n, smoke=kur_str, sbp=sad, total_chol=chol_slide, hdl=hdl_slide, region=region, diabetes_d=diabetes_d_tut, hba1c=hba1c_slide, egfr=egf_slide)
                    SCORESD.append(scod)
                    if lpaslide !=0 or chol_slide !=0 or crp_slide !=0:
                        bayes_d = bayesian_update_score(scod, crp_slide, hcy_slide, lpaslide, lpa_unit)
                        BAYESIAN_D.append(bayes_d)
                SCORES_NOW.append(sco_now)
                SCORES.append(sco2)
                if lpaslide !=0 or chol_slide !=0 or crp_slide !=0:
                    bayes_now = bayesian_update_score(sco_now, hs_crp, hcy, lpa, lpa_unit)
                    bayes = bayesian_update_score(sco2, crp_slide, hcy_slide, lpaslide, lpa_unit)
                    BAYESIAN_NOW.append(bayes_now)
                    BAYESIAN.append(bayes)

        else:
            for k in range(age,101):
                scoop_now = score2_op2(sex = sex, age = k, smoke = smoke, sbp = sbp, total_chol = total_chol, hdl = hdl, region = region, diabetes_op=diabetes_op)
                scoop = score2_op2(sex = sex, age = k, smoke = kur_str, sbp = sad, total_chol = chol_slide, hdl = hdl_slide, region = region, diabetes_op=diabetes_op)
                SCORESOP_NOW.append(scoop_now)
                SCORESOP.append(scoop) 
                if lpaslide !=0 or chol_slide !=0 or crp_slide !=0:
                    bayes_op_now = bayesian_update_score(scoop_now, hs_crp, hcy, lpa, lpa_unit)
                    bayes_op = bayesian_update_score(scoop, crp_slide, hcy_slide, lpaslide, lpa_unit)
                    BAYESIAN_OP_NOW.append(bayes_op_now)
                    BAYESIAN_OP.append(bayes_op)
        if age < 70:
            ax.scatter(age, score2(sex = sex, 
                                   age = age, 
                                   smoke = smoke, 
                                   sbp = sbp, 
                                   total_chol = total_chol, 
                                   hdl = hdl, 
                                   region = region), 
                                   s=80, 
                                   edgecolors='face', 
                                   alpha=0.8,
                                   label = 'Текущее значение SCORE2')
            if check_score2:
                ax.plot(x, SCORES_NOW, label = 'SCORE2', color='blue', ls='--', alpha=0.7, lw=1)
                ax.plot(x, SCORES, label = 'SCORE2 (ползунки)', color = 'darkblue')

            if diabetes_d == 'Есть' and hba1c !=0 and eGFR !=0 and check_score2_d:
                ax.scatter(age, score2_diabetes(sex = sex, 
                                                   age = age, 
                                                   smoke = smoke, 
                                                   sbp = sbp, 
                                                   total_chol = total_chol, 
                                                   hdl = hdl, 
                                                   region = region,
                                                   diabetes_d=diabetes_d, 
                                                   hba1c=hba1c, 
                                                   egfr=eGFR), 
                                                   s=80, 
                                                   edgecolors='face', 
                                                   alpha=0.8,
                                                   label = 'Текущее значение SCORE2-Diabetes')
                ax.plot(x, SCORESD_NOW, label = 'SCORE2-Diabetes', color='red', ls='--', alpha=0.7, lw=1)
            if (lpaslide !=0 or chol_slide !=0 or crp_slide !=0) and check_bayes_d and diabetes_d == 'Есть' and hba1c !=0 and eGFR !=0:
                ax.plot(x, BAYESIAN_D_NOW, label = 'SCORE2-Diabetes ✚ (тест)', color = 'black', ls='--', alpha=0.7, lw=1)
            if hba1c_slide !=0 and egf_slide !=0 and check_score2_d:
                ax.plot(x, SCORESD, label = 'SCORE2-Diabetes (ползунки)', color='red', ls='-')
            if (lpaslide !=0 or chol_slide !=0 or crp_slide !=0) and hba1c_slide !=0 and egf_slide !=0 and check_bayes_d:
                ax.plot(x, BAYESIAN_D, label = 'Тестовый SCORE2-Diabetes ✚ (ползунки)', color = 'chocolate', ls='-')


            if (lpaslide !=0 or chol_slide !=0 or crp_slide !=0) and check_bayes:
                ax.plot(x, BAYESIAN_NOW, label = 'SCORE2 ✚ (тест)', color = 'gold', ls='--',alpha=0.7, lw=1)
                ax.plot(x, BAYESIAN, label = 'Тестовый SCORE2 ✚ (ползунки)', color = 'magenta', ls='-')

        else:
            if check_score2_op:
                ax.scatter(age, score2_op2(sex = sex, 
                                            age = age, 
                                            smoke = smoke, 
                                            sbp = sbp, 
                                            total_chol = total_chol, 
                                            hdl = hdl, 
                                            region = region,
                                            diabetes_op=diabetes_op), 
                                            s=80, 
                                            edgecolors='face', 
                                            alpha=0.8,
                                            label = 'Текущее значение SCORE2-OP',
                                            color='green')
                ax.plot(x2, SCORESOP_NOW, label = 'SCORE2-OP', color='green', ls='--', alpha=0.7, lw=1)
                ax.plot(x2, SCORESOP, label = 'SCORE2-OP (ползунки)', color = 'lime')
            if (lpaslide + chol_slide + crp_slide) > 0.01 and check_bayes_op:
                ax.plot(x2, BAYESIAN_OP_NOW, label = 'SCORE2-OP ✚ (тест)', color = 'gold', ls='--', alpha=0.7, lw=1)
                ax.plot(x2, BAYESIAN_OP, label = 'Тестовый SCORE2-OP ✚ (ползунки)', color = 'magenta', ls='-')
        ax.set_ylabel('Риск %')
        ax.set_xlabel('Возраст')
        ax.set_title('Зависимость риска от параметров и возраста')
        ax.legend(fontsize='x-small')
        return fig
    vis = visual()
    pic2.pyplot(vis)

    st.info('Калькуляторы SCORE2/-OP/-Diabetes валидированы для соответствующих возрастов.  \n' \
    ' SCORE2 и SCORE2-Diabetes для дипазона 40-69 лет,  \n' \
    ' SCORE2-OP — 70-89 лет.  \n' \
    ' Отображение кривой на графике вне этих диапазонов является экстраполяцией')
    st.info('Пунктирные линии на графике отображают динамику только на основании введенных данных в формы заполнения.  \n ' \
    'Сплошные линии строятся на основании положения ползунков слева и дают возможность посмотреть, ' \
    'как изменится кривая риска при изменении того или иного фактора риска.  \n' \
    'HbA1c и СКФ применимы только для шкалы SCORE2-Diabetes (возраст 40-69 лет и выбрано в форме Диабет Есть)  \n ' \
    'Для дополнительных параметров (Lp(a), СРБ высокочувствительный и гомоцистеин) строятся тестовые SCORE2/-OP/-Diabetes ✚ линии  \n '\
    'Можно отключить отображение лишних шкал на графике с помощью переключателя')

            





