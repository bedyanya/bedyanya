import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import seaborn as sns
from scipy import stats
from statsmodels.nonparametric.kde import KDEUnivariate
from matplotlib import pyplot as plt
#from sklearn.linear_model import LinearRegression
from datetime import datetime,date, timedelta
from dateutil.relativedelta import relativedelta



uploaded_file = st.sidebar.file_uploader("Выбери файл Excel на компе с данными по образцу",
                                         type=['xlsx','xls'],
                                         help='NO HELP',
                                         accept_multiple_files=False)

st.info('**Шаблон Стандарт:** результаты в файле должны располагаться в одном столбце, можно несколько столбцов с разными результатами. Верхняя строчка - заголовок')
st.info('**Шаблон Интерсистемс:** результат выгрузки отчета по результатам теста за период. \
              Перед загрузкой файла удалите верхние строчки до заголовков колонок. \
              Перед загрузкой файла удалите столбцы с личными данными: ФИО, номером карты и т.д., \
              Необходимые столбцы для расчета:Результат, Прибор, Дата авторизации, Отделение, колонки с возрастом и Пол. \
              Удалите дубликаты по ФИО самостоятельно, если необходимо. \
              Дополнительного форматирования данных не требуется (перевод текстовых значений в числовые,форматирования дат) \
              Сохраните файл как Книгу Excel')

# ===================================================================
# Базовая модель (без преобразования данных)
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

    return X, A, UX, kde_f_y, yopt_std, Muopt, SDopt, L2, H2

# ГРАФИК Базовой модели
def show_base(X, A, UX, kde_f_y, yopt_std, Muopt, SDopt, L2, H2):
    fig1, ax1 = plt.subplots()
    fig1.suptitle(f'N = {len(X)}')
    ax1.set_title(f'Базовая модель. Референс: {L2} - {H2}')
    ax1.hist(A,density=True,bins = 80)
    ax1.plot(UX,kde_f_y,color='orange', linewidth=2)
    ax1.plot(UX,yopt_std,color='black',linewidth=2)
    #ax1.plot(UX,razn,color='g',linewidth=2)
    
    ax1.set_xlim(Muopt-5*SDopt,Muopt+5*SDopt)
    return fig1


#===============================================================================
# Модель с логарифмированием
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
    return X, UX, UXX, kde_f_y, yopt_std, Muopt, SDopt, LL2, HH2

# PLOT for log-transformation model
def show_log(X, UX, UXX, kde_f_y, yopt_std, Muopt, SDopt, LL2, HH2):   
    fig, ax = plt.subplots()
    fig.suptitle(f'N = {len(X)}')
    ax.set_title(f'Модель с логтрансформацией. Референс: {LL2} - {HH2}')
    ax.hist(X,density=True,bins = 80)
    ax.plot(UXX,kde_f_y,color='orange', linewidth=2)
    ax.plot(UX,yopt_std,color='black',linewidth=2)
    #ax.plot(UX,razn,color='g',linewidth=2)
    ax.set_xlim(Muopt-5*SDopt,Muopt+5*SDopt)
    return fig

#=========================================================================
# square root transformation (NEW)
# sqrt_funk_kde3(X)

def sqrt_funk_kde3(X):
    Low=[]
    High=[]
    mean=[]
    S=[]
    k=0
    YO=[]
    alphas = []
    
    #извлекаем корень
    X = np.sqrt(X)

