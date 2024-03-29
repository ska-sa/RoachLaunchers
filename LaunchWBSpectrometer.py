#!RoachSpectrometerLauncher

import casperfpga
import sys
import time
import socket as socket
import struct as struct
import os.path
from shutil import copyfile
import stat
import numpy as np
#import matplotlib.pyplot as plt

def exit_clean():
    try:
        fpga.stop()
    except: pass
    sys.exit()


##### Variables to be set ###########

#Gateware to be loaded. fpg file in the same directory as this script
gateware = 'wb_spect_r2_2019_Oct_04_1132.fpg'

#ROACH PowerPC Network:
strRoachIP = '10.0.2.43'
roachKATCPPort = 7147

#TenGbE Network:
strTGbEDestinationIP = '10.0.3.1'
tGbEDestinationPort = 60000

#Set frame data length in bytes must be submultiple of 16384 ( 1024 frequencies * 2 for complex * 2 for 2 channels with each value a 4 byte uint32_t. Also excludes 8 bytes header of each frame)
#Set interframe length clock cycles, (note 64 bytes can be transferred per cyle)
dataSizePerPacket_B = 1024
interpacketLength_cycles = 16

#FFT shift (With the number in binary each bit represents whether the corresponding stage should right shift once.There are 2048 stages)
coarseFFTShiftMask = 2047

#How many FFT frames to accumulate for. Note: This is inversely proportional to output rate and time resolution and directly proportional to size of output numbers
#TODO this will change now that the sampling frequency has changed...
#accumulationLength = 250000 # 250000 = 0.5s at 1024 MS/s
accumulationLength = 25000
#accumulationLength = 2500 # 250000 = 0.5s at 1024 MS/s

# Digital gain to add before requantising
digitalGain = 0.125

# ADC Attenuation level
ADCAttenuation = 40 # 10 = 5.0 dB

manual_sync = False

####################################

packedIP = socket.inet_aton(strTGbEDestinationIP)
tGbEDestinationIP = struct.unpack("!L", packedIP)[0]

print '\n---------------------------'
print 'Configuration:'
print '---------------------------'
print ' FPGA gateware:			', gateware
print ' Destination 10GbE host:		', strTGbEDestinationIP, '( ', tGbEDestinationIP, ' )'
print ' Data size per packet:		', dataSizePerPacket_B, ' bytes'
print ' Interpacket length		', interpacketLength_cycles, ' cycles'
print ' FFT shift mask			', coarseFFTShiftMask
print ' Accumulation length		', accumulationLength, '(', 2048 * accumulationLength / 800e3, ' ms integration per output )'
print ' Digital Gain                    ', digitalGain
print ' ADC attenuation			', ADCAttenuation, '(', ADCAttenuation / 2, ' dB )'
print '---------------------------'

print '\n---------------------------'
print 'Connecting to FPGA...'
fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort)

if fpga.is_connected():
	print 'Connected.'
else:
        print 'ERROR connecting to KATCP server.'
        exit_clean()

print 'Flashing gateware'

fpga.upload_to_ram_and_program(gateware)
sys.stdout.flush()

print '\n---------------------------'
print 'Setting destination network host...'

fpga.registers.tgbe0_dest_ip.write(reg = tGbEDestinationIP)
fpga.registers.tgbe0_dest_port.write(reg = tGbEDestinationPort)
sys.stdout.flush()

print '\n---------------------------'
print 'Checking 10 Gb Ethernet link state...'

time.sleep(2) # Wait 2 seconds for 10GbE link to come up

bTGbELinkUp = bool(fpga.read_int('tgbe0_linkup'))
if not bTGbELinkUp:
	print 'Link not detected on 10 GbE port 0. Make sure that the cable is connected to port 0 on the ROACH and to a computer NIC or switch on the other end. Exiting.\n'
	#exit_clean()

fpga.registers.eth_data_size_per_packet.write_int(dataSizePerPacket_B)
fpga.registers.eth_interpacket_length.write_int(interpacketLength_cycles)
fpga.registers.eth_packets_per_accum_window.write_int(16384 / dataSizePerPacket_B)

print '10 Gb link is up.'
sys.stdout.flush()

print '\n---------------------------'
print 'Setting FFT shift and accumulation length.'
#Setup values for WB spectrum output
fpga.registers.coarse_fft_shift_mask.write_int(coarseFFTShiftMask) #Shift for each FFT stage (2048 points -> 11 stages. Value is a bit mask so decimal of 11111111111. i.e. 2047)
fpga.registers.accumulation_length.write_int(accumulationLength) #Accumulate for this many FFT frames before outputting

print '\n---------------------------'
print 'Enabling ADCs and setting attentuation.'
#Enable the ADCs
fpga.registers.adc0_en.write_int(1)
fpga.registers.adc1_en.write_int(1)
fpga.registers.adc0_atten.write_int(ADCAttenuation)
fpga.registers.adc1_atten.write_int(ADCAttenuation)

print '\n---------------------------'
print 'Enabling digital gain.'
#Enable the ADCs
fpga.registers.digital_gain.write(reg=digitalGain)
fpga.registers.digital_gain.write(reg=digitalGain)

