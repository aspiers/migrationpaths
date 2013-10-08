#!/usr/bin/python

from vm import VM
from vmhost import VMhost

class VMmigration:
    def __init__(self, vm, from_host, to_host):
        self.vm = self._get_vm(vm)
        self.from_host = from_host
        self.to_host   = to_host

    def _get_vm(self, vm):
        if type(vm) is str:
            vm_name = vm
            vm = VM.vms[vm_name]
            if not vm:
                raise RuntimeError, "Couldn't find VM object for %s" % vm_name
            return vm

#         if isinstance(vm, VM):
#             return vm
        
        raise RuntimeError, "vm must be a VM object or string"

    def cost(self):
        #return 1
        return self.vm.ram

    def __cmp__(self, other):
        return cmp(self.cost, other.cost)

    def __str__(self):
        return "%s: %s -> %s (%d)" % \
            (self.vm, self.from_host, self.to_host, self.cost())

    __repr__ = __str__
