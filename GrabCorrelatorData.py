import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import casperfpga
import struct
import multiprocessing
import time
import sys
import h5py

KatcpRequestFail = casperfpga.katcp_fpga.KatcpRequestFail

strRoachIP = 'catseye'
roachKATCPPort = 7147
gateware = "holo"
katcp_port=7147
show_ri = False


class SubplotAnimation(animation.TimedAnimation):
    def __init__(self, send_pipe, show_ri=False, figsize=(22,12)):
        self.send_pipe = send_pipe
        self.f = np.arange(2048)
        self.fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort, timeout=10)
        self.fpga.get_system_information('%s.fpg' % gateware)
        self.show_ri = show_ri
        fig = plt.figure(figsize=figsize)

        if self.show_ri:
            pos_00_mp = 241
            pos_00_ri = 242
            pos_01_mp = 243
            pos_01_ri = 244
            pos_10_mp = 245
            pos_10_ri = 246
            pos_11_mp = 247
            pos_11_ri = 248
        else:
            pos_00_mp = 221
            pos_01_mp = 222
            pos_10_mp = 223
            pos_11_mp = 224

        self.ax_00_m = fig.add_subplot(pos_00_mp)
        self.ax_00_p = self.ax_00_m.twinx()
        if self.show_ri:
            self.ax_00_ri = fig.add_subplot(pos_00_ri)

        self.ax_01_m = fig.add_subplot(pos_01_mp)
        self.ax_01_p = self.ax_01_m.twinx()
        if self.show_ri:
            self.ax_01_ri = fig.add_subplot(pos_01_ri)

        self.ax_10_m = fig.add_subplot(pos_10_mp)
        self.ax_10_p = self.ax_10_m.twinx()
        if self.show_ri:
            self.ax_10_ri = fig.add_subplot(pos_10_ri)

        self.ax_11_m = fig.add_subplot(pos_11_mp)
        self.ax_11_p = self.ax_11_m.twinx()
        if self.show_ri:
            self.ax_11_ri = fig.add_subplot(pos_11_ri)

        self.ax_00_m.set_title("0x0 mag/phase")
        self.ax_00_m.set_xlabel("Channel")
        self.ax_00_m.set_ylabel("Magnitude (dB)")
        self.ax_00_m.yaxis.label.set_color("blue")
        self.ax_00_p.set_ylabel("Phase (degrees)")
        self.ax_00_p.yaxis.label.set_color("red")

        self.ax_01_m.set_title("0x1 mag/phase")
        self.ax_01_m.set_xlabel("Channel")
        self.ax_01_m.set_ylabel("Magnitude (dB)")
        self.ax_01_m.yaxis.label.set_color("blue")
        self.ax_01_p.set_ylabel("Phase (degrees)")
        self.ax_01_p.yaxis.label.set_color("red")

        self.ax_10_m.set_title("1x0 mag/phase")
        self.ax_10_m.set_xlabel("Channel")
        self.ax_10_m.set_ylabel("Magnitude (dB)")
        self.ax_10_m.yaxis.label.set_color("blue")
        self.ax_10_p.set_ylabel("Phase (degrees)")
        self.ax_10_p.yaxis.label.set_color("red")

        self.ax_11_m.set_title("1x1 mag/phase")
        self.ax_11_m.set_xlabel("Channel")
        self.ax_11_m.set_ylabel("Magnitude (dB)")
        self.ax_11_m.yaxis.label.set_color("blue")
        self.ax_11_p.set_ylabel("Phase (degrees)")
        self.ax_11_p.yaxis.label.set_color("red")

        if self.show_ri:
            self.ax_00_ri.set_title("0x0 real/imag")
            self.ax_00_ri.set_xlabel("Channel")
            self.ax_00_ri.set_ylabel("Value")
            self.ax_01_ri.set_title("0x1 real/imag")
            self.ax_01_ri.set_xlabel("Channel")
            self.ax_01_ri.set_ylabel("Value")
            self.ax_10_ri.set_title("1x0 real/imag")
            self.ax_10_ri.set_xlabel("Channel")
            self.ax_10_ri.set_ylabel("Value")
            self.ax_11_ri.set_title("1x1 real/imag")
            self.ax_11_ri.set_xlabel("Channel")
            self.ax_11_ri.set_ylabel("Value")

        self.line_00_m, = self.ax_00_m.plot([], [], color="blue", label="mag")
        self.line_01_m, = self.ax_01_m.plot([], [], color="blue", label="mag")
        self.line_10_m, = self.ax_10_m.plot([], [], color="blue", label="mag")
        self.line_11_m, = self.ax_11_m.plot([], [], color="blue", label="mag")

        self.line_00_p, = self.ax_00_p.plot([], [], color="red", label="phase")
        self.line_01_p, = self.ax_01_p.plot([], [], color="red", label="phase")
        self.line_10_p, = self.ax_10_p.plot([], [], color="red", label="phase")
        self.line_11_p, = self.ax_11_p.plot([], [], color="red", label="phase")

        if self.show_ri:
            self.line_00_r, = self.ax_00_ri.plot([], [], color="cyan", label="real")
            self.line_01_r, = self.ax_01_ri.plot([], [], color="cyan", label="real")
            self.line_10_r, = self.ax_10_ri.plot([], [], color="cyan", label="real")
            self.line_11_r, = self.ax_11_ri.plot([], [], color="cyan", label="real")

            self.line_00_i, = self.ax_00_ri.plot([], [], color="magenta", label="imag")
            self.line_01_i, = self.ax_01_ri.plot([], [], color="magenta", label="imag")
            self.line_10_i, = self.ax_10_ri.plot([], [], color="magenta", label="imag")
            self.line_11_i, = self.ax_11_ri.plot([], [], color="magenta", label="imag")

        self.ax_00_m.set_xlim(0,2048)
        self.ax_01_m.set_xlim(0,2048)
        self.ax_10_m.set_xlim(0,2048)
        self.ax_11_m.set_xlim(0,2048)

        if self.show_ri:
            self.ax_00_ri.set_xlim(0,2048)
            self.ax_01_ri.set_xlim(0,2048)
            self.ax_10_ri.set_xlim(0,2048)
            self.ax_11_ri.set_xlim(0,2048)

        mlim = 60
        self.ax_00_m.set_ylim(0, mlim)
        self.ax_01_m.set_ylim(0, mlim)
        self.ax_10_m.set_ylim(0, mlim)
        self.ax_11_m.set_ylim(0, mlim)

        plim = 190
        self.ax_00_p.set_ylim(-plim, plim)
        self.ax_01_p.set_ylim(-plim, plim)
        self.ax_10_p.set_ylim(-plim, plim)
        self.ax_11_p.set_ylim(-plim, plim)

        if self.show_ri:
            rilim = 20000
            self.ax_00_ri.set_ylim(-rilim, rilim)
            self.ax_01_ri.set_ylim(-rilim, rilim)
            self.ax_10_ri.set_ylim(-rilim, rilim)
            self.ax_11_ri.set_ylim(-rilim, rilim)

        animation.TimedAnimation.__init__(self, fig, interval=1010)

    def _draw_frame(self, framedata):
        try:
            p00_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x0_real_msb", 8192, 0)))
            p00_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x0_imag_msb", 8192, 0)))
        except KatcpRequestFail:
            print "Couldn't get 00 data."
            p00_r = np.zeros(2048)
            p00_i = np.zeros(2048)
        p00 = p00_r + 1j*p00_i

        try:
            p11_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x1_real_msb", 8192, 0)))
            p11_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x1_imag_msb", 8192, 0)))
        except KatcpRequestFail:
            print "Couldn't get 11 data."
            p11_r = np.zeros(2048)
            p11_i = np.zeros(2048)
        p11 = p11_r + 1j*p11_i

        try:
            p01_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x1_real_msb", 8192, 0)))
            p01_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x1_imag_msb", 8192, 0)))
        except KatcpRequestFail:
            print "Couldn't get 01 data."
            p01_r = np.zeros(2048)
            p01_i = np.zeros(2048)
        p01 = p01_r + 1j*p01_i

        try:
            p10_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x0_real_msb", 8192, 0)))
            p10_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x0_imag_msb", 8192, 0)))
        except KatcpRequestFail:
            print "Couldn't get 10 data."
            p10_r = np.zeros(2048)
            p10_i = np.zeros(2048)
        p10 = p10_r + 1j*p10_i

        self.send_pipe.send((p00, p01, p10, p11))

        p00_dB = 10 * np.log10(np.abs(p00))
        p01_dB = 10 * np.log10(np.abs(p01))
        p10_dB = 10 * np.log10(np.abs(p10))
        p11_dB = 10 * np.log10(np.abs(p11))

        self.line_00_m.set_data(self.f, p00_dB)
        self.line_01_m.set_data(self.f, p10_dB)
        self.line_10_m.set_data(self.f, p01_dB)
        self.line_11_m.set_data(self.f, p11_dB)

        self.line_00_p.set_data(self.f, np.degrees(np.angle(p00)))
        self.line_01_p.set_data(self.f, np.degrees(np.angle(p01)))
        self.line_10_p.set_data(self.f, np.degrees(np.angle(p10)))
        self.line_11_p.set_data(self.f, np.degrees(np.angle(p11)))

        if self.show_ri:
            self.line_00_r.set_data(self.f, p00_r)
            self.line_01_r.set_data(self.f, p01_r)
            self.line_10_r.set_data(self.f, p10_r)
            self.line_11_r.set_data(self.f, p11_r)

            self.line_00_i.set_data(self.f, p00_i)
            self.line_01_i.set_data(self.f, p01_i)
            self.line_10_i.set_data(self.f, p10_i)
            self.line_11_i.set_data(self.f, p11_i)

        if self.show_ri:
            self._drawn_artists = [self.line_00_m, self.line_01_m, self.line_10_m, self.line_11_m,
                                   self.line_00_p, self.line_01_p, self.line_10_p, self.line_11_p,
                                   self.line_00_r, self.line_01_r, self.line_10_r, self.line_11_r,
                                   self.line_00_i, self.line_01_i, self.line_10_i, self.line_11_i]
        else:
            self._drawn_artists = [self.line_00_m, self.line_01_m, self.line_10_m, self.line_11_m,
                                   self.line_00_p, self.line_01_p, self.line_10_p, self.line_11_p]


    def new_frame_seq(self):
        return iter(range(self.f.size))


    def _init_draw(self):
        if self.show_ri:
            lines = [self.line_00_m, self.line_01_m, self.line_10_m, self.line_11_m,
                     self.line_00_p, self.line_01_p, self.line_10_p, self.line_11_p,
                     self.line_00_r, self.line_01_r, self.line_10_r, self.line_11_r,
                     self.line_00_i, self.line_01_i, self.line_10_i, self.line_11_i]
        else:
            lines = [self.line_00_m, self.line_01_m, self.line_10_m, self.line_11_m,
                     self.line_00_p, self.line_01_p, self.line_10_p, self.line_11_p]
        for l in lines:
            l.set_data([], [])