# BOOTSTRAP:
    while k<100:
        A=np.random.choice(X,len(X))
        # Вычисляем IQR, избавляемся от больших выбросов (опционально):
        p25=np.percentile(A,25)
        p75=np.percentile(A,75)
        IQR=p75-p25
        A=A[(A>(np.median(A)-2*IQR)) & (A<(np.median(A)+3*IQR))]
    
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
        #aaa = np.mean(alphas)
        a=-0.1
        def OPT(params):
            sred, SDmin= params
            ymodel=(stats.norm(loc=sred,scale=SDmin)).pdf(UX)
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))

            # левая половина
            if alfa <=a:
                # ЕСЛИ ОПТИМИЗАЦИЯ МЕЖДУ 2S-moda
                Umodel=ymodel_std[i_2sigma1:i]
                Ukdemy=kde_m_y[i_2sigma1:i]
                # ЕСЛИ ОПТИМИЗАЦИЯ 2s-1s
                #Umodel=ymodel_std[i_2sigma1:i_sigma1]
                #Ukdemy=kde_m_y[i_2sigma1:i_sigma1]
                
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
                #Umodel=ymodel_std[i_2sigma1:i_sigma1]
                #Ukdemy=kde_m_y[i_2sigma1:i_sigma1]
                  
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
    probopt=np.max(kde_m_y)*yopt_std/kde_f_y
    razn = kde_f_y-yopt_std
    #razn2 = abs(yopt_std-razn)
    
    L2=((Muopt-1.96*SDopt)**2).round(2)
    H2=((Muopt+1.96*SDopt)**2).round(2)

    L3=((Muopt-2.6*SDopt)**2).round(2)
    H3=((Muopt+2.6*SDopt)**2).round(2)
    
    mu_convert = (Muopt**2).round(2)
    sd_before = (SDopt**2).round(2)
    sd2_convert = (mu_convert-L2).round(2)
    sd22_convert = (H2-mu_convert).round(2)
    sd_mean_convert = (sd2_convert+sd22_convert)/2
    HH2 = (mu_convert+sd2_convert).round(2)
    LL2 = (H2 - 2*sd2_convert).round(2)
    LL3 = mu_convert - sd_mean_convert
    HH3 = mu_convert + sd_mean_convert
    
    # heuristic correction
    chek_low = (LL2-L2)/(L2+LL2)
    if chek_low >0.7 and np.mean(alphas)>-0.3:
        L_cor = LL2.round(2)
    else:
        L_cor = L2.round(2)
        
    if np.mean(alphas)<=0.1:
        H_cor = HH2
    else:
        H_cor = H2
   
    return X, UX, kde_f_y, yopt_std, Muopt, SDopt, L_cor, H_cor   
   
# PLOT for sqrt root transformation model
def show_sqrt(X, UX, kde_f_y, yopt_std, Muopt, SDopt, L_cor, H_cor):
    fig, ax = plt.subplots()
    fig.suptitle(f'N = {len(X)}')
    ax.set_title(f'Модель square root transformation. Референс: {L_cor} - {H_cor}')
    ax.hist(X,density=True,bins = 80)
    ax.plot(UX,kde_f_y,color='orange', linewidth=2)
    ax.plot(UX,yopt_std,color='black',linewidth=2)
    #ax.plot(UX,razn,color='g',linewidth=2)
    ax.set_xlim(Muopt-5*SDopt,Muopt+5*SDopt)
    return fig

