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




uploaded_file = st.sidebar.file_uploader("Выбери файл Excel на компе",type=['xlsx','xls'])
st.write('Шаблон Стандарт: результаты в файле должны располагаться в одном столбце, можно несколько столбцов с разными результатами. Верхняя строчка - заголовок')
st.write('Шаблон Интерсистемс: результат выгрузки отчета по результатам теста за период. \
              Перед загрузкой файла удалите верхние строчки до заголовков колонок. \
              Удалите столбцы с личными данными: ФИО, номером карты и т.д., \
              Необходимые столбцы для расчета: Результат, Прибор, Дата авторизации, Отделение, колонки с возрастом и Пол. \
              Удалите дубликаты по ФИО самостоятельно, если необходимо. \
              Дополнительного форматирования данных не требуется (перевод текстовых значений в числовые,форматирования дат) \
              Сохраните файл как Книгу Excel')

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
    fig1.suptitle(f'N = {len(X)}')
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
    fig.suptitle(f'N = {len(X)}')
    ax.set_title(f'Модель с логтрансформацией. Референс: {LL2} - {HH2}')
    ax.hist(X,density=True,bins = 80)
    ax.plot(UXX,kde_f_y,color='orange', linewidth=2)
    ax.plot(UX,yopt_std,color='black',linewidth=2)
    #ax.plot(UX,razn,color='g',linewidth=2)
    ax.set_xlim(Muopt-5*SDopt,Muopt+5*SDopt)
    st.pyplot(fig)

