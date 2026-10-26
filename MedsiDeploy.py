import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import seaborn as sns
from scipy import stats
from statsmodels.nonparametric.kde import KDEUnivariate
from matplotlib import pyplot as plt


#========================================================

#========================================================

st.set_page_config(layout="wide")

st.header('Непрямой метод расчёта РИ')
uploaded_file = st.file_uploader("**📤 Загрузите файл Excel**",
                                         type=['xlsx','xls'],
                                         help='NO HELP',
                                         accept_multiple_files=False)
st.info('❗ Данная модель является исследовательской и не предназначена для установления/верификации РИ, ' \
        'разрабатывалась для работы со смешанными данными. ' \
        ' В данной модели взгляд на РИ отличается от общепринятого (95 % интервала референтной популяции) ' \
' и для распределений, скошенных вправо, определяется через геометрию формы распределения. ' \
'Для нормальных распределений геометрические РИ совпадают с классическими, и алгоритм вычисления отличается ' \
' от других непрямых методов лишь методологией')
ch1, ch2 = st.columns(2)
ch1.info('**Шаблон Стандарт:** Универсальный шаблон. Результаты должны быть расположены в одном столбце. Верхняя строка - заголовок. Если есть столбцы с возрастом и полом, можно воспользоваться фильтром (опционально)')
ch2.info('**Шаблон Интерсистемс:** результат выгрузки отчета по результатам теста за период. \
              Перед загрузкой файла удалите верхние строчки до заголовков колонок. \
              Перед загрузкой файла удалите столбцы с личными данными: ФИО, номером карты и т.д., \
              Необходимые столбцы для расчета:Результат, Прибор, Дата авторизации, Отделение, колонки с возрастом и Пол. \
              Удалите дубликаты по ФИО самостоятельно, если необходимо. \
              Дополнительного форматирования данных не требуется (перевод текстовых значений в числовые,форматирования дат) \
              Сохраните файл как Книгу Excel')

# ===================================================================
# это база

