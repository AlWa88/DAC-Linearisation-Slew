#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate DAC output assuming a simple static non-linear model

@author: Arnfinn Eielsen
@date: 22.02.2024
@license: BSD 3-Clause
"""

import numpy as np
from scipy import signal
import tqdm

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

def slew_rate_exp(step_size):
    a, b, c = [-13.00864654,0.13569845,12.65228228]
    return (a * np.exp(b * -step_size) + c) * 1e6 # v/us to v/s

def slew_rate_poly(step_size):
    c = [-1.63207178e-05,9.72157077e-04,-2.12312520e-02,2.04396815e-01,-8.44501935e-01,2.23143672e+00,-1.28070145e-01]
    poly = np.poly1d(c)
    return poly(step_size) * 1e6 # v/us to v/s

def slew_rate_log(step_size):
    a, b = [1.94048773,4.54441087]
    return (a * np.log(step_size) + b) * 1e6 

def slew_rate_sig(step_size):
    L, x0, k, b = [12.22112677,4.84290779,0.46157889,-0.99759254]
    return (L / (1 + np.exp(-k * (step_size - x0))) + b) * 1e6

# def slew_rate_lin(step_size):
#     return (0.6138*step_size + 1.4346) * 1e6

def slew_rate_lin2(step_size):
    return 10*1e6 * abs(step_size)

def slew_rate_rc(voltage):
    V = 10  # Supply voltage in volts
    R = 0.07  # Resistance in ohms
    C = 0.0000051  # Capacitance in farads
    SR = 10.93
    I_max = C * SR*1e6 # Maximum current in ammpered given the maximum slew rate (v/s)

    # Time range from 0 to 5 seconds
    t = np.linspace(0, 3*1e-6, 5000)
    V_t = np.zeros_like(t)
    I_t = np.zeros_like(t)

    # Calculate voltage and current with current constraint
    for i in range(1, len(t)):
        dt = t[i] - t[i-1]
        I_t[i] = min((V - V_t[i-1]) / R, I_max)
        V_t[i] = V_t[i-1] + I_t[i] * dt / C

def slew_model(y, ts, SR, t, ts_scope, mode=3):
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
    Mode   
        1=linear, 2=rc circuit with current constraint

    """
    YS = np.copy(y)
    dt_dt = round(1/(ts_scope / ts))
    if dt_dt == 0: # if ts is sampled faster than ts_scope
        ts_scope = ts
        t_scope = t
        YS_scope = np.copy(YS)
    else:       
        YS_scope = np.array([
            np.concatenate(([row[0]], np.repeat(row[1:], dt_dt)))
            for row in YS
        ])
        # YS_scope = YS_scope[np.newaxis, :]  # Ensure shape is (1, N)
        t_scope = np.linspace(0, t[-1], YS_scope.shape[1])
    
    t_index = 1
    V_t_dt = YS_scope[:,0]
    
    # dt_dt = round(1/(ts_scope / ts))
    # YS_scope = np.array([
    #     np.concatenate(([row[0]], np.repeat(row[1:], dt_dt)))
    #     for row in YS
    # ])
    # # YS_scope = YS_scope[np.newaxis, :]  # Ensure shape is (1, N)
    # t_scope = np.linspace(0, t[-1], YS_scope.shape[1])
    # t_index = 1
    # V_t_dt = YS_scope[0,0]

    match mode:
        # Linear model
        case 1: 
            R = SR*1e6 # v/us to v/s
            F = -R # falling rate
            with tqdm.tqdm(range(1,YS_scope.shape[1]), desc='Slew limitation') as pbar:
                for i in pbar:
                    # V = YS_scope[:,i]
                    rates = (YS_scope[:,i]-YS_scope[:,i-1])/ts_scope

                    for j, rate in enumerate(rates):

                    # delta_t = t1 - t0
                    # rate = (u1 - u0)/delta_t

                    # if rate + 1e-8 >= R:
                    #     y = delta_t*R + u0
                    # elif rate -1e-8 <= F: 
                    #     y = delta_t*F + u0
                    # elif rate <= R or rate >= F:
                    #     y = u1


                    # step_size = (YS_scope[:,i]-YS_scope[:,i])
                    # R = slew_rate_lin2(abs(step_size))
                    # step_size = (YS[:,i]-YS[:,i-1])
                    # R = slew_rate_lin2(abs(step_size))
                    # R = 
                        # F = -R
                        if (rate > R):
                            V_t_dt = R * ts_scope  + YS_scope[j,i-1]
                        elif (rate < F):
                            V_t_dt = F * ts_scope + YS_scope[j,i-1]
                        else:
                            V_t_dt = YS_scope[j,i]
                            # pass # y=u, vector is already copied above
                        YS_scope[j,i] = V_t_dt

                    # I_t_dt = np.minimum((V - YS_scope[:,i-1]) / R, I_max)
                    # V_t_dt += I_t_dt * ts_scope / C
                    # YS_scope[:,i] = V_t_dt
                    if t_index < len(t) and np.isclose(t[t_index], t_scope[i], rtol=0, atol=ts_scope/10):
                        YS[:,t_index] = V_t_dt
                        t_index += 1
            
            # for i in range(1,YS.shape[1]):
            #     rate = (YS[0,i]-YS[0,i-1])/ts
            #     step_size = (YS[0,i]-YS[0,i-1])
            #     R = slew_rate_lin2(abs(step_size))
            #     F = -R
            #     if (rate > R):
            #         YS[0,i] = R * ts + YS[0,i-1]
            #     elif (rate < F):
            #         YS[0,i] = F * ts + YS[0,i-1]
            #     else:
            #         pass # y=u, vector is already copied above

            return YS, YS_scope, t_scope 
        
        # # RC circuit model with maximum current constraint
        # case 2:
        #     R, C = [7.51319378e-02,4.85891103e-06] # SR = 1.14097944e+01, V = 9.94317083e+00, parameters from curve fit
        #     I_max = C * SR*1e6 # Maximum current in ammpered given the maximum slew rate (v/s)
        #     # fs_dt = (1/1e9)*100 # oversampling factor for stability of model when running at large time steps (low sampling frequency)
        #     # dt_dt = round(ts/fs_dt) # oversample in between each time step ts with factor fs_dt
        #     # dt_dt = np.arange(0, ts, fs_dt) 
        #     dt_dt = np.linspace(0, ts, 1e6)
        #     fs_dt = dt_dt[1]
        #     ys_new = [YS[0,0]]
        #     for i in range(1,YS.shape[1]):
        #         V_t_dt = YS[0,i-1]
        #         V = YS[0,i]
        #         for j in range(dt_dt):
        #             I_t_dt = min((V - V_t_dt) / R, I_max)
        #             V_t_dt = V_t_dt + I_t_dt * fs_dt / C
        #             ys_new.append(V_t_dt)
        #         YS[0,i] = V_t_dt
        #     YS_new = np.matrix(ys_new)
        #     return YS
        
        case 3:
            # R, C = [1.40406391e-01, 1.00052625e-05]
            # R, C = [1.49704655e-01, 1.16510588e-05]
            # R, C = [1.63852110e-01, 6.96231079e-06] #
            R, C = [7.51319378e-02,4.85891103e-06] # SR = 1.14097944e+01, V = 9.94317083e+00, parameters from curve fit
            I_max = C * SR*1e6 # Maximum current in ammpered given the maximum slew rate (v/s)
            with tqdm.tqdm(range(1,YS_scope.shape[1]), desc='Slew limitation') as pbar:
                for i in pbar:
                    V = YS_scope[:,i]
                    I_t_dt = np.minimum((V - YS_scope[:,i-1]) / R, I_max)
                    V_t_dt += I_t_dt * ts_scope / C
                    YS_scope[:,i] = V_t_dt
                    if t_index < len(t) and np.isclose(t[t_index], t_scope[i], rtol=0, atol=ts_scope/10):
                        YS[:,t_index] = V_t_dt
                        t_index += 1
            return YS, YS_scope, t_scope 

