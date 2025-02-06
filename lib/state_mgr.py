# manage construction of the state vector by name.  Intended to help
# avoid getting lost in our index offsets as we play around with
# different state parameters.

from math import atan2, cos, sin, sqrt
import numpy as np

from lib.constants import gravity, d2r, r2d
from lib import quaternion

num = 4 # length of history to maintain in state mgr

class StateManager():
    def __init__(self, vehicle="wing"):
        # config
        self.vehicle = vehicle
        self.input_states = []
        self.internal_states = []
        self.output_states = []
        self.state_list = []
        self.dt = None
        self.airborne_thresh_mps = 10 # default for small fixed wing drone
        self.land_thresh_mps = 7      # default for small fixed wing drone
        self.wn_filt = 0
        self.we_filt = 0
        self.wd_filt = 0

        self.rho = 1.225    # atmospheric density
        self.mass_kg = 1    # mass of aircraft = 1 aircraft would work!
        self.wing_area = 1  # wing area = 1 wing!  "S"

        # inputs
        self.aileron = [0]*num  # list maintains some past state
        self.elevator = [0]*num  # list maintains some past state
        self.rudder = [0]*num  # list maintains some past state
        self.flaps = 0
        self.throttle = [0]*num  # list maintains some past state

        # direct states
        self.time = 0
        self.gyros = [np.zeros(3)]*num  # list maintains some past state
        self.accels = [np.zeros(3)]*num  # list maintains some past state
        self.vc_mps = 0       # calibrated airspeed
        self.alpha = [0]*num  # list maintains some past state
        self.beta = [0]*num   # list maintains some past state
        self.vel_ned = np.array( [0.0, 0.0, 0.0] )
        self.gs_mps = 0
        self.phi_rad = 0
        self.the_rad = 0
        self.psi_rad = 0
        self.ned2body = quaternion.eul2quat( 0, 0, 0 )
        self.lon = 0
        self.lat = 0
        self.alt = 0

        # terms (combinations of states)
        self.qbar = 0
        self.alpha_dot_term2 = 0
        self.alpha_dot_term3 = 0

        self.Cl_raw = 0   # raw/immediate estimate from accels and qbar
        self.thrust = 0
        self.have_alpha = False
        self.alpha_dot = 0
        self.flying = False
        self.ground_alt = None
        self.g_ned = np.array( [0.0, 0.0, gravity] )
        self.g_body = np.array( [0.0, 0.0, 0.0] )
        self.vel_body = np.array( [0.0, 0.0, 0.0] )

    def set_state_names(self, input_states, internal_states, output_states):
        self.input_states = input_states
        self.internal_states = internal_states
        self.output_states = output_states
        self.state_list = self.input_states + self.internal_states + self.output_states

    def get_state_index(self, state_name_list):
        result = []
        for n in state_name_list:
            try:
                index = self.state_list.index(n)
                result.append(index)
            except:
                print("Request for non-existent state name")
                result.append(None)
        return result

    def set_dt(self, dt):
        self.dt = dt

    def set_is_flying_thresholds(self, airborne_thresh_mps, land_thresh_mps):
        if land_thresh_mps >= airborne_thresh_mps:
            print("land threshold must be lower than airborne threshold for hysterisis.")
        self.airborne_thresh_mps = airborne_thresh_mps
        self.land_thresh_mps = land_thresh_mps

    # set direct states

    def set_time(self, time):
        self.time = time

    def set_throttle(self, throttle):
        if throttle < 0: throttle = 0
        if throttle > 1: throttle = 1
        self.throttle = [throttle] + self.throttle[:num]
        # max thrust is 0.75 gravity, so we can't quite hover on full power
        self.thrust = sqrt(self.throttle[0]) * 0.75 * abs(gravity)

    def set_flight_surfaces(self, aileron, elevator, rudder, flaps=0):
        if aileron < -1: aileron = -1
        if aileron > 1: aileron = 1
        if elevator < -1: elevator = -1
        if elevator > 1: elevator = 1
        if rudder < -1: rudder = -1
        if rudder > 1: rudder = 1
        if flaps < 0: flaps = 0
        if flaps > 1: flaps = 1

        self.aileron = [aileron] + self.aileron[:num]
        self.elevator = [elevator] + self.elevator[:num]
        self.rudder = [rudder] + self.rudder[:num]
        self.flaps = flaps

    def set_motors(self, motors):
        self.motors = motors.copy()

    def set_airdata(self, vc_mps, alpha_rad=None, beta_rad=None):
        self.vc_mps = vc_mps
        self.vel_body[0] = vc_mps
        if alpha_rad is not None:
            self.have_alpha = True
            self.alpha = [alpha_rad] + self.alpha[:num]
            self.alpha_dot = (self.alpha[0] - self.alpha[1]) / self.dt
            self.vel_body[2] = vc_mps * sin(alpha_rad)
        if beta_rad is not None:
            self.beta = [beta_rad] + self.beta[:num]
            self.vel_body[1] = vc_mps * sin(beta_rad)
        # print("rudder:", self.rudder, "beta:", self.beta, "vby:", self.vel_body[1])
        # print("alpha:", self.alpha*r2d, "v_body:", self.vel_body)

    def set_wind(self, wn, we):
        self.wn_filt = 0.95 * self.wn_filt + 0.05 * wn
        self.we_filt = 0.95 * self.we_filt + 0.05 * we

    def set_gyros(self, gyros):
        self.gyros = [gyros] + self.gyros[:num]

    def set_accels(self, accels):
        self.accels = [accels] + self.accels[:num]

    def set_ned_velocity(self, vn, ve, vd, wn, we, wd):
        # store NED velocity, corrected to remove wind effects
        self.wn_filt = 0.95 * self.wn_filt + 0.05 * wn
        self.we_filt = 0.95 * self.we_filt + 0.05 * we
        self.wd_filt = 0.95 * self.wd_filt + 0.05 * wd
        self.vel_ned = np.array( [vn + wn, ve + we, vd + wd] )
        self.gs_mps = sqrt( self.vel_ned[0]**2 + self.vel_ned[1]**2 )

    def set_orientation(self, phi_rad, the_rad, psi_rad):
        self.phi_rad = phi_rad
        self.the_rad = the_rad
        self.psi_rad = psi_rad
        self.ned2body = quaternion.eul2quat( phi_rad, the_rad, psi_rad )

    def set_pos(self, lon, lat, alt):
        self.lon = lon
        self.lat = lat
        self.alt = alt
        if self.ground_alt is None or alt < self.ground_alt:
            self.ground_alt = alt

    # for simulator
    def set_body_velocity(self, v_body):
        self.vel_body = v_body

    # update attitude
    def update_attitude(self):
        # attitude: integrate rotational rates
        delta_rot = self.gyros * self.dt
        rot_body = quaternion.eul2quat(delta_rot[0], delta_rot[1], delta_rot[2])
        self.ned2body = quaternion.multiply(self.ned2body, rot_body)
        self.phi_rad, self.the_rad, self.psi_rad = quaternion.quat2eul(self.ned2body)

    # compute gravity vector in body frame
    def update_gravity_body(self):
        self.g_body = quaternion.transform(self.ned2body, self.g_ned)

    # accels = (ax, ay, az), g_body = (gx, gy, gz)
    def update_body_velocity(self):
        self.vel_body += (self.accels - self.g_body) * self.dt
        print(self.g_ned, self.g_body, self.accels - self.g_body, self.vel_body)

    def update_airdata(self, alpha_rad, beta_rad):
        # self.accels[0] = ax_mps2
        self.vel_body[0] += (self.accels[0] - self.g_body[0])  * self.dt
        self.vc_mps = self.vel_body[0]
        self.compute_qbar()
        self.alpha = [alpha_rad] + self.alpha[:num]
        self.alpha_dot = (self.alpha - self.alpha_prev1) / self.dt
        self.vel_body[2] = self.vel_body[0] * sin(alpha_rad)
        self.beta = [beta_rad] + self.beta[:num]
        self.vel_body[1] = self.vel_body[0] * sin(beta_rad)

        # hey, estimate ay, az accels! (and make the new vel official) and FIXME!
        # print("FIXME!")
        # self.accels[1] = (vby - self.vel_body[1]) / self.dt # + self.g_body[1]
        # self.vel_body[1] = vby
        # self.accels[2] = (vbz - self.vel_body[2]) / self.dt # + self.g_body[2]
        # self.vel_body[2] = vby

    def update_airdata_from_accels(self):
        # todo: use observed min/max range from model

        self.vc_mps = self.vel_body[0]
        self.compute_qbar()

        # try to clamp side/vertical velocities from getting crazy
        cutoff = 0.3
        if abs(self.vel_body[1] / self.vel_body[0]) > cutoff:
            self.vel_body[1] = np.sign(self.vel_body[1]) * abs(self.vel_body[0]) * cutoff
        if abs(-self.vel_body[2] / self.vel_body[0]) > cutoff:
            self.vel_body[2] = np.sign(self.vel_body[2]) * abs(self.vel_body[0]) * cutoff

        # alpha and beta from body frame velocity
        # max = 20 * d2r
        self.alpha = [ atan2( self.vel_body[2], self.vel_body[0] ) ] + self.alpha[:num]
        # if abs(self.alpha) > max:
        #     self.alpha = np.sign(self.alpha) * max
        if len(self.alpha) >= 2:
            self.alpha_dot = (self.alpha[0] - self.alpha[1]) / self.dt
        self.beta = [ atan2( self.vel_body[1], self.vel_body[0] ) ] + self.beta[:num]
        # if abs(self.beta) > max:
        #     self.beta = np.sign(self.beta) * max

    def is_flying(self):
        if self.vehicle == "wing":
            # test if we are flying?
            if not self.flying and self.gs_mps > self.airborne_thresh_mps*0.7 and self.vc_mps > self.airborne_thresh_mps:
                print("Start flying @ %.2f" % self.time)
                self.flying = True
            elif self.flying and self.gs_mps < self.airborne_thresh_mps*1.2 and self.vc_mps < self.land_thresh_mps:
                print("Stop flying @ %.2f" % self.time)
                self.flying = False
        elif self.vehicle == "quad":
            if not self.flying and self.alt > self.ground_alt + 2:
                print("Start flying @ %.2f" % self.time)
                self.flying = True
            elif self.flying and self.alt < self.ground_alt + 1:
                print("Stop flying @ %.2f" % self.time)
                self.flying = False
        return self.flying

    # compute body frame of reference values
    def compute_derived_states(self, have_alpha_beta=False):
        if self.dt is None:
            print("Did you forget to set dt for this system?")
            return None

        if not have_alpha_beta:
            # rotate ned velocity vector into body frame
            self.vel_body = quaternion.transform(self.ned2body, self.vel_ned)
            #print("v_ned:", self.vel_ned, np.linalg.norm(self.vel_ned),
            #      "v_body:", self.vel_body, np.linalg.norm(self.vel_body))

            # compute alpha and beta estimates) from body frame velocity
            self.alpha = [ atan2( self.vel_body[2], self.vel_body[0] ) ] + self.alpha[:num]
            self.beta = [ atan2( -self.vel_body[1], self.vel_body[0] ) ] + self.beta[:num]
            #print("v(body):", v_body, "alpha = %.1f" % (self.alpha/d2r), "beta = %.1f" % (self.beta/d2r))


        # rotate ned gravity vector into body frame
        self.g_body = quaternion.transform(self.ned2body, self.g_ned)

        # tmpx = -sin(self.the_rad) * gravity
        # print("g_body x:", self.g_body[0], "sin:", tmpx)
        # tmpy = cos(self.the_rad) * sin(self.phi_rad) * gravity
        # print("g_body y:", self.g_body[1], "sin:", tmpy)
        # tmpz = cos(self.phi_rad) * cos(self.the_rad) * gravity
        # print("g_body z:", self.g_body[2], "cos*cos:", tmpz)

    # terms are direct combinations of measurable states
    def compute_terms(self):
        # qbar = 1/2 * V^2 * rho
        self.qbar = 0.5 * self.vc_mps**2 * self.rho

        # Cl coefficient of lift (varies as a function of alpha)
        lift = -self.accels[0][2] * self.mass_kg  # actual measured force
        # lift (L) = Cl * qbar * A (wing area)
        # Cl = lift / (qbar * A)
        if self.qbar > 10:
            self.Cl_raw = lift / (self.qbar * self.wing_area)
        else:
            self.Cl_raw = 0

        # alpha_dot term2: contribution from aerodynamic lift
        self.alpha_dot_term2 = (self.qbar * self.wing_area) / (self.mass_kg * self.vc_mps * cos(self.beta[0]))

        # alpha_dot_term3: contribution from gravity forces
        self.alpha_dot_term3 = gravity * (cos(self.alpha[0]) * cos(self.phi_rad) * cos(self.the_rad) + sin(self.alpha[0]) * sin(self.the_rad)) / (self.vc_mps * cos(self.beta[0]))

        # q_term1: account for pitch bias in turns
        self.q_term1 = sin(self.phi_rad) * (sin(self.phi_rad) / cos(self.phi_rad)) / self.vc_mps

    def gen_state_vector(self, state_list=None, params=None):
        result = []
        if state_list is None:
            state_list = self.state_list
        for index, name in enumerate(state_list):
            if len(name) >= 3 and name[-2] == "_":
                field = name[:-2]
                n = int(name[-1])
            else:
                field = name
                n = 0
            # Inceptors
            if field == "throttle":
                val = self.throttle[n]
            elif field == "aileron":
                val = self.aileron[n]
            elif field == "elevator":
                val = self.elevator[n]
            elif field == "rudder":
                val = self.rudder[n]
            elif field == "flaps":
                val = self.flaps
            elif field == "aileron*vc_mps":
                val = self.aileron[n] * self.vc_mps
            elif field == "aileron*qbar":
                val = self.aileron[n] * self.qbar
            elif field == "abs(aileron)*qbar":
                val = abs(self.aileron[n]) * self.qbar
            elif field == "elevator*vc_mps":
                val = self.elevator[n] * self.vc_mps
            elif field == "elevator*qbar":
                val = self.elevator[n] * self.qbar
            elif field == "abs(elevator)*qbar":
                val = abs(self.elevator[n]) * self.qbar
            elif field == "rudder*vc_mps":
                val = self.rudder[n] * self.vc_mps
            elif field == "rudder*qbar":
                val = self.rudder[n] * self.qbar
            elif field == "abs(rudder)*qbar":
                val = abs(self.rudder[n]) * self.qbar
            elif field == "flaps*qbar":
                val = self.flaps * self.qbar
            elif field == "motor[0]":
                val = self.motors[0]
            elif field == "motor[1]":
                val = self.motors[1]
            elif field == "motor[2]":
                val = self.motors[2]
            elif field == "motor[3]":
                val = self.motors[3]
            elif field == "motor[4]":
                val = self.motors[4]
            elif field == "motor[5]":
                val = self.motors[5]
            elif field == "thrust":
                val = self.thrust
            elif field == "bgx":
                val = self.g_body[0]
            elif field == "bgy":
                val = self.g_body[1]
            elif field == "abs(bgy)":
                val = abs(self.g_body[1])
            elif field == "abs(bgy)":
                val = abs(self.g_body[1])
            elif field == "bgz":
                val = self.g_body[2]
            elif field == "bax":
                val = self.a_body[0]
            elif field == "bay":
                val = self.a_body[1]
            elif field == "abs(bay)":
                val = abs(self.a_body[1])
            elif field == "baz":
                val = self.a_body[2]
            elif field == "vc_mps":
                val = self.vc_mps
            elif field == "1/vc_mps":
                if self.vc_mps != 0:
                    val = 1 / self.vc_mps
                else:
                    val = 0
            elif field == "qbar":
                val = self.qbar
            elif field == "1/qbar":
                if self.qbar != 0:
                    val = 1 / self.qbar
                else:
                    val = 0
            elif field == "Cl":
                val = self.Cl_raw
            elif field == "alpha_deg":
                val = self.alpha[n] * r2d
            elif field == "beta_deg":
                val = self.beta[n] * r2d
            elif field == "alpha_deg*qbar":
                val = self.alpha[n] * r2d * self.qbar
            elif field == "beta_deg*qbar":
                val = self.beta[n] * r2d * self.qbar
            elif field == "alpha_deg*vc_mps":
                val = self.alpha[n] * r2d * self.vc_mps
            elif field == "beta_deg*vc_mps":
                val = self.beta[n] * r2d * self.vc_mps
            elif field == "sin(alpha_deg)*qbar":
                val = sin(self.alpha[n]) * self.qbar
            elif field == "alpha_dot":
                val = self.alpha_dot
            elif field == "alpha_dot_term2":
                val = self.alpha_dot_term2
            elif field == "alpha_dot_term3":
                val = self.alpha_dot_term3
            elif field == "sin(beta_deg)*qbar":
                val = sin(self.beta) * self.qbar
            elif field == "qbar/cos(beta_deg)":
                val = self.qbar / cos(self.beta)
            elif field == "p":
                val = self.gyros[n][0]
            elif field == "q":
                val = self.gyros[n][1]
            elif field == "q_term1":
                val = self.q_term1
            elif field == "r":
                val = self.gyros[n][2]
            elif field == "dp":
                val = (self.gyros[n][0] - self.gyros[n-1][0]) / self.dt
            elif field == "dq":
                val = (self.gyros[n][1] - self.gyros[n-1][1]) / self.dt
            elif field == "dr":
                val = (self.gyros[n][2] - self.gyros[n-1][2]) / self.dt
            elif field == "p*qbar":
                val = self.gyros[n][0]*self.qbar
            elif field == "q*qbar":
                val = self.gyros[n][1]*self.qbar
            elif field == "r*qbar":
                val = self.gyros[n][2]*self.qbar
            elif field == "p*vc_mps":
                val = self.gyros[n][0]*self.vc_mps
            elif field == "q*vc_mps":
                val = self.gyros[n][1]*self.vc_mps
            elif field == "r*vc_mps":
                val = self.gyros[n][2]*self.vc_mps

            elif field == "ax":
                val = self.accels[n][0]
            elif field == "ay":
                val = self.accels[n][1]
            elif field == "ay^2":
                val = self.accels[n][1] * self.accels[n][1]
            elif field == "ay*vc_mps":
                val = self.accels[n][1] * self.vc_mps
            elif field == "ay*qbar":
                val = self.accels[n][1] * self.qbar
            elif field == "ay/vc_mps":
                val = self.accels[n][1] / self.vc_mps
            elif field == "ay/qbar":
                val = self.accels[n][1] / self.qbar
            elif field == "abs(ay)":
                val = abs(self.accels[n][1])
            elif field == "az":
                val = self.accels[n][2]
            elif field == "az/qbar":
                val = self.accels[n][2] / self.qbar
            elif field == "one":
                val = 1.0
            else:
                raise Exception("Sorry, unknown field name requested:", field)
            #if True and params is not None and field in self.output_states:
            if params is not None:
                param = params[index]
                t = param["type"]
                if t == "input" or t == "output":
                    min = param["min"]
                    max = param["max"]
                    std = param["std"]
                    n = 2
                    if val < min - n*std:
                        val = min - n*std
                        print(field, "clipped to:", val)
                    if val > max + n*std:
                        val = max + n*std
                        print(field, "clipped to:", val)
            result.append(val)
        return result

    def state2dict(self, state):
        result = {}
        for i in range(len(state)):
            result[self.state_list[i]] = state[i]
        return result

    def output2dict(self, state):
        output_list = self.get_state_index( self.output_states )
        result = {}
        for i in range(len(output_list)):
            result[self.state_list[output_list[i]]] = state[i]
        return result

