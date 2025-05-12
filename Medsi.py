import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import seaborn as sns
from scipy import stats
from statsmodels.nonparametric.kde import KDEUnivariate
from matplotlib import pyplot as plt
#from sklearn.linear_model import LinearRegression
#from datetime import datetime,date, timedelta
#from dateutil.relativedelta import relativedelta

st.title('Расчет референсных интервалов по алгоритму')
st.text('В загружаемом файле Excel результаты показателя должны быть в одном столбце, можно сразу несколько столбцов в одном файле, самая верхняя строка - заголовки для колонок')
st.text('Базовая модель работает лучше, когда в норме показатель имеет приближенно нормальное распределение и нет большой примеси патологических результатов. В большинстве случаев предпочтительнее модель с предварительным логарифмированием данных')
uploaded_file = st.sidebar.file_uploader("Выбери файл Excel на компе с данными по образцу",type='xlsx')

def funk_kde(X):
    Low=[]
    High=[]
    mean=[]
    S=[]
    k=0
    YO=[]
    alphas = []

# BOOTSTRAP:
    while k<100:
        A=np.random.choice(X,len(X))
        # Вычисляем IQR, избавляемся от больших выбросов (опционально):
        p25=np.percentile(A,25)
        p75=np.percentile(A,75)
        IQR=p75-p25
        A=A[(A>(np.median(A)-3*IQR)) & (A<(np.median(A)+3*IQR))]
    
        A=sorted(A)

        # Получаем функцию плотности для наших данных с помощью KDEUnivariate

        # старый вариант, где UX - уникальные элементы из первоначальной выборки:
        UX=np.unique(A)
        kde_m=KDEUnivariate(A)
        kde_m.fit(kernel='gau',bw='normal_reference')
        kde_m_y=kde_m.evaluate(UX)
        #оценка функции плотностии на каждом этапе бутстрепа
        #kde_m_ax = kde_m.evaluate(AX)
        #YO.append(kde_m_ax)

        # Находим индекс максимального значения функции плотности ("моды")
        Max_KDE=np.max(kde_m_y)
        i=np.where(kde_m_y==Max_KDE)[0][0]

        # Функция для нахождения ближайшего значения до "моды"
        def find_nearest1(x,n):
            x1=x[:i]
            nearest1=(np.abs(x1-n)).argmin()
            return x1[nearest1]

        # Значение плотности в np.exp(1/2) раз меньшее, чем максимальное
        KDE_y_sigma = Max_KDE/(np.exp(1/2))
        KDE_y_2sigma = Max_KDE/(np.exp(2))
        # Находим оценку SD как расстояние от "моды" до значения, где плотность в np.exp(1/2) раз меньше 
        Nsd1=find_nearest1(kde_m_y, KDE_y_sigma)
        N2sd1=find_nearest1(kde_m_y, KDE_y_2sigma)
        i_sigma1=np.where(kde_m_y==Nsd1)[0][0]
        i_2sigma1=np.where(kde_m_y==N2sd1)[0][0]
        SD1=np.abs(UX[i_sigma1]-UX[i])
    

        # Функция для нахождения ближайшего значения после "моды"
        def find_nearest2(x,n):
            x2=x[i:]
            nearest2=(np.abs(x2-n)).argmin()
            return x2[nearest2]
        # Проводим такую же оценку для значений в правой части распределения от "моды"
        Nsd2=find_nearest2(kde_m_y, KDE_y_sigma)
        N2sd2=find_nearest2(kde_m_y, KDE_y_2sigma)
        i_sigma2=np.where(kde_m_y==Nsd2)[0][0]
        i_2sigma2=np.where(kde_m_y==N2sd2)[0][0]
        SD2=np.abs(UX[i_sigma2]-UX[i])
        
    
        # Среднее значение стандартного отклонения двух оценок:
        SD=(SD1+SD2)/2

        # Переводим значения плотности в диапазон от 0 до 1
        #kde_m_y_std=kde_m_y/np.max(kde_m_y)

        #
        # Оптимизация. Поиск наилучших Mu и Sigmа на интервале:
        # Функция возвращает оценку MSE
        # В ней заложен Дифференцированный подход к выбору участка функции плотности
        #Параметр alfpha
        S21=np.abs(UX[i_2sigma1]-UX[i])
        S22=np.abs(UX[i_2sigma2]-UX[i])
        alfa = ((np.median(A)-np.percentile(A,16))-(np.percentile(A,84)-np.median(A)))/IQR
        #alfa=(S21-S22)/SD
        alphas.append(alfa)
        a=-0.1
        def OPT(params):
            sred, SDmin= params
            ymodel=(stats.norm(loc=sred,scale=SDmin)).pdf(UX)
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))
        
            # левая половина
            if alfa <=a:
                Umodel=ymodel_std[i_2sigma1:i]
                Ukdemy=kde_m_y[i_2sigma1:i]
            else:
                pass
            # правая половина
            if alfa >= -a:
                Umodel=ymodel_std[i:i_2sigma2]
                # используем только кусок распределения между 1 и 2 сигмами с одной стороны
                #Umodel=ymodel_std[i_sigma2:i_2sigma2]
                Ukdemy=kde_m_y[i:i_2sigma2]
                # используем только кусок распределения между 1 и 2 сигмами с одной стороны
                #Ukdemy=kde_m_y[i_sigma2:i_2sigma2]
            
            else:
                pass
            # середина
            if (alfa >a and alfa <-a):
                Umodel=ymodel_std[i_sigma1:i_sigma2]
                Ukdemy=kde_m_y[i_sigma1:i_sigma2]
            else:
                pass
            #return np.mean(abs(Umodel-Ukdemy))
            return np.mean((Umodel-Ukdemy)**2)


         # Минимизация функции MSE для поиска наилучших среднего и стандартного отклонения, описывающих данные в диапазоне
        def MIN():
            x0=np.array([UX[i],SD])
            return minimize (OPT,x0,tol=1e-3,method='Nelder-Mead')
        D=MIN().x  

        Mu=D[0].round(2)
        Si=D[1].round(2)
    
        yopt=(stats.norm(loc=Mu,scale=Si)).pdf(UX)
        yopt_std=np.max(kde_m_y)*yopt/np.max(yopt)
        probopt=yopt_std/kde_m_y
    
    

    
    
        L=(Mu-1.96*Si).round(2)
        H=(Mu+1.96*Si).round(2)
    
        Low.append(L)
        High.append(H)
        mean.append(Mu)
        S.append(Si)
        k=k+1
    
    # Среднее значение оценок после бутстрепа
    Muopt=np.mean(mean).round(2)
    SDopt=np.mean(S)
    # Распределение, исходя из этих оценок
    yopt=(stats.norm(loc=Muopt,scale=SDopt)).pdf(UX)
    yopt_std=np.max(kde_m_y)*yopt/np.max(yopt)
    # Оценка функции плотности первоначальных данных
    kde_f=KDEUnivariate(X)
    kde_f.fit(kernel='gau',bw='normal_reference')
    kde_f_y=kde_m.evaluate(UX)
    #kde_f_y_std=kde_f_y/np.max(kde_f_y)

    # Расчет "вероятности" как отношение функций плотности (здесь масштаб порушен множителем np.max(kde_m_y))
    #probopt=np.max(kde_m_y)*yopt_std/kde_f_y
    #razn = kde_f_y-yopt_std
    #razn2 = abs(yopt_std-razn)
    
    L2=(Muopt-1.96*SDopt).round(2)
    H2=(Muopt+1.96*SDopt).round(2)

    L3=(Muopt-2.6*SDopt).round(2)
    H3=(Muopt+2.6*SDopt).round(2)
    #st.write(Muopt)
    #st.write(H2)
    #st.write(SDopt)

    # ГРАФИК
    fig1, ax1 = plt.subplots()
    ax1.set_title(f'Базовая модель. Референс: {L2} - {H2}')
    ax1.hist(A,density=True,bins = 80)
    ax1.plot(UX,kde_f_y,color='orange', linewidth=2)
    ax1.plot(UX,yopt_std,color='black',linewidth=2)
    #ax1.plot(UX,razn,color='g',linewidth=2)
    
    ax1.set_xlim(Muopt-5*SDopt,Muopt+5*SDopt)
    st.pyplot(fig1)



