#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MPC-Based Optimal Control for DAC Linearization 

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


class MPC:
    """
    Model Predictive Control (MPC) class to optimize DAC linearization.
    """

    def __init__(self, Nb, Qstep, QMODEL, A, B, C, D):
        """
        Constructor for the Model Predictive Controller.

        :param Nb: Number of bits in DAC
        :param Qstep: Quantizer step size (Least Significant Bit, LSB)
        :param QMODEL: Quantization model type (Ideal vs Measured)
        :param A, B, C, D: State-space matrices defining the reconstruction filter
        """
        self.Nb = Nb
        self.Qstep = abs(Qstep)  # Ensure step size is positive
        self.QMODEL = QMODEL  # Model selection flag (Ideal vs Measured)
        self.A = A  # State-space matrix A
        self.B = B  # State-space matrix B
        self.C = C  # State-space matrix C
        self.D = D  # State-space matrix D
    
        
    def state_prediction(self, st, con):
        """
        Predicts the next state of the system given the current state and control input.
        The state evolution follows the equation:
        x[k+1] = A * x[k] + B * u[k]

        :param st: Current state vector
        :param con: Control input at the current step
        :return: Predicted state for the next step
        """
        x_iplus1 = self.A @ st + self.B * con  # Compute next state
        return x_iplus1

    
    def q_scaling(self, X): 
        """
        Scales the input signal and quantization levels to a normalized range.
        Scaling improves numerical precision in optimization by avoiding issues with large/small values.

        :param X: Input signal or quantization levels
        :return: Scaled signal
        """
        Xs = X.squeeze() / self.Qstep + 2**(self.Nb - 1)  # Normalize signal
        return Xs

    
    def get_codes(self, N_PRED, Xcs, YQns, MLns):
        """
        Computes the optimal DAC codes using Model Predictive Control (MPC).
        The optimization ensures that the DAC output follows the desired signal as closely as possible.

        :param N_PRED: Prediction horizon (number of future steps considered in MPC)
        :param Xcs: Reference input signal to be quantized
        :param YQns: Ideal quantization levels
        :param MLns: Measured quantization levels
        :return: Optimal DAC code sequence
        """

        # Scale the reference signal for the quantizer
        X = self.q_scaling(Xcs)  # Normalize the input signal

        # Choose quantization levels based on the selected model (Ideal vs Measured)
        match self.QMODEL:
            case 1:
                QLS = self.q_scaling(YQns.reshape(1, -1)).squeeze()  # Ideal quantization levels
            case 2:
                QLS = self.q_scaling(MLns.reshape(1, -1)).squeeze()  # Measured quantization levels

        # Storage container for DAC codes
        C = []

        # Define loop length for MPC optimization
        len_MPC = X.size - N_PRED  # Number of iterations to perform

        # Determine the dimension of the state vector
        x_dim = int(self.A.shape[0])  # The number of state variables

        # Initialize state to zero (assumes no prior knowledge of initial conditions)
        init_state = np.zeros(x_dim).reshape(-1, 1)

        # Start MPC loop to optimize DAC codes
        for j in tqdm.tqdm(range(len_MPC)):  # Iterate over all input samples
            
            # Initialize the Gurobi optimization environment
            env = gp.Env(empty=True)
            env.setParam("OutputFlag", 0)  # Disable solver logs
            env.start()
            m = gp.Model("MPC- INL", env=env)  # Create a Gurobi model instance

            # Define decision variables for optimization
            u = m.addMVar(N_PRED, vtype=GRB.INTEGER, name="u", lb=0, ub=2**self.Nb - 1)  # Discrete control input
            x = m.addMVar((x_dim * (N_PRED + 1), 1), vtype=GRB.CONTINUOUS, 
                          lb=-GRB.INFINITY, ub=GRB.INFINITY, name="x")  # State trajectory

            # Initialize the objective function (error minimization)
            Obj = 0

            # Apply initial condition constraint
            m.addConstr(x[0:x_dim, :] == init_state)  # Set the initial state
            
            # Loop through the prediction horizon to set up constraints and objective function
            for i in range(N_PRED):
                k = x_dim * i  # Compute index for state vector
                st = x[k:k + x_dim]  # Extract current state
                con = u[i] - X[j + i]  # Compute control deviation from reference signal

                # Compute the error between desired and actual output
                e_t = self.C @ x[k:k + x_dim] + self.D * con
                Obj += e_t * e_t  # Accumulate squared error in the objective function

                # Update system dynamics constraints
                f_value = self.A @ st + self.B * con  # Compute next state
                st_next = x[k + x_dim:k + 2 * x_dim]  # Extract next state variable
                m.addConstr(st_next == f_value)  # Enforce state transition constraint

            # Update the Gurobi model
            m.update()

            # Set the optimization objective (minimize tracking error)
            m.setObjective(Obj, GRB.MINIMIZE)

            # Configure solver parameters for high precision
            m.Params.IntFeasTol = 1e-9  # Set integer feasibility tolerance
            m.Params.IntegralityFocus = 1  # Prioritize finding integer solutions

            # Solve the optimization problem
            m.optimize()

            # Extract optimal solution from solver
            allvars = m.getVars()
            values = m.getAttr("X", allvars)
            values = np.array(values)

            # Extract the optimal DAC code sequence (first N_PRED elements of "u")
            C_MPC = values[:N_PRED].astype(int)  # Convert to integer

            # Store only the first code from the prediction sequence
            C.append(C_MPC[0])

            # Get the DAC level based on the selected model (ideal or measured)
            U_opt = QLS[C_MPC[0]]

            # Predict next state based on optimal control input
            con = U_opt - X[j]
            x0_new = self.state_prediction(init_state, con)

            # Update initial state for the next iteration
            init_state = x0_new

        # Return the final computed DAC code sequence as a 2D array
        return np.array(C).reshape(1, -1)
