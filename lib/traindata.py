from math import cos, pi, sin
import numpy as np
import os
import hickle  # pip install hickle; # pickle into hdf5 format
from tqdm import tqdm

from flightdata import flight_loader, flight_interp

from .constants import d2r, r2d, kt2mps
from .wind import Wind

class TrainData():
    def __init__(self):
        self.session = None
        self.cond_list = []

    def load_flightdata(self, file_list, vehicle, invert_elevator, invert_rudder, state_mgr, conditions, train_states):
        self.session_file = "session_data.hkl"

        if os.path.exists(self.session_file):
            print("loading session from cached hickle file:", self.session_file)
            self.session = hickle.load(self.session_file)

            if self.session["file_list"] == file_list and self.session["train_states"] == train_states:
                self.flight_format = self.session["flight_format"]
                self.cond_list = self.session["cond_list"]
                self.train_states = self.session["train_states"]
                self.file_list = self.session["file_list"]
                self.dt = self.session["dt"]
                return "cached"

        print("file set or train state changed, so need to rebuild session data ...")

        self.file_list = file_list
        self.train_states = train_states

        # condition data collectors
        for i in range(len(conditions)):
            self.cond_list.append( [] )

        for file in file_list:
            data, self.flight_format = flight_loader.load(file)

            print("imu records:", len(data["imu"]))
            print("gps records:", len(data["gps"]))
            if "airdata" in data:
                print("airdata records:", len(data["airdata"]))
            if "act" in data:
                print("actuator records:", len(data["act"]))
            if "nav" in data:
                print("nav records:", len(data["nav"]))
            if len(data["imu"]) == 0 and len(data["gps"]) == 0:
                print("not enough data loaded to continue.")
                quit()

            # dt estimation
            print("Estimating median dt from IMU records:")
            iter = flight_interp.IterateGroup(data)
            last_time = None
            dt_data = []
            max_airspeed = 0
            for i in tqdm(range(iter.size())):
                record = iter.next()
                if len(record):
                    if "imu" in record:
                        imupt = record["imu"]
                        if last_time is None:
                            last_time = imupt["timestamp"]
                        dt_data.append(imupt["timestamp"] - last_time)
                        last_time = imupt["timestamp"]
                    if "airdata" in record:
                        airpt = record["airdata"]
                        if airpt["airspeed_mps"] > max_airspeed:
                            max_airspeed = airpt["airspeed_mps"]
            dt_data = np.array(dt_data)
            print("IMU mean:", np.mean(dt_data))
            print("IMU median:", np.median(dt_data))
            imu_dt = float("%.4f" % np.median(dt_data))
            print("imu dt:", imu_dt)
            print("max airspeed in flight (mps):", max_airspeed )

            self.dt = imu_dt
            state_mgr.set_dt(imu_dt)

            print("Parsing flight data log:")
            actpt = {}
            airpt = {}
            navpt = {}
            # g = np.array( [ 0, 0, -9.81 ] )

            wn = 0
            we = 0
            wd = 0

            pitot_scale = None
            psi_bias = None
            wn_interp = None
            we_interp = None

            # backup wind estimator if needed
            windest = Wind()

            if False and self.flight_format != "cirrus_pkl":
                # note: wind estimates are only needed for estimating alpha/beta (or
                # bvz/bvy) which is not needed if the aircraft is instrumented with
                # alpha/beta vanes and these are measured directly.

                from lib.wind2 import Wind2
                w2 = Wind2()
                pitot_scale, psi_bias, wn_interp, we_interp = w2.estimate( flight_interp.IterateGroup(data), imu_dt )

            # iterate through the flight data log (a sequence of time samples of all the measured states)
            iter = flight_interp.IterateGroup(data)
            for i in tqdm(range(iter.size())):
                record = iter.next()
                if len(record) == 0:
                    continue
                # print(i, "record:", record)

                # 1. Do the messy work of cherry picking out the direct measured states from each time sample
                if "nav" in record:
                    # need ahead of air in case we are doing a wind estimate
                    navpt = record["nav"]
                else:
                    continue
                if "imu" in record:
                    imupt = record["imu"]
                    state_mgr.set_time( imupt["timestamp"] )
                    p = imupt["p_rps"]
                    q = imupt["q_rps"]
                    r = imupt["r_rps"]
                    if "p_bias" in navpt:
                        p -= navpt["p_bias"]
                        q -= navpt["q_bias"]
                        r -= navpt["r_bias"]
                    state_mgr.set_gyros( np.array([p, q, r]) )
                    ax = imupt["ax_mps2"]
                    ay = imupt["ay_mps2"]
                    az = imupt["az_mps2"]
                    if "ax_bias" in navpt:
                        ax -= navpt["ax_bias"]
                        ay -= navpt["ay_bias"]
                        az -= navpt["az_bias"]
                    state_mgr.set_accels( np.array([ax, ay, az]) )
                if "effectors" in record:
                    actpt = record["effectors"]
                    if vehicle == "wing":
                        state_mgr.set_throttle( actpt["power"] )
                        ail = actpt["aileron"]
                        ele = actpt["elevator"]
                        rud = actpt["rudder"]
                        if invert_elevator:
                            ele = -ele
                        if invert_rudder:
                            rud = -rud
                        if "flaps" in actpt:
                            flaps = actpt["flaps"]
                        else:
                            flaps = 0
                        state_mgr.set_flight_surfaces( ail, ele, rud, flaps )
                    elif vehicle == "quad":
                        state_mgr.set_motors( [ actpt["output[0]"],
                                                    actpt["output[1]"],
                                                    actpt["output[2]"],
                                                    actpt["output[3]"] ] )
                if "gps" in record:
                    gpspt = record["gps"]
                if "airdata" in record:
                    airpt = record["airdata"]

                    asi_mps = airpt["airspeed_mps"]
                    # add in correction factor if available
                    if pitot_scale is not None:
                        asi_mps *= pitot_scale
                    elif "pitot_scale" in airpt:
                        asi_mps *= airpt["pitot_scale"]
                    if "alpha" in airpt and "beta" in airpt:
                        state_mgr.set_airdata( asi_mps, airpt["alpha"]*d2r, airpt["beta"]*d2r )
                    else:
                        state_mgr.set_airdata( asi_mps )
                    if wn_interp is not None and we_interp is not None:
                        # post process wind estimate
                        wn = wn_interp(imupt["timestamp"])
                        we = we_interp(imupt["timestamp"])
                        wd = 0
                    elif "wind_dir" in airpt:
                        wind_psi = 0.5 * pi - airpt["wind_dir"] * d2r
                        wind_mps = airpt["wind_speed"] * kt2mps
                        we = cos(wind_psi) * wind_mps
                        wn = sin(wind_psi) * wind_mps
                        wd = 0
                    elif False and flight_format == "cirrus_pkl" and state_mgr.is_flying():
                        windest.update(imupt["timestamp"], airpt["airspeed"], navpt["psi"], navpt["vn"], navpt["ve"])
                        wn = windest.filt_long_wn.value
                        we = windest.filt_long_we.value
                        wd = 0
                        print("%.2f %.2f" % (wn, we))
                if "nav" in record:
                    navpt = record["nav"]
                    psi = navpt["psi_deg"] * d2r
                    if psi_bias is not None:
                        psi += psi_bias
                    state_mgr.set_orientation( navpt["phi_deg"]*d2r, navpt["theta_deg"]*d2r, navpt["psi_deg"]*d2r )
                    state_mgr.set_pos(navpt["longitude_deg"], navpt["latitude_deg"], navpt["altitude_m"])
                    if vehicle == "wing" or np.linalg.norm([navpt["vn"], navpt["ve"], navpt["vd"]]) > 0.000001:
                        state_mgr.set_ned_velocity( navpt["vn_mps"], navpt["ve_mps"],
                                                        navpt["vd_mps"], wn, we, wd )
                    else:
                        state_mgr.set_ned_velocity( gpspt["vn_mps"], gpspt["ve_mps"],
                                                        gpspt["vd_mps"], wn, we, wd )

                # Our model is only valid during flight aloft, skip non-flying data points
                if not state_mgr.is_flying():
                    continue

                # 2. Derived states
                state_mgr.compute_derived_states(state_mgr.have_alpha)

                # 3. Compute terms (combinations of states and derived states)
                state_mgr.compute_terms()

                state = state_mgr.gen_state_vector(train_states)
                # print(state_mgr.state2dict(state))
                for i, condition in enumerate(conditions):
                    # print(i, condition)
                    if "flaps" in condition and abs(state_mgr.flaps - condition["flaps"]) < 0.1:
                        # print(True)
                        self.cond_list[i].append( state )
                        # if vehicle == "wing":
                        #     params = [ state_mgr.alpha[0]*r2d, state_mgr.Cl_raw, 0, state_mgr.qbar,
                        #                 state_mgr.accels[0][0], state_mgr.throttle[0] ]
                        #     # print("params:", params)
                        #     self.cond_list[i]["coeff"].append( params )

        # convert train data lists into numpy arrays
        for i in range(len(self.cond_list)):
            self.cond_list[i] = np.array(self.cond_list[i]).T
            print("cond_list shape:", self.cond_list[i].shape)

        # cache our work
        print("Saving a hickle (hdf5/pickle) cache of this session data...")
        session = {}
        session["flight_format"] = self.flight_format
        session["file_list"] = self.file_list
        session["cond_list"] = self.cond_list
        session["train_states"] = self.train_states
        session["dt"] = imu_dt
        hickle.dump(session, self.session_file, mode='w')