print '\n---------------------------'
print 'Configuring noise diode.'
fpga.registers.noise_diode_on_length.write_int(1) #Set noise diode duty-cycle in accumulation windows (note values can't be 0 will default to 1)
fpga.registers.noise_diode_off_length.write_int(1) # One second on, 59 seconds off.

fpga.registers.noise_diode_duty_cycle_en.write_int(1) #Noise diode mode: always on (0) or duty-cycle (1) as set above.
fpga.registers.noise_diode_en.write_int(0) #Global enabling or disabling of noise diode

print '\n---------------------------'
print 'Setting RTC and signal board to resync on next PPS pulse...'

#Check clock frequency
clkFreq = fpga.registers.clk_frequency.read_uint()
print 'Clock frequency is: ', clkFreq, ' Hz'
if(clkFreq == 256000000):
  print 'Frequency correct.'
else:
  print '!! Error clock frequency is not correct. Check 10 MHz reference and PPS and that Valon is locked to Ext-Ref !!'


#Important note order of commands: first load time then strobe sync_next_pps. Recommend NTP sync before this if a NTP daemon is not running on this computer.
timeNextPPS = int(round((time.time()) + 1) * 1000000) # +1 for next PPS
timeLSB = (timeNextPPS & 0x00000000ffffffff)
timeMSB = int((timeNextPPS & 0xffffffff00000000) / 2**32)

fpga.registers.time_lsb.write_int(timeLSB)
fpga.registers.time_msb.write_int(timeMSB)

#This should be the last statement of configuration. This will bring the board out of reset state on the next PPS and begin streaming data
fpga.registers.sync_next_pps.write_int(1)
fpga.registers.sync_next_pps.write_int(0)

if manual_sync:
    fpga.registers.manual_sync.write(reg="pulse")

print 'Setting RTC time to    ', timeNextPPS, ' us'
print 'Waiting 1 s to allow for PPS strobe...'
time.sleep(1)

lastTime = fpga.registers.last_timestamp_msb.read_uint() * 2**32 + fpga.registers.last_timestamp_lsb.read_uint()
print 'Last FPGA timestamp was', lastTime, ' us'

timeDifference = lastTime - timeNextPPS

print 'Difference is', timeDifference, 'us'
if(abs(timeDifference) > 1000000):
  print 'Error time is out by > 1 s. Check PPS and clock reference'
else:
  print 'Offset < 1 s. Time primed correctly.'


print '\n---------------------------'
print 'Done'



def get_adc_snap(pol=0):
    fpga.registers.adc_snap_ctrl.write(we=True)
    adc_snap = fpga.snapshots.adc_snap_ss.read(man_trig=True)
    if pol == 0:
        data0 = np.array(adc_snap["data"]["adc_data0_0"])
        data1 = np.array(adc_snap["data"]["adc_data0_1"])
        data2 = np.array(adc_snap["data"]["adc_data0_2"])
        data3 = np.array(adc_snap["data"]["adc_data0_3"])
    elif pol == 1:
        data0 = np.array(adc_snap["data"]["adc_data1_0"])
        data1 = np.array(adc_snap["data"]["adc_data1_1"])
        data2 = np.array(adc_snap["data"]["adc_data1_2"])
        data3 = np.array(adc_snap["data"]["adc_data1_3"])
    else:
        return -1
    data = np.empty((data0.size + data1.size + data2.size + data3.size,), dtype=data0.dtype)
    data[0::4] = data0
    data[1::4] = data1
    data[2::4] = data2
    data[3::4] = data3
    return data

def plot_histogram(data):
    hist = np.histogram(data, bins=256)
    plt.plot(hist[1][:-1], hist[0])
    plt.show()