def funk_kde(X):
    Low_ls=[]
    High_ls=[]
    mean_ls=[]
    S_ls=[]
    
    Low_rs=[]
    High_rs=[]
    mean_rs=[]
    S_rs=[]
    
    Low_ms=[]
    High_ms=[]
    mean_ms=[]
    S_ms=[]
    
   
    k=0

    pbar = st.progress(value=0, text = 'Тужусь, пыжусь, вычисляю...')

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

        # 
        UX=np.unique(A)
        kde_m=KDEUnivariate(A)
        kde_m.fit(kernel='gau',bw='normal_reference')
        kde_m_y=kde_m.evaluate(UX)

        # Находим индекс максимального значения функции плотности ("моды")
        Max_KDE=np.max(kde_m_y)
        i=np.where(kde_m_y==Max_KDE)[0][0]

        # Функция для нахождения ближайшего значения до "моды"
        def find_nearest1(x,n):
            x1=x[:i]
            nearest1=(np.abs(x1-n)).argmin()
            return x1[nearest1]

        # новые участки оптимизации:
        maxio = Max_KDE/1.05   #1.03
        KDE_y_sigma = Max_KDE/2.5
        KDE_y_2sigma = Max_KDE/6
        
        # Находим участки
        Nsd01=find_nearest1(kde_m_y, maxio)
        Nsd1=find_nearest1(kde_m_y, KDE_y_sigma)
        N2sd1=find_nearest1(kde_m_y, KDE_y_2sigma)
        io1=np.where(kde_m_y==Nsd01)[0][0]
        i_sigma1=np.where(kde_m_y==Nsd1)[0][0]
        i_2sigma1=np.where(kde_m_y==N2sd1)[0][0]
        SD1=np.abs(UX[i_sigma1]-UX[i])
    
        # Функция для нахождения ближайшего значения после "моды"
        def find_nearest2(x,n):
            x2=x[i:]
            nearest2=(np.abs(x2-n)).argmin()
            return x2[nearest2]
        # Проводим такую же оценку для значений в правой части распределения от "моды"
        Nsd02=find_nearest2(kde_m_y, maxio)
        Nsd2=find_nearest2(kde_m_y, KDE_y_sigma)
        N2sd2=find_nearest2(kde_m_y, KDE_y_2sigma)
        io2=np.where(kde_m_y==Nsd02)[0][0]
        i_sigma2=np.where(kde_m_y==Nsd2)[0][0]
        i_2sigma2=np.where(kde_m_y==N2sd2)[0][0]
        SD2=np.abs(UX[i_sigma2]-UX[i])
       
    
        # Среднее значение стандартного отклонения двух оценок: (названия переменных остались с предыдущей верссии)
        SD=(SD1+SD2)/2


        #==================================================
        def OPT_left(params):
            sred, SDmin= params
            ymodel=(stats.norm(loc=sred,scale=SDmin)).pdf(UX)
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))
            # левая половина
            # 2 сигмы
            #Umodel=ymodel_std[i_2sigma1:i]
            #Ukdemy=kde_m_y[i_2sigma1:i]
            # 1 сигма
            #Umodel=ymodel_std[i_sigma1:i]
            #Ukdemy=kde_m_y[i_sigma1:i]
            #
            Umodel=ymodel_std[i_2sigma1:i]
            Ukdemy=kde_m_y[i_2sigma1:i]
            return np.mean((Umodel-Ukdemy)**2)
            
        def OPT_right(params):
            sred, SDmin= params
            ymodel=(stats.norm(loc=sred,scale=SDmin)).pdf(UX)
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))   
            # правая половина
            # 2 сигмы
            #Umodel=ymodel_std[i:i_2sigma2]
            #Ukdemy=kde_m_y[i:i_2sigma2]
            # 1 сигма
            
            #Umodel=ymodel_std[i:i_sigma2]
            #Ukdemy=kde_m_y[i:i_sigma2]
            Umodel=ymodel_std[io2:i_sigma2]
            Ukdemy=kde_m_y[io2:i_sigma2]
            return np.mean((Umodel-Ukdemy)**2)
        
        def OPT_middle(params):
            sred, SDmin= params
            ymodel=(stats.norm(loc=sred,scale=SDmin)).pdf(UX)
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))
            # середина
            # 1 - 1 сигма 
            Umodel=ymodel_std[i_sigma1:i_sigma2]
            Ukdemy=kde_m_y[i_sigma1:i_sigma2]
            #return np.mean(abs(Umodel-Ukdemy))
            return np.mean((Umodel-Ukdemy)**2)
        

        #==================================================
        # Минимизация функции MSE для поиска наилучших среднего и стандартного отклонения, описывающих данные в диапазоне
        def MIN_left():
            x0=np.array([UX[i],SD])
            return minimize (OPT_left, x0, tol=1e-3, method='Nelder-Mead')
        D_left=MIN_left().x  

        Mul=D_left[0].round(3)
        Sil=D_left[1].round(3)
        
        def MIN_right():
            x0=np.array([UX[i],SD])
            return minimize (OPT_right, x0, tol=1e-3, method='Nelder-Mead')
        D_right=MIN_right().x  

        Mur=D_right[0].round(3)
        Sir=D_right[1].round(3)
        
        def MIN_middle():
            x0=np.array([UX[i],SD])
            return minimize (OPT_middle, x0, tol=1e-3, method='Nelder-Mead')
        D_middle=MIN_middle().x  

        Mum=D_middle[0].round(3)
        Sim=D_middle[1].round(3)
        
        
        #==================================================
        #left
        yopt_l = (stats.norm(loc=Mul,scale=Sil)).pdf(UX)
        yopt_std_l = np.max(kde_m_y)*yopt_l/np.max(yopt_l)
      
        L_l=(Mul-1.96*Sil).round(3)
        H_l=(Mul+1.96*Sil).round(3)
    
        Low_ls.append(L_l)
        High_ls.append(H_l)
        mean_ls.append(Mul)
        S_ls.append(Sil)
        
        #--------------------------------------------------
        #right
        yopt_r = (stats.norm(loc=Mur,scale=Sir)).pdf(UX)
        yopt_std_r = np.max(kde_m_y)*yopt_r/np.max(yopt_r)
      
        L_r=(Mur-1.96*Sir).round(3)
        H_r=(Mur+1.96*Sir).round(3)
    
        Low_rs.append(L_r)
        High_rs.append(H_r)
        mean_rs.append(Mur)
        S_rs.append(Sir)
        
        #--------------------------------------------------
        #middle
        yopt_m = (stats.norm(loc=Mum,scale=Sim)).pdf(UX)
        yopt_std_m = np.max(kde_m_y)*yopt_m/np.max(yopt_m)
      
        L_m=(Mum-1.96*Sim).round(3)
        H_m=(Mum+1.96*Sim).round(3)
    
        Low_ms.append(L_m)
        High_ms.append(H_m)
        mean_ms.append(Mum)
        S_ms.append(Sim)
        
        #--------------------------------------------------
        
        pbar.progress(k+1)  #streamlit progress bar
        k=k+1
        #==================================================
        
    # Среднее значение оценок после бутстрепа
    #--------------------------------------------------
    #left
    Muopt_l=np.mean(mean_ls).round(2)
    SDopt_l=np.mean(S_ls)
    # Распределение, исходя из оценок left
    yopt_l=(stats.norm(loc=Muopt_l,scale=SDopt_l)).pdf(UX)
    yopt_std_l=np.max(kde_m_y)*yopt_l/np.max(yopt_l)
    #--------------------------------------------------
    #Right
    Muopt_r=np.mean(mean_rs).round(2)
    SDopt_r=np.mean(S_rs)
    # Распределение, исходя из оценок right
    yopt_r=(stats.norm(loc=Muopt_r,scale=SDopt_r)).pdf(UX)
    yopt_std_r=np.max(kde_m_y)*yopt_r/np.max(yopt_r)
    #--------------------------------------------------
    #Middle
    Muopt_m=np.mean(mean_ms).round(2)
    SDopt_m=np.mean(S_ms)
    # Распределение, исходя из оценок mddle
    yopt_m=(stats.norm(loc=Muopt_m,scale=SDopt_m)).pdf(UX)
    yopt_std_m=np.max(kde_m_y)*yopt_m/np.max(yopt_m)
    #--------------------------------------------------
    #--------------------------------------------------

    # Оценка функции плотности первоначальных данных
    kde_f=KDEUnivariate(X)
    kde_f.fit(kernel='gau',bw='normal_reference')
    kde_f_y=kde_m.evaluate(UX)

    #--------------------------------------------------
    L2_l=(Muopt_l-1.96*SDopt_l).round(2)
    H2_l=(Muopt_l+1.96*SDopt_l).round(2)
    #--------------------------------------------------
    L2_r=(Muopt_r-1.96*SDopt_r).round(2)
    H2_r=(Muopt_r+1.96*SDopt_r).round(2)
    #--------------------------------------------------
    L2_m=(Muopt_m-1.96*SDopt_m).round(2)
    H2_m=(Muopt_m+1.96*SDopt_m).round(2)
    #--------------------------------------------------
    #--------------------------------------------------
    
    # списки
    Mus = [Muopt_l, Muopt_m, Muopt_r]
    SDOPTs = [SDopt_l, SDopt_m, SDopt_r]
    
    
    LS = [L2_l, L2_m, L2_r]
    HS = [H2_l, H2_m, H2_r]

    razn_l = kde_f_y-yopt_std_l
    razn_m = kde_f_y-yopt_std_m
    razn_r = kde_f_y-yopt_std_r
