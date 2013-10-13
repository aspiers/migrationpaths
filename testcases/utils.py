#!/usr/bin/python

from vm import VM
from vmhost import VMhost

def create_vmhosts(state, count, arch, ram, dom0_ram):
    width = len(str(count))
    vmhosts = [ ]
    for i in xrange(count):
        vmhost = VMhost("host{0:0{1}}".format(i+1, width), arch, ram, dom0_ram)
        vmhosts.append(vmhost)
    return vmhosts
