#!/usr/bin/python

from vm import VM
from vmhost import VMhost

class VMmigration:
    def __init__(self, vm, from_host, to_host):
        self.vm        = self._get_vm(vm)
        self.from_host = self._get_vmhost(from_host)
        self.to_host   = self._get_vmhost(to_host)

    def _get_vm(self, vm_or_name):
        if type(vm_or_name) is str:
            vm_name = vm_or_name
            vm = VM.vms[vm_name]
            if not vm:
                raise RuntimeError, "Couldn't find VM object for %s" % vm_name
            return vm
        elif isinstance(vm_or_name, VM):
            return vm_or_name
        
        raise RuntimeError, "vm must be a VM object or string"

    def _get_vmhost(self, vmhost_or_name):
        if type(vmhost_or_name) is str:
            vmhost_name = vmhost_or_name
            vmhost = VMhost.vmhosts[vmhost_name]
            if not vmhost:
                raise RuntimeError, "Couldn't find VMhost object for %s" % vmhost_name
            return vmhost
        elif isinstance(vmhost_or_name, VMhost):
            return vmhost_or_name

        raise RuntimeError, "vmhost must be a VMhost object or string"

    def cost(self):
        #return 1
        return self.vm.ram

    def __cmp__(self, other):
        return cmp(self.cost, other.cost)

    def __str__(self):
        return "%s: %s -> %s (%d)" % \
            (self.vm.name, self.from_host.name, self.to_host.name, self.cost())

    __repr__ = __str__
