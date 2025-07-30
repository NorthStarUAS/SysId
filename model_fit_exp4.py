#!/usr/bin/env python3

"""build_full_model

Attempt to use a DMD-esque approach to fit a state transition matrix
that maps previous state to next state, thereby modeling/simulating
flight that closely approximates the original real aircraft.

Author: Curtis L. Olson, University of Minnesota, Dept of Aerospace
Engineering and Mechanics, UAV Lab.

"""

import argparse
import dask.array as da         # dnf install python3-dask+array / pip install dask
from matplotlib import pyplot as plt
import numpy as np

from lib.constants import kt2mps
from lib.state_mgr import StateManager
from lib.system_id import SystemIdentification
from lib.traindata import TrainData

# command line arguments
parser = argparse.ArgumentParser(description="build full model")
parser.add_argument("flight", metavar='flight_data_log', nargs='+', help="flight data log(s)")
parser.add_argument("--write", required=True, help="write model file name")
parser.add_argument("--vehicle", default="wing", choices=["wing", "quad"], help="vehicle type represented by data file")
parser.add_argument("--invert-elevator", action='store_true', help="invert direction of elevator")
parser.add_argument("--invert-rudder", action='store_true', help="invert direction of rudder")
args = parser.parse_args()

# question 1: seem to get a better flaps up fit to airspeed (vs. qbar) but fails to converge for 50% flaps
# qbar only converges for both conditions
# question 2: would it be useful to have a gamma (flight path angle) parameter (may help asi)

# flight controls
inceptor_terms = [
    "aileron",
    "elevator",
    "rudder",
    "throttle",
]

# sensors (directly sensed, or directly converted)
inertial_terms = [
    "one",
    "p", "q", "r",        # imu (body) rates
    "dp", "dq", "dr",
    "p*qbar", "q*qbar", "r*qbar",        # imu (body) rates
    "q/qbar",  # test related to az?
    "p*vc_mps", "q*vc_mps", "r*vc_mps",        # imu (body) rates
    "ax",                 # thrust - drag
    "ay",                 # side force
    "ay^2", "ay*vc_mps", "ay*qbar",
    "az",                 # lift
    "ay/qbar", "az/qbar",
    "az/vc_mps",          # related to q
    "bgx", "bgy", "bgz",  # gravity rotated into body frame
    "abs(ay)", "abs(bgy)",
    "q_term1",            # pitch bias in level turn
    # "ax_1", "ax_2", "ax_3", "ax_4",
    # "ay_1", "ay_2", "ay_3", "ay_4",
    # "az_1", "az_2", "az_3", "az_4",
    # "p_1", "p_2", "p_3", "p_4",
    # "q_1", "q_2", "q_3", "q_4",
    # "r_1", "r_2", "r_3", "r_4",
]

airdata_terms = [
    "vc_mps",
    # "alpha_dot",
    "alpha_deg",          # angle of attack
    "beta_deg",           # side slip angle
    "alpha_deg*qbar", "alpha_deg*vc_mps",
    "beta_deg*qbar", "beta_deg*vc_mps",
    "qbar",
    "1/vc_mps",
    "1/qbar",
    # "alpha_dot_term2",
    # "sin(alpha_deg)*qbar", "sin(alpha_deg)*qbar_1",
    # "sin(beta_deg)*qbar", "sin(beta_deg)*qbar_1",
    # "qbar/cos(beta_deg)",
]

inceptor_airdata_terms = [
    "aileron*qbar", "aileron*vc_mps",   # "aileron*qbar_1",
    "abs(aileron)*qbar",
    "elevator*qbar", "elevator*vc_mps", # "elevator*qbar_1", "elevator*qbar_2", "elevator*qbar_3",
    "rudder*qbar", "rudder*vc_mps",     # "rudder*qbar_1", "rudder*qbar_2", "rudder*qbar_3",
    "abs(rudder)*qbar",
    "throttle/vc_mps", "throttle/qbar", "throttle*qbar"
]

inertial_airdata_terms = [
    "Cl",
    # "alpha_dot_term3",
]

# deterministic output states (do not include their own value in future estimates)
output_states = [
    "aileron*qbar",
    # "elevator*qbar",
    # "rudder*qbar",
    # "q",
    # "alpha_deg",
    "beta_deg",
]

# non-deterministic output states (may roll their current value into the next estimate)
output_states_2 = [
    "vc_mps",
    "p", "q", "r",
    "ax", "ay", "az",
]

# bins of unique flight conditions
conditions = [
    { "flaps": 0 },
    { "flaps": 0.5 },
    { "flaps": 1.0 },
]

state_mgr = StateManager(args.vehicle)
train_states = inceptor_terms + inceptor_airdata_terms + inertial_terms + airdata_terms
state_mgr.set_state_names(inceptor_terms, inertial_terms + airdata_terms, output_states)