def log_funk_kde(X):
    Low=[]
    High=[]
    mean=[]
    S=[]
    k=0
    YO=[]
    alphas = []
    
    # логарифмируем
    X=np.log(X)
    
    # BOOTSTRAP:
    while k<100:
        A=np.random.choice(X,len(X))
        # Вычисляем IQR, избавляемся от больших выбросов (опционально):
        p25=np.percentile(A,25)
        p75=np.percentile(A,75)
        IQR=p75-p25
        A=A[(A>(np.median(A)-3*IQR)) & (A<(np.median(A)+3*IQR))]
    
        A=sorted(A)

        # Получаем функцию плотности для наших данных с помощью KDEUnivariate

        # старый вариант, где UX - уникальные элементы из первоначальной выборки:
        UX=np.unique(A)
        kde_m=KDEUnivariate(A)
        kde_m.fit(kernel='gau',bw='normal_reference')
        kde_m_y=kde_m.evaluate(UX)
        #оценка функции плотностии на каждом этапе бутстрепа
        #kde_m_ax = kde_m.evaluate(AX)
        #YO.append(kde_m_ax)

        # Находим индекс максимального значения функции плотности ("моды")
        Max_KDE=np.max(kde_m_y)
        i=np.where(kde_m_y==Max_KDE)[0][0]

        # Функция для нахождения ближайшего значения до "моды"
        def find_nearest1(x,n):
            x1=x[:i]
            nearest1=(np.abs(x1-n)).argmin()
            return x1[nearest1]

        # Значение плотности в np.exp(1/2) раз меньшее, чем максимальное
        KDE_y_sigma = Max_KDE/(np.exp(1/2))
        KDE_y_2sigma = Max_KDE/(np.exp(2))
        # Находим оценку SD как расстояние от "моды" до значения, где плотность в np.exp(1/2) раз меньше 
        Nsd1=find_nearest1(kde_m_y, KDE_y_sigma)
        N2sd1=find_nearest1(kde_m_y, KDE_y_2sigma)
        i_sigma1=np.where(kde_m_y==Nsd1)[0][0]
        i_2sigma1=np.where(kde_m_y==N2sd1)[0][0]
        SD1=np.abs(UX[i_sigma1]-UX[i])
    

        # Функция для нахождения ближайшего значения после "моды"
        def find_nearest2(x,n):
            x2=x[i:]
            nearest2=(np.abs(x2-n)).argmin()
            return x2[nearest2]
        # Проводим такую же оценку для значений в правой части распределения от "моды"
        Nsd2=find_nearest2(kde_m_y, KDE_y_sigma)
        N2sd2=find_nearest2(kde_m_y, KDE_y_2sigma)
        i_sigma2=np.where(kde_m_y==Nsd2)[0][0]
        i_2sigma2=np.where(kde_m_y==N2sd2)[0][0]
        SD2=np.abs(UX[i_sigma2]-UX[i])
        
    
        # Среднее значение стандартного отклонения двух оценок:
        SD=(SD1+SD2)/2

        # Переводим значения плотности в диапазон от 0 до 1
        #kde_m_y_std=kde_m_y/np.max(kde_m_y)

        #
        # Оптимизация. Поиск наилучших Mu и Sigmа на интервале:
        # Функция возвращает оценку MSE
        # В ней заложен Дифференцированный подход к выбору участка функции плотности
        #Параметр alfpha
        S21=np.abs(UX[i_2sigma1]-UX[i])
        S22=np.abs(UX[i_2sigma2]-UX[i])
        alfa = ((np.median(A)-np.percentile(A,16))-(np.percentile(A,84)-np.median(A)))/IQR
        #alfa=(S21-S22)/SD
        alphas.append(alfa)
        a=-0.1
        def OPT(params):
            sred, SDmin= params
            #генерируем нормальное распределение с параметрами и вычисляем значение функции плотности в каждой точке значения распределения
            ymodel=(stats.norm(loc=sred,scale=SDmin)).pdf(UX)
            #переводим в один масштаб
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))
        
            # левая половина
            if alfa <=a:
                Umodel=ymodel_std[i_2sigma1:i]
                Ukdemy=kde_m_y[i_2sigma1:i]
            else:
                pass
            # правая половина
            if alfa >= -a:
                Umodel=ymodel_std[i:i_2sigma2]
                # используем только кусок распределения между 1 и 2 сигмами с одной стороны
                #Umodel=ymodel_std[i_sigma2:i_2sigma2]
                Ukdemy=kde_m_y[i:i_2sigma2]
                # используем только кусок распределения между 1 и 2 сигмами с одной стороны
                #Ukdemy=kde_m_y[i_sigma2:i_2sigma2]
            
            else:
                pass
            # середина
            if (alfa >a and alfa <-a):
                Umodel=ymodel_std[i_sigma1:i_sigma2]
                Ukdemy=kde_m_y[i_sigma1:i_sigma2]
            else:
                pass
            #return np.mean(abs(Umodel-Ukdemy))
            return np.mean((Umodel-Ukdemy)**2)


         # Минимизация функции MSE для поиска наилучших среднего и стандартного отклонения, описывающих данные в диапазоне
        def MIN():
            x0=np.array([UX[i],SD])
            return minimize (OPT,x0,tol=1e-3,method='Nelder-Mead')
        D=MIN().x  

        Mu=D[0].round(2)
        Si=D[1].round(2)
    
        yopt=(stats.norm(loc=Mu,scale=Si)).pdf(UX)
        yopt_std=np.max(kde_m_y)*yopt/np.max(yopt)
        probopt=yopt_std/kde_m_y
     
    
        L=(Mu-1.96*Si).round(2)
        H=(Mu+1.96*Si).round(2)
    
        Low.append(L)
        High.append(H)
        mean.append(Mu)
        S.append(Si)
        k=k+1
    # Среднее значение оценок после бутстрепа
    Muopt=np.mean(mean).round(2)
    SDopt=np.mean(S)
    #---------------------------------------------
    # Распределение, исходя из этих оценок
    #yopt=(stats.norm(loc=Muopt,scale=SDopt)).pdf(UX)
    #yopt_std=np.max(kde_m_y)*yopt/np.max(yopt)
    #---------------------------------------------
    # Оценка функции плотности первоначальных данных
    kde_f=KDEUnivariate(X)
    kde_f.fit(kernel='gau',bw='normal_reference')
    UXX=np.unique(X)
    kde_f_y=kde_m.evaluate(UXX)
    #---------------------------------------------
    kde_f_y_std=kde_f_y/np.max(kde_f_y)

    # Расчет "вероятности" как отношение функций плотности (здесь масштаб порушен множителем np.max(kde_m_y))
    #probopt=np.max(kde_m_y)*yopt_std/kde_f_y
    #razn = kde_f_y-yopt_std
    #razn2 = abs(yopt_std-razn)
    
    L2=(Muopt-1.96*SDopt).round(2)
    H2=(Muopt+1.96*SDopt).round(2)

    L3=(Muopt-2.6*SDopt).round(2)
    H3=(Muopt+2.6*SDopt).round(2)
    #print('Muopt:', Muopt)
    #print('Низ Оптимум:',L2)
    #print('Верх Оптимум:',H2)
    #print('SDopt:',SDopt.round(2))
    #------------------------------------------------------------------------------------------------------

    #print(f'{n}')
    #print('НИЗ logL2:',(np.exp(L2)).round(2))
    #print('lohH2:',np.exp(H2).round(2))

    #print('logMu:',np.exp(Muopt).round(2))

    #print('Альт.ВЕРХ:',(np.exp(Muopt)+np.exp(Muopt)-np.exp(L2)).round(2))
    #print('--------')

    LL2 = np.exp(L2).round(2)
    HH2 = (np.exp(Muopt)+np.exp(Muopt)-np.exp(L2)).round(2)

    #st.write(f'{(np.exp(L2)).round(2)} -  {(np.exp(Muopt)+np.exp(Muopt)-np.exp(L2)).round(2)}')

        # ТОЛЬКО ОДИН ГРАФИК ЕСЛИ НУЖЕН
    
    #title = ddf['ПОКАЗАТЕЛЬ'].reset_index(drop=True)[0]
    #plt.title(title)
    
    fig, ax = plt.subplots()
    ax.set_title(f'N = {len(X)}')
    ax.set_title('Модель с логтрансформацией')
    ax.set_title(f'Референс: {LL2} - {HH2}')
    ax.hist(X,density=True,bins = 80)
    ax.plot(UXX,kde_f_y,color='orange', linewidth=2)
    ax.plot(UX,yopt_std,color='black',linewidth=2)
    #ax.plot(UX,razn,color='g',linewidth=2)
    ax.set_xlim(Muopt-5*SDopt,Muopt+5*SDopt)
    st.pyplot(fig)




if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, engine='openpyxl')
    st.write(df.head(10))

    select_test = st.sidebar.selectbox('Выбери столбец',df.columns)

    calc_norm = st.sidebar.button('Рассчитать по базовой модели')
    

    calc_log =  st.sidebar.button('Рассчитать по модели с логарифмированием')
    if calc_norm:
        r = df[select_test].dropna()
        funk_kde(r)

    if calc_log:
        l = df[select_test].dropna()
        log_funk_kde(l)



