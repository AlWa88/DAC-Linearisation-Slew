#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MPC-Based Optimal Control for DAC Linearization -- Binary Variables

The goal is to improve the linearity of a Digital-to-Analog Converter (DAC) by formulating an optimal control 
problem that accounts for system constraints and non-idealities (INL). This problem is cast as a Mixed-Integer 
Programming (MIP) problem and solved using the Gurobi solver.

@author: Bikash Adhikari
@date: 22.02.2024
@license: BSD 3-Clause
"""

# Import necessary libraries
import numpy as np  # Used for numerical computations
from scipy import linalg, signal  # SciPy modules for linear algebra and signal processing
import sys
import random  # Standard Python module for random number generation
import gurobipy as gp  # Import Gurobi for solving the optimization problem
from gurobipy import GRB  # Import Gurobi constants
import tqdm  # For displaying a progress bar


class MPC_BIN:
    """
    Model Predictive Control (MPC) class for DAC linearization using Mixed-Integer Programming (MIP).
    """

    def __init__(self, Nb, Qstep, QMODEL, A, B, C, D):
        """
        Constructor for the MPC_BIN class.

        :param Nb: Number of bits in the DAC.
        :param Qstep: Quantizer step size (Least Significant Bit - LSB).
        :param QMODEL: Defines the quantization model (ideal or measured).
        :param A, B, C, D: State-space matrices representing the reconstruction filter.
        """
        self.Nb = Nb  # Number of bits of the DAC
        self.Qstep = abs(Qstep)  # Ensure the quantization step size is positive
        self.QMODEL = QMODEL  # Specifies whether we use ideal or measured quantization levels
        self.A = A  # State-space matrix A (system dynamics)
        self.B = B  # State-space matrix B (input effect)
        self.C = C  # State-space matrix C (output dynamics)
        self.D = D  # State-space matrix D (feedthrough)
        
    def state_prediction(self, st, con):
        """
        Predicts the next state using the system's state-space model:
            x[k+1] = A * x[k] + B * u[k]

        :param st: Current state vector.
        :param con: Control input.
        :return: Predicted next state.
        """
        x_iplus1 = self.A @ st + self.B * con  # Matrix multiplication for state update
        return x_iplus1

    def q_scaling(self, X):
        """
        Scales the signal and quantization levels to a normalized range.
        Scaling improves numerical precision when solving the optimization problem.

        :param X: Signal or quantization levels to be scaled.
        :return: Scaled values.
        """
        Xs = X.squeeze() / self.Qstep + 2**(self.Nb - 1)  # Normalization based on bit depth
        return Xs
    
    def get_codes(self, N_PRED, X, YQns, MLns ):
        """
        Computes the optimal control inputs to minimize DAC non-linearity errors 
        using Model Predictive Control (MPC).

        :param N_PRED: Prediction horizon (number of future steps considered).
        :param X: Reference signal (desired DAC output).
        :param YQns: Ideal quantization levels.
        :param MLns: Measured quantization levels.
        :return: Optimized control (codes corresponding to quantiser levels)
        """

        # Scale input signals for numerical stability
        Xcs = self.q_scaling(X)  # Scale reference signal
        QL_I = self.q_scaling(YQns)  # Scale ideal quantization levels
        QL_M = self.q_scaling(MLns)  # Scale measured quantization levels

        # Storage for computed codes
        C = []

        # MPC loop length (usually signal length - prediction horizon)
        len_MPC = Xcs.size - N_PRED

        # Dimension of the state vector, determined by system order
        x_dim =  int(self.A.shape[0]) 

        # Initialize system state to zero
        init_state = np.zeros(x_dim).reshape(-1,1)

        for j in tqdm.tqdm(range(len_MPC)):  # Iterate through signal samples
            
            # Initialize Gurobi optimization environment
            env = gp.Env(empty=True)
            env.setParam("OutputFlag",0) # Suppress solver logs
            env.start()
            m = gp.Model("MPC- INL", env = env)  # Create optimization model


            # Define decision variables:
            # - `u` represents binary control inputs (2^Nb choices per time step)
            # - `x` represents state variables in the prediction horizon
            u = m.addMVar((2**self.Nb, N_PRED), vtype=GRB.BINARY, name= "u")  # Binary control variables
            x = m.addMVar((x_dim*(N_PRED+1),1), vtype= GRB.CONTINUOUS, lb = -GRB.INFINITY, ub = GRB.INFINITY, name = "x")  #State variables

            # Initialize the objective function (minimization of error)
            Obj = 0 # Initialize

            # Set the initial state constraint
            m.addConstr(x[0:x_dim,:] == init_state, "Initial state")
            for i in range(N_PRED):
                k = x_dim * i
                st = x[k:k+x_dim]    # Current state

                # Compute control input using binary selection
                bin_con =  QL_I.reshape(1,-1) @ u[:,i].reshape(-1,1)  
                con = bin_con - Xcs[j+i] # Control error relative to reference

                # Objective function update (minimize squared error)
                e_t = self.C @ x[k:k+x_dim] + self.D * con
                Obj = Obj + e_t * e_t # Objective function udpate

                 # State update constraint (system dynamics)
                f_value = self.A @ st + self.B * con
                st_next = x[k+x_dim:k+2*x_dim]
                m.addConstr(st_next == f_value, "State constrait")

                # Binary constraint (ensure exactly one control value is selected)
                consi = gp.quicksum(u[:,i]) 
                m.addConstr(consi == 1)

            # Gurobi model update
            m.update()

            # Set optimization objective (minimize error)
            m.setObjective(Obj, GRB.MINIMIZE)

            # Solver precision settings
            m.Params.IntFeasTol = 1e-9 # Integer feasibility tolerance
            m.Params.IntegralityFocus = 1 # Focus on finding integer solutions

            # Solve the optimization problem
            m.optimize()

            if m.Status == GRB.OPTIMAL: # Check if an optimal solution was found
                # Extract variable values 
                allvars = m.getVars()
                values = m.getAttr("X",allvars)
                values = np.array(values)
            else:
                SystemExit("No optimal solution found.")

            # Extract binary decision variable values
            nr, nc = u.shape
            u_val = values[0:nr*nc]
            u_val = np.reshape(u_val, (2**self.Nb, N_PRED))
    
            # Decode the optimal control sequence
            C_MPC = []
            for i in range(N_PRED):
                c1 = np.nonzero(u_val[:,i])[0][0]
                c1 = int(c1)
                C_MPC.append(c1)
            C_MPC = np.array(C_MPC)
            C.append(C_MPC[0])

             # Determine output based on DAC model selection
            match self.QMODEL:
                case 1:
                    U_opt = QL_I[C_MPC[0]]  # Ideal DAC output
                case 2:
                    U_opt = QL_M[C_MPC[0]]  # Measured DAC output

            # Predict next state using chosen optimal control input 
            con = U_opt - Xcs[j]
            x0_new = self.state_prediction(init_state, con)

            # Update state for next iteration
            init_state = x0_new

        return np.array(C).reshape(1,-1)
