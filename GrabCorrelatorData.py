import numpy as np
import matplotlib.pyplot as plt
# from matplotlib.lines import Line2D
import matplotlib.animation as animation
import casperfpga
import struct

strRoachIP = 'catseye'
roachKATCPPort = 7147
gateware = "holo"
katcp_port=7147


class SubplotAnimation(animation.TimedAnimation):
    def __init__(self, show_ri=False, figsize=(10,10)):

        self.f = np.arange(2048)
        self.fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort, timeout=10)
        self.fpga.get_system_information('%s.fpg' % gateware)

        fig = plt.figure(figsize=figsize)

        self.ax_00_m = fig.add_subplot(241)
        self.ax_00_p = self.ax_00_m.twinx()
        self.ax_00_ri = fig.add_subplot(242)
        self.ax_01_m = fig.add_subplot(243)
        self.ax_01_p = self.ax_01_m.twinx()
        self.ax_01_ri = fig.add_subplot(244)
        self.ax_10_m = fig.add_subplot(245)
        self.ax_10_p = self.ax_10_m.twinx()
        self.ax_10_ri = fig.add_subplot(246)
        self.ax_11_m = fig.add_subplot(247)
        self.ax_11_p = self.ax_11_m.twinx()
        self.ax_11_ri = fig.add_subplot(248)

        self.ax_00_m.set_title("0x0 mag/phase")
        self.ax_01_m.set_title("0x1 mag/phase")
        self.ax_10_m.set_title("1x0 mag/phase")
        self.ax_11_m.set_title("1x1 mag/phase")

        self.ax_00_ri.set_title("0x0 real/imag")
        self.ax_01_ri.set_title("0x1 real/imag")
        self.ax_10_ri.set_title("1x0 real/imag")
        self.ax_11_ri.set_title("1x1 real/imag")

        self.line_00_m, = self.ax_00_m.plot([], [], color="blue", label="mag")
        self.line_01_m, = self.ax_01_m.plot([], [], color="blue", label="mag")
        self.line_10_m, = self.ax_10_m.plot([], [], color="blue", label="mag")
        self.line_11_m, = self.ax_11_m.plot([], [], color="blue", label="mag")

        self.line_00_p, = self.ax_00_p.plot([], [], color="red", label="phase")
        self.line_01_p, = self.ax_01_p.plot([], [], color="red", label="phase")
        self.line_10_p, = self.ax_10_p.plot([], [], color="red", label="phase")
        self.line_11_p, = self.ax_11_p.plot([], [], color="red", label="phase")

        self.line_00_r, = self.ax_00_ri.plot([], [], color="cyan", label="real")
        self.line_01_r, = self.ax_01_ri.plot([], [], color="cyan", label="real")
        self.line_10_r, = self.ax_10_ri.plot([], [], color="cyan", label="real")
        self.line_11_r, = self.ax_11_ri.plot([], [], color="cyan", label="real")

        self.line_00_i, = self.ax_00_ri.plot([], [], color="magenta", label="imag")
        self.line_01_i, = self.ax_01_ri.plot([], [], color="magenta", label="imag")
        self.line_10_i, = self.ax_10_ri.plot([], [], color="magenta", label="imag")
        self.line_11_i, = self.ax_11_ri.plot([], [], color="magenta", label="imag")

        animation.TimedAnimation.__init__(self, fig, interval=1000, blit=True)

    def _draw_frame(self, framedata):
        p00_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x0_real_msb", 8192, 0)))
        p00_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x0_imag_msb", 8192, 0)))
        p00 = p00_r + 1j*p00_i

        p11_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x1_real_msb", 8192, 0)))
        p11_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x1_imag_msb", 8192, 0)))
        p11 = p11_r + 1j*p11_i

        p01_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x1_real_msb", 8192, 0)))
        p01_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_0x1_imag_msb", 8192, 0)))
        p01 = p01_r + 1j*p01_i

        p10_r = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x0_real_msb", 8192, 0)))
        p10_i = np.array(struct.unpack(">2048l", self.fpga.read("acc_1x0_imag_msb", 8192, 0)))
        p10 = p10_r + 1j*p10_i

        p00_dB = 10 * np.log10(np.abs(p00))
        p01_dB = 10 * np.log10(np.abs(p01))
        p10_dB = 10 * np.log10(np.abs(p10))
        p11_dB = 10 * np.log10(np.abs(p11))

        self.line_00_m.set_data(self.f, p00_dB)
        self.line_01_m.set_data(self.f, p10_dB)
        self.line_10_m.set_data(self.f, p01_dB)
        self.line_11_m.set_data(self.f, p11_dB)

        self.ax_00_m.set_ylim(np.min(p00_dB) - 0.1*(np.max(p00_dB) - np.min(p00_dB)),
                              np.max(p00_dB) + 0.1*(np.max(p00_dB) - np.min(p00_dB)))
        self.ax_01_m.set_ylim(np.min(p01_dB) - 0.1*(np.max(p01_dB) - np.min(p01_dB)),
                              np.max(p01_dB) + 0.1*(np.max(p01_dB) - np.min(p01_dB)))
        self.ax_10_m.set_ylim(np.min(p10_dB) - 0.1*(np.max(p10_dB) - np.min(p10_dB)),
                              np.max(p10_dB) + 0.1*(np.max(p10_dB) - np.min(p10_dB)))
        self.ax_11_m.set_ylim(np.min(p11_dB) - 0.1*(np.max(p11_dB) - np.min(p11_dB)),
                              np.max(p11_dB) + 0.1*(np.max(p11_dB) - np.min(p11_dB)))

        self.ax_00_m.set_xlim(0,2048)
        self.ax_01_m.set_xlim(0,2048)
        self.ax_10_m.set_xlim(0,2048)
        self.ax_11_m.set_xlim(0,2048)

        self.ax_00_ri.set_xlim(0,2048)
        self.ax_01_ri.set_xlim(0,2048)
        self.ax_10_ri.set_xlim(0,2048)
        self.ax_11_ri.set_xlim(0,2048)

        self.line_00_p.set_data(self.f, np.degrees(np.angle(p00)))
        self.line_01_p.set_data(self.f, np.degrees(np.angle(p01)))
        self.line_10_p.set_data(self.f, np.degrees(np.angle(p10)))
        self.line_11_p.set_data(self.f, np.degrees(np.angle(p11)))

        self.ax_00_p.relim()
        self.ax_01_p.relim()
        self.ax_10_p.relim()
        self.ax_11_p.relim()

        self.line_00_r.set_data(self.f, p00_r)
        self.line_01_r.set_data(self.f, p01_r)
        self.line_10_r.set_data(self.f, p10_r)
        self.line_11_r.set_data(self.f, p11_r)

        self.line_00_i.set_data(self.f, p00_i)
        self.line_01_i.set_data(self.f, p01_i)
        self.line_10_i.set_data(self.f, p10_i)
        self.line_11_i.set_data(self.f, p11_i)

        self.ax_00_ri.relim()
        self.ax_01_ri.relim()
        self.ax_10_ri.relim()
        self.ax_11_ri.relim()

        self._drawn_artists = [self.line_00_m, self.line_01_m, self.line_10_m, self.line_11_m,
                               self.line_00_p, self.line_01_p, self.line_10_p, self.line_11_p,
                               self.line_00_r, self.line_01_r, self.line_10_r, self.line_11_r,
                               self.line_00_i, self.line_01_i, self.line_10_i, self.line_11_i]

    def new_frame_seq(self):
        return iter(range(self.f.size))

    def _init_draw(self):
        lines = [self.line_00_m, self.line_01_m, self.line_10_m, self.line_11_m,
                 self.line_00_p, self.line_01_p, self.line_10_p, self.line_11_p,
                 self.line_00_r, self.line_01_r, self.line_10_r, self.line_11_r,
                 self.line_00_i, self.line_01_i, self.line_10_i, self.line_11_i]
        for l in lines:
            l.set_data([], [])


if __name__ == "__main__":
    ani = SubplotAnimation()
    plt.show()