# previous state propagation
propagate = []
for i, s in enumerate(train_states):
    if len(s) >= 3 and s[-2] == "_":
        print("evaluating:", s)
        n = int(s[-1])
        root = s[:-2]
        if n == 1:
            if root in train_states:
                src = train_states.index(root)
            else:
                print("ERROR: requested state history without finding the current state:", s, "->", root)
                quit()
        else:
            newer = root + "_%d" % (n-1)
            if newer in train_states:
                src = train_states.index(newer)
            else:
                print("ERROR: requested state history without finding the current state:", s, "->", newer)
                quit()
        dst = i
        propagate.append( [src, dst] )
print("Previous state propagation:", propagate)

# state_mgr.set_is_flying_thresholds(15*kt2mps, 10*kt2mps) # bob ross
# state_mgr.set_is_flying_thresholds(75*kt2mps, 65*kt2mps) # sr22
state_mgr.set_is_flying_thresholds(10*kt2mps, 15*kt2mps) # skywalker

train_data = TrainData()
train_data.load_flightdata(args.flight, args.vehicle, args.invert_elevator, args.invert_rudder, state_mgr, conditions, train_states)

print("train_data.cond_list[0].shape:", train_data.cond_list[0].shape)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(526889,527132), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(526406,526650), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(520869,521115), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(520223,520477), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(519821,520066), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(519262,519629), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(518383,518623), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(517968,518217), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(484370,485507), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(476842,477080), axis=1)
# train_data.cond_list[0] = np.delete(train_data.cond_list[0], slice(310612,312500), axis=1)

print("Conditions report:")
for i, cond in enumerate(conditions):
    print(i, cond)
    if len(train_data.cond_list[i]):
        print("  Number of states:", len(train_data.cond_list[i][0]))
        print("  Input state vectors:", len(train_data.cond_list[i]))

# signal smoothing experiment
from scipy import signal
def do_filter(traindata, dt):
    print("filter...", dt)
    cutoff_freq = 3
    b, a = signal.butter(4, cutoff_freq, 'low', fs=(1/dt), output='sos', analog=False)
    print(b,a)
    for i in range(len(traindata)):
        print(i)
        x = traindata[i,:]
        print(x.shape)
        # print("any nan's?:", np.isnan(x).any())
        # print("any inf's?:", np.isinf(x).any())
        # need to use filtfilt here to avoid phase loss
        # filt = signal.filtfilt(b, a, x, method="gust")
        filt = signal.sosfilt((b, a), x)
        traindata[i,:] = filt
        print(filt)

# find/filter not-useful interpolated sections
from scipy.ndimage import gaussian_filter1d
for i, cond in enumerate(conditions):
    print(i, "len:", len(train_data.cond_list[i]))
    if not len(train_data.cond_list[i]):
        continue
    ax = train_data.cond_list[i][train_states.index("ax")]
    ay = train_data.cond_list[i][train_states.index("ay")]
    az = train_data.cond_list[i][train_states.index("az")]
    accel = np.sqrt( ax*ax + ay*ay + az*az )

    # cutoff_freq = 0.05
    # b, a = signal.butter(4, cutoff_freq, analog=False)
    # print(b,a)
    # filt = signal.filtfilt(b, a, accel)
    filt = gaussian_filter1d(accel, 2)
    print("accel shape:", accel.shape)
    print("filt shape:", filt.shape)
    print("filt:", filt)
    diff = accel-filt
    # diff = diff[np.abs(diff)<0.2]
    # plt.figure()
    # plt.plot(accel, label="cond %d: accels" % i)
    # plt.plot(filt, label="cond %d: accels (filt)" % i)
    # plt.plot(diff, label="cond %d: diff" % i)
    print("finding segments...")
    segments = []
    thresh = 0.2
    start = 0
    while start < len(diff):
        end = start
        while end < len(diff) and abs(diff[end]) < thresh:
            end += 1
        if end - start > 25:
            # 0.5 sec
            print("adding segment:", [start-5, end+5])
            segments.append([start-5, end+5])
            plt.axvspan(start-5, end+5, alpha=0.5, color='red')
        start = end + 1
    # plt.legend()
    # plt.show()

    # now delete those segments!
    for segment in reversed(segments):
        train_data.cond_list[i] = np.delete(train_data.cond_list[i], slice(segment[0],segment[1]), axis=1)

