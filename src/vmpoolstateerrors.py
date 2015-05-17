#!/usr/bin/python

class VMPoolStateSanityError(RuntimeError):
    pass

class VMPoolStateRAMError(VMPoolStateSanityError):
    pass

class VMPoolStateArchError(VMPoolStateSanityError):
    pass