#    razn_b = kde_f_y-yopt_std_b
    
   
    rzn_l = list(map(lambda x: 10*x*np.exp(-x) if x<-0.005 else x, razn_l))     # 0.005
    rzn_m = list(map(lambda x: 10*x*np.exp(-x) if x<-0.005 else x, razn_m))     # 0.005
    rzn_r = list(map(lambda x: 10*x*np.exp(-x) if x<-0.005 else x, razn_r))     # 0.005
#    rzn_b = list(map(lambda x: 10*x*np.exp(-x) if x<-0.01 else x, razn_b))
    
    skew = stats.skew(A)
    
    if skew>0:
        sumrazn_l = np.sum(np.abs(rzn_l)) - skew
    else:
        sumrazn_l = np.sum(np.abs(rzn_l))
    sumrazn_m = np.sum(np.abs(rzn_m))
    if skew<0:
        sumrazn_r = np.sum(np.abs(rzn_r)) + skew
    else:
         sumrazn_r = np.sum(np.abs(rzn_r))
    
    SR = [sumrazn_l, sumrazn_m, sumrazn_r]
    idx = np.argmin(SR)

 
#    st.write('skew:', skew)
#    st.write('sumrzn_l',round(sumrazn_l,2))
#    st.write('sumrzn_m',round(sumrazn_m,2))
#    st.write('sumrzn_r',round(sumrazn_r,2))

#    st.write('РИ left: ',L2_l ,' - ', H2_l, 'SUMR:', round(sumrazn_l,2))
#    st.write('РИ middle: ',L2_m ,' - ', H2_m, 'SUMR:', round(sumrazn_m,2)) 
#    st.write('РИ right: ',L2_r ,' - ', H2_r, 'SUMR:', round(sumrazn_r,2))
#    st.write('----------------------------')
    pbar.empty()

    # Блок построения графиков для проверки
    fig, axes = plt.subplots(figsize = (14,10)) # nrows=2, ncols=1,
    axes.set_title(f'N = {len(X)}.  РИ: {LS[idx]} - {HS[idx]}')
    axes.hist(A,density=True,bins = 80)
    axes.plot(UX,kde_f_y,color='orange', linewidth=3, label = 'данные')
    if idx == 0:
        axes.plot(UX,yopt_std_l,color='black',linewidth=2, label = 'left_opt')
        axes.plot(UX,razn_l,color='black', ls='--')
    elif idx == 1:
        axes.plot(UX,yopt_std_m,color='yellow',linewidth=2, label = 'middle_opt')
        axes.plot(UX,razn_m,color='yellow', ls = '--')
    elif idx == 2:
        axes.plot(UX,yopt_std_r,color='pink',linewidth=2, label = 'right_opt')
        axes.plot(UX,razn_r,color='r', ls = '--')

    axes.axvline(LS[idx], color = 'r', ls='--')
    axes.axvline(HS[idx], color = 'r', ls='--')
    axes.set_xlim(Muopt_l-3*SDopt_l,Muopt_l+7*SDopt_l)
    axes.legend()

    return fig, LS[idx], HS[idx]


#=========================================================================================================================================


