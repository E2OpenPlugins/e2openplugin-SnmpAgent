import os
from collections import namedtuple

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

NetworkInfoTypes = enum('total', 'ipaddr', 'desc', 'alias', 'type', 'mtu', 'speed', 'hspeed', 'hwaddr', 'status', 'inoctants', 'indiscard', 'inerrors', 'outoctacts', 'outdiscard', 'outerrors')

def disk_usage(path):
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return _ntuple_diskusage(total, used, free)

def GetNetworkInfo(infotype, devindex):
	try:
		network_stat = open('/proc/net/dev', 'r').read().strip().split('\n')

		if infotype == NetworkInfoTypes.total:
			return len(network_stat) - 2

		if devindex + 2 >= len(network_stat):
			return 0

		nline = network_stat[devindex + 2].strip()
		anameres = nline.split(':')

		if_name = anameres[0]

		if infotype == NetworkInfoTypes.ipaddr:
			ifoutput = os.popen('ifconfig %s' % if_name).read().split('\n')
			for line in ifoutput:
				lsplit = line.split()
				if lsplit[0] == 'inet':
					return lsplit[1].split(':')[1]
			return '0.0.0.0'

		if infotype == NetworkInfoTypes.ipaddr:
			return '0.0.0.0'
		if infotype == NetworkInfoTypes.desc:
			return if_name

		if infotype == NetworkInfoTypes.alias:
			return ''

		data = anameres[1].split()
		if infotype == NetworkInfoTypes.inoctants:
			return long(data[0])
		if infotype == NetworkInfoTypes.inerrors:
			return long(data[2])
		if infotype == NetworkInfoTypes.indiscard:
			return long(data[3])
		if infotype == NetworkInfoTypes.outoctacts:
			return long(data[8])
		if infotype == NetworkInfoTypes.outerrors:
			return long(data[10])
		if infotype == NetworkInfoTypes.outdiscard:
			return long(data[11])

		if infotype == NetworkInfoTypes.type:
			type = int(open('/sys/class/net/%s/type' % if_name, 'r').readline())
			if type == 1:
				return 6
			elif type == 772: #localhost
				return 24
			elif type == 801: #wifi
				return 71
			elif type == 802: #wifi
				return 71
			elif type == 803: #wifi
				return 71
			elif type == 804: #wifi
				return 71
			return 1

		if infotype == NetworkInfoTypes.mtu:
			return int(open('/sys/class/net/%s/mtu' % if_name, 'r').readline())

		#do not know how to get speed yet
		if infotype == NetworkInfoTypes.speed:
			return 0
		if infotype == NetworkInfoTypes.hspeed:
			return 0

		if infotype == NetworkInfoTypes.hwaddr:
			hwstr = open('/sys/class/net/%s/address' % if_name, 'r').readline().split('\n')[0].upper().split(':')
			retstr = ''
			for i in range(0, len(hwstr)):
				retstr += '%c' % int(hwstr[i], 16)
			return retstr
		if infotype == NetworkInfoTypes.status:
			status = open('/sys/class/net/%s/operstate' % if_name, 'r').readline().split('\n')[0]
			if status == 'up':
				return 1
			elif status == 'down':
				return 2
			elif status == 'testing':
				return 3
			elif status == 'unknown':
				return 1 #seems the box says unknown for up!?
			elif status == 'dormant':
				return 5
			elif status == 'notPresent':
				return 6
			elif status == 'lowerLayerDown':
				return 7
			return 4
		return 0
	except:
		if infotype == NetworkInfoTypes.ipaddr:
			return '0.0.0.0'
		return 0
