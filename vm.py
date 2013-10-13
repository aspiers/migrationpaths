#!/usr/bin/python

class VM:
    vms = { }

    def __init__(self, name, arch, ram):
        assert type(name) is str
        self.name = name
        self.arch = arch
        self.ram = ram
        if name in VM.vms:
            raise RuntimeError, "vm %s already initialised" % name
        VM.vms[name] = self

    def __str__(self):
        return "%s^%d" % (self.name, self.ram)
        return self.name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)

    def __eq__(self, other):
        if isinstance(other, VM):
            return self.name == other.name
        raise RuntimeError, "tried to compare VM %s with %s (%s)" % \
            (self, other.__class__, other)

    @classmethod
    def reset(cls):
        cls.vms = { }
