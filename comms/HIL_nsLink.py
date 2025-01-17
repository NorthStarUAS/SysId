from scipy.interpolate import interp1d
import socket
import time

from lib.props import airdata_node, control_node, fcs_node, gps_node, imu_node, inceptors_node, power_node

from .nst_messages import airdata_v9, effectors_v1, effectors_v1_id, gps_v5, imu_v6, inceptors_v2, power_v2
from .serial_parser import wrap_packet

link_host = "localhost"
link_recv_port = 5051
sim_recv_port = 5052

class HIL():
    def __init__(self):
        self.start_time = None
        self.sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in.bind( ("", sim_recv_port))
        self.sock_in.setblocking(0)

        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.last_gps_millis = 0.0

        self.batt_ah = 10
        self.max_amp = 15
        self.batt_last_time = 0
        self.batt_used_ah = 0

    def fake_battery(self):
        cells = 4
        batv = [ 3.3, 3.50, 3.65, 3.80, 4.20 ]
        batp = [ 0.0, 0.05, 0.27, 0.83, 1.00 ]
        batf = interp1d(batp, batv)

        imu_millis = imu_node.getUInt("millis")
        imu_time = imu_millis / 1000
        dt = imu_time - self.batt_last_time
        self.batt_last_time = imu_time
        if dt > 0.1:
            dt = 0.1
        thr = fcs_node.getDouble("cmdThrottle_nd")
        dah = thr*self.max_amp * dt / 3600
        self.batt_used_ah += dah
        batt_perc = (self.batt_ah - self.batt_used_ah) / self.batt_ah
        if batt_perc < 0:
            # this is a totally fake battery model intended only to generate
            # some plausible numbers for testing, so recycle the battery to 100%
            # when it's empty and just keep going.
            self.batt_used_ah = 0
        sag = thr * 0.1
        volt = (batf(batt_perc) - sag) * cells
        print("dt: %.2f" % dt, "batt: %.3f" % batt_perc, "dah:", dah, "volt: %.2f" % volt)
        power_node.setUInt("millis", imu_millis)
        power_node.setDouble("avionics_vcc", 5 - sag*0.1)
        power_node.setDouble("main_vcc", volt)
        power_node.setDouble("cell_vcc", volt/cells)
        power_node.setDouble("pwm_vcc", 5.25)
        power_node.setDouble("main_amps", thr*self.max_amp)
        power_node.setDouble("total_mah", self.batt_used_ah*1000)

    def write(self):
        self.fake_battery()

        msg = airdata_v9()
        msg.props2msg(airdata_node)
        msg.index = 0
        buf = msg.pack()
        packet = wrap_packet(msg.id, buf)
        self.sock_out.sendto(packet, (link_host, link_recv_port))

        msg = imu_v6()
        msg.props2msg(imu_node)
        msg.index = 0
        buf = msg.pack()
        packet = wrap_packet(msg.id, buf)
        self.sock_out.sendto(packet, (link_host, link_recv_port))

        msg = inceptors_v2()
        msg.props2msg(inceptors_node)
        msg.master_switch = True
        msg.motor_enable = True
        buf = msg.pack()
        packet = wrap_packet(msg.id, buf)
        self.sock_out.sendto(packet, (link_host, link_recv_port))
        # print("sending inceptors:", msg.id, msg.__dict__)

        msg = gps_v5()
        msg.props2msg(gps_node)
        if msg.millis >= self.last_gps_millis + 200:
            # 5 hz gps
            self.last_gps_millis += 200
            msg.index = 0
            buf = msg.pack()
            packet = wrap_packet(msg.id, buf)
            self.sock_out.sendto(packet, (link_host, link_recv_port))

        msg = power_v2()
        msg.props2msg(power_node)
        msg.index = 0
        buf = msg.pack()
        packet = wrap_packet(msg.id, buf)
        self.sock_out.sendto(packet, (link_host, link_recv_port))

    def read(self):
        data = None
        while True:
            try:
                data, addr = self.sock_in.recvfrom(1024)
            except BlockingIOError:
                break
                # print("nothing to receive")

        if data is not None:
            # trust message integrity because this is a udp link
            packet_id = data[2]
            len_lo = data[3]
            len_hi = data[4]
            packet_len = len_hi*256 + len_lo
            print(packet_len)
            payload = data[5:5+packet_len]
            if packet_id == effectors_v1_id:
                if self.start_time is None:
                    self.start_time = time.time()
                if time.time() > self.start_time + 30:
                    msg = effectors_v1(payload)
                    print("received:", msg.__dict__)
                    inceptors_node.setBool("master_switch", True)  # external FCS control
                    control_node.setDouble("throttle", msg.channel[0])
                    control_node.setDouble("aileron", msg.channel[1])
                    control_node.setDouble("elevator", msg.channel[2])
                    control_node.setDouble("rudder", msg.channel[3])