def test_slew_model():
    import matplotlib.pyplot as plt
    from pathlib import Path
    
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

    # Generate step
    rng = 20
    nbits = 16
    y_step_smallest = rng / ((2**nbits)-1)
    ts = 1/1e6
    t = np.arange(0,.00001,ts*1)
    y = np.ones((1,len(t)))*10.0 #10.0
    y[0,0] = -10.0 #-10.0
    ts_scope = 1/1e9
    
    # Slewed model
    ys, ys_slewed, t_scope = slew_model(y, ts, 7, t, ts_scope, mode=1)

    # Find slew rates until smallest step size is reached
    ys_slewed_dv = np.diff(ys_slewed)
    sr_v_s = ys_slewed_dv/ts_scope
    sr_v_us = sr_v_s*1e-6
    _,idx = np.unique(ys_slewed_dv, return_index=True)
    ys_slewed_dv_unique = ys_slewed_dv[0,np.sort(idx)]
    sr_v_s_unique = ys_slewed_dv_unique/ts_scope
    sr_v_us_unique = sr_v_s_unique*1e-6
    ys_slewed_dv_filtered = ys_slewed_dv_unique[ys_slewed_dv_unique >=y_step_smallest]
    sr_v_s_filtered = ys_slewed_dv_filtered/ts_scope
    sr_v_us_filtered = sr_v_s_filtered*1e-6
    coeff = np.polyfit(ys_slewed_dv[0,:], sr_v_us[0,:], 1)
    print(coeff)
    m,b = coeff
    y_fit = m * ys_slewed_dv[0,:] + b

    # DAC bit resolution 4-16 bits
    dac_resolution = np.ones((5,2))
    dac_y = np.array((np.min(sr_v_us), np.max(sr_v_us)))
    for i, nbits in enumerate(np.arange(8,16+2,2)):
        dac_resolution[i,:] = dac_resolution[i,:]* (rng / ((2**nbits)-1))
        
    # Plot slewed data
    plt.figure()
    plt.plot(t,y[0,:],label='xref')
    plt.plot(t_scope,ys_slewed[0,:], label='slewed')
    plt.xlabel('Time [s]')
    plt.ylabel('Output [V]')
    plt.title('Slewed data')
    plt.legend()
    plt.grid()

    # Connecting the click event to the handler function for the first figure
    cid1 = plt.gcf().canvas.mpl_connect('button_press_event', onclick)

    # Plot slew rate given step size
    plt.figure()
    plt.plot(ys_slewed_dv[0,:], sr_v_us[0,:], '-o', label='sr_data')
    plt.plot(ys_slewed_dv[0,:], y_fit, label='linear fit')
    for data in dac_resolution:
        plt.plot(data, dac_y)
    plt.xlabel('dV [V]')
    plt.ylabel('SR [V/uS]')
    plt.title('Slew rate given step size')
    plt.legend()
    plt.grid()
    
    data = np.column_stack((sr_v_s_filtered, sr_v_us_filtered, ys_slewed_dv_filtered))
    filename = Path(f'data.csv')
    header = 'sr_v_s,sr_v_us,ys_slewed_dv_filtered' # if not filename.exists() else ''
    # data = np.array([[__get_timestamp_compact(), QConfig, lin, Fx, Fc] + ENOB + SINAD + [SLEW_ERROR]], dtype=object)
    format = ['%.10f', '%.10f', '%.10f']
    with open(filename, 'w') as f:
        np.savetxt(f, data, delimiter=',', fmt=format, header=header)

    plt.show()

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