def plot_requant_snap(accumulation_length=1, db_plot=False, spectrum_size=1024):
    # Snapshot is 2^13 deep, contains 2 samples (even and odd) per "row".
    snap_depth = 2**14
    number_of_snaps = accumulation_length / (snap_depth/spectrum_size)
    extra_spectra = accumulation_length % (snap_depth/spectrum_size)  # For the ones which don't evenly divide into a snap size.

    # 0 for Requant Left
    fpga.registers.stokes_requant_snap_sel.write(reg=0)

    left_accum = np.empty((spectrum_size,), dtype=np.complex)
    for snap_no in range(number_of_snaps):
        left_snap = fpga.snapshots.requant_stokes_snap_ss.read(man_trig=True)
        left_even = np.array(left_snap["data"]["data0"]) + 1j*np.array(left_snap["data"]["data1"])
        left_odd = np.array(left_snap["data"]["data2"]) + 1j*np.array(left_snap["data"]["data3"])
        left_data = np.empty((left_even.size + left_odd.size,), dtype=np.complex)
        left_data[0::2] = left_even
        left_data[1::2] = left_odd
        for i in range(0, left_data.size/spectrum_size, spectrum_size):
            left_accum += left_data[i:i+spectrum_size]

    left_snap = fpga.snapshots.requant_stokes_snap_ss.read(man_trig=True)
    left_even = np.array(left_snap["data"]["data0"]) + 1j*np.array(left_snap["data"]["data1"])
    left_odd = np.array(left_snap["data"]["data2"]) + 1j*np.array(left_snap["data"]["data3"])
    left_data = np.empty((left_even.size + left_odd.size,), dtype=np.complex)
    left_data[0::2] = left_even
    left_data[1::2] = left_odd
    for i in range(0, extra_spectra*spectrum_size, spectrum_size):
        left_accum += left_data[i:i+spectrum_size]

    # 1 for Requant Right
    fpga.registers.stokes_requant_snap_sel.write(reg=1)

    right_accum = np.empty((spectrum_size,), dtype=np.complex)
    for snap_no in range(number_of_snaps):
        right_snap = fpga.snapshots.requant_right_snap_ss.read(man_trig=True)
        right_even = np.array(right_snap["data"]["data0"]) + 1j*np.array(right_snap["data"]["data1"])
        right_odd = np.array(right_snap["data"]["data2"]) + 1j*np.array(right_snap["data"]["data3"])
        right_data = np.empty((right_even.size + right_odd.size,), dtype=np.complex)
        right_data[0::2] = right_even
        right_data[1::2] = right_odd
        for i in range(0, right_data.size/spectrum_size, spectrum_size):
            right_accum += right_data[i:i+spectrum_size]

    right_snap = fpga.snapshots.requant_stokes_snap_ss.read(man_trig=True)
    right_even = np.array(right_snap["data"]["data0"]) + 1j*np.array(right_snap["data"]["data1"])
    right_odd = np.array(right_snap["data"]["data2"]) + 1j*np.array(right_snap["data"]["data3"])
    right_data = np.empty((right_even.size + right_odd.size,), dtype=np.complex)
    right_data[0::2] = right_even
    right_data[1::2] = right_odd
    for i in range(0, extra_spectra*spectrum_size, spectrum_size):
        right_accum += right_data[i:i+spectrum_size]

    if db_plot:
        plt.plot(20*np.log10(np.abs(left_accum)), label="left")
        plt.plot(20*np.log10(np.abs(right_accum)), label="right")
    else:
        plt.plot(np.abs(left_accum), label="left")
        plt.plot(np.abs(right_accum), label="right")
    plt.legend()
    plt.show()


def plot_stokeslr_snap(accumulation_length=1, db_plot=False, spectrum_size=1024):
    # Snapshot is 2^13 deep, contains 2 samples (even and odd) per "row".
    snap_depth = 2**14
    number_of_snaps = accumulation_length / (snap_depth/spectrum_size)
    extra_spectra = accumulation_length % (snap_depth/spectrum_size)  # For the ones which don't evenly divide into a snap size.

    # 2 for Stokes Left/right
    fpga.registers.stokes_requant_snap_sel.write(reg=2)

    left_accum = np.empty((spectrum_size,), dtype=np.complex)
    right_accum = np.empty((spectrum_size,), dtype=np.complex)

    for snap_no in range(number_of_snaps):
        snap = fpga.snapshots.requant_stokes_snap_ss.read(man_trig=True)
        left_even = np.array(left_snap["data"]["data0"])
        left_odd = np.array(left_snap["data"]["data1"])
        left_data = np.empty((left_even.size + left_odd.size,), dtype=np.complex)
        left_data[0::2] = left_even
        left_data[1::2] = left_odd
        for i in range(0, left_data.size/spectrum_size, spectrum_size):
            left_accum += left_data[i:i+spectrum_size]

        right_even = np.array(snap["data"]["data2"])
        right_odd = np.array(snap["data"]["data3"])
        right_data = np.empty((right_even.size + right_odd.size,), dtype=np.complex)
        right_data[0::2] = right_even
        right_data[1::2] = right_odd
        for i in range(0, right_data.size/spectrum_size, spectrum_size):
            right_accum += right_data[i:i+spectrum_size]

    snap = fpga.snapshots.requant_stokes_snap_ss.read(man_trig=True)
    left_even = np.array(snap["data"]["data0"])
    left_odd = np.array(snap["data"]["data1"])
    left_data = np.empty((left_even.size + left_odd.size,), dtype=np.complex)
    left_data[0::2] = left_even
    left_data[1::2] = left_odd
    right_even = np.array(snap["data"]["data2"])
    right_odd = np.array(snap["data"]["data3"])
    right_data = np.empty((right_even.size + right_odd.size,), dtype=np.complex)
    right_data[0::2] = right_even
    right_data[1::2] = right_odd
    for i in range(0, extra_spectra*spectrum_size, spectrum_size):
        left_accum += left_data[i:i+spectrum_size]
        right_accum += right_data[i:i+spectrum_size]

    if db_plot:
        plt.plot(20*np.log10(np.abs(left_accum)), label="left")
        plt.plot(20*np.log10(np.abs(right_accum)), label="right")
    else:
        plt.plot(np.abs(left_accum), label="left")
        plt.plot(np.abs(right_accum), label="right")
    plt.legend()
    plt.show()