def solve(traindata, includes_idx, solutions_idx):
    srcdata = traindata[includes_idx,:]
    soldata = traindata[solutions_idx,:]
    states = len(traindata[0])

    X = np.array(srcdata[:,:-1])
    Y = np.array(soldata[:,1:])
    print("X:", X.shape)
    print("Y:", Y.shape)
    print("X:\n", np.array(X))
    print("Y:\n", np.array(Y))

    if False:
        # knock out the noise around zero in the solution space
        max = np.max(Y)
        min = np.min(Y)
        mean = np.mean(Y)
        diff = max - min
        cutoff = max * 0.25
        a = np.abs(Y-mean)>=cutoff
        a = np.squeeze(np.asarray(a))
        print(a.shape, a)

        X = X[:,a]
        Y = Y[:,a]
        print("X1:", X.shape)
        print("Y1:", Y.shape)
        print("X1:\n", np.array(X))
        print("Y1:\n", np.array(Y))

    # for x in range(X.shape[0]):
    #     plt.figure()
    #     plt.plot(traindata[train_states.index(x)], label=train_states[train_states.index(x)])
    #     plt.legend()

    #     plt.figure()
    #     plt.plot(traindata[train_states.index(output_states[0])], traindata[train_states.index(x)], ',', label=train_states[train_states.index(x)])
    #     plt.legend()

    # for x in output_states:
    #     plt.figure()
    #     plt.plot(traindata[train_states.index(x)], label=train_states[train_states.index(x)])
    #     plt.legend()

    # Y = A * X, solve for A
    #
    # A is a matrix that projects (predicts) all the next states
    # given all the previous states (in a least squares best fit
    # sense)
    #
    # X isn't nxn and doesn't have a direct inverse, so first
    # perform an svd:
    #
    # Y = A * U * D * V.T

    # print("dask svd...")
    daX = da.from_array(X, chunks=(X.shape[0], 10000)).persist()
    u, s, vh = da.linalg.svd(daX)

    if False:
        # debug and sanity check
        print("u:\n", u.shape, u)
        print("s:\n", s.shape, s)
        print("vh:\n", vh.shape, vh)
        Xr = (u * s) @ vh[:states, :]
        print( "dask svd close?", np.allclose(X, Xr.compute()) )

    # after algebraic manipulation
    #
    # A = Y * V * D.inv() * U.T

    v = vh.T
    # print("s inv:", (1/s).compute() )

    A = (Y @ (v[:,:states] * (1/s)) @ u.T).compute()
    print("A rank:", np.linalg.matrix_rank(A))
    print("A:\n", A.shape, A)

    return A

def analyze(A, traindata, train_states, output_states):
    stds = []
    for i in range(len(train_states)):
        stds.append(np.std(traindata[i,:]))

    # output_index_list = state_mgr.get_state_index( state_mgr.output_states )
    # states = len(traindata[0])
    # params = self.parameters

    # report leading contributions towards computing each output state
    for i in range(len(output_states)):
        #print(self.state_names[i])
        row = A[i,:]
        energy = []
        for j in range(len(train_states)):
            # e = row[j] * (abs(params[j]["median"]) + 0.5 * params[j]["std"]) * np.sign(params[j]["median"])
            e = row[j] * stds[j]
            # e = row[j] * params[j]["median"]
            # e = row[j] * (params[j]["max"] - params[j]["min"]) # probably no ...
            energy.append(e)
        idx = np.argsort(-np.abs(energy))
        total = np.sum(np.abs(energy))
        # output_idx = output_index_list[i]
        contributors = output_states[i] + " = "
        formula = output_states[i] + " = "
        first = True
        for j in idx:
            perc = 100 * energy[j] / total
            if abs(perc) < 0.01:
                continue
            if first:
                first = False
            else:
                if perc >= 0:
                    contributors += " + "
                else:
                    contributors += " - "
            if row[j] < 0:
                formula += " - "
            else:
                formula += " + "
            contributors += train_states[j] + " %.1f%%" % abs(perc)
            formula += "%.3f" % abs(row[j]) + "*" + train_states[j]
        print(contributors)
        print(formula)

def simulate(traindata, includes_idx, solutions_idx, A):
    # make a copy because we are going to roll our state estimates through the
    # data matrix and make a mess (or a piece of artwork!) out of it.
    data = traindata.copy()

    # this gets a little funky because we will be using numpy implied indexing below.
    indirect_idx = []
    for i in solutions_idx:
        if i in includes_idx:
            indirect_idx.append( includes_idx.index(i) )

    if False: # we don't need this
        # more craziness ... the propagate (state history) mapping is relative to
        # the full traindata so we need to indirectly index those as well
        local_prop = []
        for [src, dst] in propagate:
            if src in includes_idx and dst in includes_idx:
                local_prop.append( [includes_idx.index(src), includes_idx.index(dst)] )

    def shuffle_down(j):
        if j < data.shape[1] - 1:
            for [src, dst] in reversed(propagate):
                data[dst,j+1] = data[src,j]

    est = []
    next = np.zeros(len(indirect_idx))
    data[solutions_idx,i] = next
    for i in range(data.shape[1]):
        # print("i:", i)
        # print("includes_idx:", includes_idx)
        # print("solutions_idx:", solutions_idx)
        v = data[includes_idx,i]
        # print(v.shape, v)
        if len(indirect_idx):
            v[indirect_idx] = next
        next = A @ v
        shuffle_down(i)
        if i < data.shape[1] - 1:
            data[solutions_idx,i+1] = next
        est.append(next)
    return np.array(est).T