class h5recorder(object):
    def __init__(self, recv_pipe):
        self.recv_pipe = recv_pipe


    def record_data(self, recv_pipe):
        record = True
        datafile = h5py.File("%s.h5"%(time.strftime("%Y.%m.%d-%H.%M.%S", time.gmtime())), "w")
        data_group = datafile.create_group("Data")
        vis_data = data_group.create_dataset("VisData", (0, 2048, 4, 2), maxshape=(None, 2048, 4, 2), dtype="f4")
        timestamps = data_group.create_dataset("Timestamps", (0,), maxshape=(None,), dtype="f4")
        received_data = 0
        while record:
            data = recv_pipe.recv()
            if data == None:
                print "Poison pill received. Stopping..."
                record = False
            else:
                timestamp = time.time()
                received_data += 1
                print "Received %d accumulations." % received_data
                current_size = timestamps.size
                vis_data.resize((current_size+1, 2048,4,2))
                vis_data[current_size,:,0,0] = np.real(data[0])
                vis_data[current_size,:,0,1] = np.imag(data[0])
                vis_data[current_size,:,1,0] = np.real(data[1])
                vis_data[current_size,:,1,1] = np.imag(data[1])
                vis_data[current_size,:,2,0] = np.real(data[2])
                vis_data[current_size,:,2,1] = np.imag(data[2])
                vis_data[current_size,:,3,0] = np.real(data[3])
                vis_data[current_size,:,3,1] = np.imag(data[3])
                timestamps.resize((current_size+1,))
                timestamps[current_size] = timestamp
        print "Broken out of while loop. Process stopped."
        datafile.close()


    def run(self):
        p = multiprocessing.Process(target=self.record_data, args=(self.recv_pipe,))
        p.start()


if __name__ == "__main__":
    recv_pipe, send_pipe = multiprocessing.Pipe(duplex=False)

    rec = h5recorder(recv_pipe)
    rec.run()

    ani = SubplotAnimation(send_pipe, show_ri=show_ri)
    plt.show()

    send_pipe.send(None)
