import numpy as np
import pandas as pd
from datetime import datetime
import streamlit as st
from pathlib import Path
#from st_aggrid import AgGrid


analizator_option = ['ERBA XL-1000', 'ACL TOP 550', 'Rotem Delta', 'Erba Elite 580', 'Lifotronic H9', 'Maglumi', 
                     'Lazurit', 'DxI800', 'Группы крови/OrthoVision','Laura XL', 'ABL 800', 
                     'Mindray BS240', 'ecl8000', 'Красители/Общая клиника' ]
analizer_select = st.sidebar.selectbox('Анализатор/Раздел', options=analizator_option)


states = ['Поставки','Списание','Итого в наличии','Статистика']
state = st.sidebar.radio('Выбери раздел',options=states,horizontal=False)
#------------------------------------------------------------------------------------


if analizer_select =='ERBA XL-1000':
    read_file = 'ERBAXL-1000.xlsx'
    analiser_df =pd.read_excel(read_file)
    st.image('https://mqst.ru/t/j-vtEsPx-j7mktwwMuBrDhyqb7c=/0x1040/2022/02/pALPXoG3oKYqfKyW3hxS3LpdazZZ09hRnzoKZB7M.jpg', width=250)
if analizer_select =='ACL TOP 550':
    analiser_df =pd.read_excel(r'C:\Users\кусь\OneDrive\Рабочий стол\GOVNO\ACL TOP 550.xlsx',sheet_name='Лист1',engine='openpyxl')
    st.image('https://avatars.mds.yandex.net/i?id=11dd2705f9f88d64fd10160131cee70006839ba0-9860796-images-thumbs&n=13',width=250)

    #grid_return = AgGrid(analiser_df, editable=True)
#st.data_editor(grid_return['data'])
reagents_list = analiser_df['Реагент'].unique()
post_spis_list = analiser_df['ИТОГ (фильтр)'].unique()
       

if state == 'Поставки':
    st.title('Информация о реагенте в поставке')
    st.sidebar.image('https://thumbs.dreamstime.com/b/british-cat-shopping-cart-25357442.jpg',width=270)
    box1 = st.form('form')
            
    col1,col2,col3,col4 = box1.columns(4)
    if 'change' not in st.session_state:
        st.session_state.change = False
    def change_reag():
        st.session_state.change = st.session_state.change

    reag = st.sidebar.selectbox('Выберите реагент/РМ',options=reagents_list, on_change=change_reag)
    
    with col1:
        #col1.image('https://thumbs.dreamstime.com/b/british-cat-shopping-cart-25357442.jpg',width=100)
        label = col1.selectbox('краткое название', options=analiser_df[analiser_df['Реагент']==reag]['краткое наименование'].unique())
        ref = col1.selectbox('каталожник',options = analiser_df[analiser_df['Реагент']==reag]['каталожник'].unique())

    with col2:
        lot = col2.text_input('лот')
        srok = col2.date_input('срок годности',format="DD/MM/YYYY")
    with col3:
        data_postavki = col3.date_input('дата поставки',format="DD/MM/YYYY")
        kolvo = col3.number_input('количество', min_value=1, step=1)
    with col4:
        contract = col4.text_input('Контракт/Накладная')
        comment = col4.text_input('Комментарий')
        
        
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=analiser_df.columns)
        #st.write(st.session_state.data)
    if 'change_post' not in st.session_state:
        st.session_state.change_post = False

    # КНОПКА ПОСТАВКИ
    postavka_button = box1.form_submit_button("Добавить запись")

    if postavka_button:
        
        dict_for_df = {'каталожник':[ref],
                       'Реагент':[reag], 
                       'краткое наименование':[label],
                       'лот': [lot], 
                       'срок годности':[srok],
                       'дата поставки': [data_postavki],
                    'поступление кол-во':[kolvo], 
                    'контракт': [contract], 
                    'ИТОГ (фильтр)': ['поставка'], 
                    'Комментарий': [comment]}
        new_df = pd.DataFrame(data=dict_for_df)
        hide_df = pd.DataFrame(columns=analiser_df.columns)
        hide_df = hide_df.merge(new_df,how='outer')
        st.session_state.data = pd.concat([st.session_state.data,hide_df],ignore_index=True)
   
        #st.data_editor(st.session_state.data,hide_index=True,num_rows='dynamic')
        #grid_return = AgGrid(st.session_state.data, editable=True)
        #st.session_state.change_post = not st.session_state.change_post
    #grid_return = AgGrid(st.session_state.data, editable=True,height=200,fit_columns_on_grid_load=False)
   
     
    st.session_state.data = st.data_editor(st.session_state.data,hide_index=True,num_rows='dynamic',
                                           column_config={'срок годности': st.column_config.DateColumn(format="DD-MM-YYYY"),
                                                          'дата поставки':st.column_config.DateColumn(format="DD-MM-YYYY")})
    # СОХРАНИТЬ ПОСТАВКУ В БАЗУ ДАННЫХ
    save_to_db = st.button('Сохранить записи в базу данных')
    if save_to_db:
        analiser_df = pd.concat([analiser_df,st.session_state.data],ignore_index=True)
        fp=Path(r'C:\Users\кусь\OneDrive\Рабочий стол\GOVNO', analizer_select+'.xlsx')
        analiser_df.to_excel(fp,sheet_name='Лист1',index=False)
        st.session_state.data = pd.DataFrame(columns=analiser_df.columns)
        st.success('Данные сохранены',icon="✅")



    #st.write('Все поставки')
    vse_postavki = st.sidebar.button('Показать все поставки')
    if vse_postavki:
        st.dataframe(analiser_df[(analiser_df['Реагент']==reag) & (analiser_df['ИТОГ (фильтр)']=='поставка')],
                              column_config={'срок годности': st.column_config.DateColumn(format="DD-MM-YYYY"),
                                             'дата поставки':st.column_config.DateColumn(format="DD-MM-YYYY")})