radio = st.sidebar.radio('Шаблон',options = ['стандарт','интерсистемс'])
radio_model = st.sidebar.radio('Модель', ['Среднее по пациентам','Свой вариант','kosmic','refineR'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, engine='openpyxl')
    st.write(df.head(10))

    if radio == 'стандарт':
        #st.write('В загружаемом файле Excel результаты показателя должны быть в одном столбце, '
        # 'можно сразу несколько столбцов в одном файле, самая верхняя строка - заголовки для колонок') 
        select_test = st.sidebar.selectbox('Выбери столбец',df.columns)
        calc_norm = st.sidebar.button('Рассчитать по базовой модели')
        calc_log =  st.sidebar.button('Рассчитать по модели с логарифмированием')
        if calc_norm:
            try:
                r = df[select_test].dropna()
                r=r.apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
                funk_kde(r)
            except:
                st.write('возможно, что-то не так с данными')
            

        if calc_log:
            try:
                l = df[select_test].dropna()
                l=l.apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
                log_funk_kde(l)
            except:
                st.write('возможно, что-то не так с данными')
    
    if radio == 'интерсистемс':
        #st.write('Перед загрузкой файла отчёта по Результатам удалите верхние строчки, ' \
        #'оставив в качестве первой строки названия столбцов, сохраните файл как Книгу Excel')
        
        #------------ФИО-------------
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
                
        box = st.form('Фильтры')
        col1,col2,col3 = box.columns(3)
        analizer = col1.selectbox('Прибор',df['Прибор'].unique())
        minage = col2.number_input('Возраст от (лет)',min_value=0,max_value=100,step=1)
        maxage = col3.number_input('Возраст до (лет)',min_value=1,max_value=120,step=1)
        sex = col1.selectbox('Пол',['Все','Мужской','Женский'])
        date_from = col2.date_input('Дата авторизации (от)',min(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
        date_to = col3.date_input('Дата авторизации (до)', max(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
        department = box.multiselect('Отделения', placeholder = 'Оставьте пустым, если нужны все отделения' , options=depart)
        

        sdf = df[df['Прибор']==analizer]
        sdf = sdf[(sdf['Лет']>=minage) & (sdf['Лет']<=maxage)]
        
        sdf = sdf[(sdf['Дата авторизации']>=date_from) & (sdf['Дата авторизации']<=date_to)]
        
        if any(n in depart for n in department):
            sdf = sdf[sdf['Отделение'].isin(list(department))]
        else:
            pass

        #sex = st.sidebar.selectbox('Пол',['Все','Мужской','Женский'])

        if sex == 'Все':
            pass
        else:
            sdf = sdf[sdf['Пол']==sex]
        
        if radio_model == 'Свой вариант':
            calc_norm2 = box.form_submit_button('Рассчитать по базовой модели')
            calc_log2 =  box.form_submit_button('Рассчитать по модели с логарифмированием')

            if calc_norm2:
                try:
                    st.write('Модель предпочтительнее, когда данные имеют нормальное распределение с относительно небольшим числом примесей патологических значений')
                    funk_kde(sdf['Результат'])

                    fig,ax = plt.subplots()
                    fig.set_size_inches(14,6)
                    sns.scatterplot(data=sdf, x='Лет', y='Результат', hue = 'Пол')
                    ax.set_xlabel('Возраст')
                    ax.set_ylabel('Результат')
                    iqr=np.percentile(sdf['Результат'],75) - np.percentile(sdf['Результат'],25)
                    ax.set_ylim(np.median(sdf['Результат'])-2*iqr,np.median(sdf['Результат'])+5*iqr)
                    ax.set_title('Динамика изменения показателя с возрастом')
                    st.pyplot(fig)
                except:
                    st.write('возможно, что-то не так с данными')
            

            if calc_log2:
                try:
                    st.write('Модель с логтрансформацией предпочтительнее в большинстве случаев, ' \
                    'когда данные не имеют нормальное распределение и/или имеют много примесей)' )
                    #st.write(f'всего значений {len(sdf['Результат'])}')
                    log_funk_kde(sdf['Результат'])

                    fig,ax = plt.subplots()
                    fig.set_size_inches(14,6)
                    sns.scatterplot(data=sdf, x='Лет', y='Результат', hue = 'Пол')
                    ax.set_xlabel('Возраст')
                    ax.set_ylabel('Результат')
                    iqr=np.percentile(sdf['Результат'],75) - np.percentile(sdf['Результат'],25)
                    ax.set_ylim(np.median(sdf['Результат'])-2*iqr,np.median(sdf['Результат'])+5*iqr)
                    ax.set_title('Динамика изменения показателя с возрастом')
                    st.pyplot(fig)
                except:
                    st.write('возможно, что-то не так с данными')
        
        if radio_model == 'kosmic':
            box.form_submit_button('Рассчитать по модели kosmic')
            st.write('Когда-нибудь появится')

        if radio_model == 'refineR':
            box.form_submit_button('Рассчитать по модели refineR')
            st.write('Когда-нибудь здесь появится и эта модель')
          
        if radio_model == 'Среднее по пациентам':
            dynamic = box.form_submit_button('Показать динамику')
            unique_date = sorted(sdf['Дата авторизации'].unique())
            ran = list(range(1,len(unique_date)+1))

            M=[]
            Med =[]
            per2_5 = []
            per97_5=[]

            for n in unique_date:
                 mdf = sdf[sdf['Дата авторизации']==n]
                 MEAN = mdf['Результат'].mean()
                 meds = mdf['Результат'].median()
                 M.append(MEAN)
                 Med.append(meds)
    
                 q1 = np.percentile(mdf['Результат'],2.5)
                 per2_5.append(q1)
    
                 q2= np.percentile(mdf['Результат'],97.5)
                 per97_5.append(q2)

            if dynamic:
                try:
                    fig2, ax2 = plt.subplots()
                    fig2.set_size_inches(14,8)
                    ax2.plot(ran,M,color='r',label='Среднее')
                    ax2.plot(ran,Med,color='y',label='Медиана')
                    ax2.plot(ran,per2_5,color='g',label='перцентиль 2.5%')
                    ax2.plot(ran,per97_5,color='b',label='перцентиль 97.5')
                    ax2.set_title('Среднее/медиана/перцентили по дням')
                    ax2.legend()
                    
                    st.pyplot(fig2)
                except:
                    st.write('Не получилось рассчитать')

 







