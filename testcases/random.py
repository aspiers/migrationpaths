#!/usr/bin/python

from __future__ import absolute_import

import copy
import random

from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
from vmpoolstateerrors import *

def randomly_populate_hosts(state, max_vms=None):
    i = 0
    for vmhost in state.vmhosts():
        free_ram = vmhost.ram - vmhost.dom0_ram
        while True:
            vm_ram = random.randint(128, vmhost.ram)
            if vm_ram > free_ram:
                break
            vm = VM("vm%02d" % (i+1), 'x86_64', vm_ram)
            state.add_vm(vm.name, vmhost.name)
            free_ram -= vm_ram
            i += 1
            if max_vms is not None and i >= max_vms:
                return

def randomly_shuffle(state, n=100):
    if len(state.vms()) == 0:
        return state # avoid error from shuffling empty list

    vm_names = state.vm_names()
    vmhost_names = state.vmhost_names()
    for i in xrange(n):
        vm_to_shuffle = random.choice(vm_names)
        #print "shuffling %s" % vm_to_shuffle
        current_vmhost = state.get_vm_vmhost(vm_to_shuffle)
        shuffled_vmhost_names = copy.copy(vmhost_names)
        random.shuffle(shuffled_vmhost_names)
        new_state = None
        for vmhost_name in shuffled_vmhost_names:
            if vmhost_name == current_vmhost:
                continue
            vmhost = VMhost.vmhosts[vmhost_name]
            try:
                state = state.check_migration_sane(vm_to_shuffle, vmhost)
                #print "shuffled %s to %s" % (vm_to_shuffle, vmhost_name)
                break
            except VMPoolStateSanityError, exc:
                #print "  couldn't shuffle to %s" % vmhost_name
                pass
    return state

def identical_hosts(num_hosts=10, max_vms=None):
    VM.reset()
    VMhost.reset()

    stateA = VMPoolState()
    for i in xrange(num_hosts):
        vmhost = VMhost("host%02d" % (i+1), 'x86_64', 4096, 280)
        stateA.init_vmhost(vmhost.name)

    randomly_populate_hosts(stateA, max_vms)
    stateB = randomly_shuffle(copy.copy(stateA))

    return (stateA, stateB, "no idea what path to expect!")
