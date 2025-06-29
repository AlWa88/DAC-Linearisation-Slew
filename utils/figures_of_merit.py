#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Implementations of figures-of-merit (FOM) for DAC testing.

Presently there SINAD is used as the main FOM, this file provides
two different methods for determining the SINAD from measurements,
an FFT-based and a curve-fitting-based.

The curve-fitting-based method is recommended based on extensive testing.

@author: Arnfinn Aas Eielsen
@date: 22.02.2024
@license: BSD 3-Clause
"""

import numpy as np
from scipy.interpolate import interp1d
import math
from enum import Enum, auto

from scipy import signal
from scipy import integrate
from matplotlib import pyplot as plt

from utils.welch_psd import welch_psd
from utils.psd_measurements import find_psd_peak
from utils.fit_sinusoid import fit_sinusoid, sin_p

class SINAD_COMP(Enum):
    FFT = auto()  # FFT based
    CFIT = auto()  # curve fit

def TS_SINAD(x, t, y_fit=None, make_plot=False, plot_label=''):
    """
    Take a time-series for computation of the SINAD using a curve-fitting method.
    Use at least 5 periods of the fundamental carrier signal for a good estimate
    (as prescribed in IEEE Std 1658-2011).
    """

    p_opt = fit_sinusoid(t, x, 1)
    # print("p_opt: ", p_opt)  # fitted params.
    # p_opt[0] = 9.92156862745098
    x_fit = sin_p(t, *p_opt)


    if make_plot:
        plt.figure()
        plt.plot(t, x, label=plot_label)
        plt.plot(t, x_fit, '--', label='fit: A=%5.3f, f=%5.3f, phi=%5.3f, C=%5.3f' % tuple(p_opt))
        plt.plot(t, x-x_fit, label='error: x-x_fit')
        plt.title(plot_label)
        plt.xlabel('t')
        plt.ylabel('out')
        plt.legend()
        # plt.show()

    error = x - x_fit
    error_rms = np.sqrt(np.mean(error**2))
    print(f'cfit rms error: {error_rms*1000}mV')

    sine_amp = p_opt[0]
    power_c = sine_amp**2/2
    power_noise = np.var(error)

    SINAD = 10*np.log10(power_c/power_noise)

    return SINAD


def FFT_SINAD(x, Fs, make_plot=False, plot_label=''):
    """
    Take a time-series for computation of the SINAD using an FFT-based method.
    Typically needs a fairly long time-series for sufficient frequency resolution.
    Rule of thumb: More than 100 periods of the fundamental carrier.
    """

    L = 4  # number of averages for PSD estimation

    N = x.size  # length of original sequence
    M = math.floor(N/L)  # length of sequence segments
    WIN = np.kaiser(M, 38)  # window for high dynamic range

    match 1:
        case 1:
            Pxx, f = welch_psd(x, L, Fs)
        case 2:
            # use library fcn.
            f, Pxx = signal.welch(x, window=WIN, fs=Fs)  # type: ignore

    df = np.mean(np.diff(f))

    # approximate noise floor
    noise_floor = np.median(Pxx)

    # equiv. noise bandwidth
    EQNBW = (np.mean(WIN**2)/((np.mean(WIN))**2))*(Fs/M)
    
    if make_plot:
        plt.loglog(f, Pxx, lw=0.5, label=plot_label)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Power (V$^2$/Hz)')
        plt.grid()
        plt.legend()
    
    power_c = 0

    match 1:
        case 1:  # use a simple peak-finding algorithm (very similar to MATLAB)
            # make an artificial peak at DC to detect and remove
            Pxx[0] = 0.99*np.max(Pxx)
            power_dc, peak_f_dc, k_max_dc, k_left_dc, k_right_dc = find_psd_peak(Pxx, f, EQNBW, 0)
            if make_plot:
                plt.vlines(x = f[k_max_dc], ymin = Pxx[k_right_dc], ymax = Pxx[k_max_dc], color = "r", lw=0.25)
                plt.hlines(y = Pxx[k_right_dc], xmin = f[k_left_dc], xmax = f[k_right_dc], color = "r")
            # setting to zero to eliminate adding to the total noise power
            Pxx[k_left_dc:k_right_dc] = 0

            # find the maximal peak in the PSD and assume this is the carrier
            power_c, peak_f_c, k_max_c, k_left_c, k_right_c = find_psd_peak(Pxx, f, EQNBW)
            if make_plot:
                plt.vlines(x = f[k_max_c], ymin = Pxx[k_left_c], ymax = Pxx[k_max_c], color = "r", lw=0.25)
                plt.hlines(y = Pxx[k_left_c], xmin = f[k_left_c], xmax = f[k_right_c], color = "r")
            # setting to zero to eliminate adding to the total noise power
            Pxx[k_left_c:k_right_c] = 0

        case 2:  # use scipy.signal.find_peaks()
            # make an artificial peak at DC to detect and remove
            Pxx[0] = 0
            Pxx[1] = 0.99*np.max(Pxx)

            # tune some magic numbers
            th = (np.max(Pxx) - noise_floor)*0.99  # force finding only maximum
            rel_th = noise_floor/(np.max(Pxx) - noise_floor)
            pk_width = np.floor(EQNBW/df)
            pks, pk_props = signal.find_peaks(Pxx, width=pk_width, prominence=th, rel_height=1-rel_th)
            
            if make_plot:
                plt.loglog(f[pks], Pxx[pks], "x")

            if make_plot:
                plt.vlines(x=f[pks], ymin=(Pxx[pks] - pk_props["prominences"]), ymax=Pxx[pks], color = "C1", lw=0.25)
            left_ips = np.floor(pk_props["left_ips"]).astype(int)
            right_ips = np.ceil(pk_props["right_ips"]).astype(int)
            if make_plot:
                plt.hlines(y=pk_props["width_heights"], xmin=f[left_ips], xmax=f[right_ips], color = "C1")
            
            k_left_dc = left_ips[0]  # assume first peak is DC
            k_right_dc = right_ips[0]
            # setting to zero to eliminate adding to the total noise power
            Pxx[k_left_dc:k_right_dc] = 0

            k_left_c = left_ips[1]  # assume second peak is fundamental
            k_right_c = right_ips[1]
            power_c = integrate.simpson(y=Pxx[k_left_c:k_right_c], x=f[k_left_c:k_right_c])
            # setting to zero to eliminate adding to the total noise power
            Pxx[k_left_c:k_right_c] = 0
    
    if make_plot:
        plt.show()
    
    # compute the remaining harmonic and noise distortion.
    power_noise = integrate.simpson(y=Pxx, x=f)

    SINAD = 10*np.log10(power_c/power_noise)

    return SINAD

def eval_enob_sinad(ty, y, Fs, TRANSOFF, SINAD_COMP_SEL:SINAD_COMP, print_results=True, plot=False, descr='', y_ref=None):
    match SINAD_COMP_SEL:
        case SINAD_COMP.FFT:  # use FFT based method to detemine SINAD
            SINAD = FFT_SINAD(y[TRANSOFF:-TRANSOFF], Fs, plot, descr)
        case SINAD_COMP.CFIT:  # use time-series sine fitting based method to detemine SINAD
            y = y.reshape(1, -1).squeeze()
            SINAD = TS_SINAD(y[TRANSOFF:-TRANSOFF], ty[TRANSOFF:-TRANSOFF], y_ref, plot, descr)

    ENOB = (SINAD - 1.76)/6.02

    # Print FOM
    if print_results:
        print(f'ENOB: {str(ENOB)} SINAD: {str(SINAD)}')

    return ENOB, SINAD

def eval_slew_distortion(y, y_slewed, t, t_slewed, print_results=False, plot_results=False, title=''):
     # Eval Sum and average
    y_avg = np.mean(y, axis=0, keepdims=True)
    y_slewed_avg = np.mean(y_slewed, axis=0, keepdims=True)

    # Extrapolate data if not sampled equally to match data lengths
    if len(t) < len(t_slewed):
        interp_slew = interp1d(t_slewed, y_slewed_avg, kind='cubic', fill_value='extrapolate')
        y_slewed_avg = interp_slew(t)

    slew_error = y_slewed_avg - y_avg
    slew_error_rms = np.sqrt(np.mean(slew_error**2)) 
  
    # Alternative to deduct y_slewed_avg from ideal (analog) wave.
    # This will include all errors and not distincly slewing as above.
    
    if print_results:
        print(f'SUM and AVERAGE error: {str(slew_error_rms)}')   

    if plot_results:
        plt.figure()
        plt.plot(t, y_avg.squeeze(), '-o', label='y_avg')
        plt.plot(t, y_slewed_avg.squeeze(), '-o', label='y_slewed_avg')
        plt.plot(t, slew_error.squeeze(), '-o', label='y_error')
        if title != '':
            plt.title('Slew distortion ' + title)
        else:
            plt.title('Slew distortion')
        plt.legend()
        plt.grid()

    return slew_error, slew_error_rms

def eval_slew_rate(y, t, print_results=False, plot_results=False):
    # Calculate all dvdt
    dv = np.diff(y)
    dt = np.diff(t)
    dvdt = dv/dt
    dvdt_us = dvdt/1e-6
    dvdt_us_no_zero = dvdt_us[dvdt_us != 0]
    closest_to_zero = dvdt_us_no_zero[np.argmin(np.abs(dvdt_us_no_zero))]

    if print_results:
        print(f'Slew rate worst case: {str(closest_to_zero)}')

    # if plot_results:
    #     plt.figure()
    #     plt.plot(t, y_avg.squeeze(), label='y_avg')
    #     plt.plot(t, y_slewed_avg.squeeze(), label='y_slewed_avg')
    #     plt.plot(t, slew_error.squeeze(), label='y_error')
    #     plt.title('Slew distortion')
    #     plt.legend()

def main():
    """
    Test the methods.
    """
    Fs = 1.0e6  # sampling rate
    Ts = 1/Fs

    t = np.arange(0, 0.1, Ts)  # time vector
    Fx = 999
    x = 1.0*np.cos(2*np.pi*Fx*t)
    x = x + 0.5*x**2 + 0.25*x**3 + 0.125*x**4 + 0.0625*x**5
    x = x + 0.01*np.random.randn(t.size)

    R_FFT = FFT_SINAD(x, Fs, make_plot=True)
    R_TS = TS_SINAD(x, t)

    print("SINAD from FFT: {}\nSINAD from curve-fit: {}".format(R_FFT, R_TS))


if __name__ == "__main__":
    main()
