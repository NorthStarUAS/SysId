from math import cos, exp, sin, tan
import numpy as np

from lib.constants import d2r, gravity
from lib.props import accel_node, aero_node, att_node, control_engine_node, control_flight_node, inceptor_node, vel_node

from .NotaPID import NotaPID

class FCS_pbeta():
    def __init__(self):
        # filtered state (clamp to minimum of 25 mps because we need to divide
        # by airspeed and qbar so this must be definitely positive 100% of the time.)
        self.vc_mps = 25
        self.vtrue_mps = 25

        # stick -> rate command scaling
        self.roll_stick_scale = 30 * d2r  # radians
        self.yaw_stick_scale = 20         # maps to beta_deg

        # envelope protection
        self.bank_limit_deg = 60.0

        # integrators
        self.aileron_int = 0.0
        self.rudder_int = 0.0

        # dampers
        self.roll_damp_gain = 1500.0
        self.yaw_damp_gain = 6000.0

        self.roll_helper = NotaPID("roll", -45, 45, integral_gain=1.0, antiwindup=0.25, neutral_tolerance=0.02)
        self.yaw_helper = NotaPID("yaw", -10, 10, integral_gain=-0.01, antiwindup=0.25, neutral_tolerance=0.02)

    def update(self, flying_confidence):
        # fetch and compute all the values needed by the control laws
        self.throttle_cmd = inceptor_node.getFloat("throttle")

        vc_mps = vel_node.getFloat("vc_mps")
        if vc_mps < 25: vc_mps = 25
        self.vc_mps = 0.99 * self.vc_mps + 0.01 * vc_mps
        vtrue_mps = vel_node.getFloat("vtrue_mps")
        if vtrue_mps < 25: vtrue_mps = 25
        self.vtrue_mps = 0.99 * self.vtrue_mps + 0.01 * vtrue_mps
        rho = 1.225
        self.qbar = 0.5 * self.vc_mps**2 * rho

        self.phi_deg = att_node.getFloat("phi_deg")
        self.theta_deg = att_node.getFloat("theta_deg")
        self.p = vel_node.getFloat("p_rps")
        self.q = vel_node.getFloat("q_rps")
        self.r = vel_node.getFloat("r_rps")
        self.ax = accel_node.getFloat("Nx") * gravity
        self.ay = accel_node.getFloat("Ny") * gravity
        self.az = accel_node.getFloat("Nz") * gravity
        self.gbody_x = -sin(self.theta_deg*d2r) * gravity
        self.gbody_y = sin(self.phi_deg*d2r) * cos(self.theta_deg*d2r) * gravity
        self.gbody_z = cos(self.phi_deg*d2r) * cos(self.theta_deg*d2r) * gravity
        self.q_term1 = sin(self.phi_deg*d2r) * (sin(self.phi_deg*d2r) / cos(self.phi_deg*d2r)) / self.vc_mps

        if flying_confidence > 0.5:
            if True:
                # sensed directly (or from sim model)
                self.alpha_deg = aero_node.getFloat("alpha_deg")
                self.beta_deg = aero_node.getFloat("beta_deg")
            else:
                # inertial+airdata estimate (behaves very wrong at low airspeeds, ok in flight!)
                self.alpha_deg = self.alpha_func()
                self.beta_deg = self.beta_func()  # this functions drifts and can get stuck!
        else:
            self.alpha_deg = self.theta_deg
            self.beta_deg = 0

        # Feed forward steady state q and r basd on bank angle/turn rate.
        # Presuming a steady state level turn, compute turn rate =
        # func(velocity, bank angle).  This is the one feed forward term used in
        # this set of control laws and it is purely physics based and works for
        # all fixed wing aircraft.
        if abs(self.phi_deg) < 89:
            turn_rate_rps = tan(self.phi_deg*d2r) * -gravity / vtrue_mps
        else:
            turn_rate_rps = 0
        # compute a baseline q and r for the presumed steady state level turn,
        # this is what we dampen towards
        baseline_q = sin(self.phi_deg*d2r) * turn_rate_rps
        baseline_r = cos(self.phi_deg*d2r) * turn_rate_rps
        # print("tr: %.3f" % turn_rate_rps, "q: %.3f %.3f" % (baseline_q, self.q), "r: %.3f %.3f" % (baseline_r, self.r))

        # Pilot commands
        roll_rate_cmd = inceptor_node.getFloat("aileron") * self.roll_stick_scale
        beta_deg_cmd = -inceptor_node.getFloat("rudder") * self.yaw_stick_scale

        # envelope protection (needs to move after or into the controller or at
        # least incorporate the ff term (and dampers?))  This must consider more
        # than just pitch rate and may need to lower the pitch angle hold value
        # simultaneously, however it takes time for speed to build up and alpha
        # to come down so how/where should the limited 'hold' value get set to?

        # bank angle limits
        max_p = (self.bank_limit_deg - self.phi_deg) * d2r * 0.5
        min_p = (-self.bank_limit_deg - self.phi_deg) * d2r * 0.5

        # Condition and limit the pilot requests
        ref_p = self.roll_helper.get_ref_value(roll_rate_cmd, 0, min_p, max_p, self.phi_deg, flying_confidence)
        ref_beta = self.yaw_helper.get_ref_value(beta_deg_cmd, 0, None, None, 0, flying_confidence)

        # compute the direct surface position to achieve the command (these
        # functions are fit from the original flight data and involve a matrix
        # inversion that is precomputed and the result is static and never needs
        # to be recomputed.)
        raw_aileron_cmd, raw_rudder_cmd = self.lat_func(ref_p, ref_beta)

        # run the integrators.  Tip of the hat to imperfect models vs the real
        # world.  The integrators suck up any difference between the model and
        # the real aircraft. Imperfect models can be due to linear fit limits,
        # change in aircraft weight and balance, change in atmospheric
        # conditions, etc.
        self.aileron_int = self.roll_helper.integrator(ref_p, self.p, flying_confidence)
        self.rudder_int = self.yaw_helper.integrator(ref_beta, self.beta_deg, flying_confidence)

        # dampers, these can be tuned to pilot preference for lighter finger tip
        # flying vs heavy stable flying.
        aileron_damp = self.p * self.roll_damp_gain / self.qbar
        rudder_damp = (self.r - baseline_r) * self.yaw_damp_gain / self.qbar

        # final output command
        aileron_cmd = raw_aileron_cmd + self.aileron_int - aileron_damp
        rudder_cmd = raw_rudder_cmd + self.rudder_int - rudder_damp
        # print("inc_q: %.3f" % pitch_rate_cmd, "bl_q: %.3f" % baseline_q, "ref_q: %.3f" % ref_q,
        #       "raw ele: %.3f" % raw_elevator_cmd, "final ele: %.3f" % elevator_cmd)

        control_flight_node.setFloat("aileron", aileron_cmd)
        control_flight_node.setFloat("rudder", rudder_cmd)

        print (' move outsdie')
        control_flight_node.setBool("flaps_down", inceptor_node.getBool("flaps_down"))
        control_flight_node.setBool("flaps_up", inceptor_node.getBool("flaps_up"))

        throttle_cmd = inceptor_node.getFloat("throttle")
        control_engine_node.setFloat("throttle", throttle_cmd)

    # a simple alpha estimator fit from flight test data
    def alpha_func(self):
        p = 0 # roll rate shows up in our alpha measurement because the alpha vane is at the end of the wing, but let's zero it and ignore that.
        # alpha_deg = -6.519 + 14920.457/self.qbar - 0.331*self.az - 4.432*self.p + 0.243*self.ax + 0.164*self.ay + 3.577*self.q
        alpha_deg = -6.3792 + 14993.7058/self.qbar -0.3121*self.az - 4.3545*p + 5.3980*self.q + 0.2199*self.ax
        return alpha_deg

    # a simple beta estimator fit from flight test data
    def beta_func(self):
        rudder_cmd = inceptor_node.getFloat("rudder")
        # beta_deg = 2.807 - 9.752*self.ay + 0.003*self.ay*self.qbar - 5399.632/self.qbar - 0.712*abs(self.ay)
        beta_deg = -0.3552 - 12.1898*rudder_cmd - 3.5411*self.ay + 7.1957*self.r + 0.0008*self.ay*self.qbar + 0.9769*self.throttle_cmd
        return beta_deg

    # compute model-based aileron and rudder command to simultaneously achieve the reference roll rate and side slip angle.
    Ainv_lat = np.array(
        [[5223.997719570232, 86.53137102359369],
         [3112.870284450966, -187.8833840322353]]
    )
    B_lat = np.array(
        [[-0.3279732547932126, -0.006061380767969274, 0.0017838077680168345, 0.002582130232044947,   8.229002177507066],
         [11.381920691905997,   0.06423929309132188, -0.1514805151401035,   -0.10031783139998209, -318.79044889415076]]
    )
    def lat_func(self, ref_p, ref_beta):
        x = np.array([ref_p, ref_beta])
        b = np.array([1, self.ay, self.gbody_y, self.vc_mps, 1/self.vc_mps])
        y = (self.Ainv_lat @ x - self.B_lat @ b) / self.qbar
        print("lon y:", y)
        return y.tolist()
