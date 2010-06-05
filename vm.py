#!/usr/bin/python

class VM:
    vms = { }

    def __init__(self, name, arch, ram):
        self.name = name
        self.arch = arch
        self.ram = ram
        if name in VM.vms:
            raise "vm %s already initialised" % name
        VM.vms[name] = self

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)
