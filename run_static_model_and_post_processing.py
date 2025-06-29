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
import tqdm
# import datetime
# from pathlib import Path

from utils.results import handle_results
from utils.static_dac_model import generate_dac_output, quantise_signal, generate_codes, quantiser_type, slew_model, reconstruction_filter
from utils.quantiser_configurations import quantiser_configurations, get_measured_levels, qs
from utils.spice_utils import run_spice_sim, run_spice_sim_parallel, gen_spice_sim_file, read_spice_bin_file
from LM.lin_method_util import lm, dm
from utils.figures_of_merit import eval_enob_sinad, eval_slew_distortion, eval_slew_rate, SINAD_COMP
from utils.test_util import sim_config, test_signal_sine
from utils.inl_processing import get_physcal_gain
from utils.save_csv import save_enob_sinad_slew, save_code, save_slew_error


def run_static_model_and_post_processing(RUN_LM, hash_stamp, MAKE_PLOT=False, SAVE=False):

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
    QConfig = qs(SC.qconfig)
    lin = lm(SC.lin)
    Nch = SC.nch
    Fs = SC.fs
    Ts = 1/Fs  # sampling time
    Fx = SC.ref_freq
    Sr = SC.sr # slew rate
    Xref = SC.xref
    Fs_scope = SC.fs_scope

    codes_fn = 'codes.npy'  # TODO: magic constant, name of codes file

    if os.path.exists(os.path.join(method_d, codes_d, codes_fn)):  # codes exists
        C = np.load(os.path.join(method_d, codes_d, codes_fn))
    else:
        raise SystemExit('No codes file found.')

    # time vector
    t = SC.t

    match 2:
        case 1:
            # use ideal model
            pass
        case 2:
            # use static non-linear quantiser model to simulate DAC
            ML = get_measured_levels(QConfig, SC.lin)
    
    # duplicate ML if Nch is larger than available measurements
    if C.shape[0] > ML.shape[0]:
        ML = np.resize(ML, (C.shape[0], ML.shape[1]))

    # generate output
    YM = generate_dac_output(C.astype(int), ML)  # using measured or randomised levels

    # calculate min max step sizes
    diff = np.diff(C.astype(int))
    print(f'min: {np.min(diff)} max: {np.max(diff)}')
    plt.figure()
    plt.plot(t[:len(diff[0,:])], diff[0,:])

    # use slew model
    ts_scope = 1/Fs_scope
    YMs, YMs_scope, t_scope = slew_model(YM, Ts, Sr, t, ts_scope, mode=1)

    # Summation stage
    # TODO: Generalize the gain K. Current solution is creates errors depending on number of channel (typical Nch=1)
    if SC.lin == lm.BASELINE:
        K = np.ones((Nch,1))
        K = 1
        # K[1] = 0.0  # null one channel (want single channel resp.)
    elif SC.lin == lm.DEM:
        K = 1/Nch
    elif SC.lin == lm.PHYSCAL:
        K = np.ones((Nch,1))
        K[1] = get_physcal_gain(QConfig)
    elif SC.lin == lm.NSDCAL:
        Nch_C = C.shape[0]
        K = np.ones((Nch_C,1))
        K = 1
    elif SC.lin is lm.MPC or SC.lin is lm.MPC_RL_RM or SC.lin is lm.MPC_SL:
        Nch_C = C.shape[0]
        K = 1
    elif SC.lin == lm.ILC:
        K = np.ones((Nch,1))
        K[1] = 0.0  # null one channel (want single channel resp.)
    else:
        K = 1/Nch

    t = t[0:YM.shape[1]]
    Fc = SC.fc
    Nf = SC.nf

    # Reconstruction filter
    ym_rf = reconstruction_filter(t, YM, Fc, Fs, Nf)
    yms_scope_rf = reconstruction_filter(t_scope, YMs_scope, Fc, Fs_scope, Nf)

    # Eval slew distortion
    slew_error, slew_error_rms = eval_slew_distortion(YM, YMs_scope, t, t_scope, print_results=True, plot_results=MAKE_PLOT, title='priod RF')
    slew_error, slew_error_rms = eval_slew_distortion(ym_rf, yms_scope_rf, t, t_scope, print_results=True, plot_results=MAKE_PLOT, title='after RF')

    # Get single channel for plotting
    ym = YM[0,:]
    ym_avg = ym_rf[0,:]
    yms_scope = YMs_scope[0,:]
    yms_scope_avg = yms_scope_rf[0,:]
    c = C[0,:].astype(int).flatten()

    # 
    eval_slew_rate(ym, t, print_results=True)

    # Eval ENOB and SINAD
    print('RESULTS WITHOUT SLEW')
    TRANSOFF = int(np.floor(1*Fs/Fx).astype(int) * 1.2)  # remove transient effects from output
    ENOB, SINAD = eval_enob_sinad(t, ym_avg, Fs, TRANSOFF, SINAD_COMP.CFIT)
    print('RESULTS WITH SLEW SCOPE')
    TRANSOFF_SCOPE = int(np.floor(1*Fs_scope/Fx).astype(int) * 1.2)  # remove transient effects from output
    ENOB_SLEWED, SINAD_SLEWED = eval_enob_sinad(t_scope, yms_scope_avg, Fs_scope, TRANSOFF_SCOPE, SINAD_COMP.CFIT, plot=True, descr='SLEWED')
    
    if SAVE: 
        save_enob_sinad_slew(QConfig.name, lin.name, Fx, Fc, [ENOB, ENOB_SLEWED], [SINAD, SINAD_SLEWED], slew_error_rms)
        save_code(QConfig.name, lin.name, Fx, Fc, t, c)

    if MAKE_PLOT:
        # Function to handle click events
        def onclick(event,x_prev=[0],y_prev=[0]):
            if event.button == 3:  # Right-click
                x, y = event.xdata, event.ydata
                dv = y_prev[0]-y
                dt = x_prev[0]-x
                dvdt = 1e-6*(dv)/(dt)
                x_prev[0] = x
                y_prev[0] = y
                print(f'x = {x}s, y = {y}V, dV = {dv}, dt = {dt}, dvdt = {dvdt}v/us')
                pyperclip.copy(f'{x},{y}')

        # TRANSOFF = 1
        plt.figure()
        plt.plot(t[TRANSOFF:-TRANSOFF],Xref[TRANSOFF:-TRANSOFF], label='xref')
        line, = plt.plot(t[TRANSOFF:-TRANSOFF],ym[TRANSOFF:-TRANSOFF], '-o', label='ym')
        plt.plot(t[TRANSOFF:-TRANSOFF],ym_avg[TRANSOFF:-TRANSOFF], '--', color=line.get_color(), label='ym_avg')
        # plt.plot(t[TRANSOFF:-TRANSOFF],ym_fit, color=line.get_color(), alpha=0.6, label='ym_fit')
        
        # line, = plt.plot(t[TRANSOFF:-TRANSOFF],yms_avg[TRANSOFF:-TRANSOFF], '--', label='yms_avg')
        # plt.scatter(t[TRANSOFF:-TRANSOFF], yms[TRANSOFF:-TRANSOFF], color=line.get_color(), label='yms_scatter')
        # plt.plot(t[TRANSOFF:-TRANSOFF],yms_fit, color=line.get_color(), alpha=0.6, label='yms_fit')

        line, = plt.plot(t_scope[TRANSOFF_SCOPE:-TRANSOFF_SCOPE], yms_scope[TRANSOFF_SCOPE:-TRANSOFF_SCOPE], '-o', label='yms_scope')
        plt.plot(t_scope[TRANSOFF_SCOPE:-TRANSOFF_SCOPE],yms_scope_avg[TRANSOFF_SCOPE:-TRANSOFF_SCOPE], '--', color=line.get_color(), label='yms_scope_avg')
        # plt.plot(t_scope[TRANSOFF_SCOPE:-TRANSOFF_SCOPE],yms_scope_fit, color=line.get_color(), alpha=0.6, label='yms_scope_fit')

        plt.title(f'Method: {lin.name}')
        plt.xlabel('Time [s]')
        plt.ylabel('Output [V]')
        plt.legend(loc='upper right')

        # Connecting the click event to the handler function for the first figure
        cid1 = plt.gcf().canvas.mpl_connect('button_press_event', onclick)

        
        # plt.figure()
        # plt.plot(t[TRANSOFF:-TRANSOFF],ym[TRANSOFF:-TRANSOFF]-yms[TRANSOFF:-TRANSOFF], label='ym-yms')
        # plt.plot(t[TRANSOFF:-TRANSOFF],ym_avg[TRANSOFF:-TRANSOFF]-yms_avg[TRANSOFF:-TRANSOFF], label='ym_avg-yms_avg')
        # plt.title(f'Method: {str(lm(SC.lin.method))} Slew Error')
        # plt.xlabel('Time [s]')
        # plt.ylabel('Output [V]')
        # plt.legend(loc='upper right')
        
        plt.show()


# def eval_codes:
