'''
Plot utility for enob csv file

File format:
Delimiter: ','
Columns: [# Timestamp,Fx,Fc,ENOB,Fc_Slew,ENOB_Slew]

Files:
'ENOB Fc100k.csv' = NSDCAL [1000,100k] Hz
'ENOB Fc100k2.csv' = NSDCAL [100,100k] Hz
'ENOB Fc100k3.csv' = BASELINE [100,100k] Hz
'ENOB Fc100k4.csv' = MPC [100,100k] Hz
'ENOB_MPC_RL_RM.csv' = MPC_RL_RM [100,20k] Hz
'ENOB_NSDCAL_8bit' = NSDCAL [100,100k] Hz
'''

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator

data = np.loadtxt('ENOB_BASELINE_8bits.csv', delimiter=',', skiprows=1, usecols=(3, 4, 5, 6, 7)) #usecols=(1, 2, 3, 4, 5))
plt.figure()
ax = plt.gca()  # Get current axes
ax.plot(data[:, 0], data[:, 2], label='without slew')
ax.plot(data[:, 0], data[:, 4], label='with slew')
ax.set_title(f'BASELINE ENOBs Fx=[{int(data[0,0])}, {int(data[-1,0])}]Hz 8bits')
ax.set_xlabel('Fx [Hz]')
ax.set_ylabel('ENOB')
ax.xaxis.set_minor_locator(MultipleLocator(1000))  # Minor ticks every 0.1 on y-axis
# ax.xaxis.set_major_locator(MultipleLocator(1))  # Minor ticks every 0.1 on y-axis
ax.yaxis.set_minor_locator(MultipleLocator(0.1))  # Minor ticks every 0.1 on y-axis
ax.yaxis.set_major_locator(MultipleLocator(1))  # Minor ticks every 0.1 on y-axis
ax.grid(which='major', linestyle='-', linewidth=0.8)
ax.grid(which='minor', linestyle=':', linewidth=0.5, color='gray')
ax.legend()

plt.show()
