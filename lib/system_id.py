"""system identification

There is nothing new under the sun, but I haven't seen a system
identification process that is this easy with this much bang for the
buck myself.

Author: Curtis L. Olson, University of Minnesota, Dept of Aerospace
Engineering and Mechanics, UAV Lab.

system id is a very broad topic that covers a multitude of approaches,
input/output parameters, system models, etc.

Here we implement a very specific approach to building a very specific
type of model.  The advantage is the approach is completely data
driven, very simple, very fast, and accurately approximates the
aircraft performance (versus some models that accurately estimate
specific aero parameters but the simulation may not perfom like the
real aircraft.)

The underlying "secret sauce" is we assemble a matrix X that is all
the v_i (state vectors) except the last one.  We make a matrix Y that
is all the v_i except the first one.)  X and Y are identical, except Y
is shifted over by one.

We write Y = A * X

If we can solve for A (in a least squares best fit senses) then we
have a state transition matrix that maps the set of current states to
the set of next states.

With this matrix we can predict the next state given any current
state.  This can be used for system integerity validataion, flight
simulation, possibly extracting traditional aero coefficients, and
possibly optimal flight control.

Note for fluids people: the problem setup is exactly the same as
performed with Dynamic Mode Decomposition (DMD), however in this
use-case we compute the fuil A matrix, whereas DMD is primarliy
interested in finding the leading eigenvalues and eigenvectors of the
A matrix, so that method employs a similarity transform to reduce the
computational effort.

"""

import dask.array as da         # dnf install python3-dask+array / pip install dask
from matplotlib import pyplot as plt
import numpy as np

from lib.state_mgr import StateManager

