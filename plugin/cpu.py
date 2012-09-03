def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

CPUStatTypes = enum('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal_time')


def GetCPUStatForType(cputype):
	try:
		cpu_stat = open('/proc/stat', 'r').readline().strip().split()
		return long(cpu_stat[cputype+1])
	except:
		return 0