#===============================================================================
# Модель с производными для скошенных вправо распределений
# вот така соба хуйнячка
def new_logfunk_kde(X):
    Low=[]
    High=[]
    mean=[]
    S=[]
    k=0

    pbar = st.progress(value=k, text='Тужусь, пыжусь, вычисляю')

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

        UX=np.unique(A)
        kde_m=KDEUnivariate(A)
        kde_m.fit(kernel='gau',bw='normal_reference')
        kde_m_y=kde_m.evaluate(UX)

        # Находим индекс максимального значения функции плотности ("моды")
        Max_KDE=np.max(kde_m_y)
        i=np.where(kde_m_y==Max_KDE)[0][0]

        
        # Функция для нахождения ближайшего значения до "моды"
        def find_nearest1(x,n):
            x1=x[:i]
            nearest1=(np.abs(x1-n)).argmin()
            return x1[nearest1]

        # новые участки оптимизации:
        #maxio = Max_KDE/1.05   #1.03
        KDE_y_sigma = Max_KDE/2.5
        #KDE_y_2sigma = Max_KDE/6
                
        # Находим участки
        Nsd1=find_nearest1(kde_m_y, KDE_y_sigma)
        i_sigma1=np.where(kde_m_y==Nsd1)[0][0]

            
        # Функция для нахождения ближайшего значения после "моды"
        def find_nearest2(x,n):
            x2=x[i:]
            nearest2=(np.abs(x2-n)).argmin()
            return x2[nearest2]
        # Проводим такую же оценку для значений в правой части распределения от "моды"
        Nsd2=find_nearest2(kde_m_y, KDE_y_sigma)
        i_sigma2=np.where(kde_m_y==Nsd2)[0][0]


        def OPT(params):
            sred, SDmin= params
            ymodel=stats.lognorm.pdf(UX, scale = sred, s = SDmin)
            ymodel_std=np.max(kde_m_y)*(ymodel/np.max(ymodel))
        
            #Umodel=ymodel_std[i_sigma1:i_sigma2]
            #Ukdemy=kde_m_y[i_sigma1:i_sigma2]

            Umodel=ymodel_std
            Ukdemy=kde_m_y

            return np.mean((Umodel-Ukdemy)**2)


         # Минимизация функции для поиска наилучших среднего и стандартного отклонения, описывающих данные в диапазоне
        def MIN():
            x0=np.array([np.median(A), 0.1])
            return minimize (OPT,x0,tol=1e-3,method='Nelder-Mead')
        D=MIN().x  

        Mu=D[0].round(2)
        Si=D[1].round(2)
    
        yopt=stats.lognorm.pdf(UX, scale = Mu, s = Si)
        yopt_std=np.max(kde_m_y)*yopt/np.max(yopt)
  

        L=stats.lognorm.ppf(q=0.025, scale = Mu, s = Si)
        H=stats.lognorm.ppf(q=0.975, scale = Mu, s = Si)
    
        Low.append(L)
        High.append(H)
        mean.append(Mu)
        S.append(Si)

        pbar.progress(k+1, text='Тужусь, пыжусь, вычисляю')   # streamlit progress bar
        k=k+1

    # Средние значения оценок после бутстрепа
    Muopt=np.mean(mean).round(2)
    SDopt=np.mean(S)
    # Распределение, исходя из этих оценок
    yopt=stats.lognorm.pdf(UX, scale = Muopt, s = SDopt)
    yopt_std=np.max(kde_m_y)*yopt/np.max(yopt)
    # Оценка функции плотности первоначальных данных
    kde_f=KDEUnivariate(X)
    kde_f.fit(kernel='gau',bw='normal_reference')
    kde_f_y=kde_m.evaluate(UX)
  

    razn = kde_f_y - yopt_std
    razn2 = abs(yopt_std-razn)
    
    L2=round(np.median(Low),2)
    H2=round(np.median(High),2)

   
    #Блок вычисления "производной"
    
    
    
    #Блок вычисления "производной"
    def derivative1(A, dx=0.0001):
        k=1
        RX=np.arange(np.min(A)/1.5, np.max(A),dx)
        #kde_dx=stats.lognorm.pdf(RX, scale = Muopt, s = SDopt)
        kde_dx=stats.lognorm.pdf(RX, scale = Muopt, s = SDopt)
        #kde_dx=(stats.norm(loc=Muopt_r,scale=SDopt_r)).pdf(RX)
        #kde_dx=(stats.norm(loc=Muopt_m,scale=SDopt_m)).pdf(RX)
        dify=[]
        difx=[]

        while k+2<=(len(RX)):
            f=kde_dx[k+1]-kde_dx[k]
            dify.append(f)
            h=(RX[k]+RX[k+1])/2
            difx.append(h)
            k=k+1

        dify_std = np.max(kde_m_y)*np.array(dify)/np.max(dify)
        maxi = np.argmax(np.array(dify))
        mini = np.argmin(np.array(dify))
        udify = np.abs(dify[maxi:mini])
        udifx = difx[maxi:mini]
    #    zeroi = np.argmin(np.array(udify))
    #    Z = udifx[zeroi]
    #    sl = Z - difx[maxi]
    #    sr = difx[mini] - Z
    #    st.write('Максимум 1 производной: ', round(difx[maxi],2))
    #    st.write('Минимум 1 производной: ', round(difx[mini],2))
    #    st.write('Zero: ', Z)
    #    st.write('Диапазон: ', round(Z-2*sl,2), round(Z+2*sr,2))
       
        dy_max = dify[maxi]
        dy_min = dify[mini]
        
    #    ul = Z-1.96*sl
    #    ur = Z+1.96*sr
        
        def find_n(x,n):            
            #x1=x[:i]
            near=(np.abs(x-n)).argmin()
            return x[near]
        
    #    find_l = find_n(difx, ul)
    #    find_r = find_n(difx, ur)
        
    #    ixl=np.where(difx==find_l)[0][0]
    #    ixr=np.where(difx==find_r)[0][0]
        
    #    dyl = dify[ixl]
    #    dyr = dify[ixr]
        
    #    vsl = dy_max/dyl
    #    vsr = dy_min/dyr
        
    #    st.write('find_l: ', find_l)
    #    st.write('find_r: ', find_r)
        
    #    st.write('dyl: ', dyl)
    #    st.write('dyr: ', dyr)
        
    #    st.write('vsl: ', vsl)
    #    st.write('vsr: ', vsr)
        
        difx13 = difx[:maxi]
        dify13 = dify[:maxi]
        difx33 = difx[mini:]
        dify33 = dify[mini:]
        
        fy_l = find_n(dify13, dy_max/2.1125)
        fy_r = find_n(dify33, dy_min/2.1125)
        
        iy_l = np.where(dify13 == fy_l)[0][0]
        iy_r = np.where(dify33 == fy_r)[0][0]
        
        fx_l = round(difx13[iy_l],2)
        fx_r = round(difx33[iy_r],2)
        
