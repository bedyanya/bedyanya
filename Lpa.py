from scipy import interpolate
import numpy as np
from numpy.polynomial import Polynomial
from matplotlib import pyplot as plt
import streamlit as st
#====================================================================
sidebox = st.sidebar.form('Calibration')
col1,col2, col3 = sidebox.columns(3)
с11 = col1.number_input('т1, мг/дл',value=0)
с12 = col1.number_input('т2, мг/дл', value = 6.8)
с13 = col1.number_input('т3, мг/дл', value = 14.4)
с14 = col1.number_input('т4, мг/дл', value = 33.8)
с15 = col1.number_input('т5, мг/дл', value = 65.5)
с16 = col1.number_input('т6, мг/дл', value = 94.4)

с21 = col2.number_input('  OD 1',value= -0.0012,step=0.0001,format="%f")
с22 = col2.number_input('  OD 2',value= 0.0307,step=0.0001, format="%f")
с23 = col2.number_input('  OD 3',value= 0.0570,step=0.0001,format="%f")
с24 = col2.number_input('  OD 4',value= 0.1374,step=0.0001,format="%f")
с25 = col2.number_input('  OD 5',value= 0.3187,step=0.0001,format="%f")
с26 = col2.number_input('  OD 6',value= 0.4763,step=0.0001,format="%f")

с31 = col3.number_input(' нмоль/л',value= 0)
с32 = col3.number_input(' нмоль/л',value= 10.8)
с33 = col3.number_input(' нмоль/л',value= 24.3)
с34 = col3.number_input(' нмоль/л',value= 61.2)
с35 = col3.number_input(' нмоль/л',value= 138)
с36 = col3.number_input(' нмоль/л',value= 215)

#====================================================================

sidebox.form_submit_button('Пересчитать калибровочную кривую')
#====================================================================

box = st.form('Рассчитать')
inp = box.number_input('Внесите значение Lp(a) в мг/дл для пересчёта')
column1,column2 = box.columns(2)
box_button = box.form_submit_button('Пересчитать в нмоль/л')

#====================================================================
mg = [с11,с12,с13,с14,с15,с16]
op = [с21,с22,с23,с24,с25,с26]
# получаем кубический интерполяционный сплайн
f_cubic = interpolate.interp1d(mg,op,kind='cubic')
# генерируем кривую 
x_data = np.linspace(с11,с16,200)
f_op = f_cubic(x_data)


#====================================================================
# Калибровочная кривая
fig,ax = plt.subplots()
ax.set_title('Калибровочная кривая')
fig.set_size_inches(14,8)
ax.plot(x_data,f_op,label='Кубический сплайн')
ax.scatter(mg,op)
ax.set_xlabel('мг/дл')
ax.set_ylabel('OD')

st.pyplot(fig)

#====================================================================
mol = [с31, с32, с33, с34, с35, с36]
f_cub = interpolate.interp1d(mg,mol,kind='cubic')
f_lin = interpolate.interp1d(mg,mol,kind='linear')
data_mg = np.linspace(с11,с16,1200)
data_mol = f_cub(data_mg)
data_mol_lin = f_lin(data_mg)
approx = Polynomial.fit(mg,mol,3)
poly = approx(data_mg)
#====================================================================

fig2, ax2 = plt.subplots(nrows=1,ncols=2)
fig2.set_size_inches(14,6)
ax2[0].plot(data_mg,data_mol,label='Кубический интерполяционный сплайн',color='g')
ax2[0].plot(data_mg,data_mol_lin,label='Линейный интерполяционный сплайн',color='orange')
ax2[1].plot(data_mg,poly, label = 'Аппроксимация полиномом 3 степени',color='black')
ax2[0].legend()
ax2[1].legend()
ax2[0].scatter(mg,mol)
ax2[1].scatter(mg,mol)
ax2[0].set_xlabel('мг')
ax2[1].set_xlabel('мг')
ax2[0].set_ylabel('нмоль')
ax2[1].set_ylabel('нмоль')
st.pyplot(fig2)

#====================================================================
# По калибровочной кривой строим обратную для нмоль/л
f_cubic_mol = interpolate.interp1d(op,mol,kind='cubic')
data_op = np.linspace(с21,с26,1200)
data_op_mol = f_cubic_mol(data_op)


if box_button:
    column1.write('Расчет по калибровочной кривой:')
    try:
        column1.text(f_cubic_mol(f_cubic(inp)).round(3))
    except:
        column1.write('Значение вне калибровочной кривой')

    column2.write('Расчет по значениям калибратора')
    try:
        column2.text('Кубическая интерполяция: ' f'{f_cub(inp).round(3)}')
        column2.text('Линейная интерполяция: ' f'{f_lin(inp).round(3)}')
        column2.text('Аппроксимация полиномом: ' f'{approx(inp).round(3)}')
    except:
        column2.write('Значение вне калибровочной кривой')
#====================================================================
#fig3, ax3 = plt.subplots()
#fig3.set_size_inches(14,6)

#ax3.plot(data_op, data_op_mol, label='Кубический сплайн, нмоль')
#ax3.scatter(op,mol)
#ax3.set_xlabel('OD')
#ax3.set_ylabel('нмоль/л')

#st.pyplot(fig3)
#====================================================================