def rms(y):
    # return np.sqrt(np.mean(y**2))
    return np.std(y)

def mass_solution_4(traindata, train_states, output_states, self_reference=False):
    outputs_idx = []
    for s in output_states:
        outputs_idx.append(train_states.index(s))

    inputs_idx = []
    for i in range(len(train_states)):
        if not self_reference:
            if i in outputs_idx:
                continue
        inputs_idx.append(i)

    A = solve(traindata, inputs_idx, outputs_idx)

    # direct solution with all current states known, how well does our fit estimate the next state?
    direct_est = A @ traindata[inputs_idx,:]
    direct_error = traindata[outputs_idx,1:] - direct_est[:,:-1]

    sim_est = simulate(traindata,inputs_idx, outputs_idx, A)
    sim_error = traindata[outputs_idx,1:] - sim_est[:,:-1]

    analyze(A, traindata, train_states, output_states)

    for i in range(len(output_states)):
        print("rms vs std:", rms(direct_error[i,:]), np.std(direct_error[i,:]))
        print("ERROR Direct:", output_states[i], rms(direct_error[i,:]), "%.3f%%" % (100 * rms(direct_error[i,:]) / rms(direct_est[i,:]) ))
        print("ERROR Sim:", output_states[i], rms(sim_error[i,:]), "%.3f%%" % (100 * rms(sim_error[i,:]) / rms(sim_est[i,:]) ))

        fig, axs = plt.subplots(2, sharex=True)
        fig.suptitle("Estimate for: " + output_states[i])
        axs[0].plot(traindata[outputs_idx[i],1:].T, label="original signal")
        axs[0].plot(direct_est[i,:-1].T, label="fit signal")
        axs[0].plot(sim_est[i,:-1].T, label="sim signal")
        axs[0].legend()
        axs[1].plot(direct_error[i,:].T, label="fit error")
        axs[1].plot(sim_error[i,:].T, label="sim error")
        axs[1].legend()
    plt.show()

def parameter_find_5(traindata, train_states, y_state, include_states, exclude_states, self_reference=False):

    include_idx = []
    output_idx = train_states.index(y_state)
    evalout_idx = [output_idx]

    # remain_states = train_states - exclude_states
    remain_states = [x for x in train_states if x not in exclude_states]

    for x in include_states:
        include_idx.append(train_states.index(x))
        if x in remain_states:
            remain_states.remove(x)

    if not self_reference:
        # ensure none of the output state history is included if we don't self reference
        if y_state in remain_states:
            remain_states.remove(y_state)
        for i in range(1, 5):
            os_prev = y_state + "_%d" % i
            if os_prev in remain_states:
                remain_states.remove(os_prev)
    else:
        # ensure /all/ of the output state history is included if we self reference
        include_idx.append(train_states.index(y_state))
        remain_states.remove(y_state)
        for i in range(1, 5):
            os_prev = y_state + "_%d" % i
            if os_prev in remain_states:
                # print(os_prev, traindata[train_states.index(os_prev),:])
                include_idx.append(train_states.index(os_prev))
                remain_states.remove(os_prev)

    # min_rms = np.std(traindata[output_idx,:])
    min_rms = None

    while len(remain_states):
        for rs in remain_states:
            print("evaluating:", rs)
            r_idx = train_states.index(rs)
            evalin_idx = include_idx + [r_idx]

            A = solve(traindata, evalin_idx, evalout_idx)

            # direct solution with all current states known, how well does our fit estimate the next state?
            direct_est = A @ traindata[evalin_idx,:]
            # print("direct_est:", direct_est.shape, direct_est)
            direct_error = traindata[output_idx,1:] - direct_est[:,:-1]
            # print("direct_error:", direct_error.shape, direct_error)
            direct_rms = np.std(direct_error)
            print("direct_rms:", direct_rms)
            if min_rms is None or direct_rms < min_rms:
                min_A = A
                min_rms = direct_rms
                min_idx = r_idx
                min_est = direct_est
                min_err = direct_error
                min_evalin_idx = evalin_idx

            print("ERROR Direct:", y_state, "->", rs, rms(direct_error), "%.3f%%" % (100 * rms(direct_error) / rms(traindata[output_idx,1:])))
            # print("ERROR Sim:", output_states[i], rms(sim_error[i,:]), "%.3f%%" % (100 * rms(sim_error[i,:]) / rms(sim_est[i,:]) ))

        print(rms(min_err), rms(traindata[output_idx,1:]))
        print("Best next parameter:", train_states[min_idx], "rms val: %.05f" % min_rms,
                "error = %.3f%%" % (100 * rms(min_err) / rms(traindata[output_idx,1:])))
        include_idx.append(min_idx)
        remain_states.remove(train_states[min_idx])

        if self_reference:
            sim_est = simulate(traindata, min_evalin_idx, evalout_idx, min_A)
            sim_error = traindata[output_idx,1:] - sim_est[:,:-1]

        terms = ""
        for i, idx in enumerate(min_evalin_idx):
            print(str(min_A[0,i]))
            terms += "%.4f*" % min_A[0,i] + train_states[idx] + ", "
        print(y_state, "=", terms)

        fig, axs = plt.subplots(2, sharex=True)
        fig.suptitle("Estimate for: " + y_state + " = " + terms)
        if self_reference:
            axs[0].plot(sim_est[:,:-1].T, label="sim signal")
        else:
            axs[0].plot(min_est[:,:-1].T, label="fit signal")
        axs[0].plot(traindata[output_idx,1:].T, label="original signal")
        axs[0].legend()
        if self_reference:
            axs[1].plot(sim_error[0,:].T, label="sim error")
            y_mean = np.mean(sim_error[0,:])
            y_std = np.std(sim_error[0,:])
        else:
            axs[1].plot(min_err.T, label="fit error")
            y_mean = np.mean(min_err)
            y_std = np.std(min_err)
        print("  mean: %.4f" % y_mean, "std: %.4f" % y_std)
        # print(len(min_est[:,:-1].T))
        axs[1].hlines(y=y_mean-2*y_std, xmin=0, xmax=len(min_est[:,:-1].T), colors='green', linestyles='--')
        axs[1].hlines(y=y_mean+2*y_std, xmin=0, xmax=len(min_est[:,:-1].T), colors='green', linestyles='--', label="2*stddev")
        axs[1].legend()
        plt.show()