class SystemIdentification():
    def __init__(self, vehicle):
        self.A = None
        self.model = {}

    def compute_lift_curve(self, coeff):
        if len(coeff):
            # fit a polynomial function for lift/drag coefficient curves
            from scipy.optimize import curve_fit

            def func(x, a, b, c):
                return a * x**2 + b * x + c

            plt.figure()
            plt.plot(coeff[:,0], coeff[:,1], ".", label="raw data")
            self.alpha_popt, pcov = curve_fit(func, coeff[:,0], coeff[:,1])
            plt.plot(coeff[:,0], func(coeff[:,0], *self.alpha_popt), '.', label='fit: a=%5.3f, b=%5.3f, c=%5.3f' % tuple(self.alpha_popt))

            # alpha vs Cl plot
            num_bins = 100
            bins = np.linspace(-5, 20, num_bins+1) # alpha range
            print(bins)

            bin_indices = np.digitize( coeff[:,0], bins )

            d1 = []
            for i in range(num_bins):
                bin = i + 1
                cl_mean = np.mean(coeff[bin_indices==i+1,1])
                if not np.isnan(cl_mean):
                    pt = 0.5 * (bins[i] + bins[i+1])
                    print( i, pt, cl_mean )
                    d1.append( [pt, cl_mean] )
            d1 = np.array(d1)
            plt.figure()
            plt.plot(d1[:,0], d1[:,1], label="Cl vs. alpha (deg)")
            plt.xlabel("alpha (deg)")
            plt.legend()
            plt.show()

    def compute_drag_no_sorry(self):
        if len(coeff):
            coeff = np.array(coeff)

            # fit a polynomial function for lift/drag coefficient curves
            from scipy.optimize import curve_fit

            def func(x, a, b, c):
                return a * x**2 + b * x + c

            plt.figure()
            plt.plot(coeff[:,0], coeff[:,2], ".", label="raw data")
            self.drag_popt, pcov = curve_fit(func, coeff[:,0], coeff[:,2])
            plt.plot(coeff[:,0], func(coeff[:,0], *self.drag_popt), '.', label='fit: a=%5.3f, b=%5.3f, c=%5.3f' % tuple(self.drag_popt))

            # alpha vs Cd plot (needs to be alpha/asi vs Cd)
            num_bins = 100
            bins = np.linspace(-5, 20, num_bins+1) # alpha range
            print(bins)

            bin_indices = np.digitize( coeff[:,0], bins )

            d1 = []
            for i in range(num_bins):
                bin = i + 1
                cd_mean = np.mean(coeff[bin_indices==i+1,2])
                if not np.isnan(cl_mean):
                    pt = 0.5 * (bins[i] + bins[i+1])
                    print( i, pt, cl_mean, cd_mean )
                    d1.append( [pt, cl_mean, cd_mean] )
            d1 = np.array(d1)
            plt.figure()
            plt.plot(d1[:,0], d1[:,2], label="Cd vs. alpha (deg)")
            plt.xlabel("alpha (deg)")
            plt.legend()

            if False:
                # asi vs drag
                num_bins = 50
                max = np.max(coeff[:,3])
                bins = np.linspace(0, max, num_bins+1) # alpha range
                print(bins)

                bin_indices = np.digitize( coeff[:,3], bins )

                d1 = []
                for i in range(num_bins):
                    bin = i + 1
                    drag_mean = np.mean(coeff[bin_indices==i+1,4])
                    if not np.isnan(drag_mean):
                        pt = 0.5 * (bins[i] + bins[i+1])
                        print( i, pt, drag_mean )
                        d1.append( [pt, drag_mean] )
                d1 = np.array(d1)
                plt.figure()
                plt.plot(d1[:,0], d1[:,1], label="airspeed vs drag")
                plt.xlabel("airspeed (mps)")
                plt.legend()
                plt.show()

    def correlation_report(self, state_mgr, traindata):
        print("test pearson correlation coefficients:")
        print(state_mgr.state_list)
        corr = np.corrcoef(traindata.T)
        print(corr)

        # report leading correlations versus each state
        for i in range(len(state_mgr.state_list)):
            print(state_mgr.state_list[i] + ": ", end="")
            row = corr[i,:]
            idx = np.argsort(-np.abs(row))
            for j in range(len(idx)):
                if i != idx[j]:
                    print("%.3f" % row[idx[j]], state_mgr.state_list[idx[j]] + ", ", end="")
            print("")

    def correlation_report_2(self, train_states, traindata, fit_states):
        print("test pearson correlation coefficients:")
        print(train_states)
        corr = np.corrcoef(traindata.T)
        print(corr)

        # pick the next most correlating state that correlates the least with already chosen states
        for i in range(len(train_states)):
            print(train_states[i] + ": ", end="")
            row = corr[i,:]
            incl = {}
            rem = {}
            for j in range(len(row)):
                if i != j:
                    rem[j] = 0
            # print()
            while len(rem):
                # score remaining states based on correlation with state[i] minus max(correlation with allocated states)
                for j in rem.keys():
                    # print(" ", state_list[j])
                    max_corr = 0
                    for k in incl.keys():
                        c = abs(corr[j,k])
                        if c > max_corr:
                            max_corr = c
                    rem[j] = abs(corr[i,j]) - max_corr
                idx = sorted(rem.items(), key=lambda item: item[1], reverse=True)
                # print(idx)
                # print("choose:", idx[0][0], state_list[idx[0][0]])
                print("%.3f" % row[idx[0][0]], train_states[idx[0][0]] + ", ", end="")
                del rem[idx[0][0]]
                incl[idx[0][0]] = True
            print("")

    def solve(self, traindata, includes_idx, solutions_idx):
        srcdata = traindata[includes_idx,:]
        soldata = traindata[solutions_idx,:]
        states = len(traindata[0])

        self.X = np.array(srcdata[:,:-1])
        self.Y = np.array(soldata[:,1:])
        print("X:", self.X.shape)
        print("Y:", self.Y.shape)
        # print("X:\n", np.array(X))
        # print("Y:\n", np.array(Y))

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
        daX = da.from_array(self.X, chunks=(self.X.shape[0], 10000)).persist()
        u, s, vh = da.linalg.svd(daX)

        if False:
            # debug and sanity check
            print("u:\n", u.shape, u)
            print("s:\n", s.shape, s)
            print("vh:\n", vh.shape, vh)
            Xr = (u * s) @ vh[:states, :]
            print( "dask svd close?", np.allclose(self.X, Xr.compute()) )

        # after algebraic manipulation
        #
        # A = Y * V * D.inv() * U.T

        v = vh.T
        # print("s inv:", (1/s).compute() )

        self.A = (self.Y @ (v[:,:states] * (1/s)) @ u.T).compute()
        print("A rank:", np.linalg.matrix_rank(self.A))
        print("A:\n", self.A.shape, self.A)

    def ranges(self, train_states):
        # compute expected ranges for output parameters
        self.parameters = []
        for i in range(len(train_states)):
            print("i:", i, train_states[i])
            row = self.X[i,:]
            min = np.min(row)
            max = np.max(row)
            mean = np.mean(row)
            # if state_mgr.state_list[i] in state_mgr.input_states:
            #     var_type = "input"
            # elif state_mgr.state_list[i] in state_mgr.internal_states:
            #     var_type = "internal"
            # elif state_mgr.state_list[i] in state_mgr.output_states:
            #     var_type = "output"
            # else:
            #     var_type = "unknown"
            self.parameters.append(
                {
                    "name": train_states[i],
                    "min": np.min(row),
                    "max": np.max(row),
                    "median": np.median(row),
                    "std": np.std(row),
                    # "type": var_type
                }
            )
            print(self.parameters[-1])

    def old_fit(self, state_mgr, traindata):
        if False:    # need to use filtfilt here to avoid phase change
            # signal smoothing experiment
            from scipy import signal
            idx_list = state_mgr.get_state_index( ["p", "q", "r"] )
            for i in idx_list:
                print(i)
                print(traindata[:,i].shape)
                sos = signal.butter(4, 15, 'low', fs=(1/state_mgr.dt),
                                    output='sos')
                filt = signal.sosfilt(sos, traindata[:,i]).astype(float)
                traindata[:,i] = filt

        output_list = state_mgr.get_state_index( state_mgr.output_states )
        print("output_list:", output_list)

        states = len(traindata[0])
        self.X = np.array(traindata[:-1]).T
        self.Y = np.array(traindata[1:,output_list]).T
        print("X:\n", self.X.shape, np.array(self.X))
        print("Y:\n", self.Y.shape, np.array(self.Y))

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

        print("dask svd...")
        daX = da.from_array(self.X, chunks=(self.X.shape[0], 10000)).persist()
        u, s, vh = da.linalg.svd(daX)

        if True:
            # debug and sanity check
            print("u:\n", u.shape, u)
            print("s:\n", s.shape, s)
            print("vh:\n", vh.shape, vh)
            Xr = (u * s) @ vh[:states, :]
            print( "dask svd close?", np.allclose(self.X, Xr.compute()) )

        # after algebraic manipulation
        #
        # A = Y * V * D.inv() * U.T

        v = vh.T
        print("s inv:", (1/s).compute() )

        self.A = (self.Y @ (v[:,:states] * (1/s)) @ u.T).compute()
        print("A rank:", np.linalg.matrix_rank(self.A))
        print("A:\n", self.A.shape, self.A)

        # compute expected ranges for output parameters
        self.parameters = []
        for i in range(states):
            print("i:", i, state_mgr.state_list[i])
            row = self.X[i,:]
            min = np.min(row)
            max = np.max(row)
            mean = np.mean(row)
            # if state_mgr.state_list[i] in state_mgr.input_states:
            #     var_type = "input"
            # elif state_mgr.state_list[i] in state_mgr.internal_states:
            #     var_type = "internal"
            # elif state_mgr.state_list[i] in state_mgr.output_states:
            #     var_type = "output"
            # else:
            #     var_type = "unknown"
            self.parameters.append(
                {
                    "name": state_mgr.state_list[i],
                    "min": np.min(row),
                    "max": np.max(row),
                    "median": np.median(row),
                    "std": np.std(row),
                    # "type": var_type
                }
            )

    def model_noise(self, state_mgr, traindata, output_idx, dt):
        # look at the frequency of the error terms in the output states which
        # suggest unmodeled effects such as short period oscillations and
        # turbulence, or artifacts in the data log (like a 5hz gps update rate
        # showing up in ekf velocity estimate.)

        pred = []
        for i in range(len(self.X.T)):
            v  = traindata[:,i].copy()
            p = self.A @ np.array(v)
            pred.append(p)
        Ypred = np.array(pred).T
        diff = Ypred - self.Y

        M=1024
        from scipy import signal
        for i in range(len(output_idx)):
            # parameter: window='hann' may need to be added to the
            # signal.spectogram() call for older scipy/numpy versions that don't
            # yet agree on this name.
            freqs, times, Sx = signal.spectrogram(diff[i,:], fs=(1/dt),
                                                  nperseg=M, noverlap=M - 100,
                                                  detrend=False, scaling='spectrum')
            if False:
                f, ax = plt.subplots()
                ax.pcolormesh(times, freqs, 10 * np.log10(Sx), cmap='viridis')
                ax.set_title(state_mgr.output_states[i] + " Spectogram")
                ax.set_ylabel('Frequency [Hz]')
                ax.set_xlabel('Time [s]');
            means = Sx.mean(axis=1)   # average each rows (by freq)
            num_bins = 15
            bins = np.linspace(0.5, num_bins+0.5, num_bins+1) # freq range
            #print(bins)

            bin_indices = np.digitize( freqs, bins )
            #print(bin_indices)
            d1 = []
            for j in range(num_bins):
                bin = j + 1
                total = np.sum(means[bin_indices==j+1])
                if not np.isnan(total):
                    pt = 0.5 * (bins[j] + bins[j+1])
                    #print( j, pt, total )
                    d1.append( [pt, total] )
            self.parameters[output_idx[i]]["noise"] = d1
            if False:
                d1 = np.array(d1)
                plt.figure()
                plt.plot(d1[:,0], d1[:,1], label="freq vs energy")
                plt.xlabel("freq")
                plt.legend()
        if False:
            plt.show()

    def analyze(self, state_mgr, train_states, output_idx):
        states = len(train_states)
        params = self.parameters

        # report leading contributions towards computing each output state
        for i in range(len(output_idx)):
            print(train_states[output_idx[i]])
            row = self.A[i,:]
            energy = []
            for j in range(states):
                # e = row[j] * (abs(params[j]["median"]) + 0.5 * params[j]["std"]) * np.sign(params[j]["median"])
                e = row[j] * params[j]["std"]
                # e = row[j] * params[j]["median"]
                # e = row[j] * (params[j]["max"] - params[j]["min"]) # probably no ...
                energy.append(e)
            idx = np.argsort(-np.abs(energy))
            total = np.sum(np.abs(energy))
            params[output_idx[i]]["contributors"] = train_states[output_idx[i]] + " = "
            params[output_idx[i]]["formula"] = train_states[output_idx[i]] + " = "
            contributors = train_states[output_idx[i]] + " = "
            formula = train_states[output_idx[i]] + " = "
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
            print(i, output_idx[i])
            params[output_idx[i]]["contributors"] = contributors
            params[output_idx[i]]["formula"] = formula
            print(params[output_idx[i]]["contributors"])
            print(params[output_idx[i]]["formula"])

    def simulate(self, traindata, train_states, includes_idx, solutions_idx):
        # make a copy because we are going to roll our state estimates through the
        # data matrix and make a mess (or a piece of artwork!) out of it.
        data = traindata.copy()
        print("simulate:", data.shape, includes_idx, solutions_idx)

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

        # def shuffle_down(j):
        #     if j < data.shape[1] - 1:
        #         for [src, dst] in reversed(propagate):
        #             data[dst,j+1] = data[src,j]

        est = []
        next = np.zeros(len(indirect_idx))
        data[solutions_idx,i] = next
        for i in range(data.shape[1]):
            # print("i:", i)
            # print("includes_idx:", includes_idx)
            # print("solutions_idx:", solutions_idx)
            v = data[includes_idx,i]
            # print("v:", v.shape, v)
            if len(indirect_idx):
                v[indirect_idx] = next
            next = self.A @ v
            # shuffle_down(i)
            if i < data.shape[1] - 1:
                data[solutions_idx,i+1] = next
            est.append(next)
        # return np.array(est).T
        est = np.array(est).T

        for j in range(len(solutions_idx)):
            plt.figure()
            plt.plot(traindata[solutions_idx[j],:], label="%s (orig)" % train_states[solutions_idx[j]])
            print(j)
            print(j, est[j,:], solutions_idx[j])
            plt.plot(est[j,:], label="%s (pred)" % train_states[solutions_idx[j]])
            # plt.ylim([-20,20])
            plt.legend()
        plt.show()

    def save(self, model_name, dt):
        # the median delta t from the data log is important to include
        # with the state transition matrix because the state
        # transition matrix coefficients assume this value for
        # realtime performance.

        self.model["dt"] = dt
        self.model["rows"] = len(state_mgr.output_states)
        self.model["cols"] = len(state_mgr.state_list)
        self.model["A"] = self.A.flatten().tolist()

        f = open(model_name, "w")
        json.dump(self.model, f, indent=4)
        f.close()
