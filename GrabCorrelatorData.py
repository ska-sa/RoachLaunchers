import casperfpga
import struct
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as anim

strRoachIP = 'catseye'
roachKATCPPort = 7147
gateware = "holo"
katcp_port=7147

fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort, timeout=10)
fpga.get_system_information('%s.fpg' % gateware)

a_r = np.array(struct.unpack(">2048l", fpga.read("acc_0x0_real_msb", 8192, 0)))
a_i = np.array(struct.unpack(">2048l", fpga.read("acc_0x0_imag_msb", 8192, 0)))
a = a_r + 1j*a_i

b_r = np.array(struct.unpack(">2048l", fpga.read("acc_1x1_real_msb", 8192, 0)))
b_i = np.array(struct.unpack(">2048l", fpga.read("acc_1x1_imag_msb", 8192, 0)))
b = b_r + 1j*b_i

c_r = np.array(struct.unpack(">2048l", fpga.read("acc_0x1_real_msb", 8192, 0)))
c_i = np.array(struct.unpack(">2048l", fpga.read("acc_0x1_imag_msb", 8192, 0)))
c = c_r + 1j*c_i

d_r = np.array(struct.unpack(">2048l", fpga.read("acc_1x0_real_msb", 8192, 0)))
d_i = np.array(struct.unpack(">2048l", fpga.read("acc_1x0_imag_msb", 8192, 0)))
d = d_r + 1j*d_i

fig = plt.figure(figsize=(25,18))

ax1 = fig.add_subplot(241)
ax1.plot(10*np.log10(np.abs(a)), 'b', label="mag")
ax1.set_ylabel("Magnitude (dB)")
ax11 = ax1.twinx()
ax11.plot(np.degrees(np.angle(a)), 'r.', label="phase")
ax11.set_ylabel("Phase (degrees)")
ax1.set_title("0x0")

ax12 = fig.add_subplot(242)
ax12.plot(a.real, 'g', label="real")
ax12.plot(a.imag, 'y', label="imag")
ax12.legend()

ax2 = fig.add_subplot(243)
ax2.plot(10*np.log10(np.abs(b)), 'b', label="imag")
ax2.set_ylabel("Magnitude (dB)")
ax22 = ax2.twinx()
ax22.plot(np.degrees(np.angle(b)), 'r.', label="phase")
ax22.set_ylabel("Phase (degrees)")
ax2.set_title("1x1")

ax22 = fig.add_subplot(244)
ax22.plot(b.real, 'g', label="real")
ax22.plot(b.imag, 'y', label="imag")
ax22.legend()

ax3 = fig.add_subplot(245)
ax3.plot(10*np.log10(np.abs(c)), 'b', label="mag")
ax3.set_ylabel("Magnitude (dB)")
ax33 = ax3.twinx()
ax33.plot(np.degrees(np.angle(c)), 'r.', label="phase")
ax33.set_ylabel("Phase (degrees)")
ax3.set_title("0x1")

ax32 = fig.add_subplot(246)
ax32.plot(c.real, 'g', label="real")
ax32.plot(c.imag, 'y', label="imag")
ax32.legend()

ax4 = fig.add_subplot(247)
ax4.plot(10*np.log10(np.abs(d)), 'b', label="mag")
ax4.set_ylabel("Magnitude (dB)")
ax44 = ax4.twinx()
ax44.plot(np.degrees(np.angle(d)), 'r.', label="phase")
ax44.set_ylabel("Phase (degrees)")
ax4.set_title("1x0")

ax42 = fig.add_subplot(248)
ax42.plot(d.real, 'g', label="real")
ax42.plot(d.imag, 'y', label="imag")
ax42.legend()

fig.tight_layout()

plt.show()
