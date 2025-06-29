#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common utility functions

@author: Arnfinn Aas Eielsen
@date: 04.04.2024
@license: BSD 3-Clause
"""

from enum import Enum, auto

class lm(Enum):  # linearisation method
    BASELINE = auto()  # baseline
    PHYSCAL = auto()  # Physical level Calibration
    DEM = auto()  # Dynamic Element Matching
    NSDCAL = auto()  # Noise shaping with Digital Calibration (INL model)
    SHPD = auto()  # Stochastic High-Pass Dithering
    PHFD = auto()  # Periodic High-Frequency Dithering
    MPC = auto()  # Model Predictive Control (with INL model)
    MHOQ = auto()  # Moving Horizon Optimal Quantiser (The same as MPC)
    ILC = auto()  # iterative learning control (with INL model, periodic signals)
    ILC_SIMP = auto()  # iterative learning control, basic implementation
    STEP = auto() # simple step respone
    MPC_RL_RM = auto() # MPC rate limiter (reduced model)
    MPC_RL = auto() # MPC rate limiter (full model)
    MPC_SL = auto() # MPC step limiter

    # def __init__(self, method):
    #     self.method = method

    # def __str__(self):
    #     match self.method:
    #         case lm.BASELINE:
    #             return 'BASELINE'
    #         case lm.PHYSCAL:
    #             return 'PHYSCAL'
    #         case lm.DEM:
    #             return 'DEM'
    #         case lm.NSDCAL:
    #             return 'NSDCAL'
    #         case lm.SHPD:
    #             return 'SHPD'
    #         case lm.PHFD:
    #             return 'PHFD'
    #         case lm.MPC | lm.MHOQ:
    #             return 'MHOQ'
    #         case lm.ILC:
    #             return 'ILC'
    #         case lm.ILC_SIMP:
    #             return 'ILC simple'
    #         case lm.STEP:
    #             return 'STEP'
    #         case lm.MPC_RL_RM:
    #             return 'MPC_RL_RM'
    #         case lm.MPC_RL:
    #             return 'MPC_RL'
    #         case lm.MPC_SL:
    #             return 'MPC_SL'
    #         case _:
    #             return '-'
            
class dm:  # DAC model
    STATIC = 1  # static model
    SPICE = 2  # spice model

    def __init__(self, model):
        self.model = model

    def __str__(self):
        match self.model:
            case dm.STATIC:
                return 'static'
            case dm.SPICE:
                return 'spice'
            case _:
                return '-'


def main():
    """
    Test
    """
    lmethod = lm(lm.BASELINE)


if __name__ == "__main__":
    main()
