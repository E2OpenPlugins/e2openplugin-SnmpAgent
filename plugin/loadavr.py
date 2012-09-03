def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

CPULoadTypes = enum('one', 'five', 'fifteen')

def GetCPULoadForType(loadtype):
	# Get CPU Load Statistics
	try:
		cpu_load = open('/proc/loadavg', 'r').readline().strip().split()
		return cpu_load[loadtype]
	except:
		return ""
