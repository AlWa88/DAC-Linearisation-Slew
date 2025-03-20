#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate static non-linear DAC response via look-up table, and process result.

@author: Arnfinn Eielsen
@date: 30.01.2025
@license: BSD 3-Clause
"""

#%reload_ext autoreload
#%autoreload 2

import os
import pickle
import numpy as np
from matplotlib import pyplot as plt
import pyperclip
from prefixed import Float
from tabulate import tabulate

from utils.results import handle_results
from utils.static_dac_model import generate_dac_output, quantise_signal, generate_codes, quantiser_type, slew_model
from utils.quantiser_configurations import quantiser_configurations, get_measured_levels, qs
from utils.spice_utils import run_spice_sim, run_spice_sim_parallel, gen_spice_sim_file, read_spice_bin_file, process_sim_output
from LM.lin_method_util import lm, dm
from utils.test_util import sim_config, sinad_comp, test_signal
from utils.inl_processing import get_physcal_gain


def run_static_model_and_post_processing(RUN_LM, hash_stamp, MAKE_PLOT=False):

    top_d = 'generated_codes/'  # directory for generated codes and configuration info
    method_d = os.path.join(top_d, str(lm(RUN_LM)))

    codes_dirs = os.listdir(method_d)

    if not codes_dirs:  # list empty?
        raise SystemExit('No codes found.')

    codes_d = hash_stamp #codes_dirs[codes_dirs.index(hash_stamp)]  ###################### pick run

    # read pickled (marshalled) state/config object
    with open(os.path.join(method_d, codes_d, 'sim_config.pickle'), 'rb') as fin:
        SC:sim_config = pickle.load(fin)

    hash_stamp = codes_d
    static_case_d = os.path.join('static_sim', 'cases', str(SC.lin).replace(' ', '_'), hash_stamp)

    if os.path.exists(static_case_d):
        print('Putting output files in existing directory: ' + static_case_d)
    else:
        os.makedirs(static_case_d)

    # Read some config. params.
    QConfig = SC.qconfig
    Nch = SC.nch
    Fs = SC.fs
    Ts = 1/Fs  # sampling time
    Fx = SC.ref_freq
    Sr = SC.sr # slew rate

    codes_fn = 'codes.npy'  # TODO: magic constant, name of codes file

    if os.path.exists(os.path.join(method_d, codes_d, codes_fn)):  # codes exists
        C = np.load(os.path.join(method_d, codes_d, codes_fn))
    else:
        raise SystemExit('No codes file found.')

    # time vector
    t = SC.t

    # use static non-linear quantiser model to simulate DAC
    ML = get_measured_levels(QConfig, SC.lin.method)
    YM = generate_dac_output(C.astype(int), ML)  # using measured or randomised levels
    tm = t[0:YM.size]

    # use slew model
    YMs = slew_model(YM, Ts, Sr)

    # Summation stage
    # TODO: Generalize the gain K. Current solution is creates errors depending on number of channel (typical Nch=1)
    if SC.lin.method == lm.BASELINE:
        K = np.ones((Nch,1))
        K = 1
        # K[1] = 0.0  # null one channel (want single channel resp.)
    elif SC.lin.method == lm.DEM:
        K = 1/Nch
    elif SC.lin.method == lm.PHYSCAL:
        K = np.ones((Nch,1))
        K[1] = get_physcal_gain(QConfig)
    elif SC.lin.method == lm.NSDCAL:
        Nch_C = C.shape[0]
        K = np.ones((Nch_C,1))
        K = 1
    elif SC.lin.method == lm.MPC:
        Nch_C = C.shape[0]
        K = 1
    elif SC.lin.method == lm.ILC:
        K = np.ones((Nch,1))
        K[1] = 0.0  # null one channel (want single channel resp.)
    else:
        K = 1/Nch
        
    print(f'Summing gain: {K}')

    ym = np.sum(K*YM, 0)
    yms = np.sum(K*YMs, 0)
    t = t[0:len(ym)]

    TRANSOFF = np.floor(1*Fs/Fx).astype(int)  # remove transient effects from output

    Fc = SC.fc
    Nf = SC.nf

    print('RESULTS WITHOUT SLEW')
    ym_avg, ENOB_M = process_sim_output(t, ym, Fc, Fs, Nf, TRANSOFF, sinad_comp.CFIT)
    print('RESULTS WITH SLEW')
    yms_avg, ENOB_M = process_sim_output(t, yms, Fc, Fs, Nf, TRANSOFF, sinad_comp.CFIT)

    # results_tab = [['DAC config', 'Method', 'Model', 'Fs', 'Fc', 'X scale', 'Fx', 'ENOB'],
    # [str(SC.qconfig), str(SC.lin), str(SC.dac), f'{Float(SC.fs):.2h}', f'{Float(SC.fc):.1h}', f'{Float(SC.ref_scale):.1h}%', f'{Float(SC.ref_freq):.1h}', f'{Float(ENOB_M):.3h}']]
    # print(tabulate(results_tab))

    handle_results(SC, ENOB_M)

    if (MAKE_PLOT):
        # Function to handle click events
        def onclick(event):
            if event.button == 3:  # Right-click
                ix, iy = event.xdata, event.ydata
                print(f'x = {ix}, y = {iy}')
                pyperclip.copy(f'{ix},{iy}')

        plt.figure()
        plt.plot(t[TRANSOFF:-TRANSOFF],ym[TRANSOFF:-TRANSOFF], label='ym')
        plt.plot(t[TRANSOFF:-TRANSOFF],yms[TRANSOFF:-TRANSOFF], '--', label='yms')
        plt.plot(t[TRANSOFF:-TRANSOFF],ym_avg[TRANSOFF:-TRANSOFF], label='ym_avg')
        plt.plot(t[TRANSOFF:-TRANSOFF],yms_avg[TRANSOFF:-TRANSOFF], '--', label='yms_avg')
        plt.title(f'Method: {str(lm(SC.lin.method))}')
        plt.xlabel('Time [s]')
        plt.ylabel('Output [V]')
        plt.legend(loc='upper right')

        # Connecting the click event to the handler function for the first figure
        cid1 = plt.gcf().canvas.mpl_connect('button_press_event', onclick)

        
        plt.figure()
        plt.plot(t[TRANSOFF:-TRANSOFF],ym[TRANSOFF:-TRANSOFF]-yms[TRANSOFF:-TRANSOFF], label='ym-yms')
        plt.plot(t[TRANSOFF:-TRANSOFF],ym_avg[TRANSOFF:-TRANSOFF]-yms_avg[TRANSOFF:-TRANSOFF], label='ym_avg-yms_avg')
        plt.title(f'Method: {str(lm(SC.lin.method))} Slew Error')
        plt.xlabel('Time [s]')
        plt.ylabel('Output [V]')
        plt.legend(loc='upper right')
        
        plt.show()