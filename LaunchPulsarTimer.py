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

def exit_clean():
    try:
        fpga.stop()
    except: pass
    sys.exit()

##### Variables to be set ###########
#gateware = "pulsar_channeliser"
gateware = "pulsar_channeliser_2018_Apr_17_1353"

#Directory on the ROACH NFS filesystem where bof files are kept. (Assumes this is hosted on this machine.)
roachGatewareDir = '/srv/roachfs/fs/boffiles'

#ROACH PowerPC Network:
strRoachIP = 'catseye'
roachKATCPPort = 7147

#TenGbE Network:
strTGbEDestinationIPBandTop = '10.0.0.4'
strTGbEDestinationIPBandBtm = '10.0.0.4'
tGbEDestinationPort = 60000

ADCAttenuation = 10
FFTShift = 10 # Until further notice.
RequantGain = 2
StartChan = 0
TVGEnable = True
UseSelfPPS = True

####################################

# Useful little trick to convert from a human-readable IP addr string to an integer like the ROACH wants.
packedIP = socket.inet_aton(strTGbEDestinationIPBandBtm)
tGbEDestinationIPBtm = struct.unpack("!L", packedIP)[0]
packedIP = socket.inet_aton(strTGbEDestinationIPBandTop)
tGbEDestinationIPTop = struct.unpack("!L", packedIP)[0]

print '\n---------------------------'
print 'Configuration:'
print '---------------------------'
print ' FPGA gateware:			    ', gateware
print ' FFT Shift mask:             ', FFTShift
print ' Requantiser gain:           ', RequantGain
print ' Start from channel:         ', StartChan
print ' Gateware directory		    ', roachGatewareDir
print ' Destination 10GbE IP (Top):	', strTGbEDestinationIPBandTop, '( ', tGbEDestinationIPTop, ' )'
print ' Destination 10GbE IP (Btm):	', strTGbEDestinationIPBandBtm, '( ', tGbEDestinationIPBtm, ' )'
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

print 'Flashing gateware...'

fpga.system_info['program_filename'] = '%s.bof' % gateware #bof needs to be on the roachfs for this to work
fpga.program()
fpga.get_system_information('%s.fpg' % gateware)
sys.stdout.flush()

time.sleep(2)

print "\n---------------------------"
print "Activating ADCs..."
#fpga.registers.adc_ctrl.write(en0=True, atten0=ADCAttenuation, en1=True, atten1=ADCAttenuation)
fpga.registers.adc0_en.write_int(1)
fpga.registers.adc1_en.write_int(1)
fpga.registers.adc0_atten.write_int(ADCAttenuation)
fpga.registers.adc1_atten.write_int(ADCAttenuation)

print '\n---------------------------'
print 'Setting TenGbE destination IP / ports...'

fpga.registers.dest_ip_top.write(reg = tGbEDestinationIPTop)
fpga.registers.dest_port_top.write(reg = tGbEDestinationPort)
fpga.registers.dest_ip_btm.write(reg = tGbEDestinationIPBtm)
fpga.registers.dest_port_btm.write(reg = tGbEDestinationPort)
sys.stdout.flush()

print '\n---------------------------'
print 'Checking 10 Gb Ethernet link state...'
print "TODO - still need to get this part implemented."
#time.sleep(2) # Wait 2 seconds for 10GbE link to come up

#bTGbELinkUp = bool(fpga.read_int('tgbe0_linkup'))
#if not bTGbELinkUp:
#	print 'Link not detected on 10 GbE port 0. Make sure that the cable is connected to port 0 on the ROACH and to a computer NIC or switch on the other end. Exiting.\n'
#	exit_clean()
#print '10 Gb link is up.'
#sys.stdout.flush()

print '\n---------------------------'
print 'Setting FFT shift, requantiser gain and start channel seletion...'
#fpga.registers.dsp_ctrl.write(fft_shift=FFTShift, requant_gain=RequantGain, requant_tvg_en=TVGEnable, band_select=StartChan)
fpga.registers.coarse_fft_shift_mask.write_int(FFTShift)
fpga.registers.digital_gain.write_int(RequantGain)
fpga.registers.coarse_channel_select.write_int(StartChan)
fpga.registers.tvg_en.write_int(TVGEnable)
sys.stdout.flush()

print "\n---------------------------"
print "Allowing DSP chain a moment to breathe..."
time.sleep(5)
sys.stdout.flush()

print "\n---------------------------"
print "Enabling sync with next PPS..."
if UseSelfPPS:
    print "WARNING: USING SELF-GENERATED 1PPS SIGNAL. IF AN EXTERNAL 1PPS IS AVAILABLE IT WILL BE IGNORED."
fpga.registers.sync_ctrl.write(enable_sync=True, use_self_pps=UseSelfPPS)
sys.stdout.flush()

print "\n#############################################"
print "#############################################"
print "### Note: ROACH initialised at UNIX time: ###"
print "### ", int(time.time()) + 1, " ###"
print "#############################################"


print "\n---------------------------"
print "Checking clock information..."
# Pause 2 seconds to check that everything is working.
time.sleep(2)
#Check clock frequency
clkFreq = fpga.registers.clk_frequency.read_uint()
print 'Clock frequency is: ', clkFreq, ' Hz'
if(clkFreq == 200000000):
  print 'Frequency correct.'
else:
  print 'ERROR! Clock frequency is not correct. Check 10 MHz reference and PPS connections.'


#TODO: Legacy from Craig's code. Still need to decide how we want to implement this.
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
print 'Done programming and configuring.'



