#!/usr/bin/python

from vm import VM
from vmhost import VMhost

class VMmigration:
    def __init__(self, vm, from_state, to_state):
        self.vm = self._get_vm(vm)
        self.from_state = from_state
        self.to_state = to_state
        self.from_host = self._get_host(self.from_state.get_vm_vmhost(vm))
        self.to_host   = self._get_host(self.to_state.get_vm_vmhost(vm))

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

    def _get_host(self, host):
        if type(host) is str:
            host_name = host
            host = VMhost.vmhosts[host_name]
            if not host:
                raise RuntimeError, "Couldn't find VMhost object for %s" % host_name
            return host

#         if isinstance(host, VMhost):
#             return host
        
        raise RuntimeError, "host must be a VMhost object or string"

    def cost(self):
        #return 1
        return self.vm.ram

    def __cmp__(self, other):
        return cmp(self.cost, other.cost)

    def __str__(self):
        return "%s: %s -> %s (%d)" % \
            (self.vm, self.from_host, self.to_host, self.cost())

    __repr__ = __str__