def parameter_fit_1(traindata, train_states, input_states, output_states, self_reference=False):

    n = len(output_states)

    input_idx = []
    output_idx = []

    # for i in range(len(train_states)):
    #     plt.figure()
    #     plt.plot(traindata[i], label=train_states[i])
    #     plt.legend()
    # plt.show()

    for x in input_states:
        print("input_state:", x)
        input_idx.append(train_states.index(x))
        plt.figure()
        plt.plot(traindata[train_states.index(x)], label=train_states[train_states.index(x)])
        plt.legend()

        plt.figure()
        plt.plot(traindata[train_states.index(output_states[0])], traindata[train_states.index(x)], ',', label=train_states[train_states.index(x)])
        plt.legend()

    for x in output_states:
        output_idx.append(train_states.index(x))
        plt.figure()
        plt.plot(traindata[train_states.index(x)], label=train_states[train_states.index(x)])
        plt.legend()

    A = solve(traindata, input_idx, output_idx)

    # direct solution with all current states known, how well does our fit estimate the next state?
    est = A @ traindata[input_idx,:]

    print("A:\n", A[:n,:n].tolist())
    print("A-1:\n", np.linalg.inv(A[:n,:n]).tolist())
    print("B:\n", A[:n,n:].tolist())

    # print("est:", est.shape, direct_est)
    for i in range(n):
        idx = output_idx[i]
        error = traindata[idx,1:] - est[i,:-1]
        # print("direct_error:", direct_error.shape, direct_error)
        # rms(error) = np.std(error)
        rms_perc = 100 * rms(error) / rms(traindata[idx,1:])
        print(output_states[i], "rms: %.4f" % rms(error), "%.2f%%" % rms_perc)

        terms = ""
        first = True
        for j, idx in enumerate(input_idx):
            if first:
                terms += "%.4f*" % A[i,j] + train_states[idx]
                first = False
            else:
                if A[i,j] < 0:
                    terms += " - %.4f*" % abs(A[i,j]) + train_states[idx]
                else:
                    terms += " + %.4f*" % A[i,j] + train_states[idx]
        print(output_states[i], "=", terms)

        fig, axs = plt.subplots(2, sharex=True)
        fig.suptitle("Estimate for: " + output_states[i] + " = " + terms)
        axs[0].plot(est[i,:-1].T, label="fit signal")
        axs[0].plot(traindata[output_idx[i],1:].T, label="original signal")
        axs[0].legend()
        axs[1].plot(error.T, label="fit error")
        y_mean = np.mean(error)
        y_std = np.std(error)
        print("  mean: %.4f" % y_mean, "std: %.4f" % y_std)
        # print(len(min_est[:,:-1].T))
        axs[1].hlines(y=y_mean-2*y_std, xmin=0, xmax=len(est[i,:-1].T), colors='green', linestyles='--')
        axs[1].hlines(y=y_mean+2*y_std, xmin=0, xmax=len(est[i,:-1].T), colors='green', linestyles='--', label="2*stddev")
        axs[1].legend()

    plt.show()

