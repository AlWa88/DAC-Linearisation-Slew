import subprocess
import tqdm
import numpy as np
from LM.lin_method_util import lm
from utils.quantiser_configurations import qs

a = np.arange(100,1000,100)
b = np.arange(1000,10000,1000)
c = np.arange(10000,100000+1000,1000)
qconfigs = [qs.w_4bit_NI_card, qs.w_6bit_NI_card, qs.w_8bit_NI_card, qs.w_10bit_NI_card, qs.w_12bit_NI_card, qs.w_14bit_NI_card, qs.w_16bit_NI_card]
# qconfigs = [qs.w_8bit_NI_card, qs.w_16bit_NI_card]
xref_freq = np.concatenate([a,b,c])
step = 1
with tqdm.tqdm(xref_freq, desc="Progressing run_me_wrapper") as pbar:
    for qconfig in qconfigs:
        for fs in pbar:
            subprocess.run([
                'python', 'run_me.py',
                '--TEST_CASE', '0',
                '--Xref_FREQ', str(fs),
                '--MPC_step_limit', str(step),
                '--METHOD_CHOICE', str(lm.NSDCAL.value),
                '--QConfig', str(qconfig.value)])