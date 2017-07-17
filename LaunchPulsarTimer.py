#!RoachSpectrometerLauncher

import casperfpga
import sys
import time
import socket as socket
import struct as struct
import os.path
#from shutil import copyfile
import stat
import numpy as np

def exit_clean():
    try:
        fpga.stop()
    except: pass
    sys.exit()

##### Variables to be set ###########
gateware = "pulsar_channeliser"

#Directory on the ROACH NFS filesystem where bof files are kept. (Assumes this is hosted on this machine.)
roachGatewareDir = '/srv/roachfs/fs/boffiles'

#ROACH PowerPC Network:
strRoachIP = 'catseye'
roachKATCPPort = 7147

#TenGbE Network:
#TODO: Fix IP addresses when installed on-site.
strTGbEDestinationIPBandTop = '10.0.0.4' # This traffic will originate from 10.0.0.10
strTGbEDestinationIPBandBtm = '10.0.0.5' # This traffic will originate from 10.0.0.20
tGbEDestinationPort = 60000

# User Variables
ADCAttenuation = 10
FFTShift = 42 # This means 101010 in binary. Should work for now.
RequantGain = 2
StartChan = 4
TVGEnable = True
UseSelfPPS = True

# For test / debug purposes:
Pause = True

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

if Pause:
    print "Pausing as configured:"
    for i in range(3,0,-1):
        print i
        time.sleep(1)
	sys.stdout.flush()
 
print "\n---------------------------"
print "Activating ADCs..."
fpga.registers.adc_ctrl.write(en0=True, atten0=ADCAttenuation, en1=True, atten1=ADCAttenuation)

if Pause:
    print "Pausing as configured:"
    for i in range(3,0,-1):
        print i
        time.sleep(1)
	sys.stdout.flush()
 


print '\n---------------------------'
print 'Setting TenGbE destination IP / ports...'

fpga.registers.dest_ip_top.write(reg = tGbEDestinationIPTop)
fpga.registers.dest_port_top.write(reg = tGbEDestinationPort)
fpga.registers.dest_ip_btm.write(reg = tGbEDestinationIPBtm)
fpga.registers.dest_port_btm.write(reg = tGbEDestinationPort)
sys.stdout.flush()
if Pause:
    print "Pausing as configured:"
    for i in range(3,0,-1):
        print i
        time.sleep(1)
	sys.stdout.flush()
 
print '\n---------------------------'
print 'Checking 10 Gb Ethernet link state...'
time.sleep(2) # Wait 2 seconds for 10GbE link to come up

TGbELinkUp = fpga.registers.ten_gbe_status.read()
if not (bool(TGbELinkUp["data"]["ten_gbe_0_linkup"]) and bool(TGbELinkUp["data"]["ten_gbe_1_linkup"])):
	print 'Link not detected on one of the 10 GbE ports. Make sure that CX4 cables are connected to ports 0 and 1 on the ROACH and to the Pulsar Timer NIC. Exiting.\n'
	#TODO: This needs to be sorted. Can't test this in my current config.
	#exit_clean()
print '10 Gb links are up.'
sys.stdout.flush()
 
print '\n---------------------------'
print 'Setting FFT shift, requantiser gain and start channel seletion...'
fpga.registers.dsp_ctrl.write(fft_shift=FFTShift, requant_gain=RequantGain, requant_tvg_en=TVGEnable, band_select=StartChan)
sys.stdout.flush()
 
print "\n---------------------------"
print "Enabling sync with next PPS..."
if UseSelfPPS:
    print "WARNING: USING SELF-GENERATED 1PPS SIGNAL. IF AN EXTERNAL 1PPS IS AVAILABLE IT WILL BE IGNORED."
fpga.registers.sync_ctrl.write(self_pps=UseSelfPPS)
sys.stdout.flush()

init_time = 0

#
while True:
    init_time = time.time()
    fraction = init_time - np.trunc(init_time)
    if fraction > 0.2 and fraction < 0.5:
        init_time = int(np.trunc(init_time)) + 2
        break

fpga.registers.sync_ctrl.write(arm="pulse")


print "\n########################################"
print "########################################"
print "### Note: ROACH synced at UNIX time: ###"
print "### ", int(time.time()) + 2, " ###"
print "########################################"


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


# TODO: Still need to do the whole ARP thing for the 10GbE core. Since this is a single link it's not such an issue but for completeness it should be done.

print '\n---------------------------'
print 'Done programming and configuring.'



