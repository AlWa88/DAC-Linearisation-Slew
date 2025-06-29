'''
Plot utility for enob csv file

File format:
Delimiter: ','
Columns: [# Timestamp,Fx,Fc,ENOB,Fc_Slew,ENOB_Slew]

Files:
ENOB_SINAD_SLEW_8_16bits.csv
'''

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator
import pandas as pd

# get data
# data = np.genfromtxt('ENOB_SINAD_SLEW_8_16bits.csv', delimiter=',', skip_header=1, dtype=None, encoding='utf-8') #usecols=(1, 2, 3, 4, 5))
data = pd.read_csv('ENOB_SINAD_SLEW_NSDCAL_4-16bits_LINEAR_SLEW.csv')
qconfig = data.iloc[:,1].values
lm = data.iloc[:,2].values
fx = data.iloc[:,3].values
enob = data.iloc[:,5].values
enob_slewed = data.iloc[:,6].values
sinad = data.iloc[:,7].values
sinad_slewed = data.iloc[:,8].values
slew_error = data.iloc[:,9].values

# auto-filter based on different lm available
lm_unique, inverse = np.unique(lm, return_inverse=True)
lm_unique_indices = {val: np.where(inverse == i)[0] for i, val in enumerate(lm_unique)}

# plot results
for val, i in lm_unique_indices.items():
    plt.figure()
    plt.title(val)
    # auto-filter based on different qconfig available
    qconfig_unique, inverse = np.unique(qconfig[i], return_inverse=True)
    qconfig_unique_indices = {val: np.where(inverse == i)[0] for i, val in enumerate(qconfig_unique)}
    for val, i in qconfig_unique_indices.items():
        ax = plt.gca()  # Get current axes
        line1, = ax.plot(fx[i], enob[i], label=f'{val} enob')
        ax.plot(fx[i], enob_slewed[i], '--', color=line1.get_color(), label=f'{val} enob slewed')
        ax.plot(fx[i], slew_error[i], color=line1.get_color(), label=f'{val} slew error [RMS]')
        # line1, = ax.plot(fx[i], sinad[i], label=f'{val} sinad') # color=line1.get_color(), label=f'{val} sinad')
        # ax.plot(fx[i], sinad_slewed[i], '--', color=line1.get_color(), label=f'{val} sinad slewed')

    ax.set_xlabel('Fx [Hz]')
    # ax.set_ylabel('ENOB')
    ax.xaxis.set_minor_locator(MultipleLocator(1000))  # Minor ticks every 0.1 on y-axis
    # ax.xaxis.set_major_locator(MultipleLocator(1))  # Minor ticks every 0.1 on y-axis
    ax.yaxis.set_minor_locator(MultipleLocator(0.5))  # Minor ticks every 0.1 on y-axis
    ax.yaxis.set_major_locator(MultipleLocator(1))  # Minor ticks every 0.1 on y-axis
    ax.grid(which='major', linestyle='-', linewidth=0.8)
    ax.grid(which='minor', linestyle=':', linewidth=0.5, color='gray')
    plt.legend()

plt.show()
