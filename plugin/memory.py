def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

MemoryTypes = enum('total', 'used', 'free', 'buffers', 'cached', 'swaptotal', 'swapfree')

def readLines(filename):
    f = open(filename, "r")
    lines = f.readlines()
    return lines

def readMemValues():
    global memTotal, memFree, memBuffers, memCached, swapTotal, swapFree
    for line in readLines('/proc/meminfo'):
        if line.split()[0] == 'MemTotal:':
            memTotal = line.split()[1]
        if line.split()[0] == 'MemFree:':
            memFree = line.split()[1]
        if line.split()[0] == 'Buffers:':
            memBuffers = line.split()[1]
        if line.split()[0] == 'Cached:':
            memCached = line.split()[1]
        if line.split()[0] == 'SwapTotal:':
            swapTotal = line.split()[1]
        if line.split()[0] == 'SwapFree:':
            swapFree = line.split()[1]

def GetMemoryForType(memorytype):
	try:
		readMemValues()
		if memorytype == MemoryTypes.total:
			return long(memTotal)
		elif memorytype == MemoryTypes.used:
			return long(memTotal)-long(memFree)
		elif memorytype == MemoryTypes.free:
			return long(memFree)
		elif memorytype == MemoryTypes.buffers:
			return long(memBuffers)
		elif memorytype == MemoryTypes.cached:
			return long(memCached)
		elif memorytype == MemoryTypes.swaptotal:
			return long(swapTotal)
		elif memorytype == MemoryTypes.swapfree:
			return long(swapFree)
		return 0
	except:
		return 0