def measurement_noise_range(Nb, Nb_measurement, Qstep, size):
    """
    Generate measurement noise range

    Parameters
    ----------
    Nb
        number of bits
    Nb_measurement
        number of bits of emulated measurement
    Qstep
        step size
    Size
        array size to generate
    Returns
    -------
    ML_err_rng
        Uniform random 
    """
    ML_err_rng = Qstep/pow(2, Nb_measurement - Nb) # (try to emulate 18-bit measurements (add 12 bit))
    return np.random.uniform(-ML_err_rng, ML_err_rng, size)

def reconstruction_filter(ty, y, Fc, Fs, Nf): # , print_results=True):
    # Filter the output using a reconstruction (output) filter
    y_avg = np.zeros(y.shape)
    with tqdm.tqdm(range(y_avg.shape[0]), desc='Reconstruction filter') as pbar:
        for i in pbar:
            y_ch = y[i,:].reshape(-1, 1)  # ensure the vector is a column vector
            match 1:
                case 1:
                    Wc = 2*np.pi*Fc
                    b, a = signal.butter(Nf, Wc, 'lowpass', analog=True)  # filter coefficients
                    Wlp = signal.lti(b, a)  # filter LTI system instance
                    y_avg_out = signal.lsim(Wlp, y_ch, ty, X0=None, interp=False)  # filter the output
                    y_avg[i] = y_avg_out[1]  # extract the filtered data; lsim returns (T, y, x) tuple, want output y
                case 2:
                    bd, ad = signal.butter(Nf, Fc, fs=Fs)
                    y_avg[i] = signal.lfilter(bd, ad, y_ch)
                case 3:
                    y_avg[i] = y_ch.squeeze()
    
    # if print_results:
    #     print(y_avg.shape)

    return y_avg

# test_slew _model()