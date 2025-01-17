#!/usr/bin/env python3

"""run_simulator

Front end to the simulation module

Author: Curtis L. Olson, University of Minnesota, Dept of Aerospace
Engineering and Mechanics, UAV Lab.

"""

from apscheduler.schedulers.background import BackgroundScheduler   # pip install APScheduler (dnf install python3-APScheduler)
import argparse
import os
import time

from comms.HIL_nsLink import HIL
from FCS.fcs_mgr import FCSMgr
from sim.jsbsim import JSBSimWrap
from sim.joystick import Joystick
from visuals.fgfs import fgfs
from visuals.display import Display
from visuals.xp.xp import XPlane

# command line arguments
parser = argparse.ArgumentParser(description="run the simulation")
parser.add_argument("model", help="flight model")
parser.add_argument('--realtime', action='store_true', help='run sim in realtime')
parser.add_argument('--no-trim', action='store_true', help="don't trim")
args = parser.parse_args()

joystick = Joystick()
display = Display()
xp = XPlane()
hil = HIL()

model = 'Rascal110-JSBSim'
#model = 'SR22T'
# pathJSB = os.path.join("/home/clolson/Projects/ADD_Simulator/simulation-python-jsbsim", "JSBSim")
# pathJSB = os.path.join("/Users/Cirrus/Projects/ADD_Simulator/simulation-python-jsbsim", "JSBSim")
#pathJSB = os.path.join("/home/curt/Sync", "JSBSim")
pathJSB = "/home/clolson/Projects/FlightGear/flightgear-fgaddon/Aircraft/Rascal"
sim = JSBSimWrap(model, pathJSB)
sim.SetupICprops()

if not args.no_trim: # fixme
    trimType = 6  # 0 = full, 1 = in air, 2 = on the ground, 6 = no trim! (for ground)
    sim.RunTrim(trimType=trimType, throttle=0.0, flap=0.0)
    sim.DispTrim()
sim.SetTurb(turbSeverity=1, vWind20_mps=2, vWindHeading_deg=45) # Trim with wind, no turbulence

fcs = FCSMgr()

def update():
    joystick.update()
    hil.read()
    fcs.update()
    # hil.read()
    sim.RunSteps(4, updateWind=True)
    sim.PublishProps()
    hil.write()
    fgfs.send_to_fgfs()
    display.update()
    xp.update()

if args.realtime:
    sched = BackgroundScheduler()
    sched.add_job(update, 'interval', seconds=sim.dt*4)
    sched.start()
    while True:
        time.sleep(1)
    sched.shutdown()
else:
    while sim.time <= run_time:
        sim.update()

sim.plot()
