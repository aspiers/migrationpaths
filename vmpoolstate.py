#!/usr/bin/python

from copy import deepcopy
import sys

from types import *
from vm import VM
from vmhost import VMhost
from vmpoolstateerrors import *

class VMPoolState:
    """
    This class represents a pool of VMs and VM hosts together with
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

    def vms(self):
        return self.vm2vmhost.keys()

    def vmhosts(self):
        return self.vmhost2vms.keys()

    def get_vm_vmhost(self, vm):
        return self.vm2vmhost[vm]

    def init_vmhost(self, vmhost_name):
        """Adds a new vmhost to the pool."""
        if vmhost_name in self.vmhost2vms:
            raise ValueError, "tried to init vmhost %s twice" % vmhost_name
        self.vmhost2vms[vmhost_name] = { }
        
    def init_by_vmhosts(self, state):
        """
        Adds multiple VMs and VM hosts in one go.  The placement is
        determined by the state dict whose keys are VM host names,
        and whose values are the VM objects (N.B. not VM names)
        corresponding to that key.
        """
        for vmhost_name, vms in state.iteritems():
            self.init_vmhost(vmhost_name)
            for vm in vms:
                self.add_vm(vm.name, vmhost_name)
        return self

    def add_vm(self, vm_name, vmhost_name):
        """Add a VM (by name) to a VM host (by name).
        Changes the current state in-place."""
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
        Changes the current state in-place."""
        if vm_name not in self.vm2vmhost:
            raise KeyError, "VM %s not in pool" % vm_name
        vmhost_name = self.vm2vmhost[vm_name]
        if vmhost_name not in self.vmhost2vms:
            raise RuntimeError, "BUG: no such vmhost %s" % vmhost_name
        del self.vmhost2vms[vmhost_name][vm_name]
        del self.vm2vmhost[vm_name]

    def provision_vm(self, vm_name, vmhost_name):
        """Provision VM (by name) to a VM host (by name).
        Returns the new state."""
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

    def migrate(self, vm, to_host):
        """
        Generate a new instance representing the state after migration
        of vm to to_host.
        """
        assert type(to_host) is StringType
        from_host = self.vm2vmhost[vm]
        if from_host == to_host:
            raise RuntimeError, "can't migrate %s from %s to same vmhost" % \
                  (vm, from_host)
            
        #new = self.clone()
        new = deepcopy(self)
        new.remove_vm(vm)
        new.add_vm(vm, to_host)
        return new
        
    def check_migration_sane(self, vm, to_host):
        new = self.migrate(str(vm), str(to_host))
        try:
            new.check_sane()
        except VMPoolStateSanityError, e:
            return (None, e)
        return (new, None)

    def total_guest_RAM(self, vmhost_name):
        guests = self.vmhost2vms[vmhost_name]
        return sum([VM.vms[guest].ram for guest in guests])

    def check_sane(self):
        for vmhost_name in self.vmhosts():
            self.check_vmhost_sane(vmhost_name)

    def check_vmhost_sane(self, vmhost_name):
        """
        Raises a VMPoolStateSanityError exception if given VM host is
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
        for vmhost in sorted(self.vmhosts()):
            vms = self.vmhost2vms[vmhost].keys()
            vms.sort()
            vmhost_strs.append(vmhost + "[" + ' '.join(vms) + "]")
        str = " ".join(vmhost_strs)
        return str

    __str__ = unique

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.unique())

    def path_to(self, final_state, finder_class):
        return finder_class(self, final_state).find_path()
