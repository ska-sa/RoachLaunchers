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
import logging
import matplotlib.pyplot as plt


##### Variables to be set ###########
gateware = "pocket_correlator"
katcp_port=7147

#Directory on the ROACH NFS filesystem where bof files are kept. (Assumes this is hosted on this machine.)
roachGatewareDir = '/srv/roachfs/fs/boffiles'

#ROACH PowerPC Network:
strRoachIP = 'catseye'
roachKATCPPort = 7147

ADCAttenuation = 10
FFTShift = 2**11-1 # Should just be 11 ones.
RequantGain = 1
UseSelfPPS = True
AccumulationLength = (2**28)/1024

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

    p = OptionParser()
    p.set_usage("python " + __file__ + " <ROACH_HOSTNAME_or_IP> [options]")
    p.set_description(__doc__)
    p.add_option('-l', '--acc_len', dest='acc_len', type='int',default=AccumulationLength,
        help='Set the number of vectors to accumulate between dumps. default is (2^28)/1024.')
    p.add_option('-g', '--gain', dest='gain', type='int',default=RequantGain,
        help='Set the digital gain (4bit quantisation scalar). default is %d.'%(RequantGain))
    p.add_option('-s', '--skip', dest='skip', action='store_true',
        help='Skip reprogramming the FPGA and configuring EQ.')
    opts, args = p.parse_args(sys.argv[1:])

    if args==[]:
        print 'Please specify a ROACH board. \nExiting.'
        exit()
    else:
        roach = args[0]

try:
    loggers = []
    lh=casperfpga.log_handlers.DebugLogHandler()
    logger = logging.getLogger(roach)
    logger.addHandler(lh)
    logger.setLevel(10)

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
    fpga = casperfpga.katcp_fpga.KatcpFpga(strRoachIP, roachKATCPPort, timeout=10,logger=logger)

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
    print "Setting DSP control...."
    fpga.registers.dsp_ctrl.write(requant_gain=RequantGain, fft_shift=FFTShift)

    print '\n---------------------------'
    print 'Configuring accumulation period...',
    fpga.registers.acc_len.write_int(opts.acc_len)
    print 'done'

    print "\n---------------------------"
    print "Activating ADCs..."
    fpga.registers.adc_ctrl.write(en0=True, atten0=ADCAttenuation, en1=True, atten1=ADCAttenuation)


    print "\n---------------------------"
    print "Resetting board..."
    fpga.registers.sync_ctrl.write(enable_sync=True, use_self_pps=UseSelfPPS, master_reset="pulse")
    print 'done'

    print "Correlator setup complete. Use TestCorrelator.py to plot output."s

except KeyboardInterrupt:
    exit_clean()
except:
    exit_fail()

exit_clean()
