#!/usr/bin/python

from __future__ import absolute_import

import copy
import random

from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
from vmpoolstateerrors import *
import testcases.utils

def randomly_populate_hosts(state, max_vms=None, min_vm_ram=None, max_vm_ram=None):
    i = 0
    width = 2 if max_vms is None else len(str(max_vms))
    if min_vm_ram is None:
        min_vm_ram = 128
    for vmhost in state.vmhosts():
        if max_vm_ram is None:
            max_vm_ram = vmhost.ram
        free_ram = vmhost.ram - vmhost.dom0_ram
        while True:
            vm_ram = random.randint(min_vm_ram, max_vm_ram)
            if vm_ram > free_ram:
                break
            vm = VM("vm{0:0{1}}".format(i+1, width), 'x86_64', vm_ram)
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

def identical_hosts(num_hosts=10, max_vms=None,
                    min_vm_ram=None, max_vm_ram=None):
    VM.reset()
    VMhost.reset()

    stateA = VMPoolState()
    vmhosts = testcases.utils.create_vmhosts(num_hosts, 'x86_64', 4096, 280)
    for vmhost in vmhosts:
        stateA.init_vmhost(vmhost.name)

    randomly_populate_hosts(stateA, max_vms,
                            min_vm_ram=min_vm_ram,
                            max_vm_ram=max_vm_ram)
    stateB = randomly_shuffle(copy.copy(stateA))

    return (stateA, stateB, "no idea what path to expect!")
