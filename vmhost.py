#!/usr/bin/python

class VMhost:
    vmhosts = { }

    def __init__(self, name, arch, ram):
        assert type(name) is str
        self.name = name
        self.arch = arch
        self.ram = ram
        if name in VMhost.vmhosts:
            raise RuntimeError, "vmhost %s already initialised" % name
        VMhost.vmhosts[name] = self

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)