#        st.write('------------------------')
#        st.write('Нижняя граница (fx_l): ', fx_l)
#        st.write('Верхняя граница (fx_r): ', fx_r)
#        st.write('------------------------')
                

        return difx, dify_std, fx_l, fx_r
#! 2    
#    def derivative2(A, kde_dx, sl, sr, Z, dx=0.0001):
#        k=1
#        RX=np.arange(np.min(A)-(np.min(A)/2), np.max(A),dx)
        #kde_dx=stats.lognorm.pdf(RX, scale = Muopt, s = SDopt)
#        dify=[]
#        difx=[]

#        while k < (len(RX)-1):
#            f=kde_dx[k+1]-kde_dx[k]
#            dify.append(f)
#            h=(RX[k]+RX[k+1])/2
#            difx.append(h)
#            k=k+1

#        dify_std = np.max(kde_m_y)*np.array(dify)/np.max(dify)
        
#        min_i = np.argmin(np.array(dify))
#        poludify1 = dify[:min_i]
#        poludify2 = dify[min_i:]
#        poludifx1 = difx[:min_i]
#        poludifx2 = difx[min_i:]
#        max_2d1 = round(poludifx1[np.argmax(np.array(poludify1))],2)
#        max_2d2 = round(poludifx2[np.argmax(np.array(poludify2))],2)
        
        #min2d = difx[np.argmin(np.array(dify))]
#        s2d_l = np.round(Z - max_2d1, 2)
#        s2d_r = np.round(max_2d2 - Z, 2)
        
#        otn_l = s2d_l/sl
#        otn_r = s2d_r/sr
        
        #print('zero2d: ', min2d)
#        st.write('otn_l: ', otn_l)
#        st.write('otn_r: ', otn_r)
        
#        st.write('1 Максимум 2 производной: ', max_2d1)
#        st.write('2 Максимум 2 производной: ', max_2d2)
#        st.write('-------------------------')

#        return difx, dify_std

#! 3
#    def derivative3(A, kde_dx, dx=0.0001):
#        k=1
#        RX=np.arange(0, np.max(A),dx)
#        #kde_dx=stats.lognorm.pdf(RX, scale = Muopt, s = SDopt)
#        dify=[]
#        difx=[]

#        while k < (len(RX)-1):
#            f=kde_dx[k+1]-kde_dx[k]
#            dify.append(f)
#            h=(RX[k]+RX[k+1])/2
#            difx.append(h)
#            k=k+1

#        dify_std = np.max(kde_m_y)*np.array(dify)/np.max(dify)
#        min_i = np.argmin(np.array(dify))
#        poludify1 = dify[:min_i]
#        poludify2 = dify[min_i:]
#        poludifx1 = difx[:min_i]
#        poludifx2 = difx[min_i:]
#        max_2d1 = round(poludifx1[np.argmax(np.array(poludify1))],2)
#        max_2d2 = round(poludifx2[np.argmax(np.array(poludify2))],2)
        #print('1 Максимум 3 производной: ', max_2d1)
        #print('2 Максимум 3 производной: ', max_2d2)
        
#        min_i = np.argmin(np.array(kde_dx))
#        polu2d1 = dify[:min_i]
#        polu2d2 = dify[min_i:]
#        polux1 = difx[:min_i]
#        polux2 = difx[min_i:]
#        max_3d = round(polux1[np.argmax(np.array(polu2d1))],2)
#        min_3d = round(polux2[np.argmin(np.array(polu2d2))],2)
#        print('1 Максимум 3 производной: ', max_3d)
#        print('2 Минимум 3 производной: ', min_3d)

#        return difx, dify_std 

    
    difx, dify_std, fx_l, fx_r = derivative1(A, dx=0.0001)

    pbar.empty()
#    difx2, dify2_std = derivative2(difx, dify_std, sl, sr, Z, dx=0.0001)
    
#    difx3, dify3_std = derivative3(difx2, dify2_std, dx=0.0001)

    # Блок построения графиков для проверки
    fig, ax = plt.subplots(figsize = (14,10))
    ax.set_title(f'N = {len(X)}.  Референс: {fx_l} - {fx_r}')
    ax.hist(A,density=True,bins = 80)
    ax.plot(UX,kde_f_y,color='orange', linewidth=2)
    ax.plot(UX,yopt_std,color='black',linewidth=2)
    #ax.plot(difx,dify_std, color='brown',linewidth=2)
    
    ax.plot(UX,razn,color='g')
    ax.axvline(fx_l, color = 'r', ls='--')
    ax.axvline(fx_r, color = 'r', ls='--')

    return fig, fx_l, fx_r


