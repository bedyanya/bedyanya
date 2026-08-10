import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
import plotly.express as px
#from datetime import datetime,date, timedelta

st.set_page_config(layout="wide")
#
#uploaded_file = st.sidebar.file_uploader("Выбери файл Excel на компе",
#                                         type=['xlsx','xls'])

radio = st.sidebar.radio('**Выбери тип исследования**', 
                         options= ['Cosinor-модель для ТТГ',
                                   '🔀 Визуализация данных и их взаимосвязи', 
                                   '📈 Среднее по пациентам'])

#st.info('🔀 Визуализация данных и их взаимосвязи: необходимы колонки с результатами (от 1 до 3 показателей) и колонки с заголовками Пол и Лет')
#st.info('📈 Среднее по пациентам: необходимы колонки с заголовками Результат, Пол, Дата авторизации. Для получения статистики по отправителям (опционально) необходима колонка Отправитель')


if radio == '🔀 Визуализация данных и их взаимосвязи' or '📈 Среднее по пациентам':
    uploaded_file = st.sidebar.file_uploader("Выбери файл Excel на компьютере",type=['xlsx','xls'])
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        st.write(df.head(10))


        # ВИЗУАЛИЗАЦИЯ
        if radio == '🔀 Визуализация данных и их взаимосвязи':

            st.info('🔀 Визуализация данных и их взаимосвязи: необходимы колонки с результатами (от 1 до 3 показателей) и колонки с заголовками Пол и Лет')
            snum = st.sidebar.number_input('Количество переменных', value=3, min_value=1, max_value=3, step=1)
            form = st.form('Форма')
            с00, c01 = form.columns(2)
            sex = с00.selectbox('Пол', options = ['Все', 'Мужской', 'Женский'])

            def show_dist(xs, fx):
                fig,ax = plt.subplots()
                fig.set_size_inches(14,6)
                ax.set_title(f"Распределение данных {fx}")
                ax.hist(x = xs, bins=80, density = True,  edgecolor = 'black')
                ax.set_xlabel(f'Результат {fx}')
                return fig
    
            def show_ages(fx, sdf):
                fig,ax = plt.subplots()
                fig.set_size_inches(14,6)
                med_let_m = []
                med_let_w = []
                goda = []
                sdf['Лет'] = sdf['Лет'].apply(lambda x: int(x))
                for n in range (min(sdf['Лет']), max(sdf['Лет']), 10):
                    if n < (max(sdf['Лет'])-10):
                        duf1 = sdf[(sdf['Лет']>=n) & (sdf['Лет']< (n+10))]
                        medresM = np.median(duf1[sdf['Пол']=='Мужской'][fx])
                        medresW = np.median(duf1[sdf['Пол']=='Женский'][fx])
                        med_let_m.append(medresM)
                        med_let_w.append(medresW)
                        goda.append(n)
                    else:
                        duf2 = sdf[(sdf['Лет']>=n) & (sdf['Лет']< max(sdf['Лет']))]
                        medresM = np.median(duf2[sdf['Пол']=='Мужской'][fx])
                        medresW = np.median(duf2[sdf['Пол']=='Женский'][fx])
                        med_let_m.append(medresM)
                        med_let_w.append(medresW)
                        goda.append(n)

                sns.scatterplot(data=sdf, x='Лет', y= fx, hue = 'Пол')
                ax.plot(goda,med_let_m, color = 'red', label = 'Медиана (мужчины)')
                ax.plot(goda,med_let_w, color = 'black', label = 'Медиана (женщины)')
                ax.set_xlabel('Возраст')
                ax.set_ylabel('Результат')
                iqr=np.percentile(sdf[fx],75) - np.percentile(sdf[fx],25)
                ax.set_ylim(np.median(sdf[fx])-2*iqr,np.median(sdf[fx])+5*iqr)
                ax.set_title(f'Динамика изменения {fx} с возрастом')
                ax.legend()
                return fig
    
            def show_2d(xs,ys,kat, fx, fy):
                fig,ax = plt.subplots()
                fig.set_size_inches(14,6)
                sns.scatterplot(x = xs, y = ys, hue = kat, palette='hsv_r')
                ax.set_xlabel(fx)
                ax.set_ylabel(fy)
                return fig
   
            if snum == 3:
                c1,c2,c3, c4 = form.columns(4)
                b1 = c1.container(border = True)
                b2 = c2.container(border = True)
                b3 = c3.container(border = True)
                b4 = c4.container(border = True)

                fx = b1.selectbox('x', options=df.columns)
                fy = b2.selectbox('y', options=df.columns)
                fz = b3.selectbox('z', options=df.columns)
                cat = b4.selectbox('Возраст', options='Лет')
  
                c11, c12 = b1.columns(2) 
                c13, c14 = b2.columns(2)  
                c15, c16 = b3.columns(2)  
                c17, c18 = b4.columns(2)
                x11 = c11.number_input('min x',help = 'Оставьте 0, если фильтр не нужен')
                x12 = c12.number_input('max x',help = 'Оставьте 0, если фильтр не нужен')
                y13 = c13.number_input('min y',help = 'Оставьте 0, если фильтр не нужен')
                y14 = c14.number_input('max y',help = 'Оставьте 0, если фильтр не нужен')
                z15 = c15.number_input('min z',help = 'Оставьте 0, если фильтр не нужен')
                z16 = c16.number_input('max z',help = 'Оставьте 0, если фильтр не нужен')
                l17 = c17.number_input('min Лет',help = 'Оставьте 0, если фильтр не нужен')
                l18 = c18.number_input('max Лет',help = 'Оставьте 0, если фильтр не нужен')

                butt = form.form_submit_button('🚀 Запуск')

                if butt:
                    columns = [fx,fy,fz]
                    for n in columns:
                        df[n]=df[n].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
       
                    fpl = df.dropna(subset=[fx, fy, fz])

                    if sex == 'Мужской' or sex == "Женский":
                        fpl = fpl[fpl['Пол'] == sex]
                    else:
                        pass
  
                    if x11-x12 !=0:
                        fpl = fpl[(fpl[fx]>x11) & (fpl[fx]<x12)]
                    else:
                        pass
                    if y13-y14 !=0:
                        fpl = fpl[(fpl[fy]>y13) & (fpl[fy]<y14)]
                    else:
                        pass
                    if z15-z16 !=0:
                        fpl = fpl[(fpl[fz]>z15) & (fpl[fz]<z16)]
                    else:
                        pass
                    if l17-l18 !=0:
                        fpl = fpl[(fpl[cat]>l17) & (fpl[cat]<l18)]
                    else:
                        pass
     
                    xs = fpl[fx]
                    ys = fpl[fy]
                    zs = fpl[fz]
                    kat = fpl[cat]
         
                    def show_3d(xs,ys,zs,kat):
                        fig = px.scatter_3d(x = xs, y = ys, z = zs, width=800, height = 800, color = kat , color_continuous_scale = 'hsv_r' )
                        fig.update_traces(marker = dict(size=2.5))
                        fig.update_layout(scene = dict(xaxis = dict(range =[min(xs), max(xs)]), xaxis_title = fx,
                                            yaxis = dict(range = [min(ys), max(ys)]), yaxis_title = fy,
                                            zaxis = dict(range = [min(zs), max(zs)]), zaxis_title = fz),
                                            coloraxis_colorbar = dict(title = 'Возраст'))
                        #fig.show()
                        return fig
                    fig3d = show_3d(xs,ys,zs,kat)
                    st.plotly_chart(fig3d, use_container_width=True)

                    fig2d1 = show_2d(xs,ys,kat, fx, fy)
                    st.pyplot(fig2d1)
                    fig2d2 = show_2d(xs,zs,kat, fx, fz)
                    st.pyplot(fig2d2)
                    fig2d3 = show_2d(ys,zs,kat, fy, fz)
                    st.pyplot(fig2d3)

                    cd1, cd2 = st.columns(2)

                    figdist1 = show_dist(xs,fx)
                    cd1.pyplot(figdist1)
                    figdist2 = show_dist(ys,fy)
                    cd1.pyplot(figdist2)
                    figdist3 = show_dist(zs,fz)
                    cd1.pyplot(figdist3)

                    figages1 = show_ages(fx, fpl)
                    figages2 = show_ages(fy, fpl)
                    cd2.pyplot(figages2)
                    figages3 = show_ages(fz, fpl)
                    cd2.pyplot(figages3)

            if snum == 2:
                c1,c2,c3 = form.columns(3)
                b1 = c1.container(border = True)
                b2 = c2.container(border = True)
                b3 = c3.container(border = True)
  
                fx = b1.selectbox('x', options=df.columns)
                fy = b2.selectbox('y', options=df.columns)
                cat = b3.selectbox('Возраст', options='Лет')
  
                c11, c12 = b1.columns(2) 
                c13, c14 = b2.columns(2)  
                c15, c16 = b3.columns(2)  
                x11 = c11.number_input('min x',help = 'Оставьте 0, если фильтр не нужен')
                x12 = c12.number_input('max x',help = 'Оставьте 0, если фильтр не нужен')
                y13 = c13.number_input('min y',help = 'Оставьте 0, если фильтр не нужен')
                y14 = c14.number_input('max y',help = 'Оставьте 0, если фильтр не нужен')
                l17 = c15.number_input('min Лет',help = 'Оставьте 0, если фильтр не нужен')
                l18 = c16.number_input('max Лет',help = 'Оставьте 0, если фильтр не нужен')
 
                butt = form.form_submit_button('🚀 Запуск')

                if butt:
                    columns = [fx,fy]
                    for n in columns:
                        df[n]=df[n].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
       
                    fpl = df.dropna(subset=[fx, fy])

                    if sex == 'Мужской' or sex == "Женский":
                        fpl = fpl[fpl['Пол'] == sex]
                    else:
                        pass
  
                    if x11-x12 !=0:
                        fpl = fpl[(fpl[fx]>x11) & (fpl[fx]<x12)]
                    else:
                        pass
                    if y13-y14 !=0:
                        fpl = fpl[(fpl[fy]>y13) & (fpl[fy]<y14)]
                    else:
                        pass
                    if l17-l18 !=0:
                        fpl = fpl[(fpl[cat]>l17) & (fpl[cat]<l18)]
                    else:
                        pass
     
                    xs = fpl[fx]
                    ys = fpl[fy]
                    kat = fpl[cat]  
 
                       
                    fig2d = show_2d(xs,ys,kat, fx, fy)
                    st.pyplot(fig2d)

                    cd1, cd2 = st.columns(2)

                    figdist1 = show_dist(xs,fx)
                    cd1.pyplot(figdist1)
                    figdist2 = show_dist(ys,fy)
                    cd1.pyplot(figdist2)

                    figages1 = show_ages(fx, fpl)
                    cd2.pyplot(figages1)
                    figages2 = show_ages(fy, fpl)
                    cd2.pyplot(figages2)

            if snum == 1:
                c1,c3 = form.columns(2)
                b1 = c1.container(border = True)
                b3 = c3.container(border = True)
  
                fx = b1.selectbox('x', options=df.columns)
                cat = b3.selectbox('Возраст', options='Лет')
  
                c11, c12 = b1.columns(2) 
                c15, c16 = b3.columns(2)  
                x11 = c11.number_input('min x',help = 'Оставьте 0, если фильтр не нужен')
                x12 = c12.number_input('max x',help = 'Оставьте 0, если фильтр не нужен')
                l17 = c15.number_input('min Лет',help = 'Оставьте 0, если фильтр не нужен')
                l18 = c16.number_input('max Лет',help = 'Оставьте 0, если фильтр не нужен')

                butt = form.form_submit_button('🚀 Запуск')

                if butt:
                    columns = [fx]
                    for n in columns:
                        df[n]=df[n].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
       
                    fpl = df.dropna(subset=[fx])

                    if sex == 'Мужской' or sex == "Женский":
                        fpl = fpl[fpl['Пол'] == sex]
                    else:
                        pass
  
                    if x11-x12 !=0:
                        fpl = fpl[(fpl[fx]>x11) & (fpl[fx]<x12)]
                    else:
                        pass
                    if l17-l18 !=0:
                        fpl = fpl[(fpl[cat]>l17) & (fpl[cat]<l18)]
                    else:
                        pass
    
                    xs = fpl[fx]
                    kat = fpl[cat]  
                      
          
                    figdist1 = show_dist(xs,fx)
                    st.pyplot(figdist1)

                    figages1 = show_ages(fx, fpl)
                    st.pyplot(figages1)

        # СРЕДНЕЕ ПО ПАЦИЕНТАМ    
        if radio == '📈 Среднее по пациентам':

            st.info('📈 Среднее по пациентам: необходимы колонки с заголовками Результат, Пол, Дата авторизации. Для получения статистики по отправителям (опционально) необходима колонка Отправитель')
            df['Результат']=df['Результат'].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
            df['Дата авторизации'] = pd.to_datetime(df['Дата авторизации']).dt.date
            df['Лет'] = df['Лет'].apply(lambda x: int(x))
            box = st.form('Форма для средних', border=True)
            cb1, cb2 = box.columns(2)
            #date_from = cb1.date_input('Дата авторизации (от)',min(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
            #date_to = cb2.date_input('Дата авторизации (до)', max(df['Дата авторизации']),min_value=min(df['Дата авторизации']),max_value=max(df['Дата авторизации']),format = 'DD/MM/YYYY')
            sexbox = cb1.selectbox('Пол', options= ['Все', 'Мужской', 'Женский', 'Сравнить'])
            #otpr = cb2.multiselect('Выбрать отправителей', options= df['Отправитель'].unique(), placeholder= 'Оставьте пустым, если нужны все')
            porog = box.number_input("Введите пороговое значение для отображения % результатов выше этого порога за день", step = 0.01)
            dynamic = box.form_submit_button('📈 Показать динамику')
            unique_date = sorted(df['Дата авторизации'].unique())
            ran = list(range(1,len(unique_date)+1))
            #ddf = df[(df['Дата авторизации']>=date_from) & (df['Дата авторизации']<date_to)]


            def show_dynamic(sexdf):
                M=[]
                Med =[]
                per25 = []
                per75=[]
                dolyas = []
                days = []

                for n in unique_date:
                    mdf = sexdf[sexdf['Дата авторизации']==n]
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

                return M, Med, per25, per75, dolyas, days

            def show_dispatcher(df):
                fig, ax = plt.subplots()
                fig.set_size_inches(14,55)
                otprav = df['Отправитель'].unique()
                xx = []
                yy = []
                lens = []

                for n in otprav:
                    y = df[df['Отправитель'] == n]['Результат'].median()
                    yy.append(y)
                    xx.append(n)
                    lens.append(len(df[df['Отправитель'] == n]['Результат']))

                dick = {'Результат':yy, 'Отправитель':xx, 'Число проб': lens}
                didf = pd.DataFrame(dick)
                sorted_didf = didf.sort_values(by = 'Результат', ascending = False)
                sorted_didf['Отправитель'] = sorted_didf['Отправитель'] + ' N = ' + sorted_didf['Число проб'].apply(lambda x: str(x))
                nx = sorted_didf['Отправитель']
                ny = sorted_didf['Результат']
                sns.barplot(y=nx, x=ny)
                ax.bar_label(ax.containers[0], fontsize=10)
                return fig


            if dynamic:
                def show_plot_dynamic(M, Med, per25, per75, dolyas, days):
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
                        #st.pyplot(fig2)
                        return fig2
                    except:
                        st.warning('Не получилось рассчитать')

                if sexbox == 'Мужской' or sexbox == 'Женский':
                    sexdf = df[df['Пол'] == sexbox]
                    M, Med, per25, per75, dolyas, days = show_dynamic(sexdf)
                    figa = show_plot_dynamic(M, Med, per25, per75, dolyas, days)
                    st.pyplot(figa)
                elif sexbox == 'Сравнить':
                    csd1, csd2 = st.columns(2)
                    sexwomendf = df[df['Пол'] == 'Женский']
                    wM, wMed, wper25, wper75, wdolyas, wdays = show_dynamic(sexwomendf)
                    figa1 = show_plot_dynamic(wM, wMed, wper25, wper75, wdolyas, wdays)
                    sexmendf = df[df['Пол'] == 'Мужской'] 
                    mM, mMed, mper25, mper75, mdolyas, mdays = show_dynamic(sexmendf)
                    figa2 = show_plot_dynamic(mM, mMed, mper25, mper75, mdolyas, mdays)
                    csd1.subheader('Женщины')  
                    csd1.pyplot(figa1)
                    csd2.subheader('Мужчины') 
                    csd2.pyplot(figa2)
                else:
                    M, Med, per25, per75, dolyas, days = show_dynamic(df)
                    figa = show_plot_dynamic(M, Med, per25, per75, dolyas, days) 
                    st.pyplot(figa)    

                if 'Отправитель' in df.columns:
                    figus = show_dispatcher(df)    
                    st.pyplot(figus) 
                else:
                    st.warning('⚠️❗ В загруженном файле нет колонки Отправитель. Статистика по отправителям не может быть отображена')  