#===============================================================
# Таблица по возрастам
# ПОД МЕДСИ РЕФЫ ПО ВОЗРАСТАМ:
def show_age_table(funktion, df):
    #mf = df[df['Прибор']==analizer]
    if any(n in analizers for n in analizer):
        mf = df[df['Прибор'].isin(list(analizer))]
    else:
        mf = df 

    min_age = min(mf['Лет'])
    max_age = max(mf['Лет'])

    # сначала нам нужно набрать достаточное количество человек в возрастных группах
    # создаем список возрастов до которых мы набираем группу из n-человек (lisage), например по 200 человек, 
    # dlina - технический список с помощью которого мы набираем группы, суммируя n каждого возраста, обнуляется как только набрали группу
    lisage = []
    dlina = []

    for i in range(min_age,max_age):
        adf = len(mf[mf['Лет']==i])
        dlina.append(adf)
        if sum(dlina)>200:
            lisage.append(i)
            dlina = []
    
    # добавляем минимальный и максимальный возраст диапазона в список, если они не вошли в него        
    if lisage[0] != min_age:
         lisage = [min_age]+lisage

    if lisage[-1] != max_age:
        lisage.pop()
        lisage = lisage + [max_age]

    # Теперь соседние группы сравниваем с помощью KS-теста, если есть различия добавляем в новый список возрастов
    lis = [min_age]
    for i in range(0, len(lisage)-1):
        if lisage[i+1] != max_age:
            v1df = mf[(mf['Лет']>=lisage[i]) & (mf['Лет']<lisage[i+1])]
            v2df = mf[(mf['Лет']>=lisage[i+1]) & (mf['Лет']<lisage[i+2])]
            v1=v1df['Результат']
            v2=v2df['Результат']
            sta1, pval1 = stats.ks_2samp(v1,v2)
            if pval1<0.05:
                lis.append(lisage[i+1])
    lis.append(max_age)

    # Теперь в каждой возрастной группе сравниваем муж и жен с помощью KS-теста и делим, если есть разница
    age_group = []
    boys = []
    girls = []
    for k in range(0,len(lis)-1):
        group = mf[(mf['Лет']>=lis[k]) & (mf['Лет']<lis[k+1])]
        res_total = group['Результат']
        res_m = group[group['Пол']=='Мужской']['Результат']
        res_w = group[group['Пол']=='Женский']['Результат']
        sta2, pval2 = stats.ks_2samp(res_m,res_w)
    
        if pval2<0.05:
            lm, hm = funktion(res_m)[-2:]
            lw, hw = funktion(res_w)[-2:]
            age1 = f'{lis[k]}'+'-' f'{lis[k+1]}' 
            age_group.append(age1)
            M = f'{lm}'+ '-' + f'{hm}' + f' (N: {len(res_m)})'
            boys.append(M)
            W = f'{lw}'+ '-' + f'{hw}' f' (N: {len(res_w)})'
            girls.append(W)
        else: 
            lt, ht = funktion(res_total)[-2:]
            age1 = f'{lis[k]}'+'-' f'{lis[k+1]}' 
            age_group.append(age1)
            M = f'{lt}'+ '-' + f'{ht}' + f' (N: {len(res_total)})'
            W = f'{lt}'+ '-' + f'{ht}' + f' (N: {len(res_total)})'
            boys.append(M)
            girls.append(W)

    dict1 = {'Возраст (лет)':age_group, 'Мужчины':boys,'Женщины':girls}  

    return pd.DataFrame(dict1)



