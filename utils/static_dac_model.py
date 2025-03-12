#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate DAC output assuming a simple static non-linear model

@author: Arnfinn Eielsen
@date: 22.02.2024
@license: BSD 3-Clause
"""

import numpy as np

class quantiser_type:
    midtread = 1
    midriser = 2


def quantise_signal(w, Qstep, Qtype):
    """
    Quantise a signal with given quantiser specifications
    """
    
    match Qtype:
        case quantiser_type.midtread:
            q = np.floor(w/Qstep + 0.5) # truncated/quantised value, mid-tread
        case quantiser_type.midriser:
            q = np.floor(w/Qstep) + 0.5 # truncated/quantised value, mid-riser
    
    return q


def generate_codes(q, Nb, Qtype):
    """
    Generate codes for quantised signal with given quantiser specifications
    """
    
    match Qtype:
        case quantiser_type.midtread:
            #c = q - np.floor(Vmin/Qstep) # code, mid-tread
            c = q + 2**(Nb-1) # code, mid-tread
        case quantiser_type.midriser:
            #c = q - np.floor(Vmin/Qstep) - 0.5 # code, mid-riser
            c = q + 2**(Nb-1) - 0.5 # code, mid-riser

    return c.astype(int)

def slew_model(y, ts, R):
    """
    Add slewing affect to a given DAC output signal.
    
    Parameters
    ----------
    y
        dac output signal
    ts
        time step (delta t)
    R
        rising rate, in V/us, typically given by datasheet
    """
    YS = np.copy(y)
    R = R*1e6 # v/us to v/s
    F = -R # falling rate
    for i in range(1,YS.shape[1]):
        rate = (YS[0,i]-YS[0,i-1])/ts
        if (rate > R):
            YS[0,i] = R * ts + YS[0,i-1]
        elif (rate < F):
            YS[0,i] = F * ts + YS[0,i-1]
        else:
            pass # y=u, vector is already copied above
    return YS

def generate_dac_output(C, ML):
    """
    Table look-up to implement a simple static non-linear DAC model

    Parameters
    ----------
    C
        input codes, one channel per row, must be integers, 2d array
    ML
        static DAC model output levels, one channel per row, 2d array

    Returns
    -------
    Y
        emulated DAC output
    """
    
    if C.shape[0] > ML.shape[0]:
        print(C.shape[0])
        print(ML.shape[0])
        raise ValueError('Not enough channels in model.')

    Y = np.zeros(C.shape)
    
    match 2:
        case 1: # use loops
            for k in range(0,C.shape[0]):
                for j in range(0,C.shape[1]):
                    c = C[k,j]
                    ml = ML[k,c]
                    Y[k,j] = ml
        case 2: # use numpy indexing
            for k in range(0,C.shape[0]):
                Y[k,:] = ML[k,C[k,:]]
    return Y
