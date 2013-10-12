#!/usr/bin/python

from copy import deepcopy
import os
import sys

from termcolor import colored

from types import *
from vm import VM
from vmhost import VMhost
from vmpoolstateerrors import *

class VMPoolState:
    """This class represents a pool of VMs and VM hosts together with
    a particular placement of the VMs across the VM hosts.
    """

    # Define which guest VM architectures can be hosted by which VM
    # host architectures.
    guest_archs_ok = {
        'i386'   : { 'i386' : 1 },
        'x86_64' : { 'i386' : 1, 'x86_64' : 1 },
        }

    dom0_RAM_required = 256

    def __init__(self):
        self.vm2vmhost = { }
        self.vmhost2vms = { }

    def vm_names(self):
        """Returns a list of names of VMs in this state."""
        return self.vm2vmhost.keys()

    def vmhost_names(self):
        """Returns a list of names of VM hosts in this state."""
        return self.vmhost2vms.keys()

    def get_vm_vmhost(self, vm_name):
        """Returns the host for a given VM in this state."""
        return self.vm2vmhost[vm_name]

    def init_vmhost(self, vmhost_name):
        """Adds a new vmhost to the pool by name."""
        if vmhost_name in self.vmhost2vms:
            raise ValueError, "tried to init vmhost %s twice" % vmhost_name
        self.vmhost2vms[vmhost_name] = { }

    def init_by_vmhosts(self, state):
        """Adds multiple VMs and VM hosts in one go, changing the
        current state in place.  The placement is determined by the
        state dict whose keys are VM host names, and whose values are
        the VM objects (N.B. not VM names) corresponding to that key.
        """
        for vmhost_name, vms in state.iteritems():
            self.init_vmhost(vmhost_name)
            for vm in vms:
                self.add_vm(vm.name, vmhost_name)
        return self

    def add_vm(self, vm_name, vmhost_name):
        """Add a VM (by name) to a VM host (by name).
        Changes the current state in-place.
        """
        assert type(vm_name) is StringType
        assert type(vmhost_name) is StringType
        if vm_name in self.vm2vmhost:
            raise ValueError, "tried to init vm %s twice" % vm_name
        self.vm2vmhost[vm_name] = vmhost_name
        if vmhost_name not in self.vmhost2vms:
            self.init_vmhost(vmhost_name)
        self.vmhost2vms[vmhost_name][vm_name] = 1

    def remove_vm(self, vm_name):
        """Remove a VM (by name) from its current VM host.
        Changes the current state in-place.
        """
        if vm_name not in self.vm2vmhost:
            raise KeyError, "VM %s not in pool" % vm_name
        vmhost_name = self.vm2vmhost[vm_name]
        if vmhost_name not in self.vmhost2vms:
            raise RuntimeError, "BUG: no such vmhost %s" % vmhost_name
        del self.vmhost2vms[vmhost_name][vm_name]
        del self.vm2vmhost[vm_name]

    def provision_vm(self, vm_name, vmhost_name):
        """Provision VM (by name) to a VM host (by name).
        Returns the new state.
        """
        new = deepcopy(self)
        new.add_vm(vm_name, vmhost_name)
        return new

    def shutdown_vm(self, vm_name):
        """Shuts down VM (by name).  Returns the new state."""
        new = deepcopy(self)
        new.remove_vm(vm_name)
        return new

