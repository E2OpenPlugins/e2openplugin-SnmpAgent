import os

from collections import namedtuple

_ntuple_diskusage = namedtuple('diskusage', 'total used free')

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

DiskInfoTypes = enum('totalmounts', 'mountpoint', 'filesystem', 'used', 'avail', 'total')

def disk_usage(path):
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return _ntuple_diskusage(total, used, free)

def GetDiskInfo(infotype, devindex):
	try:
		dfoutput = os.popen('df').read().strip().split('\n')

		if infotype == DiskInfoTypes.totalmounts:
			return len(dfoutput) - 1
		elif infotype == DiskInfoTypes.mountpoint:
			if devindex + 1 < len(dfoutput):
				return dfoutput[devindex + 1].split()[5]
			return ''
		elif infotype == DiskInfoTypes.filesystem:
			if devindex + 1 < len(dfoutput):
				return dfoutput[devindex + 1].split()[0]
			return ''

		if devindex + 1 < len(dfoutput):
			myusage = disk_usage(dfoutput[devindex + 1].split()[5])

			if infotype == DiskInfoTypes.used:
				return long(myusage.used) / 1000
			elif infotype == DiskInfoTypes.avail:
				return long(myusage.free) / 1000
			elif infotype == DiskInfoTypes.total:
				return long(myusage.total) / 1000
		return 0
	except:
		return 0
