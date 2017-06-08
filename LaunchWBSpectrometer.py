#!RoachSpectrometerLauncher

import casperfpga
import sys
import time
import socket as socket
import struct as struct
import os.path
from shutil import copyfile
import stat
import numpy

def exit_clean():
    try:
        fpga.stop()
    except: pass
    sys.exit()

##### Variables to be set ###########

#Gateware to be loaded.a bof should be on the ROACH and a fpg file in the same directory as this script
#gateware = 'wb_spectrometer_16_2016_Feb_24_1041' # Older one, linearity problem.
gateware = "wb_spectrometer_17_2016_Aug_26_1630" # Newer one, still not linear but high-end problem fixed.


#Directory on the ROACH NFS filesystem where bof files are kept. (Assumes this is hosted on this machine.)
roachGatewareDir = '/srv/roachfs/fs/boffiles'

#ROACH PowerPC Network:
strRoachIP = 'helix'
roachKATCPPort = 7147

#TenGbE Network:
strTGbEDestinationIP = '10.0.0.4'
tGbEDestinationPort = 60000

#Set frame data length in bytes must be submultiple of 16384 ( 1024 frequencies * 2 for complex * 2 for 2 channels with each value a 4 byte uint32_t. Also excludes 8 bytes header of each frame)
#Set interframe length clock cycles, (note 64 bytes can be transferred per cyle)
dataSizePerPacket_B = 1024
interpacketLength_cycles = 16

#FFT shift (With the number in binary each bit represents whether the corresponding stage should right shift once.There are 2048 stages)
coarseFFTShiftMask = 2047 #shift all stages.

#Enable calculation of stokes parameters (otherwise complex PFB/FFT output)
enableStokes = 1;

#The PFB windowing can be bypassed so thay only a FFT is performed for channlising
bypassPFB = 0;

#How many FFT frames to accumulate for. Note: This is inversely proportional to output rate and time resolution and directly proportional to size of output numbers
<<<<<<< Updated upstream
# 39062 is just a touch short of 1 second.
accumulationLength = 3125*125

ADCAttenuation =40

#Threshold detection for ADC to ensure input signal is in the required range
lowerADCThreshold = 1000
upperADCThreshold = 100000
ADCThresholdAccumLength = 1000 #Note accumulation is done with every 4th sample at 800 MSps

####################################

packedIP = socket.inet_aton(strTGbEDestinationIP)
tGbEDestinationIP = struct.unpack("!L", packedIP)[0]

powerPerADCValue_mW = pow(1.9 / pow(2, 8), 2) / 50 * 1000 #V*V/R to get power with 1.9V across 8 bits into 50 Ohm impedance.

print '\n---------------------------'
print 'Configuration:'
print '---------------------------'
print ' FPGA gateware:			', gateware
print ' Gateware directory		', roachGatewareDir
print ' Destination 10GbE host:		', strTGbEDestinationIP, '( ', tGbEDestinationIP, ' )'
print ' Data size per packet:		', dataSizePerPacket_B, ' bytes'
print ' Interpacket length		', interpacketLength_cycles, ' cycles'
print ' FFT shift mask			', coarseFFTShiftMask
print ' Accumulation length		', accumulationLength, '(', 2048 * accumulationLength / 800e3, ' ms integration per output )'
print ' ADC attenuation			', ADCAttenuation, '(', ADCAttenuation / 2, ' dB )'
print ' ADC upper threshold		', lowerADCThreshold, '(', 10 * numpy.log10( powerPerADCValue_mW * lowerADCThreshold / ADCThresholdAccumLength ), ' dBm at ADC input )'
print ' ADC lower threshold		', upperADCThreshold, '(', 10 * numpy.log10( powerPerADCValue_mW * upperADCThreshold / ADCThresholdAccumLength ), ' dBm at ADC input )'
print ' ADC thres accumulation length	', ADCThresholdAccumLength, '(', ADCThresholdAccumLength / 50, ' dB )'
print '---------------------------'

print '\n---------------------------'
print 'Checking gateware...'
if not( roachGatewareDir.endswith('/') ):
  roachGatewareDir += '/'

if os.path.isfile(roachGatewareDir + gateware + '.bof'):
  print 'Found bof file:', gateware + '.bof'
else:
  print 'Copying bof file', gateware + '.bof', 'to NFS (' +  roachGatewareDir + ')'
  copyfile(gateware + '.bof', roachGatewareDir + gateware + '.bof')
  os.chmod(roachGatewareDir + gateware + '.bof', stat.S_IXUSR | stat.S_IXGRP |  stat.S_IXOTH)

print '\n---------------------------'
print 'Connecting to FPGA...'
fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort)

if fpga.is_connected():
	print 'Connected.'
else:
        print 'ERROR connecting to KATCP server.'
        exit_clean()

print 'Flashing gateware'

fpga.system_info['program_filename'] = '%s.bof' % gateware #bof needs to be on the roachfs for this to work
fpga.program()
fpga.get_system_information('%s.fpg' % gateware)
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
	exit_clean()

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
print 'Enabling/disabling Stokes Parameter Calculation.'
fpga.registers.stokes_enable.write_int(enableStokes)

print '\n---------------------------'
print 'Enabling/disabling PFB bypass.'
fpga.registers.bypass_pfb.write_int(bypassPFB)

print '\n---------------------------'
print 'Enabling ADCs and setting attentuation.'
#Enable the ADCs
fpga.registers.adc0_en.write_int(1)
fpga.registers.adc1_en.write_int(1)
fpga.registers.adc0_atten.write_int(ADCAttenuation)
fpga.registers.adc1_atten.write_int(ADCAttenuation)

print '\n---------------------------'
print 'Setting up ADC threshold notification.'
fpga.registers.upper_adc_threshold.write_int(upperADCThreshold)
fpga.registers.lower_adc_threshold.write_int(lowerADCThreshold)
fpga.registers.adc_threshold_acc_length.write_int(ADCThresholdAccumLength)

print '\n---------------------------'
print 'Configuring noise diode.'
fpga.registers.noise_diode_on_length.write_int(1) #Set noise diode duty-cycle in accumulation windows (note values can't be 0 will default to 1)
fpga.registers.noise_diode_off_length.write_int(12) # One second on, 59 seconds off.

fpga.registers.noise_diode_duty_cycle_en.write_int(0) #Noise diode mode: always on (0) or duty-cycle (1) as set above.
fpga.registers.noise_diode_en.write_int(0) #Global enabling or disabling of noise diode

print '\n---------------------------'
print 'Setting RTC and signal board to resync on next PPS pulse...'

#Check clock frequency
clkFreq = fpga.registers.clk_frequency.read_uint()
print 'Clock frequency is: ', clkFreq, ' Hz'
if(clkFreq == 200000000):
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

fpga.registers.manual_sync.write(reg="pulse")
