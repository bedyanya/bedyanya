from scipy import interpolate
from scipy.optimize import fsolve
from scipy.interpolate import InterpolatedUnivariateSpline
import numpy as np
from numpy.polynomial import Polynomial
from matplotlib import pyplot as plt
import streamlit as st
#====================================================================
sidebox = st.sidebar.form('Calibration')
col1,col2, col3 = sidebox.columns(3)
с11 = col1.number_input('т1, пг/мл',value=0)
с12 = col1.number_input('т2, пг/мл', value = 9.5)
с13 = col1.number_input('т3, пг/мл', value = 61.1)
с14 = col1.number_input('т4, пг/мл', value = 311)
с15 = col1.number_input('т5, пг/мл', value = 1483)
с16 = col1.number_input('т6, пг/мл', value = 3278)

с21 = col2.number_input('  OD 1',value= 23994.5,step=0.1,format="%f")
с22 = col2.number_input('  OD 2',value= 99776.5,step=0.1, format="%f")
с23 = col2.number_input('  OD 3',value= 477244.0,step=0.1,format="%f")
с24 = col2.number_input('  OD 4',value= 2273422.5,step=0.1,format="%f")
с25 = col2.number_input('  OD 5',value= 9279334.5,step=0.1,format="%f")
с26 = col2.number_input('  OD 6',value= 16554929.5,step=0.1,format="%f")

с31 = col3.number_input(' пг/мл',value= 0)
с32 = col3.number_input(' пг/мл',value= 9.5)
с33 = col3.number_input(' пг/мл',value= 61.1)
с34 = col3.number_input(' пг/мл',value= 311)
с35 = col3.number_input(' пг/мл',value= 1483)
с36 = col3.number_input(' пг/мл',value= 3278)

#====================================================================

sidebox.form_submit_button('Пересчитать калибровочную кривую')
#====================================================================

box = st.form('Рассчитать')
inp = box.number_input('Внесите значение Lp(a) в мг/дл для пересчёта',step=0.001,format="%f")
column1,column2 = box.columns(2)
box_button = box.form_submit_button('Пересчитать в нмоль/л')

#====================================================================

box2 = st.form('OD')
input_OD = box2.number_input('Внесите значение OD',step=0.0001,format="%f")
box2_button = box2.form_submit_button('Рассчитать концентрацию в мг/дл и в нмоль/л по калибровочной кривой')

#====================================================================
mg = [с11,с12,с13,с14,с15,с16]
op = [с21,с22,с23,с24,с25,с26]
# получаем кубический интерполяционный сплайн
# мг/дл ---> OD
f_cubic = interpolate.interp1d(mg,op,kind='cubic')
# OD ---> мг/дл
from_op_to_mg = interpolate.interp1d(op,mg,kind='cubic')
# генерируем кривую 
x_data = np.linspace(с11,с16,1200)
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
# Калибратор
mol = [с31, с32, с33, с34, с35, с36]
f_cub = interpolate.interp1d(mg,mol,kind='cubic')
f_lin = interpolate.interp1d(mg,mol,kind='linear')
data_mg = np.linspace(с11,с16,1200)
data_mol = f_cub(data_mg)
data_mol_lin = f_lin(data_mg)
approx = Polynomial.fit(mg,mol,3)
poly = approx(data_mg)
#====================================================================
# Графики по калибратору
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

if box_button:
    column1.write('Расчет по калибровочной кривой:')
    try:
        num = f_cubic(inp)
        num_mol = InterpolatedUnivariateSpline(mol,op-num).roots().round(3)
        column1.text(num_mol[0])
        #column1.text(f_cubic_mol(f_cubic(inp)).round(3))
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

if box2_button:
    try:
        n_mg = InterpolatedUnivariateSpline(mg,np.array(op)-input_OD).roots().round(3)
        n_mol = InterpolatedUnivariateSpline(mol,np.array(op)-input_OD).roots().round(3)

        box2.text(f'{n_mg[0]}' ' мг/дл')
        box2.text(f'{n_mol[0]}' ' нмоль/л')
    except:
        box2.write('Значение OD вне диапазона калибровочной кривой')

#====================================================================
