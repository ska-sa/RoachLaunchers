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

#gateware = "pulchan_8bit_2017_May_25_1111"
gateware = "pulchan_18bit_requant_2017_May_26_1100"

#Directory on the ROACH NFS filesystem where bof files are kept. (Assumes this is hosted on this machine.)
roachGatewareDir = '/srv/roachfs/fs/boffiles'

#ROACH PowerPC Network:
strRoachIP = 'catseye'
roachKATCPPort = 7147

#TenGbE Network:
strTGbEDestinationIP = '10.0.0.4'
tGbEDestinationPort = 60000

FFTShift = 10 # Until further notice.
RequantGain = 4000

####################################

packedIP = socket.inet_aton(strTGbEDestinationIP)
tGbEDestinationIP = struct.unpack("!L", packedIP)[0]


print '\n---------------------------'
print 'Configuration:'
print '---------------------------'
print ' FPGA gateware:			', gateware
print ' Gateware directory		', roachGatewareDir
print ' Destination 10GbE host:		', strTGbEDestinationIP, '( ', tGbEDestinationIP, ' )'
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

time.sleep(2)

#print '\n---------------------------'
#print 'Setting destination network host...'

#fpga.registers.dest_ip.write(reg = tGbEDestinationIP)
#fpga.registers.dest_port.write(reg = tGbEDestinationPort)
#sys.stdout.flush()

#print '\n---------------------------'
#print 'Checking 10 Gb Ethernet link state...'

#time.sleep(2) # Wait 2 seconds for 10GbE link to come up

#bTGbELinkUp = bool(fpga.read_int('tgbe0_linkup'))
#if not bTGbELinkUp:
#	print 'Link not detected on 10 GbE port 0. Make sure that the cable is connected to port 0 on the ROACH and to a computer NIC or switch on the other end. Exiting.\n'
#	exit_clean()


#print '10 Gb link is up.'
#sys.stdout.flush()

print '\n---------------------------'
print 'Setting FFT shift'
#Setup values for WB spectrum output
fpga.registers.fft_shift.write_int(FFTShift) #Shift for each FFT stage (2048 points -> 11 stages. Value is a bit mask so decimal of 11111111111. i.e. 2047)
fpga.registers.requant_gain.write_int(RequantGain)
sys.stdout.flush()

print '\n---------------------------'
print 'Setting FPGA to sync manually and use self-generated PPS.'
fpga.registers.use_self_pps.write(reg=1)

# Pause 2 seconds to check that everything is working.
time.sleep(2)
#Check clock frequency
clkFreq = fpga.registers.clk_frequency.read_uint()
print 'Clock frequency is: ', clkFreq, ' Hz'
if(clkFreq == 200000000):
  print 'Frequency correct.'
else:
  print '!! Error clock frequency is not correct. Check 10 MHz reference and PPS and that Valon is locked to Ext-Ref !!'


#Important note order of commands: first load time then strobe sync_next_pps. Recommend NTP sync before this if a NTP daemon is not running on this computer.
#timeNextPPS = int(round((time.time()) + 1) * 1000000) # +1 for next PPS
#timeLSB = (timeNextPPS & 0x00000000ffffffff)
#timeMSB = int((timeNextPPS & 0xffffffff00000000) / 2**32)

#fpga.registers.time_lsb.write_int(timeLSB)
#fpga.registers.time_msb.write_int(timeMSB)

#This should be the last statement of configuration. This will bring the board out of reset state on the next PPS and begin streaming data
#fpga.registers.sync_next_pps.write_int(1)
#fpga.registers.sync_next_pps.write_int(0)

# Manual sync just because the GPS-Rb isn't available anymore.
#fpga.registers.manual_sync.write(reg="pulse")

#print 'Setting RTC time to    ', timeNextPPS, ' us'
#print 'Waiting 1 s to allow for PPS strobe...'
#time.sleep(1)

#lastTime = fpga.registers.last_timestamp_msb.read_uint() * 2**32 + fpga.registers.last_timestamp_lsb.read_uint()
#print 'Last FPGA timestamp was', lastTime, ' us'

#timeDifference = lastTime - timeNextPPS

#print 'Difference is', timeDifference, 'us'
#if(abs(timeDifference) > 1000000):
#  print 'Error time is out by > 1 s. Check PPS and clock reference'
#else:
#  print 'Offset < 1 s. Time primed correctly.'

# TODO: Still need to do the whole ARP thing for the 10GbE core. Since this is a single link it's not such an issue but for completeness it should be done.

print '\n---------------------------'
print 'Done programming and configuring'

time.sleep(5)

import numpy as np
import matplotlib.pyplot as plt

left_data = fpga.snapshots.lcp_snap_ss.read()

left_even_r = np.array(left_data["data"]["even_r"])
left_even_i = np.array(left_data["data"]["even_i"])
left_even_cplx = left_even_r + 1j*left_even_i
left_even_abs = np.abs(left_even_cplx)

left_odd_r = np.array(left_data["data"]["odd_r"])
left_odd_i = np.array(left_data["data"]["odd_i"])
left_odd_cplx = left_odd_r + 1j*left_odd_i
left_odd_abs = np.abs(left_odd_cplx)

num_integrations = len(left_odd_r) / 16

spectrum_grid = np.zeros((num_integrations,32))

for i in range(num_integrations):
    for j in range(16):
            spectrum_grid[i,2*j] = left_even_abs[i*16+j]
            spectrum_grid[i,2*j+1] = left_odd_abs[i*16+j]

spectrum_average = np.average(spectrum_grid, axis=0)

plt.plot(spectrum_average)
plt.show()
 

