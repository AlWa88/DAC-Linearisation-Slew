
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MHOQ implementation with rate (step) limitation - MPC using Binary Variables
This script implements Model Predictive Control (MPC)-based linearization and performance enhancement 
of the Digital-to-Analog Converter (DAC). The optimal control problem accounts for system constraints, 
integral non-linearity (INL), and rate limitation (slewing). The optimization is formulated as Mixed Integer 
Programming (MIP) and solved using the Gurobi solver.

@author: Bikash Adhikari
@date: 20.02.2025 
@license: BSD 3-Clause
"""

import numpy as np
from scipy import linalg , signal
import sys
import random
import gurobipy as gp
from gurobipy import GRB
import tqdm



class MHOQ_RLIM_RM:
    """Moving Horizon Optimization Quantization (MHOQ) class with rate (step) limitation."""

    def __init__(self, Nb, Qstep, QMODEL, A, B, C, D):
        """
        Constructor for the Model Predictive Controller.
        :param Nb: Number of bits representing the DAC resolution
        :param Qstep: Quantizer step size / Least Significant Bit (LSB)
        :param QMODEL: Quantization model
        :param A, B, C, D: State-space matrices representing the reconstruction filter
        """
        self.Nb = Nb  # Number of bits
        self.Qstep = abs(Qstep)  # Ensure quantization step size is positive
        self.QMODEL = QMODEL  # Quantization model
        self.A = A  # State transition matrix
        self.B = B  # Input matrix
        self.C = C  # Output matrix
        self.D = D  # Feedthrough matrix

    def __get_scalar(self, val):
        if isinstance(val, np.ndarray):
            return val.item()  # safely extract scalar from 0-d or 1-element array
        return val  # already a scalar

    def state_prediction(self, st, con):
        """Predicts the next state based on the system dynamics.
        State evolution follows: x[k+1] = A * x[k] + B * u[k]

        :param st: Current state vector
        :param con: Control input at the current step
        :return: Predicted next state
        """
        return self.A @ st + self.B * con  # Compute next state

    def q_scaling(self, X):
        """Scales the input signal and quantization levels to a normalized range.
        This improves numerical precision in optimization.

        :param X: Signal or quantization levels to be scaled
        :return: Scaled values
        """
        # return np.floor(X.squeeze() / self.Qstep + 2**(self.Nb - 1))   # Normalize based on bit depth
        return X.squeeze() / self.Qstep + 2**(self.Nb - 1)

    def get_codes(self, N_PRED, Xcs, YQns, MLns, Step):

        """Computes optimal DAC codes using Mixed-Integer Optimization while minimizing switching frequency.
        
        :param N_PRED: Prediction horizon (number of future steps considered in optimization)
        :param Xcs: Reference input signal to be quantized
        :param YQns: Ideal quantization levels
        :param MLns: Measured quantization levels
        :param Step: Maximum allowable change (step) between consecutive quantization levels
        :return: Optimal DAC code sequence
        """
        # # Scale input signals for numerical stability
        Xcs = self.q_scaling(Xcs)  # Scale reference signal
        QL_I = self.q_scaling(YQns)  # Scale reference signal
        QL_M = self.q_scaling(MLns)  # Scale reference signal
        # QL_I = YQns.squeeze()  # Scale ideal quantization levels
        # QL_M = MLns  # Scale measured quantization levels

        C_Store = []  # Storage container for DAC codes
        len_MPC = Xcs.size - N_PRED  # Number of optimization iterations
        x_dim = self.A.shape[0]  # Dimension of the state vector
        e_step = []
        init_state = np.zeros((x_dim, 1))  # Initialize state vector to zero

        # Initialize previous control input based on first sample quantization
        u_kminus1_ind = int(np.floor(Xcs[0]  + 0.5))
        # u_kminus1_ind = np.ones(N_PRED) * u_kminus1_ind  # Extend to prediction horizon
        
        # MPC loop
        for j in tqdm.tqdm(range(len_MPC), desc='MHOQ_RLIM_RM'):
            env = gp.Env(empty=True)  # Initialize Gurobi environment
            env.setParam("OutputFlag", 0)  # Suppress solver logs
            env.start()
            m = gp.Model("MPC-INL-RL", env=env)  # Create optimization model

            # Reduced (Sub problem)
            # Constraint set depending on the step size 
            # idx = np.where(QL_I == u_kminus1_ind)[0]
            idx = np.abs(QL_I - u_kminus1_ind).argmin()
            e_step.append(abs(self.__get_scalar(u_kminus1_ind) - Xcs[j]))
            # idx = idx[0]
            # lb = max(idx - Step,0)
            # ub = min(idx + Step,2**self.Nb-1)+1
            lb = int(max(idx - Step - e_step[j], 0))
            ub = int(min(idx + Step + e_step[j], 2**self.Nb-1)) + 1

            YQns_Const = YQns[lb:ub]
            QL_I_Const = QL_I[lb:ub]
            QL_M_Const = QL_M[lb:ub]
            len_SP = len(QL_I_Const) 

            # Define decision variables
            u = m.addMVar((len_SP, N_PRED), vtype=GRB.BINARY, name="u")  # Control variables (binary choice)
            x = m.addMVar((x_dim * (N_PRED + 1), 1), vtype=GRB.CONTINUOUS,  lb = -GRB.INFINITY, ub = GRB.INFINITY, name = "x")  # State variables

            Obj = 0  # Initialize objective function (error minimization)
            m.addConstr(x[0:x_dim, :] == init_state)  # Set initial condition

           # Loop through prediction horizon to set constraints and objective
            for i in range(N_PRED):
                k = x_dim * i  # Index for state vector
                st = x[k:k+x_dim]  # Extract current state

                bin_con = QL_I_Const.reshape(1, -1) @ u[:, i].reshape(-1, 1)  # Convert binary input to actual control value
                con = bin_con - Xcs[j + i]  # Compute control deviation from reference signal

                e_t = self.C @ x[k:k+x_dim] + self.D * con  # Compute output error
                Obj += e_t * e_t  # Accumulate squared error in the objective function

                # State transition constraint
                f_value = self.A @ st + self.B * con  # Compute next state
                st_next = x[k + x_dim:k + 2 * x_dim]  # Extract next state variable
                m.addConstr(st_next == f_value)  # Enforce state transition constraint
                m.addConstr(gp.quicksum(u) == 1)  # Ensure only one control input is selected

                # # Define search bounds for control input
                # ub = min(int(u_kminus1_ind[i] + Step), 2**self.Nb - 1)
                # lb = max(int(u_kminus1_ind[i] - Step), 0)
                
                # U1 = u[lb:ub+1, i].reshape(-1, 1)  # Selected control input range
                # m.addConstr(gp.quicksum(U1) == 1)  # Ensure only one control input is selected
                
                # mask = np.ones(u[:, i].size, dtype=bool)
                # mask[np.arange(lb, ub+1)] = False
                # U2 = u[:, i][mask]
                # m.addConstr(U2 == 0)  # Enforce binary constraint

            m.update()
            m.setObjective(Obj, GRB.MINIMIZE)  # Set objective function

            # Gurobi setting for precision  
            m.Params.IntFeasTol = 1e-9
            m.Params.IntegralityFocus = 1
            m.optimize()  # Solve optimization problem

            values = np.array(m.getAttr("X", m.getVars()))  # Extract solution values
            u_val = values[:u.size].reshape(len_SP, N_PRED).astype(int)

            # Extract optimal DAC code
            opt_index = np.array([np.nonzero(u_val[:, i])[0][0] for i in range(N_PRED)])[0] 
            opt_code = lb + opt_index 
            C_Store.append(opt_code)

            # Select DAC output based on the quantization model
            match self.QMODEL:
                case 1:
                    U_opt = QL_I[opt_code] 
                case 2:
                    U_opt = QL_M[opt_code] 

            # Predict next state based on optimal control input
            con = U_opt - Xcs[j]
            init_state = self.state_prediction(init_state, con)  # Update state
            u_kminus1_ind =opt_code 

        return np.array(C_Store).reshape(1, -1)  # Return optimized DAC codes