if radio == 'Cosinor-модель для ТТГ': 
    st.header('Калькулятор референсных значений ТТГ на основе cosinor-модели')   
    st.info('Cоздан по данным статьи: Interpretation of TSH results can be improved by reference value fluctuating in time ' \
    'https://www.degruyterbrill.com/document/doi/10.1515/hmbci-2024-0043/html')    
    cosform = st.form('cosinor')
    cossubh = cosform.subheader('Внесите время, скорректируйте пороги, если необходимо, и нажмите Посчитать')
    time = cosform.number_input('**Укажите время забора крови (в часах)**', min_value=0.0, max_value=24.0, value=6.0)
    cosc001, cosc002, cosc003, cosc004 = cosform.columns([1,1,2,1])
    cosc01, cosc02, cosc03, cosc04 = cosform.columns([1,1,2,1])
    cosc11, cosc12, cosc13, cosc14 = cosform.columns([1,1,2,1])
    cosc21, cosc22, cosc23, cosc24 = cosform.columns([1,1,2,1])

    cosc002.markdown('**Внесите пороговые значения**')
    cosc003.markdown('**Формула расчёта из статьи**')

    markc1 = cosc01.markdown('Верхняя граница РИ')
    markc2 = cosc11.markdown('Медиана')
    markc3 = cosc21.markdown('Нижняя граница РИ')

    hlev = cosc02.number_input('Верхняя граница РИ', value=5.20, min_value=0.00, label_visibility = 'collapsed')
    mlev = cosc12.number_input('Медиана', value=1.71, min_value=0.00, label_visibility = 'collapsed')
    llev = cosc22.number_input('Нижняя граница РИ', value=0.40, min_value=0.00, label_visibility = 'collapsed')

    latex1 = cosc03.latex(r"""\text{TSH}_{\text{cutoff}}(h) = 5{,}20 + 0{,}60 \cdot \cos\left(\frac{\pi}{12}(h - 6)\right)""")
    latex2 = cosc13.latex(r"""\text{TSH}_{\text{cutoff}}(h) = 1{,}71 + 0{,}30 \cdot \cos\left(\frac{\pi}{12}(h - 6)\right)""")
    latex3 = cosc23.latex(r"""\text{TSH}_{\text{cutoff}}(h) = 0{,}40 + 0{,}24 \cdot \cos\left(\frac{\pi}{12}(h - 6)\right)""")

    cosbutton = cosform.form_submit_button('😎 **Посчитать**')

    def low_level(t):
        ll = llev + 0.24 * np.cos((np.pi/12)*(t-6))
        return ll

    def med_level(t):
        ml = mlev + 0.3 * np.cos((np.pi/12)*(t-6))
        return ml   

    def high_level(t):
        hl = hlev + 0.6 * np.cos((np.pi/12)*(t-6))
        return hl   

    def cosinor_plot():
        hours = np.arange(0,25,1)
        lls = []
        mls = []
        hls = []

        for n in hours:
            t = hours[n]
            l = low_level(t)
            m = med_level(t)
            h = high_level(t)
    
            lls.append(l)
            mls.append(m)
            hls.append(h)

        fig, ax = plt.subplots(figsize=(10,5),dpi = 200)
        ax.plot(hours,lls, label = 'Нижняя граница РИ')
        ax.plot(hours, mls, label = 'Медиана')
        ax.plot(hours, hls, label = 'Верхняя граница РИ')
        if cosbutton:
            point_low = low_level(time)
            point_med = med_level(time)
            point_high = high_level(time)
            ax.scatter(time, point_low, s=80, edgecolors='face', alpha=0.8)
            ax.annotate(f'{point_low:.2f}', (time,point_low), xytext=(5,5), textcoords='offset points')
            ax.scatter(time, point_med, s=80, edgecolors='face', alpha=0.8)
            ax.annotate(f'{point_med:.2f}', (time,point_med), xytext=(5,5), textcoords='offset points')
            ax.scatter(time, point_high, s=80, edgecolors='face', alpha=0.8)
            ax.annotate(f'{point_high:.2f}', (time,point_high), xytext=(5,5), textcoords='offset points')
        ax.set_xlabel('Время взятия крови (в часах)')
        ax.set_ylabel('Результат ТТГ, мМЕ/л')
        ax.set_ylim(0, max(hls)+0.4)
        ax.set_xlim(-1,25.3)
        ax.set_title('Динамика изменения референсных значений ТТГ в течение дня')
        ax.legend()

        return fig


    cos_fig = cosinor_plot()
    st.pyplot(cos_fig)



    