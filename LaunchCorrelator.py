#!/usr/bin/env python
'''
This script demonstrates programming an FPGA and configuring a wideband Pocket
correlator using the Python KATCP library along with the katcp_wrapper
distributed in the corr package. Designed for use with CASPER workshop Tutorial 4.
\n\n
Author: Jason Manley, August 2010.
Modified: May 2012, Medicina.
Modified: Aug 2012, Nie Jun
'''

import casperfpga
import time
import numpy as np
import sys
import os.path
from shutil import copyfile
import logging
import stat
import matplotlib.pyplot as plt
import struct

##### Variables to be set ###########
gateware = "holo"
katcp_port=7147

#Directory on the ROACH NFS filesystem where bof files are kept. (Assumes this is hosted on this machine.)
roachGatewareDir = '/srv/roachfs/fs/boffiles'

#ROACH PowerPC Network:
strRoachIP = 'catseye'
roachKATCPPort = 7147
acc_len = 8137 # This is ever so slightly less than 1 second.
ADCAttenuation = 2

def exit_fail():
    print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
    try:
        fpga.stop()
    except: pass
    raise
    exit()

def exit_clean():
    try:
        fpga.stop()
    except: pass
    exit()


if __name__ == '__main__':
    from optparse import OptionParser

    #p = OptionParser()
    #p.set_usage("python " + __file__ + " <ROACH_HOSTNAME_or_IP> [options]")
    #p.set_description(__doc__)
    #p.add_option('-l', '--acc_len', dest='acc_len', type='int',default=AccumulationLength,
    #    help='Set the number of vectors to accumulate between dumps. default is (2^28)/1024.')
    #p.add_option('-g', '--gain', dest='gain', type='int',default=RequantGain,
    #    help='Set the digital gain (4bit quantisation scalar). default is %d.'%(RequantGain))
    #p.add_option('-s', '--skip', dest='skip', action='store_true',
    #    help='Skip reprogramming the FPGA and configuring EQ.')
    #opts, args = p.parse_args(sys.argv[1:])

    #if args==[]:
    #    print 'Please specify a ROACH board. \nExiting.'
    #    exit()
    #else:
    #    strRoachIP = args[0]

try:
    #loggers = []
    #lh=casperfpga.log_handlers.DebugLogHandler()
    #logger = logging.getLogger(strRoachIP)
    #logger.addHandler(lh)
    #logger.setLevel(10)

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
    fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort, timeout=10)

    if fpga.is_connected():
    	print 'Connected.'
    else:
            print 'ERROR connecting to KATCP server.'
            exit_fail()

    print 'Flashing gateware...'

    fpga.system_info['program_filename'] = '%s.bof' % gateware #bof needs to be on the roachfs for this to work
    fpga.program()
    fpga.get_system_information('%s.fpg' % gateware)
    sys.stdout.flush()

    time.sleep(2)

    print "\n---------------------------"
    print "Activating ADCs..."
    fpga.registers.adc_ctrl.write(en0=True, atten0=ADCAttenuation, en1=True, atten1=ADCAttenuation)
    fpga.registers.acc_len.write(reg=acc_len)
    print "Correlator setup complete."

    #time.sleep(2)

    #a_r = np.array(struct.unpack(">2048l", fpga.read("acc_0x0_real_msb", 8192, 0)))
    #a_i = np.array(struct.unpack(">2048l", fpga.read("acc_0x0_imagl_msb", 8192, 0)))
    #a = a_r + 1j*a_i

    #b_r = np.array(struct.unpack(">2048l", fpga.read("acc_1x1_real_msb", 8192, 0)))
    #b_i = np.array(struct.unpack(">2048l", fpga.read("acc_1x1_imag_msb", 8192, 0)))
    #b = b_r + 1j*b_i

    #c_r = np.array(struct.unpack(">2048l", fpga.read("acc_0x1_real_msb", 8192, 0)))
    #c_i = np.array(struct.unpack(">2048l", fpga.read("acc_0x1_imag_msb", 8192, 0)))
    #c = c_r + 1j*c_i

    #d_r = np.array(struct.unpack(">2048l", fpga.read("acc_1x0_real_msb", 8192, 0)))
    #d_i = np.array(struct.unpack(">2048l", fpga.read("acc_1x0_imag_msb", 8192, 0)))
    #d = d_r + 1j*d_i

    #fig = plt.figure(figsize=(12,10))
    #ax1 = fig.add_subplot(241)
    #ax1.plot(10*np.log10(np.abs(a)), 'b', label="mag")
    #ax1.set_ylabel("Magnitude (dB)")
    #ax11 = ax1.twinx()
    #ax11.plot(np.degrees(np.angle(a)), 'r', label="phase")
    #ax11.set_ylabel("Phase (degrees)")
    #ax1.set_title("0x0")

    #ax2 = fig.add_subplot(242)
    #ax2.plot(10*np.log10(np.abs(b)), 'b', label="imag")
    #ax2.set_ylabel("Magnitude (dB)")
    #ax22 = ax2.twinx()
    #ax22.plot(np.degrees(np.angle(b)), 'r', label="phase")
    #ax22.set_ylabel("Phase (degrees)")
    #ax2.set_title("1x1")

    #ax3 = fig.add_subplot(243)
    #ax3.plot(10*np.log10(np.abs(c)), 'b', label="mag")
    #ax3.set_ylabel("Magnitude (dB)")
    #ax33 = ax3.twinx()
    #ax33.plot(np.angle(c), 'r', label="phase")
    #ax33.set_ylabel("Phase (degrees)")
    #ax3.set_title("0x1")

    #ax4 = fig.add_subplot(244)
    #ax4.plot(10*np.log10(np.abs(d)), 'b', label="mag")
    #ax4.set_ylabel("Magnitude (dB)")
    #ax44 = ax4.twinx()
    #ax44.plot(np.angle(d), 'r', label="phase")
    #ax44.set_ylabel("Phase (degrees)")
    #ax4.set_title("1x0")

    #plt.show()

except KeyboardInterrupt:
    exit_clean()
#except:
#    exit_fail()
