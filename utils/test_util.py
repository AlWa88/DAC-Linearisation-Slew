#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions for DAC test stimuli

@author: Arnfinn Eielsen
@date: 29.01.2025
@license: BSD 3-Clause
"""

import numpy as np
from prefixed import Float


def test_signal_sine(SCALE, MAXAMP, FREQ, OFFSET, t):
    """
    Generate a test signal (reference)
    
    Arguments
        SCALE - percentage of maximum amplitude
        MAXAMP - maximum amplitude
        FREQ - signal frequency in hertz
        OFFSET - signal offset
        t - time vector
    
    Returns
        x - sinusoidal test signal
    """
    return (SCALE/100)*MAXAMP*np.cos(2*np.pi*FREQ*t) + OFFSET

def test_signal_square(SCALE, MAXAMP, FREQ, OFFSET, t):
    """
    Generate a test signal (reference)
    
    Arguments
        SCALE - percentage of maximum amplitude
        MAXAMP - maximum amplitude
        FREQ - signal frequency in hertz
        OFFSET - signal offset
        t - time vector
    
    Returns
        x - square wave test signal
    """
    return (SCALE/100)*MAXAMP*np.sign(np.sin(2*np.pi*FREQ*t)) + OFFSET

class sim_config:
    def __init__(self, qconfig, lin, dac, fs, t, fc, nf, ref_scale, ref_freq, ncyc, sr, xref, fs_scope, nch=1):
        self.qconfig = qconfig
        self.lin = lin
        self.dac = dac
        self.fs = fs
        self.t = t
        self.fc = fc
        self.nf = nf
        self.ref_scale = ref_scale
        self.ref_freq = ref_freq
        self.ncyc = ncyc # number of periods/cycles of the fundamental/carrier
        self.sr = sr # slew rate
        self.xref = xref # reference (ideal) signal
        self.fs_scope = fs_scope
        self.nch = nch # number of channels

    def __str__(self):
        s = str(self.qconfig) + '\n'
        s = s + str(self.lin) + '\n'
        s = s + str(self.dac) + '\n'
        s = s + 'Fs=' + f'{Float(self.fs):.0h}' + '\n'
        # s = s + 't=' + f'{Float(self.t):.0h}' + '\n'
        s = s + 'Fc=' + f'{Float(self.fc):.0h}' + '\n'
        s = s + 'Nf=' + f'{Float(self.nf):.0h}' + '\n'
        s = s + 'Xs=' + f'{Float(self.ref_scale):.0h}' + '\n'
        s = s + 'Fx=' + f'{Float(self.ref_freq):.0h}' + '\n'
        s = s + 'Ncyc=' + f'{Float(self.ncyc):.0h}' + '\n'
        s = s + 'SR=' + f'{Float(self.sr):.0h}' + '\n'
        # s = s + 'Xref=' + f'{Float(self.xref):.0h}' + '\n'
        s = s + 'Fs_scope=' + f'{Float(self.fs_scope):.0h}' + '\n'
        s = s + 'Nch=' + f'{Float(self.nch):.0h}' + '\n'

        return s