#=========================================================================
# Здесь будет третий вариант модели....

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

    for i in range(min_age,max_age+1):
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
            if pval1<0.1: # 0.05 не очень
                lis.append(lisage[i+1])
    lis.append(max_age)

    # Теперь в каждой возрастной группе сравниваем муж и жен с помощью KS-теста и делим, если есть разница
    age_group = []
    boys = []
    girls = []
    med_boys = []
    med_girls = []

    for k in range(0,len(lis)-1):
        group = mf[(mf['Лет']>=lis[k]) & (mf['Лет']<lis[k+1])]
        res_total = group['Результат']
        res_m = group[group['Пол']=='Мужской']['Результат']
        res_w = group[group['Пол']=='Женский']['Результат']
        sta2, pval2 = stats.ks_2samp(res_m,res_w)
    
        if pval2<0.1:  # 0.05 слишком 
            fg1, lm, hm = funktion(res_m)
            fg2, lw, hw = funktion(res_w)                   #  [-2:]
            age1 = f'{lis[k]}'+'-' f'{lis[k+1]}' 
            age_group.append(age1)
            M = f'{lm}'+ '-' + f'{hm}' + f' (N: {len(res_m)})'
            boys.append(M)
            W = f'{lw}'+ '-' + f'{hw}' + f' (N: {len(res_w)})'
            girls.append(W)
            med_b = np.median(res_m)
            med_boys.append(np.round(med_b,2))
            med_g = np.median(res_w)
            med_girls.append(np.round(med_g,2))
        else: 
            fg3, lt, ht = funktion(res_total)
            age1 = f'{lis[k]}'+'-' f'{lis[k+1]}'
            age_group.append(age1)
            M = f'{lt}'+ '-' + f'{ht}' + f' (N: {len(res_total)})'
            W = f'{lt}'+ '-' + f'{ht}' + f' (N: {len(res_total)})'
            boys.append(M)
            girls.append(W)
            med_t = np.median(res_total)
            med_boys.append(np.round(med_t,2))
            med_girls.append(np.round(med_t,2))

    dict1 = {'Возраст (лет)':age_group, 
             'Мужчины':boys,
             'Медиана (М)': med_boys,
             'Женщины':girls,
             'Медиана (Ж)': med_girls}  

    return pd.DataFrame(dict1)



# UI ===================================================================
radio = st.sidebar.radio('**Шаблон**',options = ['стандарт','интерсистемс'])
    
if radio == 'интерсистемс':
    radio_model = st.sidebar.radio('**Модель**', ['РИ (свои наработки)','Среднее по пациентам (для шаблона "интерсистемс")'])
else:
    pass