#------------------------------------------------------------------------------------
if state == 'Списание':

    reag = st.sidebar.selectbox('Выбери Реагент/РМ 👈🏼',options=reagents_list)
    kratkoe = st.sidebar.selectbox('краткое название', options=analiser_df[analiser_df['Реагент']==reag]['краткое наименование'].unique())
    ref = st.sidebar.selectbox('каталожник',options = analiser_df[analiser_df['Реагент']==reag]['каталожник'].unique())
    lot = st.sidebar.selectbox('Выбери ЛОТ 👈🏼',options = analiser_df[analiser_df['Реагент']==reag]['лот'].unique())
    srok_godnosti = st.sidebar.selectbox('срок годности', options=analiser_df[analiser_df['лот']==lot]['срок годности'].unique())
    #srok_godnosti = st.sidebar.date_input('срок годности', analiser_df[analiser_df['лот']==lot]['срок годности'].unique(),format="DD-MM-YYYY")
    #contract=st.sidebar.selectbox('контракт/накладная', options=analiser_df[analiser_df['Реагент']==reag]['контракт'].unique())
    #st.write(analiser_df[(analiser_df['Реагент']==reag) & (analiser_df['ИТОГ (фильтр)']=='списание')])

    box_spis = st.form('form_spisanie')

    col11,col22,col33 = box_spis.columns(3)

    with col11:
        date_spis = col11.date_input('дата списания',format="DD/MM/YYYY")
        #lot = col11.selectbox('ЛОТ',options = analiser_df[analiser_df['Реагент']==reag]['лот'].unique())

    with col22:
        kolvo_spis = col22.number_input('количество', min_value=1, step=1)
    with col33:
        comment_spis = col33.text_input('Комментарий к списанию')

    if 'data_spis' not in st.session_state:
        st.session_state.data_spis = pd.DataFrame(columns=analiser_df.columns)

    #КНОПКА СПИСАНИЯ:
    spisanie_button = box_spis.form_submit_button("Добавить запись на списание")
    if spisanie_button:
        #sum(analiser_df[analiser_df['лот']==lot]['поступление кол-во'])
        if kolvo_spis> (np.sum(analiser_df[analiser_df['лот']==lot]['поступление кол-во'])-np.sum(analiser_df[analiser_df['лот']==lot]['списано кол-во'])):
            st.write('Данного лота столько нет в наличии. Всего у нас:')
            st.write(np.sum(analiser_df[analiser_df['лот']==lot]['поступление кол-во'])-np.sum(analiser_df[analiser_df['лот']==lot]['списано кол-во']))
        else:
            dict_for_spisanie_df = {'каталожник':[ref],
                                    'Реагент':[reag],
                                    'краткое наименование': [kratkoe],
                                    'лот': [lot], 
                                    'срок годности':[srok_godnosti],
                                    'дата списания':[date_spis],
                                    'списано кол-во':[kolvo_spis], 
                                    'ИТОГ (фильтр)': ['списание'], 
                                    'Комментарий': [comment_spis]}
            spis_df = pd.DataFrame(data=dict_for_spisanie_df)
            sp_hide_df = pd.DataFrame(columns=analiser_df.columns)
            sp_hide_df = sp_hide_df.merge(spis_df,how='outer')
            st.session_state.data_spis = pd.concat([st.session_state.data_spis,sp_hide_df],ignore_index=True)

    st.session_state.data_spis = st.data_editor(st.session_state.data_spis,hide_index=True,num_rows='dynamic',
                                                column_config={'дата списания':st.column_config.DateColumn(format="DD-MM-YYYY")})
    
    # СОХРАНИь В БАЗУ ДАННЫХ
    spis_base_button = st.button('Списать в базе данных')
    if spis_base_button:
        for i in st.session_state.data_spis['лот']:
            if np.sum(st.session_state.data_spis[st.session_state.data_spis['лот']==i]['списано кол-во'])>(np.sum(analiser_df[analiser_df['лот']==i]['поступление кол-во'])-np.sum(analiser_df[analiser_df['Реагент']==i]['списано кол-во'])):
                st.write('❌ Нет столько у нас лота '
                          f'{i}', 
                          str(st.session_state.data_spis[st.session_state.data_spis['лот']==i]['краткое наименование'].unique()),
                          '. Проверь правильность внесения данных')
            else:
                analiser_df = pd.concat([analiser_df,st.session_state.data_spis],ignore_index=True)
                analiser_df.to_excel(r'C:\Users\кусь\OneDrive\Рабочий стол\GOVNO\ERBA XL-1000.xlsx',sheet_name='Лист1',index=False) 
                st.session_state.data_spis = pd.DataFrame(columns=analiser_df.columns)
                st.success('Списание добавлено в базу данных',icon="✅")
    
    # ВСЕ Списания
    vse_spisaniya = st.sidebar.button('Показать все списания')
    if vse_spisaniya:
        st.dataframe(analiser_df[(analiser_df['Реагент']==reag) & (analiser_df['ИТОГ (фильтр)']=='списание')],
                              column_config={'дата списания':st.column_config.DateColumn(format="DD-MM-YYYY")})           
           