# evaluate each condition
for i, cond in enumerate(conditions):
    print(i, cond)
    traindata = train_data.cond_list[i]
    dt = train_data.dt

    if True:
        print("test pearson correlation coefficients:")
        print(traindata)
        corr = np.corrcoef(traindata)
        print("corr:\n", corr)

    if False:
        do_filter(traindata, dt)

    # sysid = SystemIdentification(args.vehicle)
    # train_data.cond_list[i]["sysid"] = sysid

    if False and False:
        mass_solution_4(traindata, train_states, output_states, self_reference=True)

    if False:
        # Parameter predictionive correlation: these are the things we want to
        # control, this will find the most important "predictive" correlations,
        # hopefully some external input (inceptor, control surface, etc.)
        # parameters show up because those would be the external influences on
        # the system that the control laws would ultimate manipulate to achieve
        # the desired result.
        #
        # This section is informative to help understand the dominant
        # correlations in the system.
        #
        # Note: use "engineering judgement" to determine which states to include
        # (seed) or exclude to test a fit with paramters you think should or
        # shouldn't be included.  Or leave these blank to let the system find
        # the best fit for you.  There may be correlations (between lateral and
        # longitudinal axes) that we expressly want to avoid building into the
        # flight control laws.
        #
        # Also we can specify if the estimation should be self referencing
        # (incremental.)  A self referencing system can be a better fit, but is
        # also non-deterministic.

        # Notes: include terms in a way that acknowledges rudder/aileron,
        # roll/yaw rates, and beta are coupled, but pitch is independent(-ish)
        #
        # ax, az, bgx, and bgz are longitudinal terms so we probably don't want
        # them included in our lateral controller, even if there is a
        # clear correlation in the flight data.

        # y_state = "az"
        # include_states = ["one"]
        # exclude_states = []

        # enable these one at a time (decide if we are building the controller around yaw rate or beta_deg)

        include_states = ["one"]

        # note there exist dynamic terms which we are ignoring

        # y_state = "p"                                                      # roll rate
        # include_states += ["aileron*qbar", "elevator*qbar", "rudder*qbar"] # control terms
        # # include_states += ["alpha_deg*qbar", "beta_deg*qbar"]              # stability terms
        # include_states += ["az/qbar", "ay/qbar"]              # proxy stability terms
        # exclude_states = ["p", "p*vc_mps", "p*qbar", "rudder*vc_mps"]

        # y_state = "q"                                                      # pitch rate
        # # include_states += ["aileron*qbar", "elevator*qbar", "rudder*qbar"] # control terms
        # # include_states += ["alpha_deg*qbar", "beta_deg*qbar"]              # stability terms
        # # include_states += ["az/qbar", "ay/qbar"]              # proxy stability terms
        # exclude_states = ["q", "q*qbar", "q/qbar", "q*vc_mps", "bgz", "q_term1", "abs(bgy)", "dq", "alpha_deg", "alpha_deg*qbar", "beta_deg", "ay^2",
        #                   "elevator*qbar", "elevator*vc_mps", "elevator", "ax", "bgx", "alpha_deg*vc_mps"]

        # y_state = "r"                                                      # yaw rate
        # include_states += ["aileron*qbar", "elevator*qbar", "rudder*qbar"] # control terms
        # include_states += ["alpha_deg*qbar", "beta_deg*qbar"]              # stability terms
        # include_states += ["az/qbar", "ay/qbar"]              # proxy stability terms
        # exclude_states = ["r", "r*qbar", "r*vc_mps"]

        # bgy (roll angle) correlates very well (too well?) with yaw rate
        # y_state = "r"
        # exclude_states = ["r*vc_mps", "r*qbar"]

        # no good correlators with beta
        # y_state = "beta_deg"
        # exclude_states = ["beta_deg*vc_mps", "beta_deg*qbar"]

        # y_state = "ay"
        # include_states = ["aileron*qbar", "rudder*qbar", "bgy"]
        # exclude_states = ["beta_deg*vc_mps", "beta_deg*qbar"]
        # exclude_states = ["ay*vc_mps", "ay*qbar", "ay^2", "abs(ay)", "ax", "az"]

        y_state = "elevator"
        include_states += []
        exclude_states = ["elevator*vc_mps", "elevator", "elevator*qbar", "alpha_deg", "beta_deg", "bgz", "bgx", "bgy", "r", "r*vc_mps", "r*qbar"]
        # exclude_states = ["beta_deg*vc_mps", "beta_deg*qbar"]
        # exclude_states = ["ay*vc_mps", "ay*qbar", "ay^2", "abs(ay)", "ax", "az"]

        # notice that rudder deflection leads to significant pitch down moment in decrab ... do we want to factor that in some how?
        # y_state = "q"
        # include_states = ["elevator*qbar", "one"]

        # y_state = "alpha_deg"
        # include_states = ["one", "1/qbar", "1/vc_mps", "az"]
        # include_states = ["one", "1/qbar", "q", "az"]
        # include_states = ["one"]
        # exclude_states = ["alpha_deg", "alpha_deg*qbar", "alpha_deg*vc_mps", "ay*vc_mps", "ay*qbar", "ay^2", "abs(ay)", "p", "bgx", "beta_deg", "abs(rudder)*qbar"]

        # exclude states
        # exclude_states = ["p", "q", "r"] + inceptor_terms + inceptor_airdata_terms  # avoid self referencing
        # exclude_states = ["p", "q", "r", "beta_deg"]
        # exclude_states = []

        parameter_find_5(traindata, train_states, y_state, include_states, exclude_states, self_reference=False)

    if False and False:
        # Inverse parameter predictions.  This reverses the order of training
        # data and 'predicts' what the previous control value should have been
        # to get to the desired state now.
        #
        # Hopefully the thing we want to control with the input shows up in the fit!

        # reverse the training data
        traindata = np.fliplr(traindata)

        # uncomment these one at a time
        y_state = "aileron*qbar"
        # y_state = "elevator*qbar"
        # y_state = "rudder*qbar"

        include_states = ["one"]
        exclude_states = inceptor_terms + inceptor_airdata_terms  # avoid self referencing

        parameter_find_5(traindata, train_states, y_state, include_states, exclude_states, self_reference=False)

    if False and False:
        # Direct model fit.  Use the previous two sections to determine the
        # relevants states, now go!  But stop!  This computes these terms
        # independently, so there could be doubling up of effects, really nead
        # to solve 3 simultaneous equations at the end, not 3 separate
        # equations!

        # reverse the training data because we want to fit to the previous input
        # that gets us to the desired state in the next time step. (this is a
        # nuanced thing, probably unnecessary over-engineering!)
        traindata = np.fliplr(traindata)

        include_states = ["one", "alpha_deg", "beta_deg", "p", "q", "r", "bgx", "bgy", "bgz", "abs(bgy)", "ax", "ay", "az", "abs(ay)", "throttle"]

        # uncomment these one at a time to compute the final fit formula for each
        # y_state = "aileron*qbar"
        y_state = "elevator*qbar"
        # y_state = "rudder*qbar"

        parameter_fit_1(traindata, train_states, y_state, include_states, self_reference=False)

    if True:
        # Direct model fit to p, q, beta.  Use the previous two sections to
        # determine the relevants states, now go!
        #
        # This leaves us with equations for p, q, and beta based on 3 variables
        # (ail, ele, rud).  In the control laws we'll fill in desired values for
        # p, q, and beta.  We'll leave the control surface positions as
        # unknowns.  We can evaluate/sum/collapse the remaining terms into a
        # single vector [b1, b2, b3] because we know the current state values.
        #
        # This gives us:  THIS MATH IS SUSPECT!
        #
        #   [ p    ]   [ a11 a12 a13 ] [ ail*qbar ]   [ b11 b12 ... b1n ] [ p1  ]
        #   [ q    ] = [ a21 a22 a23 ]*[ ele*qbar ] + [ b21 b22 ... b2n ]*[ p2  ]
        #   [ beta ]   [ a31 a32 a33 ] [ rud*qbar ]   [ b31 b32 ... b3n ] [ ... ]
        #                                                                 [ pn  ]
        #
        #   [ p    ]   [     ] [ ail*qbar ]   [     ] [ p1  ]
        #   [ q    ] = [  A  ]*[ ele*qbar ] + [  B  ]*[ p2  ]
        #   [ beta ]   [     ] [ rud*qbar ]   [     ] [ ... ]
        #                                             [ pn  ]
        #
        #   [       ] [ p    ]   [ b1 ]   [ ail*qbar ]
        #   [  A-1  ]*[ q    ] - [ b2 ] = [ ele*qbar ]
        #   [       ] [ beta ]   [ b3 ]   [ rud*qbar ]
        #

        # Todo: look if the p <- ay relationship is linear enough or if we need other ay * airspeed terms
        # same with q <- ay
        #
        #   Answer: p relates better to ay*vc_mps

        # check again after data cleanup! Note 1: from a cool perspective we can
        # combine all the terms into a single solution, but there is too much
        # cross coupling in our flight test data leading to weird correlations
        # in the solution.  It makes more practical sense to separate the
        # lateral and longitudinal axes ... Even so, there is a /lot/ of cross
        # coupling between aileron and rudder and we may not actually want a
        # pure system in the end.

        # Note 2: sometimes simpler is better ... fewer terms means less of a
        # good model fit, but more terms can introduce unpredictability (or
        # unexpectability)  Often additional terms add very little value.

        # Note 3: Feb 4, 2025
        # p (roll) terms: aileron*qbar, ay*vc_mps, rudder*qbar

        # test (3x3)
        # include_states = ["aileron*qbar", "elevator*qbar", "rudder*qbar", "one", "ay", "bgy", "vc_mps", "1/vc_mps"]
        # output_states = ["p", "q", "r"]

        # example
        # include_states = ["aileron*qbar", "rudder*qbar", "one"]
        # output_states = ["p", "r"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # p-beta
        # include_states = ["aileron*qbar", "rudder*qbar", "one", "ay", "bgy", "vc_mps", "1/vc_mps"]
        # output_states = ["p", "beta_deg"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # p-ay
        # include_states = ["aileron*qbar", "rudder*qbar", "one", "bgy", "vc_mps", "1/vc_mps"]
        # output_states = ["p", "ay"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # pr
        # include_states = ["aileron*qbar", "rudder*qbar", "one", "ay", "bgy", "vc_mps", "1/vc_mps", "beta_deg"]
        # output_states = ["p", "r"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # q (old, better fit, but the ay terms imply a correlation with turning
        #    which may only be there because that's how pilots fly planes, not
        #    because these parameters are physically correlated.)
        # include_states = ["elevator*qbar", "one", "ay", "abs(ay)", "bgy", "vc_mps", "1/vc_mps"]
        # output_states = ["q"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # q
        # include_states = ["elevator*qbar"]                     # control terms
        # include_states += ["one", "qbar"]
        # include_states += ["alpha_deg*qbar", "beta_deg*qbar"]  # stability terms
        # output_states = ["q"]                                  # pitch rate
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # az
        # include_states = ["one", "q*qbar", "elevator*qbar", "elevator*vc_mps", "elevator"]
        # output_states = ["az"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # pqr group damper
        # include_states = ["aileron*qbar", "elevator*qbar", "rudder*qbar", "one"]
        # output_states = ["p", "q", "r"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # new work: Feb 7, 2025 (ignoring dynamics terms)
        include_states = ["one"]

        # inertial alpha estimate
        # ## include_states = ["one", "elevator", "bgx", "1/qbar"]
        # ## include_states = ["one", "1/qbar", "az", "q", "elevator"]
        # ## include_states = ["one", "q", "qbar", "bgx", "az"]
        # include_states += ["az/qbar"]
        # output_states = ["alpha_deg"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # For Envelope Protection: what az gives us our 'max' allowable alpha?
        #
        # inverse inertial alpha estimate: az = f(alpha*qbar) (not no "one"
        # constant term, because... reasons ... inverting the forward estimate
        # doesn't lead to a constant term)
        # include_states = ["qbar", "alpha_deg*qbar"]
        # output_states = ["az"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # inertial beta estimate
        # include_states = ["ay/qbar"]
        # include_states += ["one"]
        # output_states = ["beta_deg"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # output_states = ["p"]                                               # roll rate
        # include_states += ["aileron*qbar", "elevator*qbar", "rudder*qbar"]  # control terms
        # include_states += ["az/qbar", "ay/qbar"]                            # proxy stability terms
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # what if we fit directly rather than inversely and solved afterwards
        # (we can do this because we aren't considering any time sequencing/lag
        # states in the data)

        # output_states = ["aileron*qbar"]                    # roll rate
        # include_states += ["p"]                             # the main input we want to achieve
        # include_states += ["elevator*qbar", "rudder*qbar", "throttle*qbar"]  # control terms
        # include_states += ["ay", "az"]                      # proxy stability terms
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # output_states = ["elevator*qbar"]
        # include_states += ["q"]                                                      # pitch rate
        # include_states += ["abs(aileron)*qbar", "abs(rudder)*qbar"] # control terms
        # include_states += ["abs(ay)", "az"]              # proxy stability terms
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # psuedo-beta
        # output_states = ["rudder*qbar"]
        # include_states += ["ay*qbar"]                                                      # proxy beta angle
        # include_states += ["aileron*qbar", "elevator*qbar"] # control terms
        # include_states += ["ay", "az"]                              # proxy stability terms
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # yaw rate (explicitely do not include non-symetric terms)
        # output_states = ["rudder*qbar"]
        # include_states += ["r"]                                                      # yaw rate
        # # include_states += ["aileron*qbar"] # control terms
        # include_states += ["ay"]                              # proxy stability terms
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # # load factor controller
        # output_states = ["elevator"]
        # include_states += ["az/qbar", "throttle"] # 1/qbar also correlates linearly ... Chris said there should be an inverse speed term in there, but this doesn't help the fit get tighter.
        # # include_states += ["abs(aileron)*qbar", "abs(rudder)*qbar"] # control terms
        # # include_states += ["abs(ay)", "az"]              # proxy stability terms
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # another experiment for skywalker
        output_states = ["p", "ay"]
        include_states += ["aileron*qbar", "rudder*qbar"] # primary
        include_states += ["elevator*qbar", "throttle*qbar"] # secondary
        include_states += ["az", "r"]                      # proxy alpha/beta terms
        parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        output_states = ["aileron*qbar", "rudder*qbar"]
        include_states += ["p", "r"]
        include_states += ["throttle*qbar"]
        include_states += ["az", "ay"]                      # proxy alpha/beta terms
        parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # q vs az?
        # output_states = ["q"]
        # include_states += ["az/vc_mps", "1/vc_mps"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)

        # az vs. q?
        # output_states = ["az"]
        # include_states += ["q/qbar"]
        # parameter_fit_1(traindata, train_states, include_states, output_states, self_reference=False)
