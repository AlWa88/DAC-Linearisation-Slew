#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gains with some moderate pains

@author: Bikash Adhikari
@date: 22.02.2024
@license: BSD 3-Clause
"""

# %%
import numpy as np
from matplotlib import pyplot as plt
import os

# %% DAC  and sampling frequency
DAC_6bit_SKY_Fs_102MHz = 1
DAC_6bit_SKY_Fs_327MHz = 2
DAC_10bit_SKY_Fs_102MHz = 3
DAC_10bit_SKY_Fs_327MHz = 4
DAC_6bit_PRO_Fs_209MHz = 5
DAC_10bit_PRO_Fs_209MHz = 6

# %%
match 6:
    case 1: # 6 bit SkyWater at 1.02 MHz 
        tech = 'SkyWater'
        node = 'SKY130'
        method0 = 'static'
        method1 = 'spice'

        methods = f'{method0}-{method1}'

        Nb = 6
        Fs = 1.02
        static_baseline = 6.1
        static_physcal = 6.87
        static_nsdcal = 8.09
        static_phfd = 6.81
        static_shpd = 5.82
        static_dem = 4.92
        static_mhoq = 7.93

        # Spice simulation results
        spice_baseline = 6.07
        spice_physcal = 6.93
        spice_nsdcal = 8.12
        spice_phfd = 6.81
        spice_shpd = 5.82
        spice_dem = 4.85
        spice_mhoq = 7.93

        
        static_gains = np.array([static_physcal, static_nsdcal, static_phfd, static_shpd, static_dem, static_mhoq]) - static_baseline
        spice_gains = np.array([spice_physcal, spice_nsdcal,  spice_phfd, spice_shpd, spice_dem, spice_mhoq]) - spice_baseline
        mos_model_gains = spice_gains

        lin_methods =  ['PHYSCAL', 'NSDCAL', 'PHFD', 'SHPD', 'DEM', 'MHOQ']

    case 2: # 6-bit SkyWater at 32.07 MHz
        tech = 'SkyWater'
        node = 'SKY130'
        method0 = 'static'
        method1 = 'spice'

        methods = f'{method0}-{method1}'

        Nb = 6
        Fs = 32.07

        static_baseline = 6.39
        static_physcal = 8.88
        static_nsdcal = 18.11
        static_phfd = 9.25
        static_shpd = 7.35
        static_dem = 7.36
        static_mhoq = 18.16

        # Spice simulation results
        spice_baseline = 6.39
        spice_physcal = 8.88
        spice_nsdcal = 12.77
        spice_phfd = 9.25
        spice_shpd = 7.36
        spice_dem = 7.36
        spice_mhoq = 12.36
        # Calculate gains
        static_gains = np.array([static_physcal, static_nsdcal, static_phfd, static_shpd, static_dem, static_mhoq]) - static_baseline
        spice_gains = np.array([spice_physcal, spice_nsdcal,  spice_phfd, spice_shpd, spice_dem, spice_mhoq]) - spice_baseline
        mos_model_gains = spice_gains

        lin_methods =  ['PHYSCAL', 'NSDCAL', 'PHFD', 'SHPD', 'DEM', 'MHOQ']

    case 3: # 10 bit SkyWater at 1.02 MHz 
        tech = 'SkyWater'
        node = '130 nm'
        method0 = 'static'
        method1 = 'spice'

        methods = f'{method0}-{method1}'

        Nb = 10
        Fs = 1.02
        static_baseline = 7.65
        static_physcal = 11.02
        static_nsdcal = 11.81
        static_phfd = 8.90
        static_shpd = 8.68
        static_dem = 4.83
        static_mhoq = 9.64


        # Spice simulation results
        spice_baseline = 9.64
        spice_physcal = 11.04
        spice_nsdcal = 11.84
        spice_phfd = 8.90
        spice_shpd = 8.65
        spice_dem = 4.78
        spice_mhoq = 9.64

        # Calculate gains
        static_gains = np.array([static_physcal, static_nsdcal, static_phfd, static_shpd, static_dem, static_mhoq]) - static_baseline
        spice_gains = np.array([spice_physcal, spice_nsdcal,  spice_phfd, spice_shpd, spice_dem, spice_mhoq]) - spice_baseline
        mos_model_gains = spice_gains

        lin_methods =  ['PHYSCAL', 'NSDCAL', 'PHFD', 'SHPD', 'DEM', 'MHOQ']

    case 4: #10 bit SkyWater at 32.07 MHz,
        tech = 'SkyWater'
        node = '130 nm'
        method0 = 'static'
        method1 = 'spice'

        methods = f'{method0}-{method1}'

        Nb = 10
        Fs = 32.07

        static_baseline = 7.66
        static_physcal = 13.61
        static_nsdcal = 18.44
        static_phfd = 12.44
        static_shpd = 8.54
        static_dem = 7.27
        static_mhoq = 18.39

        # Spice simulation results
        spice_baseline = 6.093
        spice_physcal = 6.164
        spice_nsdcal = 8.343
        spice_phfd = 6.783
        spice_shpd= 3.522
        spice_dem = 4.874
        spice_mhoq = 17.12
        # Calculate gains
        static_gains = np.array([static_physcal, static_nsdcal, static_phfd, static_shpd, static_dem, static_mhoq]) - static_baseline
        spice_gains = np.array([spice_physcal, spice_nsdcal,  spice_phfd, spice_shpd, spice_dem, spice_mhoq]) - spice_baseline
        mos_model_gains = spice_gains

        lin_methods =  ['PHYSCAL', 'NSDCAL', 'PHFD', 'SHPD', 'DEM', 'MHOQ']
    
    case 5: ## 6 bit ZTC ARTI
        tech = 'Proprietary'
        node = '130 nm'
        method0 = 'static'
        method1 = 'spectre'

        methods = f'{method0}_{method1}'

        Nb = 6
        Fs = 209.72 

        static_baseline = 11.00
        static_physcal = 10.93
        static_nsdcal = 11.86
        static_phfd = 10.40
        static_shpd = 10.82
        static_dem = 10.92
        static_mhoq = 19.30
        

        # Spectre simulation results
        spice_baseline = 10.22
        spice_physcal = 9.90
        spice_nsdcal = 9.80
        spice_phfd = 10.36
        spice_shpd = 9.96
        spice_dem = 9.69
        spice_mhoq = 9.65
        
        # Calculate gains
        static_gains = np.array([static_physcal, static_nsdcal, static_phfd, static_shpd, static_dem, static_mhoq]) - static_baseline
        spice_gains = np.array([spice_physcal, spice_nsdcal, spice_phfd, spice_shpd, spice_dem, spice_mhoq]) - spice_baseline
        mos_model_gains = spice_gains

        lin_methods =  ['PHYSCAL', 'NSDCAL', 'PHFD', 'SHPD', 'DEM', 'MHOQ']
    
    case 6: # 10 bit ZTC ARTI
        tech = 'Proprietary'
        node = '130 nm'
        method0 = 'static'
        method1 = 'sprectre'

        methods = f'{method0}-{method1}'

        Nb = 10
        Fs = 209.72 

        static_baseline = 11.00
        static_physcal = 14.96
        static_nsdcal = 18.78
        static_phfd = 14.36
        static_shpd = 11.66
        static_dem = 12.32
        static_mhoq = 18.10


        # Spectre simulation results
        spice_baseline = 8.92
        spice_physcal = 8.66
        spice_nsdcal = 8.50
        spice_phfd = 9.43
        spice_shpd = 8.92
        spice_dem = 8.05
        spice_mhoq = 8.69
        

        # Calculate gains
        static_gains = np.array([static_physcal, static_nsdcal, static_phfd, static_shpd, static_dem, static_mhoq]) - static_baseline
        spice_gains = np.array([spice_physcal, spice_nsdcal, spice_phfd, spice_shpd, spice_dem, spice_mhoq]) - spice_baseline
        mos_model_gains = spice_gains

        lin_methods =  ['PHYSCAL', 'NSDCAL', 'PHFD', 'SHPD', 'DEM', 'MHOQ']

# %% Plots
barWidth = 0.25
# set position of the bar on X axis
bar1 = np.arange(static_gains.size)
bar2 = [x + barWidth for x in bar1] 
bar3 = [x + barWidth for x in bar2]

# % Draw plot
fig, ax = plt.subplots(figsize = (7,5))
plt.axhline(y = 0, color = 'black', linestyle = '-')
b1 = plt.bar(bar2, static_gains,    width = barWidth, color = 'tab:cyan',   edgecolor = 'white', label = method0)
b2 = plt.bar(bar3, mos_model_gains, width = barWidth, color = 'tab:orange', edgecolor = 'white', label = method1)
# match methods:
#     case "static-spice":
#         b2 = plt.bar(bar3, spice_gains, width = barWidth,  color = 'tab:orange',edgecolor = 'white', label = 'SPICE')
#     case "static-spectre":
#         b2 = plt.bar(bar3, spice_gains, width = barWidth,  color = 'tab:orange',edgecolor = 'white', label = 'Spectre')

plt.xlabel('Linearisation method', fontweight ='bold', fontsize = 15) 
plt.ylabel('ENOB gain', fontsize = 13) 

pos_xticks = np.array([r + barWidth for r in range(len(static_gains))]) + barWidth/2
plt.xticks(pos_xticks, lin_methods , fontsize = 13)

fontsize = 13

ah = []
for rect in b1 + b2 :
    height = rect.get_height()
    ah.append(height)
    if height > 0 :
        plt.text(rect.get_x() + rect.get_width()/2.0 - 0.075, 0.3, f'{height:.2f} bits', rotation=90, fontsize=fontsize)        
    if height < 0 :
        plt.text(rect.get_x() + rect.get_width()/2.0 - 0.075, 0.3, f'{height:.2f} bits', rotation=90, fontsize=fontsize)        

# Adjust location of the value Fs    
# ax.text(1, -1.2,  f'Fs = {Fs} MHz',  ha='right', va='bottom', fontsize = "20")

# for rect in b1 + b2:
#     height = rect.get_height()
#     if height > 0 :
#         plt.text(rect.get_x() + rect.get_width() / 2.0 -0.03, -1, '1.02 MHz', rotation = 90, fontsize = 13)        
#     if height < 0 :
#         plt.text(rect.get_x() + rect.get_width() / 2.0 -0.03, 0.3, '1.02 MHz', rotation = 90, fontsize = 13)

# for rect in b3 + b4:
#     height = rect.get_height()
#     if height > 0 :
#         plt.text(rect.get_x() + rect.get_width() / 2.0 -0.03, -1.25, '1 MHz', rotation = 90, fontsize = 13)        
#     if height < 0 :
#         plt.text(rect.get_x() + rect.get_width() / 2.0 -0.03, 0.5, '1 MHz', rotation = 90, fontsize = 13)        

plt.title(f"{int(Nb)}-bit DAC | Technology: {tech} {node} | Fs: {Fs} MHz", fontsize = "13")

# plt.title(f"{int(Nb)}-bit DAC | Technology: {tech} {node} | Fs: {Fs} MHz\n{method0} baseline: {static_baseline} bits | {method1} baseline: {mos_model_baseline} bits", fontsize = "13")
plt.legend(fontsize="13", loc='upper right')
ax.set_axisbelow(True)
ax.grid(zorder=0, axis = "y")
fig.tight_layout()
# plt.savefig(f"Gainplot-{Nb}bits.pdf")

# %%
# fname = f"figures/Gainplot_{Nb}b_{tech}_{node}_{int(Fs)}MHz_{methods}".replace(" ", "_")
# fname = str(fname)
# fig.savefig(fname + ".svg", format='svg', bbox_inches='tight') # Practical for PowerPoint and other applications
# fig.savefig(fname + ".pdf", format='pdf', bbox_inches='tight') # Best for LaTeX

# %%

# fname = f"Gainplot_{Nb}b_{tech}_{node}_{int(Fs)}MHz_{methods}".replace(" ", "_")
fname = f"Gainplot_{Nb}b_{tech}_{node}_{int(Fs)}MHz_{methods}".replace(" ", "_")
fname = str(fname)

script_dir = os.path.dirname(__file__)
results_dir = os.path.join(script_dir, 'Figures/')
if not os.path.isdir(results_dir):
    os.makedirs(results_dir)

# plt.plot([1,2,3,4])
# plt.ylabel('some numbers')
fig.savefig(results_dir + fname + ".svg", format ='svg', bbox_inches ='tight')
fig.savefig(results_dir + fname + ".pdf", format ='pdf', bbox_inches ='tight')

# fig.savefig(fname + ".svg", format='svg', bbox_inches='tight') # Practical for PowerPoint and other applications
# fig.savefig(fname + ".pdf", format='pdf', bbox_inches='tight') # Best for LaTeX
# %%