# ИТОГО все
if state == 'Итого в наличии':
    toggle = st.sidebar.toggle('Показать выборочно')
    toggle_lot = st.sidebar.toggle('Показать лоты')
    st.header('ИТОГО')
    if toggle is False:
        itog_list = []
        kats =[]
        ns = []
        ms = []
        noms = []
        # lots
        #itog_list_lot = []
        #kats_lot =[]
        #ns_lot = []
        #ms_lot = []
        #noms_lot = []
        #lots = []
        #sroks = []
        for n in reagents_list:
            df_n = analiser_df[analiser_df['Реагент']==n]
            razn = np.sum(df_n['поступление кол-во'])-np.sum(df_n['списано кол-во'])
            itog_list.append(razn)
            kat = df_n['каталожник'].iloc[0]
            m = df_n['краткое наименование'].unique()
            kats.append(kat)
            ms.append(m)
            ns.append(n)
            nom = df_n['номенклатура']
            noms.append(nom.iloc[0])
            #for l in list(df_n['лот'].unique()):
            #    df_lot = df_n[df_n['лот']==l]
            #    kat_l = df_lot['каталожник']
            #    kats_lot.append(kat_l)
            #    m_l = df_lot['краткое наименование'].unique()
            #    srok_l = df_lot['срок годности']
            #    sroks.append(srok_l)
            #    ms_lot.append(m_l)
            #    ns_lot.append(n)
            #    lots.append(l)
            #    nom_l = df_lot['номенклатура']
            #    noms_lot.append(nom_l)
            #    razn_lot = np.sum(df_lot['поступление кол-во'])-np.sum(df_lot['списано кол-во'])
            #    itog_list_lot.append(razn_lot)
        dict_itog = {'REF':kats,'Реагент':ns, 'краткое наименование':ms,'ВСЕГО':itog_list, 'номенклатура':noms}
        df_itog = pd.DataFrame(dict_itog)
        st.dataframe(df_itog,hide_index=True, use_container_width=300)
        #if toggle_lot is True:
        #    dict_itog_lot = {'REF':kats_lot,'Реагент':ns_lot, 'краткое наименование':ms_lot,'ЛОТ':lots ,
        #                     'Срок':sroks, 'ВСЕГО':itog_list_lot}
        #    df_itog_lot = pd.DataFrame(dict_itog_lot)
        #    st.dataframe(df_itog_lot,hide_index=True, use_container_width=300, 
        #                 column_config={'Срок':st.column_config.DateColumn(format="DD-MM-YYYY")})

    if toggle is True:
        vibor = st.sidebar.multiselect('Выбери Реагенты/РМ ℹ️ ',options=reagents_list)
        df_vibor = analiser_df[analiser_df['Реагент'].isin(vibor)]
        itog_list2 = []
        ns2 = []
        ms2 = []
        kats2=[]
        noms2 = []
        for n2 in vibor:
            df_n2 = df_vibor[df_vibor['Реагент']==n2]
            razn2 = np.sum(df_n2['поступление кол-во'])-np.sum(df_n2['списано кол-во'])
            itog_list2.append(razn2)
            kat2 = df_n2['каталожник'].iloc[0]
            m2 = df_n2['краткое наименование'].unique()
            nom2 = df_n2['номенклатура'].iloc[0]
            noms2.append(nom2)
            kats2.append(kat2)
            ms2.append(m2)
            ns2.append(n2)
        dict_itog2 = {'REF':kats2,'Реагент':ns2, 'краткое наименование':ms2,'ВСЕГО':itog_list2, 'номенклатура':noms2}
        df_itog2 = pd.DataFrame(dict_itog2)
        st.dataframe(df_itog2,use_container_width=200, hide_index=True)

        #pokaz_vibor = st.sidebar.button('Показать')
        #if pokaz_vibor:
        #    st.table(df_vibor,hide_index=True)




# СТАТИСТИКА
if state == 'Статистика':
    st.header('Данный функционал в разработке')