# UI ===================================================================
radio = st.sidebar.radio('**Шаблон**',options = ['стандарт','интерсистемс'])
radio_model = st.sidebar.radio('**Модель**', ['Среднее по пациентам','Свой вариант','kosmic','refineR'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, engine='openpyxl')
    st.write(df.head(10))

    if radio == 'стандарт':
        st.write('В загружаемом файле Excel результаты показателя должны быть в одном столбце, '
         'можно сразу несколько столбцов в одном файле, самая верхняя строка - заголовки для колонок') 
        select_test = st.sidebar.selectbox('Выбери столбец',df.columns)
        calc_norm = st.sidebar.button('Рассчитать по базовой модели')
        calc_log =  st.sidebar.button('Рассчитать по модели с логарифмированием')
        calc_sqrt = st.sidebar.button('Рассчитать по модели square root transformation')
        
        df = df[pd.to_numeric(df[select_test], errors='coerce').notnull()]
        df[select_test] = df[select_test].astype(float)

        if calc_norm:
            try:
                r = df[select_test].dropna()
                r=r.apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
                X, A, UX, kde_f_y, yopt_std, Muopt, SDopt, L2, H2 = funk_kde(r)
                st.pyplot(show_base(X, A, UX, kde_f_y, yopt_std, Muopt, SDopt, L2, H2))
            except:
                st.write('возможно, что-то не так с данными')
            

        if calc_log:
            try:
                l = df[select_test].dropna()
                l=l.apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
                X, UX, UXX, kde_f_y, yopt_std, Muopt, SDopt, LL2, HH2 = log_funk_kde(l)
                st.pyplot(show_log(X, UX, UXX, kde_f_y, yopt_std, Muopt, SDopt, LL2, HH2))
            except:
                st.write('возможно, что-то не так с данными')
        
        if calc_sqrt:
            try:
                sq = df[select_test].dropna()
                sq=sq.apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
                X, UX, kde_f_y, yopt_std, Muopt, SDopt, L_cor, H2 = sqrt_funk_kde3(sq)
                st.pyplot(show_sqrt(X, UX, kde_f_y, yopt_std, Muopt, SDopt, L_cor, H2))
            except:
                st.write('возможно, что-то не так с данными')
        
    
    if radio == 'интерсистемс':
         
        #df['Фамилия'].astype(str)
        #df['Имя'].astype(str)
        #df['Отчество'].astype(str)
        #df['ФИО'] = df['Фамилия'] + df['Имя'] + df['Отчество']
        #st.write('В файле нет ФИО, удаление дубликатов не произведено')
        #df = df.drop_duplicates(subset='ФИО')
        #df['Результат']=df['Результат'].apply(lambda x: float(str(x).replace('&gt;','')))
        df['Результат']=df['Результат'].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
        df['Дата авторизации'] = pd.to_datetime(df['Дата авторизации']).dt.date
        df['Прибор'] = df['Прибор'].fillna("не указан")
        df = df.dropna(subset=['Результат','Дата авторизации'])
        
        #st.write(df)
        
        depart = list(df['Отделение'].astype(str).sort_values().unique())
        analizers = list(df['Прибор'].astype(str).sort_values().unique())
                
        box = st.form('Фильтры')
        col1,col2,col3 = box.columns(3)
        #analizer = col1.selectbox('Прибор',df['Прибор'].unique())
        minage = col2.number_input('Возраст от (лет)',min_value=0,max_value=100,step=1)
        maxage = col3.number_input('Возраст до (лет)',min_value=1,max_value=120,step=1)
        sex = col1.selectbox('Пол',['Все','Мужской','Женский'])
        date_from = col2.date_input('Дата авторизации (от)',min(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
        date_to = col3.date_input('Дата авторизации (до)', max(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
        analizer = box.multiselect('Приборы', placeholder= 'Оставьте поле пустым, если нужны все приборы', options=analizers)
        department = box.multiselect('Отделения', placeholder = 'Оставьте поле пустым, если нужны все отделения' , options=depart)
        col11 , col22 = box.columns(2)
        

        #sdf = df[df['Прибор']==analizer]
        sdf = df[(df['Лет']>=minage) & (df['Лет']<=maxage)]
        
        sdf = sdf[(sdf['Дата авторизации']>=date_from) & (sdf['Дата авторизации']<=date_to)]
        
        if any(n in analizers for n in analizer):
            sdf = sdf[sdf['Прибор'].isin(list(analizer))]
        else:
            pass 

        if any(n in depart for n in department):
            sdf = sdf[sdf['Отделение'].isin(list(department))]
        else:
            pass

        #sex = st.sidebar.selectbox('Пол',['Все','Мужской','Женский'])

        if sex == 'Все':
            pass
        else:
            sdf = sdf[sdf['Пол']==sex]
        
        # Scatter-plot для результатов
        def show_age_scatter():
            fig,ax = plt.subplots()
            fig.set_size_inches(14,6)
            sns.scatterplot(data=sdf, x='Лет', y='Результат', hue = 'Пол')
            ax.set_xlabel('Возраст')
            ax.set_ylabel('Результат')
            iqr=np.percentile(sdf['Результат'],75) - np.percentile(sdf['Результат'],25)
            ax.set_ylim(np.median(sdf['Результат'])-2*iqr,np.median(sdf['Результат'])+5*iqr)
            ax.set_title('Динамика изменения показателя с возрастом')
            return fig
        
        # общий график распределения данных в соответствии с фильтрами
        def distribution_plot(sdf):
            fig, ax = plt.subplots()
            fig.set_size_inches(14,6)
            ax.set_title("Распределение данных")
            if sex == 'Все':
                M = sdf[sdf['Пол']=="Мужской"]['Результат']
                W = sdf[sdf['Пол']=="Женский"]['Результат']
                iqrm=np.percentile(M,75) - np.percentile(M,25)
                iqrw=np.percentile(W,75) - np.percentile(W,25)
                Mp=M[(M>(np.median(M)-2*iqrm)) & (M<(np.median(M)+3*iqrm))]
                Wp=W[(W>(np.median(W)-2*iqrw)) & (W<(np.median(W)+3*iqrw))]
                ax.hist(Mp, color='blue', alpha=0.6, bins=80, edgecolor = 'black', label = 'Мужчины')
                ax.hist(Wp, color='pink', alpha=0.6, bins=80, edgecolor = 'black', label = 'Женщины')
                ax.set_xlabel('Результат')
                ax.set_ylabel('Частота')
                ax.legend()
            if sex == 'Мужской':
                M = sdf[sdf['Пол']=="Мужской"]['Результат']
                iqrm=np.percentile(M,75) - np.percentile(M,25)
                Mp=M[(M>(np.median(M)-2*iqrm)) & (M<(np.median(M)+3*iqrm))]
                ax.hist(Mp, color='blue', alpha=0.6, bins=80, edgecolor = 'black', label = 'Мужчины')
                ax.set_xlabel('Результат')
                ax.set_ylabel('Частота')
                ax.legend()
            if sex == 'Женский':
                W = sdf[sdf['Пол']=="Женский"]['Результат']
                iqrw=np.percentile(W,75) - np.percentile(W,25)
                Wp=W[(W>(np.median(W)-2*iqrw)) & (W<(np.median(W)+3*iqrw))]
                ax.hist(Wp, color='pink', alpha=0.6, bins=80, edgecolor = 'black', label = 'Женщины')
                ax.set_xlabel('Результат')
                ax.set_ylabel('Частота')
                ax.legend()           
            return fig
        
        # График распределения данных для разных приборов
        def analizers_plot(df):
            fig, ax = plt.subplots()
            fig.set_size_inches(14,6)
            ax.set_title("Распределение данных для разных приборов")
            if len(analizer)>0:
                for a in analizer:
                    pribor = df[df['Прибор']==a]['Результат']
                    iqra = np.percentile(pribor,75) - np.percentile(pribor,25)
                    p_pribor = pribor[(pribor>(np.median(pribor)-2*iqra)) & (pribor<(np.median(pribor)+3*iqra))]
                    ax.hist(p_pribor, density=True, alpha=0.3, bins=80, edgecolor = 'black', label = a)
            else:
                for a in df['Прибор'].unique():
                    pribor = df[df['Прибор']==a]['Результат']
                    iqra = np.percentile(pribor,75) - np.percentile(pribor,25)
                    p_pribor = pribor[(pribor>(np.median(pribor)-2*iqra)) & (pribor<(np.median(pribor)+3*iqra))]
                    ax.hist(p_pribor, density=True, alpha=0.3, bins=80, edgecolor = 'black', label = a)
            ax.set_xlabel('Результат')
            ax.set_ylabel('Относительная частота')
            ax.legend()
            return fig     


        if radio_model == 'Свой вариант':
            info1 = col11.write('*Для расчёта используйте фильтры выше*')
            info2 = col22.write('*Для таблиц выбрать только приборы*')
            calc_norm2 = col11.form_submit_button('**Рассчитать по базовой модели (без преобразования данных)**')
            calc_log2 =  col11.form_submit_button('**Рассчитать по модели log-tranform with heuristic correction**')
            calc_sqrt2 = col11.form_submit_button('**Рассчитать по модели square root transformation with heuristic correction**')
            table_norm = col22.form_submit_button('Таблица референсов по возрасту и полу (базовая модель)')
            table_log = col22.form_submit_button('Таблица референсов по возрасту и полу (log-model)')
            table_sqrt = col22.form_submit_button('Таблица референсов по возрасту и полу (sqrt root tranform-model)')

            if calc_norm2:
                try:
                    st.info('**Базовый алгоритм** находит составляющую в данных с нормальным распределением. ' \
                    'Не подходит, если искомое распределение с ассиметрией')
                    X, A, UX, kde_f_y, yopt_std, Muopt, SDopt, L2, H2 = funk_kde(sdf['Результат'])
                    st.pyplot(show_base(X, A, UX, kde_f_y, yopt_std, Muopt, SDopt, L2, H2))
                    st.pyplot(show_age_scatter())
                    st.pyplot(distribution_plot(sdf))
                    st.pyplot(analizers_plot(df))
                except:
                    st.write('возможно, что-то не так с данными')
            
            if calc_log2:
                try:
                    st.info('**Модель с логтрансформацией** предпочтительнее, ' \
                    'когда данные не имеют нормального распределения и/или имеют много примесей)' \
                    'Алгоритм не подразумевает прямой обратной трансформации данных после вычислений.' \
                    'Недостатком в некоторых случаях может служить некоторое завышение нижней границы и занижение верхней границы.' )
                    X, UX, UXX, kde_f_y, yopt_std, Muopt, SDopt, LL2, HH2 = log_funk_kde(sdf['Результат'])
                    st.pyplot(show_log(X, UX, UXX, kde_f_y, yopt_std, Muopt, SDopt, LL2, HH2))
                    st.pyplot(show_age_scatter())
                    st.pyplot(distribution_plot(sdf))
                    st.pyplot(analizers_plot(df))
                except:
                    st.write('возможно, что-то не так с данными')
            
            if calc_sqrt2:
                try:
                    st.info('**Модель с преобразованием квадратного корня**. ' \
                    'Данный вид преобразования действует аналогично логарифмическому преобразованию, но менее агрессивно.' \
                    'В алгоритм встроена автоматическая коррекция верхней/нижней границы на основании эмпирически выведенного критерия. ' \
                    'Алгоритм неплохо отрабатывает на большинстве данных как с нормальным распределением, так и с ассиметрией')
                    X, UX, kde_f_y, yopt_std, Muopt, SDopt, L_cor, H2 = sqrt_funk_kde3(sdf['Результат'])
                    st.pyplot(show_sqrt(X, UX, kde_f_y, yopt_std, Muopt, SDopt, L_cor, H2))
                    st.pyplot(show_age_scatter())
                    st.pyplot(distribution_plot(sdf))
                    st.pyplot(analizers_plot(df))
                except:
                    st.write('возможно, что-то не так с данными')

            if table_norm:
                try:
                    st.info('Принцип деления по возрасту и полу:\
                            1) Сначала проверяется количество проб каждого возраста, затем ближайшие по возрасту объединяются, ' \
                            'если данных недостаточно. \
                            2) Каждая набранная группа сравнивается с соседней, используя тест Колмогорова-Смирнова для двух выборок,' \
                            'если тест показывает статистически значимое различие, выборки дальше тестируются отдельно,' \
                            'если тест не показывает различий, группы объединяются. \
                            3) После разделения по возрасту внутри каждой группы проводится разделение по полу так же ' \
                            'с помощью теста Колмогорова-Смирнова. \
                            Обратите внимание, если количество проб среди лиц конкретного возраста слишком мало, ' \
                            'может произойти некорректное объединение возрастных групп.')
                    st.subheader('Base model')
                    st.dataframe(show_age_table(funk_kde, df), hide_index=True)
                except:
                    st.write('что-то пошло не так')

            if table_log:
                try:
                    st.info('Принцип деления по возрасту и полу:\
                            1) Сначала проверяется количество проб каждого возраста, затем ближайшие по возрасту объединяются, ' \
                            'если данных недостаточно. \
                            2) Каждая набранная группа сравнивается с соседней, используя тест Колмогорова-Смирнова для двух выборок,' \
                            'если тест показывает статистически значимое различие, выборки дальше тестируются отдельно,' \
                            'если тест не показывает различий, группы объединяются. \
                            3) После разделения по возрасту внутри каждой группы проводится разделение по полу так же ' \
                            'с помощью теста Колмогорова-Смирнова. \
                            Обратите внимание, если количество проб среди лиц конкретного возраста слишком мало, ' \
                            'может произойти некорректное объединение возрастных групп.')
                    st.subheader('Log-transformation heuristic model')
                    st.dataframe(show_age_table(log_funk_kde, df), hide_index=True)
                except:
                    st.write('что-то пошло не так')
            
            if table_sqrt:
                try:
                    st.info('Принцип деления по возрасту и полу:\
                            1) Сначала проверяется количество проб каждого возраста, затем ближайшие по возрасту объединяются, ' \
                            'если данных недостаточно. \
                            2) Каждая набранная группа сравнивается с соседней, используя тест Колмогорова-Смирнова для двух выборок,' \
                            'если тест показывает статистически значимое различие, выборки дальше тестируются отдельно,' \
                            'если тест не показывает различий, группы объединяются. \
                            3) После разделения по возрасту внутри каждой группы проводится разделение по полу так же ' \
                            'с помощью теста Колмогорова-Смирнова. \
                            Обратите внимание, если количество проб среди лиц конкретного возраста слишком мало, ' \
                            'может произойти некорректное объединение возрастных групп.')
                    st.subheader('Square root transformation model')
                    st.dataframe(show_age_table(sqrt_funk_kde3, df), hide_index=True)
                except:
                    st.write('что-то пошло не так')
    



        if radio_model == 'kosmic':
            box.form_submit_button('Рассчитать по модели kosmic')
            st.write('Когда-нибудь появится')

        if radio_model == 'refineR':
            box.form_submit_button('Рассчитать по модели refineR')
            st.write('Когда-нибудь здесь появится и эта модель')

        if radio_model == 'Среднее по пациентам':
            dynamic = box.form_submit_button('Показать ди намику')
            unique_date = sorted(sdf['Дата авторизации'].unique())
            ran = list(range(1,len(unique_date)+1))

            M=[]
            Med =[]
            per25 = []
            per75=[]

            for n in unique_date:
                 mdf = sdf[sdf['Дата авторизации']==n]
                 MEAN = mdf['Результат'].mean()
                 meds = mdf['Результат'].median()
                 M.append(MEAN)
                 Med.append(meds)
    
                 q1 = np.percentile(mdf['Результат'],25)
                 per25.append(q1)
    
                 q2= np.percentile(mdf['Результат'],75)
                 per75.append(q2)

            if dynamic:
                try:
                    fig2, ax2 = plt.subplots()
                    fig2.set_size_inches(14,8)
                    ax2.plot(ran,M,color='r',label='Среднее')
                    ax2.plot(ran,Med,color='y',label='Медиана')
                    ax2.plot(ran,per25,color='g',label='перцентиль 25%')
                    ax2.plot(ran,per75,color='b',label='перцентиль 75')
                    ax2.set_title('Среднее/медиана/перцентили по дням')
                    ax2.set_xlabel('Дни')
                    ax2.legend()
                    
                    st.pyplot(fig2)
                except:
                    st.write('Не получилось рассчитать')
                     









