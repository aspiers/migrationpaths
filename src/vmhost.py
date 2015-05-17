#!/usr/bin/python

class VMhost:
    vmhosts = { }

    def __init__(self, name, arch, ram, dom0_ram=None):
        if dom0_ram is None:
            dom0_ram = 256
        assert type(name) is str
        self.name = name
        self.arch = arch
        self.ram = ram
        self.dom0_ram = dom0_ram
        if name in VMhost.vmhosts:
            raise RuntimeError, "vmhost %s already initialised" % name
        VMhost.vmhosts[name] = self

    def __str__(self):
        return "%s^%d" % (self.name, self.ram)
        return self.name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

    def __eq__(self, other):
        if isinstance(other, VMhost):
            return self.name == other.name
        raise RuntimeError, "tried to compare VMhost %s with %s (%s)" % \
            (self, other.__class__, other)

    @classmethod
    def reset(cls):
        cls.vmhosts = { }
