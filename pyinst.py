import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
import plotly.express as px
#from datetime import datetime,date, timedelta

st.set_page_config(layout="wide")
#
uploaded_file = st.sidebar.file_uploader("Выбери файл Excel на компе",
                                         type=['xlsx','xls'])
radio = st.sidebar.radio('**Выбери тип исследования**', options= ['🔀 Визуализация данных и их взаимосвязи', '📈 Среднее по пациентам'])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, engine='openpyxl')
    st.write(df.head(10))

#radio = st.sidebar.radio('', options= ['Исследование данных', 'Среднее по пациентам'])

    if radio == '🔀 Визуализация данных и их взаимосвязи':
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
        #form = st.form('Форма')
        #с00, c01 = form.columns(2)
        #sex = с00.selectbox('Пол', options = ['Все', 'Мужской', 'Женский'])
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
                cd2.pyplot(figages1)
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
    
    if radio == '📈 Среднее по пациентам':
        df['Результат']=df['Результат'].apply(lambda x: float(str(x).translate({ord(i): None for i in '&gt;l<>'})))
        df['Дата авторизации'] = pd.to_datetime(df['Дата авторизации']).dt.date
        box = st.form('Форма для средних', border=True)
        porog = box.number_input("Введите пороговое значение для отображения % результатов выше этого порога за день", step = 0.01)
        dynamic = box.form_submit_button('📈 Показать динамику')
        unique_date = sorted(df['Дата авторизации'].unique())
        ran = list(range(1,len(unique_date)+1))

        M=[]
        Med =[]
        per25 = []
        per75=[]
        dolyas = []
        days = []

        for n in unique_date:
            mdf = df[df['Дата авторизации']==n]
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
                st.warning('Не получилось рассчитать')
                     


    
