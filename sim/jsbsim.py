# -*- coding: utf-8 -*-

'''
Copyright (c) 2016 - 2020 Regents of the University of Minnesota.
MIT License; See LICENSE.md for complete details
Author: Chris Regan
Modifications: Curtis Olson
'''

#%% JSBSim
import numpy as np
import time

import jsbsim as jsb    # pip install jsbsim

from lib.constants import gravity
from lib.props import accel_node, aero_node, airdata_node, att_node, control_node, engine_node, environment_node, fcs_node, gps_node, imu_node, mass_node, pos_node, root_node, vel_node

slug2kg = 14.5939029
in2m = 0.0254
ft2m = 0.3048
m2ft = 1 / ft2m
rad2deg = 180 / np.pi
deg2rad = 1 / rad2deg
lb2N = 4.44822162
hp22W = 745.699872

class JSBSimWrap:
    def __init__ (self, model, pathJSB = '.', dt = 1/200):

        self.model = model
        self.dt = dt
        self.pathJSB = pathJSB

        self.fdm = jsb.FGFDMExec(pathJSB, None)
        self.fdm.load_model_with_paths(self.model, pathJSB, pathJSB, pathJSB, False)
        # self.fdm.load_model(self.model)
        self.fdm.set_dt(self.dt)

        self.fileLog = []

    def SetupICprops(self):
        # Load IC file
        self.fdm["ic/vt-kts"] = 0
        if False:
            # St George, UT
            self.fdm["ic/lat-geod-deg"] = 37.03
            self.fdm["ic/long-gc-deg"] = -113.52
            self.fdm["ic/terrain-elevation-ft"] = 2500
            self.fdm["ic/h-agl-ft"] = 15000
        if True:
            # Duluth, MN
            self.fdm["ic/lat-geod-deg"] = 46.866
            self.fdm["ic/long-gc-deg"] = -92.168
            self.fdm["ic/terrain-elevation-ft"] = 1414
            self.fdm["ic/h-agl-ft"] = 3.0
            self.fdm["ic/phi-deg"] = 0.0
            self.fdm["ic/theta-deg"] = 10
            self.fdm['ic/psi-true-deg'] = -135
        if False:
            # North Platte, NE
            self.fdm["ic/lat-geod-deg"] = 41.12
            self.fdm["ic/long-gc-deg"] = -100.68
            self.fdm["ic/terrain-elevation-ft"] = 2777
            self.fdm["ic/h-agl-ft"] = 1000
            self.fdm['ic/psi-true-deg'] = -135
        if False:
            # Land Airport, CO
            self.fdm["ic/lat-geod-deg"] = 40.09
            self.fdm["ic/long-gc-deg"] = -104.62
            self.fdm["ic/terrain-elevation-ft"] = 5000
            self.fdm["ic/h-agl-ft"] = 1000
            self.fdm['ic/psi-true-deg'] = -135
        if False:
            # Alamosa, NM
            self.fdm["ic/lat-geod-deg"] = 37.47
            self.fdm["ic/long-gc-deg"] = -105.85
            self.fdm["ic/terrain-elevation-ft"] = 7539
            self.fdm["ic/h-agl-ft"] = 1000
            self.fdm['ic/psi-true-deg'] = -135
        self.fdm["propulsion/set-running"] = -1

        # self.fdm.disable_output() # Disable Output
        self.fdm.run_ic()
        # self.fdm.enable_output()

        self.fdm['fcs/aileron-cmd-norm'] = 0
        self.fdm['fcs/roll-trim-cmd-norm'] = 0

        self.fdm['fcs/elevator-cmd-norm'] = 0
        self.fdm['fcs/pitch-trim-cmd-norm'] = 0

        self.fdm['fcs/rudder-cmd-norm'] = 0
        self.fdm['fcs/yaw-trim-cmd-norm'] = 0

        self.fdm['fcs/throttle-cmd-norm'] = 0

    def SetupICfile(self, icFile):
        # Load IC file
        self.fdm.load_ic(icFile, True)

        self.fdm.disable_output() # Disable Output
        self.fdm.run_ic()
        self.fdm.enable_output()

    def SetupOutput(self, outList = ['scripts/OutputFgfs.xml', 'scripts/OutputLog.xml']):
        for outFile in outList:
            self.fdm.set_output_directive(outFile)

    def DispOutput(self):
        # Display the Output
        i = 0
        while (self.fdm.get_output_filename(i) != ''):
            outStr = self.fdm.get_output_filename(i)
            if '/UDP' in outStr:
                print('Output FGFS: ', outStr)
            elif '.csv' in outStr:
                self.fileLog = outStr
                print('Output Log: ', outStr)
            i += 1


    def RunTrim(self, trimType = 1, throttle = 0.0, flap = 0.0):
        # trimType 0 = full, 1 = ground, ... https://jsbsim-team.github.io/jsbsim/classJSBSim_1_1FGFDMExec.html

        # FDM Initialize
        self.fdm.disable_output() # Disable Output
        self.fdm.run_ic()

        # self.fdm['fcs/throttle-cmd-norm[0]'] = throttle
        # self.fdm['fcs/flap-cmd-norm'] = flap

        self.fdm.run()
        self.fdm.do_trim(trimType)
        self.fdm.get_trim_status()

        self.fdm.enable_output()

        # Purge JSBSim Trim
        self.fdm['fcs/aileron-cmd-norm'] = 0
        self.fdm['fcs/roll-trim-cmd-norm'] = 0

        self.fdm['fcs/elevator-cmd-norm'] = 0
        self.fdm['fcs/pitch-trim-cmd-norm'] = 0

        self.fdm['fcs/rudder-cmd-norm'] = 0
        self.fdm['fcs/yaw-trim-cmd-norm'] = 0


    def DispTrim(self):
        print('Altitude :', self.fdm['position/geod-alt-ft'] * ft2m)

        print('Nx :', self.fdm['accelerations/Nx'])
        print('Ny :', self.fdm['accelerations/Ny'])
        print('Nz :', self.fdm['accelerations/Nz'])

        print('Phi :', self.fdm['attitude/phi-deg'])
        print('Theta :', self.fdm['attitude/theta-deg'])
        print('Psi :', self.fdm['attitude/psi-deg'])
        print('Alpha :', self.fdm['aero/alpha-deg'])

        print('Throttle :', self.fdm['fcs/throttle-cmd-norm'])
        print('Pitch :', self.fdm['fcs/pitch-trim-cmd-norm'])

    def SetWindNED(self, vWind_mps = [0.0, 0.0, 0.0]):

        self.vWind_mps = vWind_mps

        self.fdm['atmosphere/wind-north-fps'] = vWind_mps[0] * m2ft
        self.fdm['atmosphere/wind-east-fps'] = vWind_mps[1] * m2ft
        self.fdm['atmosphere/wind-down-fps'] = vWind_mps[2] * m2ft

    def GetWindNED(self):

        self.vWind_mps = [self.fdm['atmosphere/wind-north-fps'] * ft2m, self.fdm['atmosphere/wind-east-fps'] * ft2m, self.fdm['atmosphere/wind-down-fps'] * ft2m]

        return self.vWind_mps

    def SetWind(self, vWindMag_mps = 0.0, vWindHeading_deg = 0.0, vWindDown_mps = 0.0):

        self.fdm['atmosphere/wind-mag-fps'] = vWindMag_mps * m2ft
        self.fdm['atmosphere/psiw-rad'] = vWindHeading_deg * deg2rad
        self.fdm['atmosphere/wind-down-fps'] = vWindDown_mps * m2ft

    # Update the wind in JSBSim for the current altitude
    def UpdateWind(self):
        vWind20_fps = self.fdm['atmosphere/turbulence/milspec/windspeed_at_20ft_AGL-fps']
        h_ft = np.max([self.fdm['position/h-agl-ft'], 0.1])

        # Compute Wind Shear (MIL-DTL-9490E, 3.1.3.7.3.2) to compute
        self.fdm['atmosphere/wind-mag-fps'] = vWind20_fps * (0.46 * np.log10(h_ft) + 0.4)

        self.vWind20_mps = vWind20_fps * ft2m
        self.vWind_mps = self.GetWindNED()

    def SetTurb(self, turbType = 3, turbSeverity = 0, vWind20_mps = None, vWindHeading_deg = 0.0):
        self.vWind20_mps = vWind20_mps
        # Type
        # 0: ttNone (turbulence disabled)
        # 1: ttStandard
        # 2: ttCulp
        # 3: ttMilspec (Dryden spectrum)
        # 4: ttTustin (Dryden spectrum) - doesn't work!!

        # Severity
        # 3: 10^-2 (Light)
        # 4: 10^-3 (Moderate)
        # 6: 10^-5 (Severe)

        self.fdm['atmosphere/turb-type'] = turbType
        self.fdm['atmosphere/turbulence/milspec/severity'] = turbSeverity
        self.fdm['atmosphere/turbulence/milspec/windspeed_at_20ft_AGL-fps'] = vWind20_mps * m2ft
        self.fdm['atmosphere/psiw-rad'] = vWindHeading_deg * deg2rad
        self.UpdateWind()

    def RunTo(self, time_s, updateWind = None):
        # honor visual system ground elevation if set
        vis_ground_m = pos_node.getDouble("visual_terrain_elevation_m")
        if vis_ground_m > 0:
            self.fdm["position/terrain-elevation-asl-ft"] = vis_ground_m * m2ft

        while (self.fdm.get_sim_time() <= time_s): # Run the FDM
            if updateWind ==  True:
                self.UpdateWind()
            self.fdm.run()

    def RunSteps(self, steps, updateWind = None):
        # update control inputs
        self.fdm['fcs/throttle-cmd-norm'] = control_node.getDouble("throttle")
        self.fdm['fcs/aileron-cmd-norm'] = control_node.getDouble("aileron")
        self.fdm['fcs/elevator-cmd-norm'] = control_node.getDouble("elevator")
        self.fdm['fcs/pitch-trim-cmd-norm'] = control_node.getDouble("elevator_trim")
        self.fdm['fcs/rudder-cmd-norm'] = -control_node.getDouble("rudder")

        # 3 position flap dance
        flap_pos = self.fdm['fcs/flap-pos-norm']
        # print(flap_pos, abs(flap_pos % 0.5))
        if abs(flap_pos % 0.5) < 0.01:
            if control_node.getBool("flaps_down"):
                flap_pos = int((flap_pos + 0.5)*2) * 0.5
                if flap_pos > 1.0: flap_pos = 1.0
                # print("flaps down:", flap_pos)
                self.fdm['fcs/flap-cmd-norm'] = flap_pos
            if control_node.getBool("flaps_up"):
                flap_pos = int((flap_pos - 0.5)*2) * 0.5
                if flap_pos < 0.0: flap_pos = 0.0
                # print("flaps up:", flap_pos)
                self.fdm['fcs/flap-cmd-norm'] = flap_pos


        # honor visual system ground elevation if set
        vis_ground_m = pos_node.getDouble("visual_terrain_elevation_m")
        if vis_ground_m > 0:
            self.fdm["position/terrain-elevation-asl-ft"] = vis_ground_m * m2ft
        for i in range(steps):
            if updateWind ==  True:
                self.UpdateWind()
            self.fdm.run()

    # estimate the 'ideal' magnetometer reading in body coordinates
    def EstMagBody(self, lat_deg, lon_deg, phi_rad, the_rad, psi_rad):
        import geomag  # pip install geomag
        import navpy
        gm = geomag.geomag.GeoMag()
        mag = gm.GeoMag(lat_deg, lon_deg)
        mag_ned = np.array( [mag.bx, mag.by, mag.bz] )
        norm = np.linalg.norm(mag_ned)
        mag_ned /= norm
        N2B = navpy.angle2dcm(psi_rad, the_rad, phi_rad, input_unit='rad')
        mag_body = N2B.dot(mag_ned)
        norm = np.linalg.norm(mag_body)
        mag_body /= norm
        # print("  mag ned:", mag_ned, "body:", mag_body)
        return mag_body

    def PublishProps(self):
        root_node.setDouble("sim_time_sec", self.fdm['simulation/sim-time-sec'])

        # Mass Properties
        mass_node.setDouble("mass_kg", self.fdm['inertia/mass-slugs'] * slug2kg)
        mass_node.setDouble("weight_lb", self.fdm['inertia/weight-lbs'])
        mass_node.setDouble("weight_N", self.fdm['inertia/weight-lbs'] * lb2N)

        mass_node.setDouble("weightFuel_lb", self.fdm['propulsion/total-fuel-lbs'])
        mass_node.setDouble("weightFuel_N", self.fdm['propulsion/total-fuel-lbs'] * lb2N)

        mass_node.setDouble("rCgX_Bf_m", self.fdm['inertia/cg-x-in'] * in2m)
        mass_node.setDouble("rCgY_Bf_m", self.fdm['inertia/cg-y-in'] * in2m)
        mass_node.setDouble("rCgZ_Bf_m", self.fdm['inertia/cg-z-in'] * in2m)

        mass_node.setDouble("inertiaXX_kgm2", self.fdm['inertia/ixx-slugs_ft2'] * slug2kg * ft2m**2)
        mass_node.setDouble("inertiaYY_kgm2", self.fdm['inertia/iyy-slugs_ft2'] * slug2kg * ft2m**2)
        mass_node.setDouble("inertiaZZ_kgm2", self.fdm['inertia/izz-slugs_ft2'] * slug2kg * ft2m**2)
        mass_node.setDouble("inertiaXY_kgm2", self.fdm['inertia/ixy-slugs_ft2'] * slug2kg * ft2m**2)
        mass_node.setDouble("inertiaYZ_kgm2", self.fdm['inertia/iyz-slugs_ft2'] * slug2kg * ft2m**2)
        mass_node.setDouble("inertiaXZ_kgm2", self.fdm['inertia/ixz-slugs_ft2'] * slug2kg * ft2m**2)

        # Environment
        environment_node.setDouble("aGrav_mps2", self.fdm['accelerations/gravity-ft_sec2'] * ft2m)

        environment_node.setDouble("rho_kgpm3", self.fdm['atmosphere/rho-slugs_ft3'] * slug2kg * m2ft**3)
        environment_node.setDouble("temp_C", (self.fdm['atmosphere/T-R'] - 491.67) / 1.8)
        environment_node.setDouble("pres_Pa", self.fdm['atmosphere/P-psf'] * lb2N * m2ft**2)

        environment_node.setDouble("psiWind_rad", self.fdm['atmosphere/psiw-rad'])
        environment_node.setDouble("vWindMag_mps", self.fdm['atmosphere/wind-mag-fps'] * ft2m)
        environment_node.setDouble("vWindMag20_mps", self.fdm['atmosphere/turbulence/milspec/windspeed_at_20ft_AGL-fps'] * ft2m) # Wind at 20ft AGL
        environment_node.setDouble("turbSeverity", self.fdm['atmosphere/turbulence/milspec/severity']) # Wind at 20ft AGL

        environment_node.setDouble("pTurb_rps", self.fdm['atmosphere/p-turb-rad_sec'])
        environment_node.setDouble("qTurb_rps", self.fdm['atmosphere/q-turb-rad_sec'])
        environment_node.setDouble("rTurb_rps", self.fdm['atmosphere/r-turb-rad_sec'])

        environment_node.setDouble("vTurbN_mps", self.fdm['atmosphere/turb-north-fps'] * ft2m)
        environment_node.setDouble("vTurbE_mps", self.fdm['atmosphere/turb-east-fps'] * ft2m)
        environment_node.setDouble("vTurbD_mps", self.fdm['atmosphere/turb-down-fps'] * ft2m)

        environment_node.setDouble("vWindN_mps", self.fdm['atmosphere/total-wind-north-fps'] * ft2m)
        environment_node.setDouble("vWindE_mps", self.fdm['atmosphere/total-wind-east-fps'] * ft2m)
        environment_node.setDouble("vWindD_mps", self.fdm['atmosphere/total-wind-down-fps'] * ft2m)

        # Accelerations
        accel_node.setDouble("pDot_rps2", self.fdm['accelerations/pdot-rad_sec2'])
        accel_node.setDouble("qDot_rps2", self.fdm['accelerations/qdot-rad_sec2'])
        accel_node.setDouble("rDot_rps2", self.fdm['accelerations/rdot-rad_sec2'])
        accel_node.setDouble("uDot_mps2", self.fdm['accelerations/udot-ft_sec2'] * ft2m)
        accel_node.setDouble("vDot_mps2", self.fdm['accelerations/vdot-ft_sec2'] * ft2m)
        accel_node.setDouble("wDot_mps2", self.fdm['accelerations/wdot-ft_sec2'] * ft2m)

        # Aerodynamics
        aero_node.setDouble("alpha_deg", self.fdm['aero/alpha-deg'])
        aero_node.setDouble("beta_deg", self.fdm['aero/beta-deg'])
        aero_node.setDouble("alphaDot_dps", self.fdm['aero/alphadot-deg_sec'])
        aero_node.setDouble("beta_deg", self.fdm['aero/beta-deg'])
        aero_node.setDouble("betaDot_dps", self.fdm['aero/betadot-deg_sec'])

        aero_coef_elements = self.fdm.query_property_catalog('aero/coefficient')
        aero_coef_elements = aero_coef_elements.replace(' (R)', '')
        aero_coef_elements = aero_coef_elements.replace(' (RW)', '')
        aero_coef_elements = aero_coef_elements.split('\n')
        for elem in aero_coef_elements:
            if elem != '':
                aero_node.setDouble(elem, self.fdm[elem])

        # Attitude
        att_node.setDouble("phi_deg", self.fdm['attitude/phi-deg'])
        att_node.setDouble("theta_deg", self.fdm['attitude/theta-deg'])
        att_node.setDouble("psi_deg", self.fdm['attitude/psi-deg'])
        att_node.setDouble("gamma_deg", self.fdm['flight-path/gamma-deg'])

        # Propulsion
        engine_node.setDouble("propeller_rpm", self.fdm['propulsion/engine/propeller-rpm'])
        engine_node.setDouble("power_hp", self.fdm['propulsion/engine/power-hp'])
        engine_node.setDouble("power_W", self.fdm['propulsion/engine/power-hp'] * hp22W)
        engine_node.setDouble("blade_angle", self.fdm[ 'propulsion/engine/blade-angle'])
        engine_node.setDouble("advance_ratio", self.fdm[ 'propulsion/engine/advance-ratio'])
        engine_node.setDouble("thrust_lb", self.fdm[ 'propulsion/engine/thrust-lbs'])
        engine_node.setDouble("thrust_N", self.fdm[ 'propulsion/engine/thrust-lbs'] * lb2N)

        # Flight Control System (Actuators)
        fcs_node.setDouble("cmdAil_deg", self.fdm['fcs/aileron-cmd-norm'])
        fcs_node.setDouble("posAil_deg", self.fdm['fcs/left-aileron-pos-norm'])
        fcs_node.setDouble("cmdElev_deg", self.fdm['fcs/elevator-cmd-norm'])
        fcs_node.setDouble("posElev_deg", self.fdm['fcs/elevator-pos-norm'])
        fcs_node.setDouble("cmdRud_deg", self.fdm['fcs/rudder-cmd-norm'])
        fcs_node.setDouble("posRud_deg", self.fdm['fcs/rudder-pos-norm'])
        fcs_node.setDouble("cmdFlap_deg", self.fdm['fcs/flap-cmd-norm'])
        fcs_node.setDouble("posFlap_deg", self.fdm['fcs/flap-pos-norm'])
        fcs_node.setDouble("cmdThrottle_nd", self.fdm['fcs/throttle-cmd-norm'])
        fcs_node.setDouble("posThrottle_nd", self.fdm['fcs/throttle-pos-norm'])
        fcs_node.setDouble("cmdBrakeLeft_nd", self.fdm['fcs/left-brake-cmd-norm'])
        fcs_node.setDouble("cmdBrakeRight_nd", self.fdm['fcs/right-brake-cmd-norm'])

        # Positions
        pos_node.setDouble("long_gc_deg", self.fdm['position/long-gc-deg'])
        pos_node.setDouble("lat_geod_deg", self.fdm['position/lat-geod-deg'])
        pos_node.setDouble("geod_alt_m", self.fdm['position/geod-alt-ft'] * ft2m)
        pos_node.setDouble("h_sl_m", self.fdm['position/h-sl-ft'] * ft2m)
        pos_node.setDouble("h_agl_m", self.fdm['position/h-agl-ft'] * ft2m)

        # Velocities
        vel_node.setDouble("vtrue_mps", self.fdm['velocities/vtrue-fps'] * ft2m)
        vel_node.setDouble("vtrue_kts", self.fdm['velocities/vtrue-kts'])
        vel_node.setDouble("vc_mps", self.fdm['velocities/vc-fps'] * ft2m)
        vel_node.setDouble("vc_kts", self.fdm['velocities/vc-kts'])
        vel_node.setDouble("mach_nd", self.fdm['velocities/mach'])
        vel_node.setDouble("hDot_mps", self.fdm['velocities/h-dot-fps'] * ft2m)
        vel_node.setDouble("vn_mps", self.fdm['velocities/v-north-fps'] * ft2m)
        vel_node.setDouble("ve_mps", self.fdm['velocities/v-east-fps'] * ft2m)
        vel_node.setDouble("vd_mps", self.fdm['velocities/v-down-fps'] * ft2m)

        vel_node.setDouble("u_mps", self.fdm['velocities/u-fps'] * ft2m)
        vel_node.setDouble("v_mps", self.fdm['velocities/v-fps'] * ft2m)
        vel_node.setDouble("w_mps", self.fdm['velocities/w-fps'] * ft2m)

        millis = int(round(self.fdm['simulation/sim-time-sec']*1000))

        # airdata
        airdata_node.setUInt("millis", millis)
        airdata_node.setDouble("baro_press_pa", self.fdm['atmosphere/P-psf'] * lb2N * m2ft**2)
        airdata_node.setDouble("diff_press_pa", 0)
        airdata_node.setDouble("air_temp_C", (self.fdm['atmosphere/T-R'] - 491.67) / 1.8)
        airdata_node.setDouble("airspeed_mps", self.fdm['velocities/vc-fps'] * ft2m)
        airdata_node.setDouble("altitude_m", self.fdm['position/h-sl-ft'] * ft2m)
        # airdata_node.setDouble("altitude_agl_m", self.fdm['position/h-agl-ft'] * ft2m)
        # airdata_node.setDouble("altitude_true_m", self.fdm['position/h-sl-ft'] * ft2m)
        # airdata_node.setDouble("altitude_ground_m", self.fdm["position/terrain-elevation-asl-ft"] * ft2m)
        # airdata_node.setUInt("is_airborne", self.fdm['position/h-agl-ft'] >= 10.0)
        # airdata_node.setUInt("flight_timer_millis", millis)
        # airdata_node.setDouble("wind_dir_deg", self.fdm['atmosphere/psiw-rad'] * rad2deg)
        # airdata_node.setDouble("wind_speed_mps", self.fdm['atmosphere/wind-mag-fps'] * ft2m)
        # if self.fdm['velocities/vc-fps'] > 10:
        #     airdata_node.setDouble("pitot_scale_factor", self.fdm['velocities/vtrue-fps'] / self.fdm['velocities/vc-fps'] )
        # else:
        #     airdata_node.setDouble("pitot_scale_factor", 1.0)
        airdata_node.setUInt("error_count", 0)

        # gps
        gps_node.setUInt("millis", millis)
        gps_node.setUInt64("unix_usec", int(round(time.time() * 1000000)))
        gps_node.setUInt("num_sats", 9)
        gps_node.setUInt("status", 3)
        gps_node.setDouble("longitude_raw", int(round(self.fdm['position/long-gc-deg'] * 10000000)))
        gps_node.setDouble("latitude_raw", int(round(self.fdm['position/lat-geod-deg'] * 10000000)))
        gps_node.setDouble("altitude_m", self.fdm['position/geod-alt-ft'] * ft2m)
        gps_node.setDouble("vn_mps", self.fdm['velocities/v-north-fps'] * ft2m)
        gps_node.setDouble("ve_mps", self.fdm['velocities/v-east-fps'] * ft2m)
        gps_node.setDouble("vd_mps", self.fdm['velocities/v-down-fps'] * ft2m)

         # imu
        mag_body = self.EstMagBody(self.fdm['position/lat-geod-deg'], self.fdm['position/long-gc-deg'], self.fdm['attitude/phi-rad'], self.fdm['attitude/theta-rad'], self.fdm['attitude/psi-rad'])
        imu_node.setUInt("millis", millis)
        imu_node.setDouble("ax_raw", -self.fdm['accelerations/Nx'] * gravity)
        imu_node.setDouble("ay_raw", self.fdm['accelerations/Ny'] * gravity)
        imu_node.setDouble("az_raw", self.fdm['accelerations/Nz'] * gravity)
        imu_node.setDouble("hx_raw", mag_body[0])
        imu_node.setDouble("hy_raw", mag_body[1])
        imu_node.setDouble("hz_raw", mag_body[2])
        imu_node.setDouble("ax_mps2", -self.fdm['accelerations/Nx'] * gravity)
        imu_node.setDouble("ay_mps2", self.fdm['accelerations/Ny'] * gravity)
        imu_node.setDouble("az_mps2", self.fdm['accelerations/Nz'] * gravity)
        imu_node.setDouble("p_rps", self.fdm['velocities/p-rad_sec'])
        imu_node.setDouble("q_rps", self.fdm['velocities/q-rad_sec'])
        imu_node.setDouble("r_rps", self.fdm['velocities/r-rad_sec'])
        imu_node.setDouble("hx", mag_body[0])
        imu_node.setDouble("hy", mag_body[1])
        imu_node.setDouble("hz", mag_body[2])
        imu_node.setDouble("temp_C", 15)

    # def InitLog(self, logList=None):
    #     self.dataLog = {}

    #     if logList is None:
    #         logList = ['simulation/sim-time-sec', \
    #                    'position/lat-geod-rad', 'position/long-gc-rad', 'position/geod-alt-ft', 'position/h-sl-ft', 'position/h-agl-ft',\
    #                    'fcs/throttle-cmd-norm', 'fcs/throttle-pos-norm', 'velocities/vtrue-kts', 'velocities/vc-kts', 'velocities/vtrue-fps', 'velocities/vc-fps', 'velocities/h-dot-fps', \
    #                    'propulsion/engine/propeller-rpm', 'propulsion/engine/power-hp', 'propulsion/engine/blade-angle', 'propulsion/engine/advance-ratio', \
    #                    'aero/beta-rad', 'aero/alpha-rad', 'aero/betadot-rad_sec', 'aero/alphadot-rad_sec', \
    #                    'aero/beta-deg', 'aero/alpha-deg', 'aero/betadot-deg_sec', 'aero/alphadot-deg_sec', \
    #                    'atmosphere/p-turb-rad_sec', 'atmosphere/q-turb-rad_sec', 'atmosphere/r-turb-rad_sec', \
    #                    'atmosphere/turb-north-fps', 'atmosphere/turb-east-fps', 'atmosphere/turb-down-fps', \
    #                    'atmosphere/total-wind-north-fps', 'atmosphere/total-wind-east-fps', 'atmosphere/total-wind-down-fps', \
    #                    'attitude/phi-rad', 'attitude/theta-rad', 'attitude/psi-rad', 'attitude/roll-rad', 'attitude/pitch-rad', \
    #                    'attitude/phi-deg', 'attitude/theta-deg', 'attitude/psi-deg', \
    #                    'velocities/p-rad_sec', 'velocities/q-rad_sec', 'velocities/r-rad_sec', 'velocities/psidot-rad_sec', \
    #                    'flight-path/gamma-rad', 'flight-path/gamma-deg',
    #                    'accelerations/Nx', 'accelerations/Ny', 'accelerations/Nz', \
    #                    'accelerations/pdot-rad_sec2', 'accelerations/qdot-rad_sec2', 'accelerations/rdot-rad_sec2', \
    #                    'fcs/cmdAil_deg', 'fcs/cmdElev_deg', 'fcs/cmdRud_deg', 'fcs/cmdFlap_deg', \
    #                    'fcs/posAil_deg', 'fcs/posElev_deg', 'fcs/posRud_deg', 'fcs/posFlap_deg', \
    #                    'fcs/left-brake-cmd-norm', 'fcs/right-brake-cmd-norm', \
    #                    'velocities/v-fps', 'velocities/v-down-fps', 'velocities/w-fps', 'velocities/w-aero-fps', \
    #                    'inertia/pointmass-weight-lbs', 'inertia/pointmass-weight-lbs[1]', 'inertia/pointmass-weight-lbs[2]', 'inertia/pointmass-weight-lbs[3]', 'inertia/pointmass-weight-lbs[4]', 'inertia/pointmass-weight-lbs[5]']

    #     for sig in logList:
    #         self.dataLog[sig] = []

    # def UpdateLog(self):
    #     for sig in self.dataLog.keys():
    #         self.dataLog[sig].append(self.fdm[sig])

    # def LogLists2Array(self):
    #     for sig in self.dataLog.keys():
    #         self.dataLog[sig] = np.array(self.dataLog[sig])

    def __del__(self):
        del self.fdm


# %%