# use copy.deepcopy instead
#     def clone(self):
#         new = VMPoolState()
#         new.vm2vmhost  = self.vm2vmhost.copy()
#         new.vmhost2vms = { }
#         for vmhost, vms in self.vmhost2vms.iteritems():
#             new.vmhost2vms[vmhost] = vms.copy()
#         return new

    def migrate(self, vm_name, to_host):
        """Generate a new instance representing the state after
        migration of the VM with name vm_name to to_host.
        """
        assert type(to_host) is StringType
        if to_host not in VMhost.vmhosts:
            raise RuntimeError, "can't migrate %s to non-existent vmhost %s" % \
                (vm_name, to_host)
        from_host = self.vm2vmhost[vm_name]
        if from_host == to_host:
            raise RuntimeError, "can't migrate %s from %s to same vmhost" % \
                  (vm_name, from_host)

        #new = self.clone()
        new = deepcopy(self)
        new.remove_vm(vm_name)
        new.add_vm(vm_name, to_host)
        return new

    def check_migration_sane(self, vm_name, to_host):
        """Checks whether vm can be moved to to_host.  Returns new
        pool state if sane, otherwise raises a VMPoolStateSanityError.
        """
        new_state = self.migrate(vm_name, to_host.name)
        new_state.check_sane()
        return new_state

    def total_guest_RAM(self, vmhost_name):
        guests = self.vmhost2vms[vmhost_name]
        return sum([VM.vms[guest].ram for guest in guests])

    def check_sane(self):
        for vmhost_name in self.vmhost_names():
            self.check_vmhost_sane(vmhost_name)

    def check_vmhost_sane(self, vmhost_name):
        """Raises a VMPoolStateSanityError exception if given VM host is
        capable of hosting VMs allocated to it in this state object.
        """
        guest_RAM_required = self.total_guest_RAM(vmhost_name)
        vmhost_RAM_required = guest_RAM_required \
                            + VMPoolState.dom0_RAM_required
        vmhost_RAM_available = VMhost.vmhosts[vmhost_name].ram
        if vmhost_RAM_required > vmhost_RAM_available:
            raise VMPoolStateRAMError, \
                  "vmhost %s requires %d for guests + %d for dom0 == %d > %d" \
                  % (vmhost_name,
                     guest_RAM_required,
                     VMPoolState.dom0_RAM_required,
                     vmhost_RAM_required,
                     vmhost_RAM_available)
        self.check_vms_sane(vmhost_name)

    def check_vms_sane(self, vmhost_name):
        vmhost = VMhost.vmhosts[vmhost_name]
        vms = self.vmhost2vms[vmhost_name]
        for vm_name in vms:
            vm = VM.vms[vm_name]
            self.check_vm_arch_sane(vm, vmhost)

    def check_vm_arch_sane(self, vm, vmhost):
        ok = VMPoolState.guest_archs_ok
        if vmhost.arch not in ok:
            raise RuntimeError, \
                  "unrecognised arch %s for %s" % (vmhost.arch, vmhost)
        if vm.arch not in ok[vmhost.arch]:
            raise VMPoolStateArchError, \
                  "%s has arch %s; incapable of hosting %s with arch %s" \
                  % (vmhost, vmhost.arch, vm, vm.arch)

    def unique(self):
        """Return unique, deterministic string representing this state."""
        vmhost_strs = [ ]
        for vmhost_name in sorted(self.vmhost_names()):
            vm_names = self.vmhost2vms[vmhost_name].keys()
            vm_names.sort()
            vmhost_strs.append(vmhost_name + "[" + ' '.join(vm_names) + "]")
        return " ".join(vmhost_strs)

    __str__ = unique

    def __eq__(self, other):
        if isinstance(other, VMPoolState):
            return self.unique() == other.unique()
        return NotImplemented

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.unique())

    def ascii_meters(self, host_width, meter_width, indent='',
                     highlight_vms={}):
        s = ''
        for vmhost_name in sorted(self.vmhost_names()):
            vmhost = VMhost.vmhosts[vmhost_name]
            meter = self.vmhost_ascii_meter(vmhost, meter_width, highlight_vms)
            s += "{0}{1:{2}} {3}\n".format(indent,
                                           colored(vmhost, attrs=['bold']),
                                           host_width, meter)
        return s

    def vmhost_ascii_meter(self, vmhost, width, highlight_vms):
        width -= 1 # allow space for trailing '|'
        vm_names = self.vmhost2vms[vmhost.name].keys()
        vm_names.sort()
        vms = [ VM.vms[vm_name] for vm_name in vm_names ]
        ram_used = 0
        doms  = [ ('dom0', VMPoolState.dom0_RAM_required) ]
        doms += [ (vm.name, vm.ram) for vm in vms ]
        ram_used = reduce(lambda acc, dom: acc + dom[1], doms, 0)
        spare_ram = vmhost.ram - ram_used
        if spare_ram > 0:
            spare_ram_label = '%d' % spare_ram
            doms += [ (spare_ram_label, spare_ram) ]
            highlight_vms[spare_ram_label] = ['grey', None, ['bold']]

        meter = ''
        printable_char_count = 0
        offset = 0.0
        for i, (dom_name, dom_ram) in enumerate(doms):
            length = float(dom_ram) / vmhost.ram * width
            offset += length
            dom_width = int(offset) - printable_char_count
            dom_text = ''
            if i > 0:
                meter += '|'
                printable_char_count += 1
            if dom_width <= 1:
                raise RuntimeError("dom labelled '%s' had width %d" %
                                   (dom_name, dom_width))
            dom_text = "{0:^{1}.{1}}".format(dom_name, dom_width - 1)
            printable_char_count += len(dom_text)
            if dom_name in highlight_vms:
                args = highlight_vms[dom_name]
                dom_text = colored(dom_text, *args)
            meter += dom_text

        return "[%s]" % meter
