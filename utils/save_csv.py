#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Util code for saving data to csv file.

@author: Alexander Waldejer
@date: 12.06.2025
@license: BSD 3-Clause
"""

from calendar import c
import datetime
from pathlib import Path
import numpy as np

def __get_timestamp():
    date_and_time = datetime.datetime.fromtimestamp(int(datetime.datetime.now(datetime.UTC).timestamp()), tz=datetime.UTC)
    return f'{date_and_time.strftime("%Y-%m-%d")}-{date_and_time.strftime("%H:%M:%S")}'

def __get_timestamp_compact():
    date_and_time = datetime.datetime.fromtimestamp(int(datetime.datetime.now(datetime.UTC).timestamp()), tz=datetime.UTC)
    return f'{date_and_time.strftime("%Y%m%d")}_{date_and_time.strftime("%H%M%S")}'

def save_enob_sinad_slew(QConfig:str, lin:str, Fx:int, Fc:int, ENOB:list, SINAD:list, SLEW_ERROR=None, file:str='ENOB_SINAD_SLEW', path:str='.\\results\\', append_file=True):
    filename = Path(f'{path}{file}.csv')
    header = f'Timestamp,QConfig,LM,Fx,Fc{',ENOB'*len(ENOB)}{',SINAD'*len(SINAD)},SLEW_ERROR' if not filename.exists() else ''
    data = np.array([[__get_timestamp_compact(), QConfig, lin, Fx, Fc] + ENOB + SINAD + [SLEW_ERROR]], dtype=object)
    format = ['%s', '%s', '%s', '%d', '%d'] + ['%.6f']*len(ENOB) + ['%.6f']*len(SINAD) + ['%.6f']
    if append_file:
        with open(filename, 'a') as f:
            np.savetxt(f, data, delimiter=',', fmt=format, header=header)
    else:
        with open(filename, 'w') as f:
            np.savetxt(f, data, delimiter=',', fmt=format, header=header)

def save_code(QConfig:str, lin:str, Fx:int, Fc:int, t, code, file:str='CODE', path:str='.\\results\\CODE\\'):       
    filename = Path(f'{path}{file}_{QConfig}_{lin}_{str(Fx)}_{__get_timestamp_compact()}.csv')
    header = f'Code @ Fx:{str(Fx)}Hz Fc:{str(Fc)}Hz' if not filename.exists() else ''
    format = ['%f', '%d']
    with open(filename, 'w') as f:
        np.savetxt(f, np.column_stack((t,code)), delimiter=',', fmt=format, header=header)

def save_slew_error():
    # date_and_time = datetime.datetime.fromtimestamp(int(datetime.datetime.now(datetime.UTC).timestamp()), tz=datetime.UTC)
    # time_string = f'{date_and_time.strftime("%Y-%m-%d")}-{date_and_time.strftime("%H:%M:%S")}'
    # t_save = t[:-1]
    # data_flat = C.astype(int).flatten()
    # # data_flat = data_flat[:-1]
    # combined = np.column_stack((t, data_flat))
    # filename = Path('.\\results\\CODE.csv')
    # np.savetxt(filename, combined, delimiter=',', fmt=['%f', '%d'], header='time,code', comments='') 
    # combined = np.column_stack((y_error))
    # filename = Path('.\\results\\Y_ERROR.csv')
    # np.savetxt(filename, combined, delimiter=',', fmt=['%.6f'], header='y_error', comments='') 
    pass