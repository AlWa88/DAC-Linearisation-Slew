#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run DAC simulations using various linearisation methods

@author: Arnfinn Eielsen, Bikash Adhikari
@date: 22.02.2024
@license: BSD 3-Clause
"""

# %%
# %reload_ext autoreload
# %autoreload 2

# Imports
import sys
import numpy as np
from numpy import matlib
import os
#import statistics
#import scipy
from scipy import signal
from matplotlib import pyplot as plt
#import tqdm
#import math
#import csv
import datetime
import pickle
#from prefixed import Float
#from tabulate import tabulate
import argparse

LATEX_PLOT = 0
if LATEX_PLOT:
    plt.rcParams['text.usetex'] = True

import utils.dither_generation as dither_generation
from utils.dual_dither import dual_dither, hist_and_psd
from utils.quantiser_configurations import quantiser_configurations, get_measured_levels, qs
from utils.results import handle_results
from utils.static_dac_model import generate_dac_output, quantise_signal, generate_codes, quantiser_type, measurement_noise_range
from utils.figures_of_merit import FFT_SINAD, TS_SINAD
from utils.balreal import balreal_ct, balreal
from utils.mpc_filter_parameters import mpc_filter_parameters

from LM.lin_method_nsdcal import nsdcal
from LM.lin_method_dem import dem
# from lin_method_ilc import get_control, learning_matrices
# from lin_method_ilc_simple import ilc_simple
from LM.lin_method_mpc import MPC
from LM.lin_method_mpc_bin import MPC_BIN
# from lin_method_ILC_DSM import learningMatrices, get_ILC_control
from LM.lin_method_dsm_ilc import DSM_ILC
from LM.lin_method_util import lm, dm
from LM.lin_method_mpc_rl_rm import MHOQ_RLIM_RM
from LM.lin_method_mpc_rl import MHOQ_RLIM
from utils.figures_of_merit import SINAD_COMP
from utils.test_util import sim_config, test_signal_sine, test_signal_square
from run_static_model_and_post_processing import run_static_model_and_post_processing

#%% Configure DAC and test conditions

# Test/reference signal spec. (to be recovered on the output)
Xref_SCALE = (65535/65535)*100 # %
Xref_FREQ = 10000 #166999 # 14915.49431 # 301592.5178 # 90796 # 79760  # 181592.5178 Hz
Slew_rate = 10 # 11.4097944 # V/us
MPC_step_limit = 2

# Output low-pass filter configuration
Fc_lp = 100e3 # cut-off frequency in hertz
N_lp = 3  # filter order

METHOD_CHOICE = 1
DAC_MODEL_CHOICE = 1  # 1 - static, 2 - spice
DITHER_BASELINE = 0 # 0=off, 1=dither on for BASELINE
# SETUP = 7
TEST_CASE = 6
M_NOISE = 1 # 0=off
SINAD_COMP_SEL = SINAD_COMP.CFIT
PLOTS = False
SAVE_ENOB = True
N_PRED = 1 # prediction horizon (MPC)
NCH = 1

#%% Parse arguments if used
# This section is used when run_me.py is called from command line.
# run_me_wrapper.py does this for repeated simulations with for different xrefs and methods
parser = argparse.ArgumentParser()
parser.add_argument('--TEST_CASE', type=int)
parser.add_argument('--Xref_FREQ', type=int)
parser.add_argument('--MPC_step_limit', type=int)
parser.add_argument('--METHOD_CHOICE', type=int)
parser.add_argument('--QConfig', type=int)
args = parser.parse_args()

if args.TEST_CASE == 0:
    TEST_CASE = args.TEST_CASE
    Xref_FREQ = args.Xref_FREQ
    MPC_step_limit = args.MPC_step_limit
    Slew_rate = 7
    Fc_lp = 100e3
    Fs_Scope = 1e7
    RUN_LM = lm(args.METHOD_CHOICE)
    # SETUP = 0
    FS_CHOICE = 1
    QConfig = qs(args.QConfig)
    PLOTS = False
    SAVE_ENOB = True
    print(f'Running with CLI arguments: {args}')

#%% Run case
match TEST_CASE:
    case 0:
        pass
#     case 1:
#         # BASELINE fail
#         Xref_FREQ = 166999
#         Slew_rate = 10
#         Fc_lp = 100e6
#         RUN_LM = lm.BASELINE
#         # SETUP = 0
#         FS_CHOICE = 3
#         QConfig = qs.w_16bit_NI_card 
#     case 2:
#         # NSDCAL fail
#         Xref_FREQ = 7500
#         Slew_rate = 1
#         Fc_lp = 100e3
#         RUN_LM = lm.NSDCAL
#         # SETUP = 0
#         FS_CHOICE = 1
#         QConfig = qs.w_16bit_NI_card 

#     case 3:
#         # NSDCAL 
#         Xref_FREQ = 100000
#         Slew_rate = 10
#         Fc_lp = 100e12
#         RUN_LM = lm.NSDCAL
#         # SETUP = 0
#         FS_CHOICE = 1
#         QConfig = qs.w_16bit_NI_card 

#     case 4:
#         # BASE
#         Xref_FREQ = 50000
#         Slew_rate = 7
#         Fc_lp = 350e3
#         Fs_Scope = 1e9
#         RUN_LM = lm.BASELINE
#         # SETUP = 0
#         FS_CHOICE = 1
#         QConfig = qs.w_16bit_NI_card    

#     case 5:
#         # NSDCAL - ENOB=18.17 
#         Xref_FREQ = 5000
#         Slew_rate = 7
#         Fc_lp = 50e3
#         Fs_Scope = 1e7
#         RUN_LM = lm.NSDCAL
#         # SETUP = 0
#         FS_CHOICE = 1
#         QConfig = qs.w_16bit_NI_card

    case 6:
        # MPC_RL 
        Xref_FREQ = 5000
        Slew_rate = 7
        Fc_lp = 100e3
        Fs_Scope = 1e7
        RUN_LM = lm.NSDCAL
        # SETUP = 0
        FS_CHOICE = 1
        QConfig = qs.w_16bit_NI_card
        M_NOISE = 1
        PLOTS = True

# match SETUP:
#     case 0:
#         pass
#     case 1:
#         FS_CHOICE = 3
#         DAC_CIRCUIT = 7  # 6 bit spice
#     case 2:
#         FS_CHOICE = 7
#         DAC_CIRCUIT = 7  # 6 bit spice
#     case 3:
#         FS_CHOICE = 4
#         DAC_CIRCUIT = 9  # 10 bit spice
#     case 4:
#         FS_CHOICE = 7
#         DAC_CIRCUIT = 9  # 10 bit spice
#     case 5:
#         FS_CHOICE = 10
#         DAC_CIRCUIT = 10  # 6 bit spectre
#     case 6:
#         FS_CHOICE = 10
#         DAC_CIRCUIT = 11  # 10 bit spectre
#     case 7: # ni dac slew
#         FS_CHOICE = 2
#         DAC_CIRCUIT = 12

##### METHOD CHOICE - Choose which linearisation method you want to test
# match METHOD_CHOICE:
    # case 1: RUN_LM = lm.BASELINE
    # case 2: RUN_LM = lm.PHYSCAL
    # case 3: RUN_LM = lm.NSDCAL
    # case 4: RUN_LM = lm.PHFD
    # case 5: RUN_LM = lm.SHPD
    # case 6: RUN_LM = lm.DEM
    # case 7: RUN_LM = lm.MPC # lm.MPC or lm.MHOQ
    # case 8: RUN_LM = lm.ILC
    # case 9: RUN_LM = lm.ILC_SIMP
    # case 10: RUN_LM = lm.STEP
    # case 11: RUN_LM = lm.MPC_RL_RM
    # case 12: RUN_LM = lm.MPC_RL
    # case 13: RUN_LM = lm.MPC_SL

lin = RUN_LM

##### DAC MODEL CHOICE (TODO: consider deprecating)

match DAC_MODEL_CHOICE:
    case 1: dac = dm(dm.STATIC)  # use static non-linear quantiser model to simulate DAC
    case 2: dac = dm(dm.SPICE)  # use SPICE to simulate DAC output

# ##### Chose how to compute SINAD
# match SINAD_COMP_CHOICE:
#     case 1: SINAD_COMP_SEL = SINAD_COMP.CFIT  # use curve-fit (best for short time-series)
#     case 2: SINAD_COMP_SEL = SINAD_COMP.FFT  # use frequency response (better for long time-series)

##### Sampling rate (over-sampling) in hertz
match FS_CHOICE:
    case 1: Fs = 1e6
    case 2: Fs = 25e6
    case 3: Fs = 250e6
    case 4: Fs = 1022976                    # SPICE DAC 
    case 5: Fs = 1638400                    # Coherent sampling at 5 cycles, 8192 points, and f0 = 1 kHz 
    case 6: Fs = 16367616
    case 7: Fs = 32735232                   # SPICE DAC 
    case 8: Fs = 65470464
    case 9: Fs = 130940928
    case 10: Fs = 209715200                 # Coherent sampling at 5 cycles, 1048576 points, and f0 = 1 kHz 
    case 11: Fs = 261881856
    case 12: Fs = 226719135.13513514400
    case 13: Fs = 2e6

Ts = 1/Fs  # sampling time

if Fs < 2* Xref_FREQ:
    print('2*Fs Nyquist teorem exceeded')
    exit(1)

##### Set DAC circuit model
# match DAC_CIRCUIT:
#     case 1: QConfig = qs.w_6bit  # "ideal" model (no circuit sim.)
#     case 2: QConfig = qs.w_16bit_SPICE
#     case 3: QConfig = qs.w_16bit_ARTI
#     case 4: QConfig = qs.w_16bit_6t_ARTI
#     case 5: QConfig = qs.w_6bit_ARTI
#     case 6: QConfig = qs.w_10bit_ARTI
#     case 7: QConfig = qs.w_6bit_2ch_SPICE
#     case 8: QConfig = qs.w_16bit_2ch_SPICE
#     case 9: QConfig = qs.w_10bit_2ch_SPICE
#     case 10: QConfig = qs.w_6bit_ZTC_ARTI
#     case 11: QConfig = qs.w_10bit_ZTC_ARTI
#     case 12: QConfig = qs.w_16bit_NI_card
#     case 13: QConfig = qs.w_8bit_NI_card
#     case 14: QConfig = qs.w_6bit_NI_card
#     case 15: QConfig = qs.w_4bit_NI_card

Nb, Mq, Vmin, Vmax, Rng, Qstep, YQ, Qtype = quantiser_configurations(QConfig)
print(f'QConfig: {QConfig.name} LM: {lin.name} Nch: {str(NCH)} FS: {str(Fs)}Hz Xref: {str(Xref_FREQ)}Hz')

# %%
# Generate time vector
match 2:
    case 1:  # specify duration as number of samples and find number of periods
        Nts = 1e6  # no. of time samples
        Np = np.ceil(Xref_FREQ*s*Nts).astype(int)  # no. of periods for carrier
    case 2:  # specify duration as number of periods of carrier
        if SINAD_COMP_SEL is SINAD_COMP.FFT:
            Np = 50  # no. of periods for carrier
        else:
            Np = 5  # no. of periods for carrier (IEEE recommended for curve-fit is 5)
            # Np = 3

Npt = 1  # no. of test signal periods to use to account for transients
Ncyc = Np + 2*Npt

t_end = Ncyc/Xref_FREQ  # time vector duration
t = np.arange(0, t_end, Ts)  # time vector

# Generate test/reference signal
SIGNAL_MAXAMP = Rng/2 - Qstep  # make headroom for noise dither (see below)
SIGNAL_OFFSET = -Qstep/2  # try to center given quantiser type
if lin is lin.STEP:
    Xref = test_signal_square(Xref_SCALE, SIGNAL_MAXAMP, Xref_FREQ, SIGNAL_OFFSET, t)
else:
    Xref = test_signal_sine(Xref_SCALE, SIGNAL_MAXAMP, Xref_FREQ, SIGNAL_OFFSET, t)

print(f'Xref min: {np.amin(Xref)} max: {np.amax(Xref)} SIGNAL_MAXAMP: {SIGNAL_MAXAMP}')

# TODO: ref_scale is misleading; should be % of baseline full range possible for a method
# setting ref_scale=0, to be updated per method
SC = sim_config(QConfig, lin, dac, Fs, t, Fc_lp, N_lp, 0, Xref_FREQ, Ncyc, Slew_rate, Xref, Fs_Scope)

# %% Configure and run linearisation methods
# Each method should produce a vector of codes 'C'
# that can be input to a given DAC circuit.

match SC.lin:
    case lm.BASELINE:  # baseline, only carrier
        # Generate unmodified DAC output without any corrections.

        if QConfig in [qs.w_6bit_2ch_SPICE, qs.w_16bit_2ch_SPICE, qs.w_10bit_2ch_SPICE, qs.w_6bit_ZTC_ARTI, qs.w_10bit_ZTC_ARTI]:
            Nch = 2  # number of channels to use (averaging to reduce noise floor)
        else:
            Nch = NCH
        
        # Quantisation dither (eliminate harm. distortion from quantisation)
        Q_DITHER_ON = DITHER_BASELINE
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_white)
        Dq = Q_DITHER_ON*Dq

        # Add headroom for quantisation dither if needed
        HEADROOM = 0*(Qstep/Rng)
        Xscale = 100 - HEADROOM
        SC.ref_scale = Xscale  # save scale param.

        # Repeat reference on all channels
        Xref = matlib.repmat(Xref, Nch, 1)

        X = (Xscale/100)*Xref + Dq  # quantiser input

        Q = quantise_signal(X, Qstep, Qtype)  # uniform quantiser
        C = generate_codes(Q, Nb, Qtype)  ##### output codes

    case lm.PHYSCAL:  # physical level calibration
        # This method relies on a main/primary DAC operating normally
        # whilst a secondary DAC with a small gain tries to correct
        # for the level mismatches for each and every code.
        # Needs INL measurements and a calibration step.

        # Quantisation dither
        Q_DITHER_ON = 1
        Nch_in = 1  # effectively 1 channel input (with 1 DAC pair)
        Dq = dither_generation.gen_stochastic(t.size, Nch_in, Qstep, dither_generation.pdf.triangular_hp)
        Dq = Q_DITHER_ON*Dq

        # Add headroom for quantisation dither if needed
        HEADROOM = 0*(Qstep/Rng)
        Xscale = 100 - HEADROOM
        SC.ref_scale = Xscale  # save scale param.

        X = (Xscale/100)*Xref + Dq  # quantiser input
        
        # Assume look-up table has been generated for a given DAC
        lutfile = os.path.join('generated_physcal_luts', 'LUTcal_' + str(QConfig) + '.npy')
        LUTcal = np.load(lutfile)  # load calibration look-up table
        
        q = quantise_signal(X, Qstep, Qtype)  # uniform quantiser
        c_pri = generate_codes(q, Nb, Qtype)

        c_sec = LUTcal[c_pri.astype(int)]

        C = np.stack((c_pri[0, :], c_sec[0, :]))  ##### output codes

        # Zero contribution from secondary in ideal case
        Nch = 2  # number of physical channels
        YQ = np.stack((YQ[0, :], np.zeros(YQ.shape[1])))

    case lm.DEM:  # dynamic element matching
        # Here we assume standard off-the-shelf DACs which translates to
        # full segmentation, which then means we have 2 DACs to work with.

        Nch = 1  # DEM effectively has 1 channel input

        # Quantisation dither
        Q_DITHER_ON = 1
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)
        Dq = Q_DITHER_ON*Dq[0]  # convert to 1d

        # Add headroom for quantisation dither if needed
        HEADROOM = 0*(Qstep/Rng)
        Xscale = 100 - HEADROOM
        SC.ref_scale = Xscale  # save scale param.

        X = (Xscale/100)*Xref + Dq  # input

        C = dem(X, Rng, Nb)  ##### output codes

        Nch = 2  # number of physical channels  
        # two identical, ideal channels
        # YQ = matlib.repmat(YQ, 2, 1)

    case lm.NSDCAL:  # noise shaping with digital calibration
        # Use a simple static model as an open-loop observer for a simple
        # noise-shaping feed-back filter. Model is essentially the INL.
        # Open-loop observer error feeds directly to output, so very
        # sensitive to model error.

        Nch = 1  # only supports a single channel (at this point)

        # Re-quantisation dither
        Q_DITHER_ON = 1
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_white)
        Dq = Q_DITHER_ON*Dq[0]  # convert to 1d, add/remove dither
        
        # The feedback generates an actuation signal that may cause the
        # quantiser to saturate if there is no "headroom"
        # Also need room for re-quantisation dither
        if   QConfig == qs.w_16bit_SPICE:       HEADROOM = 10   # 16 bit DAC
        elif QConfig == qs.w_6bit_ARTI:         HEADROOM = 15   # 6 bit DAC
        elif QConfig == qs.w_6bit_ZTC_ARTI:     HEADROOM = 10   #15  # 6 bit DAC
        elif QConfig == qs.w_10bit_ARTI:        HEADROOM = 15   # 10 bit DAC
        elif QConfig == qs.w_10bit_ZTC_ARTI:    HEADROOM = 5    #15  # 10 bit DAC
        elif QConfig == qs.w_16bit_ARTI:        HEADROOM = 10   # 16 bit DAC
        elif QConfig == qs.w_6bit_2ch_SPICE:    HEADROOM = 10   # 6 bit DAC
        elif QConfig == qs.w_16bit_2ch_SPICE:   HEADROOM = 1    # 16 bit DAC
        elif QConfig == qs.w_10bit_2ch_SPICE:   HEADROOM = 5    # 10 bit DAC
        elif QConfig == qs.w_16bit_6t_ARTI:     HEADROOM = 1    # 16 bit DAC
        # elif QConfig == qs.w_16bit_NI_card:     HEADROOM = 15
        # elif QConfig == qs.w_8bit_NI_card:      HEADROOM = 15
        else: HEADROOM = 10 #sys.exit('NSDCAL: Missing config.')
        print(f'HEADROOM: {HEADROOM}')
        Xscale = 100 - HEADROOM

        # Repeat reference on all channels
        # Xref = matlib.repmat(Xref, Nch, 1)

        X = (Xscale/100)*Xref  # input

        SC.ref_scale = Xscale  # save scale param.
        
        ML = get_measured_levels(QConfig, SC.lin) # get_measured_levels(lm.NSDCAL)  # TODO: Redundant re-calling below in this case

        YQns = YQ[0]  # ideal output levels
        MLns = ML[0]  # measured output levels (convert from 2d to 1d)

        # Adding some "measurement/model error" in the levels
        MLns_err = measurement_noise_range(Nb, 18, Qstep, MLns.shape)
        MLns = MLns + M_NOISE * MLns_err

        QMODEL = 2  # 1: no calibration, 2: use calibration
        C = nsdcal(X, Dq, YQns, MLns, Qstep, Vmin, Nb, QMODEL)  ##### output codes
        SC.xref = X

        # Zero input to sec. channel for sims with two channels (only need one channel)
        if QConfig in [qs.w_6bit_2ch_SPICE, qs.w_16bit_2ch_SPICE, qs.w_10bit_2ch_SPICE]:
            C = np.stack((C[0, :], np.zeros(C.shape[1])))
        
        # Print noise shaping amplitudes and occurency count (frequency of each value)
        # diff = np.abs(np.diff(C))
        # elements, counts = np.unique(diff, return_counts=True)
        # plt.stem(elements, counts)
        # plt.xlabel('Value')
        # plt.ylabel('Frequency')
        
    case lm.SHPD:  # stochastic high-pass noise dither
        # Adds a large(ish) high-pass filtered normally distributed noise dither.
        # A normal/gaussian PDF has poor INL averaging properties.
        # The "tuning" of this method is very ad-hoc (amplitude, PSD, ...)

        # most recent prototype has 4 channels, so limit to 4
        Nch = 2

        # Quantisation dither
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)

        # Repeat carrier on all channels
        Xref = matlib.repmat(Xref, Nch, 1)

        # Large high-pass dither set-up
        #Xscale = 10  # carrier to dither ratio (between 0% and 100%)
        #Xscale = 5  # carrier to dither ratio (between 0% and 100%)

        match QConfig:
            case qs.w_6bit_2ch_SPICE:
                if Fs == 1022976:
                    Xscale = 50
                    Fc_hf = 250e3
                elif Fs == 32735232:
                    Xscale = 50
                    Fc_hf = 250e3
                else:
                    sys.exit('SHPD: Missing config.')
            case qs.w_10bit_2ch_SPICE:
                if Fs == 1022976:
                    Xscale = 70
                    Fc_hf = 250e3
                elif Fs == 32735232:
                    Xscale = 50
                    Fc_hf = 250e3
                else:
                    sys.exit('SHPD: Missing config.')
            case  qs.w_6bit_ARTI:
                if Fs == 1022976:
                    Xscale = 50
                    Fc_hf = 200e3
                elif Fs == 65470464:
                    Xscale = 20
                    Fc_hf = 200e3
                elif Fs in [209715200, 226719135.13513514400, 261881856]:
                    Xscale = 10
                    Fc_hf = 0.20e6
                else:
                    sys.exit('SHPD: Missing config.')
            case qs.w_6bit_ZTC_ARTI:
                if Fs == 65470464:
                    Xscale = 20
                    Fc_hf = 200e3
                elif Fs in [209715200, 226719135.13513514400, 261881856]:
                    Xscale = 90
                    Fc_hf = 20e6
                elif Fs == 1638400:
                    Xscale = 50
                    Fc_hf = 275e3
                else:
                    sys.exit('SHPD: Missing config.')
            case qs.w_10bit_ARTI:
                if Fs == 65470464:
                    Xscale = 20
                    Fc_hf = 200e3
                elif Fs in [209715200, 226719135.13513514400]:
                    Xscale = 30
                    Fc_hf = 30.0e6
                elif Fs == 261881856:
                    Xscale = 10
                    Fc_hf = 0.20e6
                else:
                    sys.exit('SHPD: Missing config.')
            case qs.w_10bit_ZTC_ARTI:
                if Fs == 65470464:
                    Xscale = 20
                    Fc_hf = 200e3
                elif Fs in [209715200, 226719135.13513514400]:
                    Xscale = 30
                    Fc_hf = 30.0e6
                elif Fs == 261881856:
                    Xscale = 10
                    Fc_hf = 0.20e6
                elif Fs == 1638400:
                    Xscale = 50
                    Fc_hf = 275e3
                else:
                    sys.exit('SHPD: Missing config.')
            case qs.w_16bit_6t_ARTI:
                if Fs == 65470464:
                    Xscale = 10
                    Fc_hf = 200e3
                elif Fs == 261881856:
                    Xscale = 10
                    Fc_hf = 200e3
                else:
                    sys.exit('SHPD: Missing config.')
            case qs.w_16bit_ARTI:
                if Fs == 65470464:
                    Xscale = 50
                    Fc_hf = 200e3
                else:
                    sys.exit('SHPD: Missing config.')
            case _:
                sys.exit('SHPD: Missing config.')

        Dscale = 100 - Xscale  # dither to carrier ratio

        SC.ref_scale = Xscale  # save param.

        match 3:
            case 1:
                Dmaxamp = Rng/2  # maximum dither amplitude (volt)
                Dscale = 100  # %
                Ds = dither_generation.gen_stochastic(t.size, Nch, Dmaxamp, dither_generation.pdf.uniform)
                Dsf = Ds
            case 2:
                Ds = dither_generation.gen_stochastic(t.size, Nch, 1, dither_generation.pdf.uniform)

                N_hf = 1
                b, a = signal.butter(N_hf, Fc_hf/(Fs/2), btype='high', analog=False)#, fs=Fs)

                Dsf = signal.filtfilt(b, a, Ds, method="gust")
                Dsf[0,:] = 2.*(Dsf[0,:] - np.min(Dsf[0,:]))/np.ptp(Dsf[0,:]) - 1
                Dsf[1,:] = 2.*(Dsf[1,:] - np.min(Dsf[1,:]))/np.ptp(Dsf[1,:]) - 1
                
                Dmaxamp = Rng/2  # maximum dither amplitude (volt)
                Dsf = Dmaxamp*Dsf
            case 3:  # 6 bit and 16 bit ARTI
                ds = np.random.normal(0, 1.0, [1, t.size])  # normally distr. noise
                
                N_hf = 1
                b, a = signal.butter(N_hf, Fc_hf/(Fs/2), btype='high', analog=False)#, fs=Fs)

                dsf = signal.filtfilt(b, a, ds, method="gust")
                dsf = dsf.squeeze()
                dsf = 2.*(dsf - np.min(dsf))/np.ptp(dsf) - 1
                
                # Opposite polarity for HF dither for pri. and sec. channel
                if Nch == 2:
                    Dsf = np.stack((dsf, -dsf))
                elif Nch == 4:
                    Dsf = np.stack((dsf, -dsf, dsf, -dsf))
                else:
                    sys.exit("Invalid channel config. for stoch. dithering.")

                Dmaxamp = Rng/2  # maximum dither amplitude (volt)
                Dsf = Dmaxamp*Dsf
            case 4:
                Ds = np.random.normal(0, 1.0, [Nch, t.size])  # normally distr. noise

                N_hf = 1
                b, a = signal.butter(N_hf, Fc_hf/(Fs/2), btype='high', analog=False)#, fs=Fs)

                Dsf = signal.filtfilt(b, a, Ds, method="gust")
                Dsf[0,:] = 2.*(Dsf[0,:] - np.min(Dsf[0,:]))/np.ptp(Dsf[0,:]) - 1
                Dsf[1,:] = 2.*(Dsf[1,:] - np.min(Dsf[1,:]))/np.ptp(Dsf[1,:]) - 1
                
                Dmaxamp = Rng/2  # maximum dither amplitude (volt)
                Dsf = Dmaxamp*Dsf

            case 5:
                Dsf = np.zeros((Nch, t.size))
                Dmaxamp = Rng/2  # maximum dither amplitude (volt)
                Dsf[0,:] = 0.99*Dmaxamp*dual_dither(N=t.size)
                Dsf[1,:] = 0.99*Dmaxamp*dual_dither(N=t.size)
        
        if (PLOTS):
            hist_and_psd(Dsf[0,:].squeeze())

        # for k in range(0,Nch):
        #     dsf = Dsf[k,:]
        #     dsf = 2.*(dsf - np.min(dsf))/np.ptp(dsf) - 1
        #     Dsf[k,:] = dsf

        X = (Xscale/100)*Xref + (Dscale/100)*Dsf + Dq

        print(np.max(X))
        print(Vmax)
        print(np.min(X))
        print(Vmin)

        #if np.max(X) > Vmax:
        #    raise ValueError('Input out of bounds.') 
        #if np.min(X) < Vmin:
        #    raise ValueError('Input out of bounds.')

        Q = quantise_signal(X, Qstep, Qtype)
        C = generate_codes(Q, Nb, Qtype)  ##### output codes

        # two identical, ideal channels
        YQ = matlib.repmat(YQ, Nch, 1)

    case lm.PHFD:  # periodic high-frequency dither
        # Adds a large, periodic high-frequency dither.
        # Uniform ADF has good averaging effect on INL.
        # May experiment with other ADFs for smoothing results (there may be an optimal one).
        # Tuning can be done by optimisation on dither amplitude and frequency with
        # SINAD as cost. Typically several optimal points; often just as quick to
        # experiment manually.

        # most recent prototype has 4 channels, so limit to 4
        Nch = 2  # this method requires even no. of channels

        # Quantisation dither
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)

        # Repeat carrier on all channels
        Xref = matlib.repmat(Xref, Nch, 1)

        # Optimising scale and freq. using grid search
        # (elsewhere; TODO: convert MATLAB code for grid search)
        # Scale: carrier to dither ratio (between 0% and 100%)
        if QConfig == qs.w_16bit_SPICE:
            Xscale = 50  # carrier to dither ratio (between 0% and 100%)
        elif QConfig == qs.w_6bit_ZTC_ARTI:
            if Fs == 1638400:
                Xscale = 83 #64*100*Qstep/Rng
                Dfreq = 275e3
            elif Fs == 32735232:
                Xscale = 74
                Dfreq = 1.0e6
            elif Fs == 209715200:
                Xscale = 50
                Dfreq = 5.0e6
            else:
                sys.exit('PHFD: Missing config.')
        elif QConfig == qs.w_6bit_ARTI:
            Xscale = 80  # carrier to dither ratio (between 0% and 100%)
            Dfreq = 15.0e6 # Fs262Mhz - 6 bit ARTI
        elif QConfig == qs.w_10bit_ARTI:
            Xscale = 50  # carrier to dither ratio (between 0% and 100%)
            Dfreq = 5.0e6
        elif QConfig == qs.w_10bit_ZTC_ARTI:
            if Fs == 1638400:
                Xscale = 66
                Dfreq = 275e3
            elif Fs == 32735232:
                Xscale = 74
                Dfreq = 1.0e6
            elif Fs == 209715200:
                Xscale = 50
                Dfreq = 5.0e6
            else:
                sys.exit('PHFD: Missing config.')
        elif QConfig == qs.w_16bit_ARTI:
            Xscale = 50  # carrier to dither ratio (between 0% and 100%)
            Dfreq = 5.0e6 #10.0e6 # Fs262Mhz - 16 bit ARTI
        elif QConfig == qs.w_16bit_6t_ARTI:
            if Fs == 65470464:
                Xscale = 45
                Dfreq = 5.0e6 
            elif Fs == 261881856:
                Xscale = 6
                Dfreq = 3.0e6
            else:
                sys.exit('PHFD: Missing config.')
        elif QConfig == qs.w_6bit_2ch_SPICE:
            if Fs == 1022976:
                Xscale = 75
                Dfreq = 300e3
            elif Fs == 32735232:
                Xscale = 74
                Dfreq = 900e3
            else:
                sys.exit('PHFD: Missing config.')
        elif QConfig == qs.w_16bit_2ch_SPICE:
            Xscale = 50  # carrier to dither ratio (between 0% and 100%)
            Dfreq = 250e3 # Fs1022976 - 16 bit 2 Ch
            #Dfreq = 5.0e6 # Fs32735232 - 16 bit 2 Ch
            #Dfreq = 1.0e6 # Fs32735232 - 16 bit 2 Ch
            #Dfreq = 5.0e6 # Fs262Mhz - 16 bit 2 Ch
        elif QConfig == qs.w_10bit_2ch_SPICE:
            if Fs == 1022976:
                Xscale = 80
                Dfreq = 300e3
            elif Fs == 32735232:
                Xscale = 50
                Dfreq = 900e3
            else:
                sys.exit('PHFD: Missing config.')
        else:
            sys.exit('PHFD: Missing config.')
        
        Dscale = 100 - Xscale  # dither to carrier ratio
        
        SC.ref_scale = Xscale  # save param.

        Dadf = dither_generation.adf.uniform  # amplitude distr. funct. (ADF)
        # Generate periodic dither
        Dmaxamp = Rng/2  # maximum dither amplitude (volt)
        dp = 0.975*Dmaxamp*dither_generation.gen_periodic(t, Dfreq, Dadf)
        
        # Opposite polarity for HF dither for pri. and sec. channel
        if Nch == 2:
            Dp = np.stack((dp, -dp))
        elif Nch == 4:
            Dp = np.stack((dp, -dp, dp, -dp))
        else:
            sys.exit("Invalid channel config. for periodic dithering.")

        Dq = np.stack((Dq[1,:], -Dq[1,:]))

        X = (Xscale/100)*Xref + (Dscale/100)*Dp + Dq
        #X = (Xscale/100)*Xref + (Dscale/100)*Dp

        Q = quantise_signal(X, Qstep, Qtype)
        C = generate_codes(Q, Nb, Qtype)  ##### output codes

        # two/four identical, ideal channels
        YQ = matlib.repmat(YQ, Nch, 1)

    case lm.MPC | lm.MHOQ:  # model predictive control (with INL model)
        Nch = 1

        # Quantisation dither
        DITHER_ON = 0
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)
        Dq = DITHER_ON*Dq[0]  # convert to 1d, add/remove dither

        # Also need room for re-quantisation dither
        if QConfig == qs.w_16bit_SPICE: HEADROOM = 10  # 16 bit DAC
        elif QConfig == qs.w_6bit_ARTI: HEADROOM = 0*15  # 6 bit DAC
        elif QConfig == qs.w_6bit_ZTC_ARTI: HEADROOM = 15  # 6 bit DAC
        elif QConfig == qs.w_16bit_ARTI: HEADROOM = 1  # 16 bit DAC
        elif QConfig == qs.w_6bit_2ch_SPICE: HEADROOM = 5  # 6 bit DAC
        elif QConfig == qs.w_16bit_2ch_SPICE: HEADROOM = 10  # 16 bit DAC
        elif QConfig == qs.w_10bit_2ch_SPICE: HEADROOM = 0  # 10 bit DAC
        elif QConfig == qs.w_10bit_ARTI: HEADROOM = 0* 10  # 10 bit DAC
        elif QConfig == qs.w_10bit_ZTC_ARTI: HEADROOM = 0*10  # 10 bit DAC
        elif QConfig == qs.w_16bit_NI_card: HEADROOM = 10
        elif QConfig == qs.w_8bit_NI_card: HEADROOM = 0
        else: sys.exit('MPC: Missing config.')

        Xscale = 100 - HEADROOM
        X = (Xscale/100)*Xref + Dq # input

        SC.ref_scale = Xscale  # save param.

        # Ideal Levels
        YQns = YQ[0]
        
        # Unsigned integers representing the level codes
        # level_codes = np.arange(0, 2**Nb,1) # Levels:  0, 1, 2, .... 2^(Nb)
        ML = get_measured_levels(QConfig, SC.lin)
        MLns = ML[0]
        
        # Adding some "measurement/model error" in the levels
        MLns_err = measurement_noise_range(Nb, 18, Qstep, MLns.shape)
        MLns = MLns + M_NOISE * MLns_err
 
        # Reconstruction filter
        A1, B1, C1, D1 = mpc_filter_parameters(FS_CHOICE)

        # Quantiser model
        QMODEL = 2 #: 1 - no calibration, 2 - Calibration

        # Run MPC Binary variables
        # MPC_OBJ = MPC_BIN(Nb, Qstep, QMODEL, A1, B1, C1, D1)
        MPC_OBJ = MPC(Nb, Qstep, QMODEL, A1, B1, C1, D1)
        C = MPC_OBJ.get_codes(N_PRED, X, YQns, MLns)  ##### output codes

        t = t[0:C.size]

        # Zero input to sec. channel for sims with two channels (only need one channel)
        if QConfig == qs.w_6bit_2ch_SPICE or QConfig == qs.w_16bit_2ch_SPICE or QConfig == qs.w_10bit_2ch_SPICE:
            C = np.stack((C[0, :], np.zeros(C.shape[1])))

    case lm.ILC:  # iterative learning control (with INL model, only periodic signals)

        Nch = 1

        # Quantisation dither
        DITHER_ON = 1
        Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)
        Dq = DITHER_ON*Dq[0]  # convert to 1d, add/remove dither

        # Headrooom for requantisation
        if QConfig == qs.w_16bit_SPICE: HEADROOM = 10  # 16 bit DAC
        elif QConfig == qs.w_6bit_ARTI: HEADROOM = 15  # 6 bit DAC
        elif QConfig == qs.w_16bit_ARTI: HEADROOM = 10  # 16 bit DAC
        elif QConfig == qs.w_6bit_2ch_SPICE: HEADROOM = 10  # 6 bit DAC
        elif QConfig == qs.w_16bit_2ch_SPICE: HEADROOM = 10  # 16 bit DAC
        else: sys.exit('ILC: Fix qconfig')

        Xscale = (100-HEADROOM)/100
        X = Xscale*Xref  # input

        SC.ref_scale = Xscale  # save param.

        # Ideal Levels
        YQns = YQ[0]

        # % Measured Levels
        ML = get_measured_levels(QConfig, SC.lin) # get_measured_levels(lm.ILC)
        MLns = ML[0] # one channel only
        
        # Adding some "measurement/model error" in the levels
        MLns_err = measurement_noise_range(Nb, 18, Qstep, MLns.shape)
        MLns = MLns + M_NOISE * MLns_err

        # if QConfig == qws.w_6bit_ARTI or QConfig == qws.w_16bit_ARTI:
        #     MLns = np.flip(MLns)
        #     YQns = np.flip(YQns)

        # Reconstruction filter
        match 2:
            case 1:
                Wn = Fc_lp/(Fs/2)
                b1, a1 = signal.butter(2, Wn)
                l_dlti = signal.dlti(b1, a1, dt=Ts)
            case 2:  # bilinear transf., seems to work ok, not a perfect match to physics
                Wn = Fc_lp/(Fs/2)
                b1, a1 = signal.butter(N_lp, Wn)
                l_dlti = signal.dlti(b1, a1, dt=Ts)
        
        len_X = len(Xref)
        ft, fi = signal.dimpulse(l_dlti, n=2*len_X)
        
        # new updated ILC implementation
        # Quantizer model
        # QMODEL = 1      # Ideal model
        QMODEL = 2      # Measured/Calibrated

        # Tuning matrices
        We = np.identity(len_X)
        Wf = np.identity(len_X)*1e-4
        Wdf = np.identity(len_X)*1e-1

        itr = 10

        dsmilc = DSM_ILC(Nb, Qstep, Vmin, Vmax, Qtype, QMODEL)
        # Get Q filtering, learning and output matrices
        Q, L, G = dsmilc.learningMatrices(X.size, We, Wf, Wdf,fi)

        # Get DSM_ILC codes
        C = dsmilc.get_codes(X, Dq, itr, YQns, MLns, Q, L, G)  ##### output codes

        # Zero input to sec. channel for sims with two channels (only need one channel)
        if QConfig == qs.w_6bit_2ch_SPICE or QConfig == qs.w_16bit_2ch_SPICE or QConfig == qs.w_10bit_2ch_SPICE:
            C = np.stack((C[0, :], np.zeros(C.shape[1])))
        
    case lm.ILC_SIMP:  # iterative learning control, basic implementation (TODO: broken)
        
        Nch = 1  # number of channels to use

        # Quantisation dither
        #Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)

        # Repeat carrier on all channels
        Xref = matlib.repmat(Xref, Nch, 1)

        X = Xref #+ Dq  # quantiser input
        x = X.squeeze()

        # Plant: Butterworth or Bessel reconstruction filter
        Wn = 2*np.pi*Fc_lp
        b, a = signal.butter(N_lp, Wn, 'lowpass', analog=True)
        Wlp = signal.lti(b, a)  # filter LTI system instance
        G = Wlp.to_discrete(dt=Ts, method='zoh')

        # Q filter
        M = 2001  # Support/filter length/no. of taps
        Q_Fc = 2.0e4  # Cut-off freq. (Hz)
        alpha = (np.sqrt(2)*np.pi*Q_Fc*M)/(Fs*np.sqrt(np.log(4)))
        sigma = (M - 1)/(2*alpha)
        Qfilt = signal.windows.gaussian(M, sigma)
        Qfilt = Qfilt/np.sum(Qfilt)

        # L filter tuning (for Fs = 1 MHz, Nb = 16 bit)
        kp = 0.3
        kd = 20
        Niter = 50

        c, y1 = ilc_simple(x, G, Qfilt, Qstep, Nb, Qtype, kp, kd, Niter)  # TODO: Get this running again
        c_ = c.clip(0, 2**16-1)
        C = np.array([c_])
        print('** ILC simple end **')

    case lm.STEP:  # step response
        # Generate unmodified DAC output without any corrections.

        if QConfig in [qs.w_6bit_2ch_SPICE, qs.w_16bit_2ch_SPICE, qs.w_10bit_2ch_SPICE, qs.w_6bit_ZTC_ARTI, qs.w_10bit_ZTC_ARTI]:
            Nch = 2  # number of channels to use (averaging to reduce noise floor)
        else:
            Nch = 1
        
        # Quantisation dither (eliminate harm. distortion from quantisation)
        # Q_DITHER_ON = DITHER_BASELINE
        # Dq = dither_generation.gen_stochastic(t.size, Nch, Qstep, dither_generation.pdf.triangular_hp)
        # Dq = Q_DITHER_ON*Dq

        # Add headroom for quantisation dither if needed
        HEADROOM = 0*(Qstep/Rng)
        Xscale = 100 - HEADROOM
        SC.ref_scale = Xscale  # save scale param.

        # Repeat reference on all channels
        Xref = matlib.repmat(Xref, Nch, 1)

        X = (Xscale/100)*Xref #+ Dq  # quantiser input

        Q = quantise_signal(X, Qstep, Qtype)  # uniform quantiser
        C = generate_codes(Q, Nb, Qtype)  ##### output codes

    case lm.MPC_RL_RM:
        # Optimal filter parameters
        Nch = 1

        # Change the filter order in get_optFilterParams.m file if necessary. The default value is set as N_lp = 3.
        match 2:
            case 1:     # Calculates the optimal filter parmaters by running the MATLAB  code.
                eng = matlab.engine.start_matlab()
                B_LPF = eng.feval('get_optFilterParams', Fs, Fc)
                b_lpf = np.array(B_LPF)[0]
                a_lpf = np.array(B_LPF)[1]
                A, B, C, D  = signal.tf2ss(b_lpf, a_lpf)  # Tf to state space
            case 2:   # Optimal filter paramters for Fs = 1e6, Fc = 1e5, and N_lp =3
                b_lpf = np.array([ 1.        , -0.74906276,  0.35356745, -0.05045204])
                a_lpf = np.array([ 1.        , -1.76004281,  1.18289728, -0.27806204])
                A, B, C, D  = signal.tf2ss(b_lpf, a_lpf)  # Tf to state space

        # Quantiser levels : Ideal and Measured
        # Ideal levels 
        YQns = YQ.squeeze()     
        # Measured Levels
        MLns  =  get_measured_levels(QConfig).squeeze()

        # Adding some "measurement/model error" in the levels
        MLns_err = measurement_noise_range(Nb, 18, Qstep, MLns.shape)
        MLns = MLns + M_NOISE * MLns_err

        # Direct Quantization 
        # C_DQ = (np.floor(Xref/Qstep +1/2)).astype(int)
        # match QMODEL:
        #     case 1:
        #         Xcs_DQ = generate_dac_output(C_DQ, YQns)
        #     case 2:
        #         Xcs_DQ = generate_dac_output(C_DQ, MLns)

        # Quantiser model: 1 - Ideal , 2- Calibrated
        QMODEL = 2

        # MHOQ Ratelimit
        # N_PRED = 1      # Prediction horizon 
        # Steps constraints for the MPC search space. MPC is constrained by:    current input- Step  <= current input <=  current input +  Step  
        Step = MPC_step_limit

        # if RUN_MPC:
        MHOQ_RL = MHOQ_RLIM_RM(Nb, Qstep, QMODEL, A, B, C, D)
        C_MHOQ = MHOQ_RL.get_codes(N_PRED, Xref, YQns, MLns[Nch-1,:], Step)
        # match QMODEL:
        #     case 1:
        #         Xcs_MHOQ = generate_dac_output(C_MHOQ, YQns)
        #     case 2:
        #         Xcs_MHOQ = generate_dac_output(C_MHOQ, MLns) 

        C = C_MHOQ

        t = t[0:C.size]

        # Zero input to sec. channel for sims with two channels (only need one channel)
        if QConfig == qs.w_6bit_2ch_SPICE or QConfig == qs.w_16bit_2ch_SPICE or QConfig == qs.w_10bit_2ch_SPICE:
            C = np.stack((C[0, :], np.zeros(C.shape[1])))

    case lm.MPC_RL:
        # Optimal filter parameters
        Nch = 1

        # Change the filter order in get_optFilterParams.m file if necessary. The default value is set as N_lp = 3.
        match 2:
            case 1:     # Calculates the optimal filter parmaters by running the MATLAB  code.
                eng = matlab.engine.start_matlab()
                B_LPF = eng.feval('get_optFilterParams', Fs, Fc)
                b_lpf = np.array(B_LPF)[0]
                a_lpf = np.array(B_LPF)[1]
                A, B, C, D  = signal.tf2ss(b_lpf, a_lpf)  # Tf to state space
            case 2:   # Optimal filter paramters for Fs = 1e6, Fc = 1e5, and N_lp =3
                b_lpf = np.array([ 1.        , -0.74906276,  0.35356745, -0.05045204])
                a_lpf = np.array([ 1.        , -1.76004281,  1.18289728, -0.27806204])
                A, B, C, D  = signal.tf2ss(b_lpf, a_lpf)  # Tf to state space

        # Quantiser model: 1 - Ideal , 2- Calibrated
        QMODEL = 2

        # Quantiser levels : Ideal and Measured
        # Ideal levels 
        YQns = YQ.squeeze()     
        # Measured Levels
        MLns  =  get_measured_levels(QConfig).squeeze()

        # Adding some "measurement/model error" in the levels
        MLns_err = measurement_noise_range(Nb, 18, Qstep, MLns.shape)
        MLns = MLns + M_NOISE * MLns_err

        # Direct Quantization 
        # C_DQ = (np.floor(Xref/Qstep +1/2)).astype(int)
        # match QMODEL:
        #     case 1:
        #         Xcs_DQ = generate_dac_output(C_DQ, YQns)
        #     case 2:
        #         Xcs_DQ = generate_dac_output(C_DQ, MLns)

        # MHOQ Ratelimit
        N_PRED = 1      # Prediction horizon 
        # Steps constraints for the MPC search space. MPC is constrained by:    current input- Step  <= current input <=  current input +  Step  
        Step = MPC_step_limit

        # if RUN_MPC:
        MHOQ_RL = MHOQ_RLIM(Nb, Qstep, QMODEL, A, B, C, D)
        C_MHOQ = MHOQ_RL.get_codes(N_PRED, Xref, YQns, MLns[Nch-1,:], Step)
        # match QMODEL:
        #     case 1:
        #         Xcs_MHOQ = generate_dac_output(C_MHOQ, YQns)
        #     case 2:
        #         Xcs_MHOQ = generate_dac_output(C_MHOQ, MLns) 

        C = C_MHOQ

        t = t[0:C.size]

        # Zero input to sec. channel for sims with two channels (only need one channel)
        if QConfig == qs.w_6bit_2ch_SPICE or QConfig == qs.w_16bit_2ch_SPICE or QConfig == qs.w_10bit_2ch_SPICE:
            C = np.stack((C[0, :], np.zeros(C.shape[1])))

    case lm.MPC_SL:
        pass

# %% Generate DAC output
SC.nch = Nch  # update with no. channels set for simulation

# Use the config to generate a hash; overwrite results for identical configurations 
import hashlib
hash_stamp = hashlib.sha1(SC.__str__().encode('utf-8')).hexdigest()

top_d = 'generated_codes/'  # directory for generated codes and configuration info

method_d = top_d + str(SC.lin).replace(" ", "_") + '/'  # archive outputs according to method
os.makedirs(method_d, exist_ok=True)  # make sure the method directory exists

codes_d = method_d + hash_stamp + '/'
os.makedirs(codes_d, exist_ok=True)

config_f = 'sim_config'  # file with configuration info
with open(os.path.join(codes_d, config_f + '.txt'), 'w') as fout:  # save as plain text
    fout.write(SC.__str__())
with open(os.path.join(codes_d, config_f + '.pickle'), 'wb') as fout:  # marshalled object
    pickle.dump(SC, fout)

codes_f = codes_d + 'codes'
np.save(codes_f, C)

# %% 
if (DAC_MODEL_CHOICE == 1):
    run_static_model_and_post_processing(RUN_LM, hash_stamp, MAKE_PLOT=PLOTS, SAVE=SAVE_ENOB)

pass
# %%