if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, engine='openpyxl')
    st.write(df.head(10))

    if radio == 'стандарт':

        st.write('В загружаемом файле Excel результаты показателя должны быть в одном столбце, '
         'можно сразу несколько столбцов в одном файле, самая верхняя строка - заголовки для колонок') 
        #=======
        select_test = st.sidebar.selectbox('Выбери столбец с результатами',df.columns)
        ne_uk = ['Не указано']
        choise = ne_uk + (list(df.columns))
        #dop_filter = st.sidebar.selectbox('Дополнительный фильтр', options=choise)

        sc1, sc2 = st.sidebar.columns(2)
        select_sexcol = sc1.selectbox('Колонка Пол', options=choise)
        if select_sexcol != 'Не указано':
            select_sex = sc2.selectbox('Выбрать Пол', df[select_sexcol].unique())
        else:
            pass
        select_age = st.sidebar.selectbox('Колонка Возраст (лет)', options=choise)
        sc11, sc22 = st.sidebar.columns(2)
        if select_age != 'Не указано':
            sc11.number_input('Возраст (от)', min_value=0, max_value=80, value=0, step=1)
            sc22.number_input('Возраст (до)', min_value=1, value = 100, max_value=120, step=1)
        else:
            pass
        
        df = df[pd.to_numeric(df[select_test], errors='coerce').notnull()]
        df[select_test] = df[select_test].astype(float)

        if select_sexcol != 'Не указано':
            sexdf = df[df[select_sexcol] == select_sex]
        else:
            sexdf = df
        rv = sexdf[select_test].dropna()
        rv=rv.apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))

        #if radio_model == 'Референсные интервалы (своя модель)':
        st.sidebar.divider()
        st.sidebar.markdown('Свои наработки')
        scol1,scol2 = st.sidebar.columns(2)
        calc_norm = scol1.button('Normal D')
        calc_log =  scol2.button('Right Scewed D')
        #calc_sqrt = scol1.button('Test calculation')
        st.sidebar.divider()
        #st.sidebar.markdown('Другие модели')
        scol11,scol22 = st.sidebar.columns(2)

        if calc_norm:
            try:
                fg, LOWn, HIGHn = funk_kde(rv)
                st.pyplot(fg)
            except:
                st.write('возможно, что-то не так с данными')
            
        if calc_log:
            #try:
            lfig, fxl, fxr = new_logfunk_kde(rv)
            st.pyplot(lfig)
            #except:
            #    st.write('возможно, что-то не так с данными')
        

        #if radio_model == 'refineR':
        #calc_refiner = scol11.button('refineR')
        #if calc_refiner:
            #========================================================
            # ДЛЯ ебучего R
        #    import os

        #    R_HOME = r"C:\Program Files\R\R-4.5.1"
        #    R_BIN = os.path.join(R_HOME, "bin", "x64")
        #    os.environ["R_LIBS_USER"] = r"C:\Rlib"
        #    os.environ["R_HOME"] = R_HOME
        #    os.environ["PATH"] = R_BIN + os.pathsep + os.environ.get("PATH", "")
        #    _r_dll_dir = os.add_dll_directory(R_BIN)

        #    from rpy2.robjects import r
        #    from rpy2.robjects import pandas2ri, default_converter
        #    from rpy2.robjects.conversion import localconverter
        #    from rpy2.robjects.packages import importr
        #    import rpy2.robjects as ro

            #========================================================
        #    with localconverter(default_converter):
            # данные -> в R как вектор
        #        vals = rv.dropna().values if hasattr(rv, "dropna") else rv
        #        ro.globalenv['dat'] = ro.FloatVector(list(vals))

        #        ro.r('.libPaths(c("C:/Rlib", .libPaths()))')
        #        ro.r('library(refineR)')
        #        ro.r('fit <- findRI(Data = dat, NBootstrap = 0, model = "BoxCox", seed = 123)')

        #        summary_txt = "\n".join(ro.r('capture.output(print(fit))'))
        #        ro.r('ri <- getRI(fit, RIperc = c(0.025, 0.975))')
        #        ri_text = "\n".join(ro.r('capture.output(print(ri))'))

        #        ro.r('png("C:/Rlib/refiner_plot.png", width = 900, height = 600); plot(fit); dev.off()')

        #    st.text(summary_txt)
        #    st.text(ri_text)
        #    st.image("C:/Rlib/refiner_plot.png")

        #if radio_model == 'kosmic':
        #calc_kosmic = scol22.button('kosmic')
        #if calc_kosmic:
            #========================================================
            # ДЛЯ ебучего R
        #    import os
            
        #    R_HOME = r"C:\Program Files\R\R-4.5.1"
        #    R_BIN = os.path.join(R_HOME, "bin", "x64")
        #    os.environ["R_LIBS_USER"] = r"C:\Rlib"
        #    os.environ["R_HOME"] = R_HOME
        #    os.environ["PATH"] = R_BIN + os.pathsep + os.environ.get("PATH", "")
        #    _r_dll_dir = os.add_dll_directory(R_BIN)
            
        #    from rpy2.robjects import r
        #    from rpy2.robjects import pandas2ri, default_converter
        #    from rpy2.robjects.conversion import localconverter
        #    from rpy2.robjects.packages import importr
        #    import rpy2.robjects as ro
            #==========================================================
        #    with localconverter(default_converter):
        #        vals = rv.dropna().values if hasattr(rv, "dropna") else rv
        #        ro.globalenv['dat'] = ro.FloatVector(list(vals))
        #        ro.r('.libPaths(c("C:/Rlib", .libPaths()))')
        #        ro.r('suppressMessages({library(stats); library(utils); library(graphics); library(grDevices)})')
        #        ro.r('library(tidykosmic)')
        #        ro.r('res <- kosmic(dat, decimals = 2)')

        #        q = list(ro.r('as.numeric(quantile(res, probs = c(0.025, 0.5, 0.975)))'))
        #        summary_txt = "\n".join(ro.r('capture.output(summary(res))'))

        #        ro.r('png("C:/Rlib/kosmic_plot.png", width = 900, height = 600); '
        #            'try(plot(res)); dev.off()')

        #    st.write(f"Референс kosmic: {q[0]:.2f} – {q[2]:.2f} (медиана {q[1]:.2f})")
        #    st.text(summary_txt)
        #    st.image("C:/Rlib/kosmic_plot.png")

#==================================================================================================    
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
        df['Лет']=df['Лет'].apply(pd.to_numeric, errors='coerce')
        
        #st.write(df)
        
        depart = list(df['Отделение'].astype(str).sort_values().unique())
        analizers = list(df['Прибор'].astype(str).sort_values().unique())
                
        box = st.form('Фильтры')
        col1,col2,col3 = box.columns(3)
        #analizer = col1.selectbox('Прибор',df['Прибор'].unique())
        minage = col2.number_input('Возраст от (лет)',min_value=0,max_value=100,step=1)
        maxage = col3.number_input('Возраст до (лет)',min_value=1,max_value=120,step=1, value=100)
        sex = col1.selectbox('Пол',['Все','Мужской','Женский'])
        date_from = col2.date_input('Дата авторизации (от)',min(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
        date_to = col3.date_input('Дата авторизации (до)', max(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
        analizer = box.multiselect('Приборы', placeholder= 'Оставьте поле пустым, если нужны все приборы', options=analizers)
        department = box.multiselect('Отделения', placeholder = 'Оставьте поле пустым, если нужны все отделения' , options=depart)
        col11 , col22 = box.columns(2)
        

        #sdf = df[df['Прибор']==analizer]
        sdf = df[(df['Лет']>=minage) & (df['Лет']<=maxage)]
        
        sdf = sdf[(sdf['Дата авторизации']>=date_from) & (sdf['Дата авторизации']<date_to)]
        
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

            med_let_m = []
            med_let_w = []
            goda = []
            for n in range (min(sdf['Лет']), max(sdf['Лет']), 10):
                if n < (max(sdf['Лет'])-10):
                    duf1 = sdf[(sdf['Лет']>=n) & (sdf['Лет']< (n+10))]
                    medresM = np.median(duf1[sdf['Пол']=='Мужской']['Результат'])
                    medresW = np.median(duf1[sdf['Пол']=='Женский']['Результат'])
                    med_let_m.append(medresM)
                    med_let_w.append(medresW)
                    goda.append(n)
                else:
                    duf2 = sdf[(sdf['Лет']>=n) & (sdf['Лет']< max(sdf['Лет']))]
                    medresM = np.median(duf2[sdf['Пол']=='Мужской']['Результат'])
                    medresW = np.median(duf2[sdf['Пол']=='Женский']['Результат'])
                    med_let_m.append(medresM)
                    med_let_w.append(medresW)
                    goda.append(n)

            sns.scatterplot(data=sdf, x='Лет', y='Результат', hue = 'Пол')
            ax.plot(goda,med_let_m, color = 'red', label = 'Медиана (мужчины)')
            ax.plot(goda,med_let_w, color = 'black', label = 'Медиана (женщины)')
            ax.set_xlabel('Возраст')
            ax.set_ylabel('Результат')
            iqr=np.percentile(sdf['Результат'],75) - np.percentile(sdf['Результат'],25)
            ax.set_ylim(np.median(sdf['Результат'])-2*iqr,np.median(sdf['Результат'])+5*iqr)
            ax.set_title('Динамика изменения показателя с возрастом')
            ax.legend()
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


        if radio_model == 'РИ (свои наработки)':
            info1 = col11.write('*Для расчёта используйте фильтры выше*')
            info2 = col22.write('*Для таблиц выбрать только приборы*')
            calc_norm2 = col11.form_submit_button('**Normal D**')
            calc_log2 =  col11.form_submit_button('**Right Scewed D**')
            #calc_sqrt2 = col11.form_submit_button('**Рассчитать по модели square root transformation with heuristic correction**')
            table_norm = col22.form_submit_button('Таблица референсов по возрасту и полу (Normal D)')
            table_log = col22.form_submit_button('Таблица референсов по возрасту и полу (Right Scewed D)')
            #table_sqrt = col22.form_submit_button('Таблица референсов по возрасту и полу (sqrt root tranform-model)')

            if calc_norm2:
                try:
                    figa, LOWn, HIGHn = funk_kde(sdf['Результат'])  
                #X, A, UX, LSidx, HSidx, kde_f_y, yopt_std_l, yopt_std_m, yopt_std_r, razn_l, razn_m, difx,dify_std, Muopt_l, SDopt_l = funk_kde(sdf['Результат'])
                #figa = show_base(X, A, UX, LSidx, HSidx, kde_f_y, yopt_std_l, yopt_std_m, yopt_std_r, razn_l, razn_m, difx,dify_std, Muopt_l, SDopt_l)
                    st.pyplot(figa)
                    st.pyplot(show_age_scatter())
                    st.pyplot(distribution_plot(sdf))
                    st.pyplot(analizers_plot(df))
                except:
                    st.write('возможно, что-то не так с данными')
            
            if calc_log2:
            #    try:
                lfiga, fxl, fxr = new_logfunk_kde(sdf['Результат'])
                st.pyplot(lfiga)
                st.pyplot(show_age_scatter())
                st.pyplot(distribution_plot(sdf))
                st.pyplot(analizers_plot(df))
            #    except:
            #        st.write('возможно, что-то не так с данными')
            

            if table_norm:
                try:
                    st.subheader('ND model')
                    st.dataframe(show_age_table(funk_kde, df), hide_index=True)
                except:
                    st.write('что-то пошло не так')

            if table_log:
                #try:
                st.subheader('RSD model')
                st.dataframe(show_age_table(new_logfunk_kde, df), hide_index=True)
                #except:
                #    st.write('что-то пошло не так')
            


        if radio_model == 'Среднее по пациентам (для шаблона "интерсистемс")':
            porog = box.number_input("Введите пороговое значение для отображения % результатов выше этого порога за день", step = 0.01)
            dynamic = box.form_submit_button('Показать динамику')
            unique_date = sorted(sdf['Дата авторизации'].unique())
            ran = list(range(1,len(unique_date)+1))

            M=[]
            Med =[]
            per25 = []
            per75=[]
            dolyas = []
            days = []

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

                 days.append(n)

                 if porog is not None:
                    if len(mdf['Результат'])>0:
                       dolya = 100*len(mdf[mdf['Результат']>porog])/len(mdf['Результат'])
                       dolyas.append(dolya)
                    else:
                       dolya = 0
                       dolyas.append(dolya)
                

            if dynamic:
                try:
                    fig2, ax2 = plt.subplots(nrows=2,ncols=1)
                    fig2.set_size_inches(14,12)
                    ax2[0].plot(ran,M,color='r',label='Среднее')
                    ax2[0].plot(ran,Med,color='y',label='Медиана')
                    ax2[0].plot(ran,per25,color='g',label='перцентиль 25%')
                    ax2[0].plot(ran,per75,color='b',label='перцентиль 75')
                    ax2[0].set_title('Среднее/медиана/перцентили по дням')
                    ax2[0].set_xlabel('Дни')
                    ax2[0].legend()
                    
                    if porog is not None:
                        ax2[1].plot(days, dolyas, label= f'% результатов выше порога {porog}')
                        ax2[1].set_title('Динамика изменения количества образцов(%) выше порога')
                        ax2[1].set_ylabel('% результатов выше порога')
                        ax2[1].legend()                      
                    st.pyplot(fig2)
                except:
                    st.write('Не получилось рассчитать')
