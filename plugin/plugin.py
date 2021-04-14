from Components.ActionMap import ActionMap
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigEnableDisable
from Components.config import ConfigInteger, ConfigSubList, ConfigSubDict, ConfigText
from Components.config import configfile, ConfigYesNo, ConfigPassword
from Components.Label import Label
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Network import iNetwork
from Components.Sources.ServiceList import ServiceList
from enigma import eTimer, iFrontendInformation, iPlayableService, eActionMap, eServiceReference, iServiceInformation
from enigma import eDVBResourceManager, eDVBFrontendParametersSatellite, eDVBFrontendParameters
import NavigationInstance
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
import time
import platform

# SNMP support
from twisted.internet import error as twisted_error
from twistedsnmp import agent, agentprotocol, bisectoidstore
from twistedsnmp.pysnmpproto import v1, oid

# import own classes
from bitrate import Bitrate
from emm import Emm
from cpu import GetCPUStatForType, CPUStatTypes
from loadavr import GetCPULoadForType, CPULoadTypes
from memory import GetMemoryForType, MemoryTypes
from disk import GetDiskInfo, DiskInfoTypes
from network import GetNetworkInfo, NetworkInfoTypes

# for localized messages
from . import _

config.plugins.SnmpAgent = ConfigSubsection()
config.plugins.SnmpAgent.startuptype = ConfigYesNo(default=True)
config.plugins.SnmpAgent.managerip = ConfigText(default='0.0.0.0')
config.plugins.SnmpAgent.systemname = ConfigText(default=platform.node())
config.plugins.SnmpAgent.systemdescription = ConfigText(default='SNMP Agent for Enigma2')
config.plugins.SnmpAgent.supportaddress = ConfigText(default='support@somewhere.tv')
config.plugins.SnmpAgent.location = ConfigText(default='default location')
config.plugins.SnmpAgent.measurebitrate = ConfigYesNo(default=False)
config.plugins.SnmpAgent.checkemm = ConfigYesNo(default=False)
config.plugins.SnmpAgent.save()

config.tv.lastroot = ConfigText()


#------------------------------------------------------------------------------------------
#VERSION
versionstr = "2.0.4"
#------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------
#GLOBAL
#------------------------------------------------------------------------------------------
global_session = None
global_my_agent = None

#===============================================================================
# class
# SNMPAgentMainMenu
#===============================================================================
class SNMPAgent_MainMenu(Screen, ConfigListScreen):
	skin = """
  <screen name="SNMPAgent_MainMenu" title="SNMP Agent Menu" position="center,center" size="565,370">
    <ePixmap name="red" position="0,0" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
    <ePixmap name="green" position="140,0" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
    <ePixmap name="yellow" position="280,0" size="140,40" pixmap="skin_default/buttons/yellow.png" alphatest="on" />
    <ePixmap name="blue" position="420,0" size="140,40" pixmap="skin_default/buttons/blue.png" alphatest="on" />
    <widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
    <widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
    <widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
    <widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
    <widget name="config" position="5,50" size="555,250" scrollbarMode="showOnDemand" />
    <ePixmap pixmap="skin_default/div-h.png" position="0,301" zPosition="1" size="565,2" />
  </screen>"""

	def __init__(self, session, args=None):
		self.skin = SNMPAgent_MainMenu.skin
		Screen.__init__(self, session)

		ConfigListScreen.__init__(
			self,
			[
				getConfigListEntry(_("Startup type"), config.plugins.SnmpAgent.startuptype, _("Should the SnmpAgent start automatically on startup?")),
				getConfigListEntry(_("Manager IP"), config.plugins.SnmpAgent.managerip, _("Which IP Address is used for the manager?")),
				getConfigListEntry(_("System Name"), config.plugins.SnmpAgent.systemname, _("Which name should be used to identify the device?")),
				getConfigListEntry(_("System Description"), config.plugins.SnmpAgent.systemdescription, _("Description for the device")),
				getConfigListEntry(_("Support Address"), config.plugins.SnmpAgent.supportaddress, _("Support Email Address")),
				getConfigListEntry(_("Location"), config.plugins.SnmpAgent.location, _("Description of Location where the device resides")),
				getConfigListEntry(_("Measure Bitrate"), config.plugins.SnmpAgent.measurebitrate, _("Do bitrates have to be Monitored?")),
				getConfigListEntry(_("Measure EMM"), config.plugins.SnmpAgent.checkemm, _("Do EMMs have to be Monitored?")),
			],
			session=session,
			on_change=self._changed
		)

		self._session = session
		self._hasChanged = False

		# Initialize widgets
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Start Service"))
		self["key_blue"] = Label(_("Stop Service"))

		# Define Actions
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
      "red": self.keyCancel,
			"green": self.keySave,
			"yellow": self.keyStart,
			"blue": self.keyStop,
      "back": self.keyCancel,		
		}, -2)

		self.onLayoutFinish.append(self.setCustomTitle)

	def _changed(self):
		self._hasChanged = True

	def keySave(self):
		print "[SnmpAgent] pressed save"
		self.saveAll()
		self.close()

	def keyCancel(self):
		print "[SnmpAgent] pressed cancel"
		self.close()

	def keyStart(self):
		print "[SnmpAgent] pressed start"
		print "[SnmpAgent] trying to stop if running"
		stopSNMPserver(global_session)
		print "[SnmpAgent] trying to start"
		startSNMPserver(global_session)
		self.session.openWithCallback(self.close, MessageBox, _("Service successfully started"), MessageBox.TYPE_INFO, timeout=5)

	def keyStop(self):
		print "[SnmpAgent] pressed stop"
		stopSNMPserver(global_session)
		self.session.openWithCallback(self.close, MessageBox, _("Service successfully stoped"), MessageBox.TYPE_INFO, timeout=5)


	def quitPlugin(self, answer):
		if answer is True:
			self.close()

	def restartGUI(self, answer):
		if answer is True:
			from Screens.Standby import TryQuitMainloop
			stopSNMPserver(global_session)
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	def setCustomTitle(self):
		#TRANSLATORS: SnmpAgent settings window title, the plugin version is printed in {0}
		self.setTitle( _("Settings for SnmpAgent V{0}").format(versionstr))

class ourOIDStore(bisectoidstore.BisectOIDStore):
	startTime = time.time()
	haspicture = False
	oldframes = 0
	iface = 'eth0'

	ip_adentifindex_ref = {}
	ip_adentaddr_ref = {}

	SYSUPTIME_OID = '.1.3.6.1.2.1.1.3.0'
	SYSTEMDESCRIPTION_OID = '.1.3.6.1.2.1.1.1.0'
	SUPPORTADDRESS_OID = '.1.3.6.1.2.1.1.4.0'
	SYSTEMNAME_OID = '.1.3.6.1.2.1.1.5.0'
	LOCATION_OID = '.1.3.6.1.2.1.1.6.0'
	BER_OID = '.1.3.6.1.2.1.1.10000.0'
	AGC_OID = '.1.3.6.1.2.1.1.10001.0'
	SNR_OID = '.1.3.6.1.2.1.1.10002.0'
	SNRDB_OID = '.1.3.6.1.2.1.1.10003.0'
	LOCK_OID = '.1.3.6.1.2.1.1.10004.0'
	HASPICTURE_OID = '.1.3.6.1.2.1.1.10009.0'
	CHANNELNAME_OID = '.1.3.6.1.2.1.1.10010.0'
	SERVICESTRING_OID = '.1.3.6.1.2.1.1.10011.0'
	FASTSCANSTRING_OID = '.1.3.6.1.2.1.1.10012.0'
	SERVICEPARAMS_OID = '.1.3.6.1.2.1.1.10013.0'
	TUNERTYPE_OID = '.1.3.6.1.2.1.1.10014.0'
	MANAGERIP_OID = '.1.3.6.1.2.1.1.10020.0'
	ENABLE_BITRATE_OID = '.1.3.6.1.2.1.1.10030.0'
	VIDEO_BITRATE_OID = '.1.3.6.1.2.1.1.10031.0'
	AUDIO_BITRATE_OID = '.1.3.6.1.2.1.1.10032.0'
	IP_OID = '.1.3.6.1.2.1.1.10050.0'
	NETMASK_OID = '.1.3.6.1.2.1.1.10051.0'
	GATEWAY_OID = '.1.3.6.1.2.1.1.10052.0'
	ENABLE_EMM_OID = '.1.3.6.1.2.1.1.10060.0'
	EMM_OID = '.1.3.6.1.2.1.1.10061.0'
	CPU_USER = '.1.3.6.1.4.1.2021.11.50.0'
	CPU_NICE = '.1.3.6.1.4.1.2021.11.51.0'
	CPU_SYSTEM = '.1.3.6.1.4.1.2021.11.52.0'
	CPU_IDLE = '.1.3.6.1.4.1.2021.11.53.0'
	CPU_WAIT = '.1.3.6.1.4.1.2021.11.54.0'
	LOAD_AVR1 = '.1.3.6.1.4.1.2021.10.1.3.1'
	LOAD_AVR5 = '.1.3.6.1.4.1.2021.10.1.3.2'
	LOAD_AVR15 = '.1.3.6.1.4.1.2021.10.1.3.3'
	MEM_TOTAL = '.1.3.6.1.4.1.2021.4.5.0'
	MEM_TOTAL2 = '.1.3.6.1.2.1.25.2.2.0'
	MEM_USED = '.1.3.6.1.4.1.2021.4.11.0'
	MEM_FREE = '.1.3.6.1.4.1.2021.4.6.0'
	MEM_BUFFER = '.1.3.6.1.4.1.2021.4.14.0'
	MEM_CACHED = '.1.3.6.1.4.1.2021.4.15.0'
	MEM_SWAPTOTAL = '.1.3.6.1.4.1.2021.4.3.0'
	MEM_SWAPFREE = '.1.3.6.1.4.1.2021.4.4.0'
	DISK_INDEX = '.1.3.6.1.4.1.2021.9.1.1'
	DISK_PATHNAME = '.1.3.6.1.4.1.2021.9.1.2'
	DISK_DEVICENAME = '.1.3.6.1.4.1.2021.9.1.3'
	DISK_AVAIL = '.1.3.6.1.4.1.2021.9.1.7'
	DISK_USED = '.1.3.6.1.4.1.2021.9.1.8'
	IF_NUMBER = '.1.3.6.1.2.1.2.1.0'
	IF_INDEX = '.1.3.6.1.2.1.2.2.1.1'
	IF_DESC = '.1.3.6.1.2.1.2.2.1.2'
	IF_TYPE = '.1.3.6.1.2.1.2.2.1.3'
	IF_MTU = '.1.3.6.1.2.1.2.2.1.4'
	IF_SPEED = '.1.3.6.1.2.1.2.2.1.5'
	IF_HWADDR = '.1.3.6.1.2.1.2.2.1.6'
	IF_STATUS = '.1.3.6.1.2.1.2.2.1.8'
	IF_INOCTANTS = '.1.3.6.1.2.1.2.2.1.10'
	IF_INDISCARD = '.1.3.6.1.2.1.2.2.1.13'
	IF_INERRORS = '.1.3.6.1.2.1.2.2.1.14'
	IF_OUTOCTANTS = '.1.3.6.1.2.1.2.2.1.16'
	IF_OUTDISCARD = '.1.3.6.1.2.1.2.2.1.19'
	IF_OUTERRORS = '.1.3.6.1.2.1.2.2.1.20'
	IF_IPADENTADDR = '.1.3.6.1.2.1.4.20.1.1'
	IP_ADENTIFINDEX = '.1.3.6.1.2.1.4.20.1.2'
	IF_NAME = '.1.3.6.1.2.1.31.1.1.1.1'
	IF_HSPEED = '.1.3.6.1.2.1.31.1.1.1.15'
	IF_ALIAS = '.1.3.6.1.2.1.31.1.1.1.18'

	def __init__(self, session, oids={}):
		self.session = session
		oids.update({
			self.SYSTEMDESCRIPTION_OID: self.getValue,
			'.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.88.3.1',
			self.SYSUPTIME_OID:  self.getValue,
			self.SUPPORTADDRESS_OID: self.getValue,
			self.SYSTEMNAME_OID: self.getValue,
			self.LOCATION_OID: self.getValue,
			self.BER_OID: self.getValue,
			self.AGC_OID: self.getValue,
			self.SNR_OID: self.getValue,
			self.SNRDB_OID: self.getValue,
			self.LOCK_OID: self.getValue,
			self.HASPICTURE_OID: self.getValue,
			self.VIDEO_BITRATE_OID: self.getValue,
			self.AUDIO_BITRATE_OID: self.getValue,
			self.CHANNELNAME_OID: self.getValue,
			self.SERVICESTRING_OID: self.getValue,
			self.FASTSCANSTRING_OID: self.getValue,
			self.SERVICEPARAMS_OID: self.getValue,
			self.TUNERTYPE_OID: self.getValue,
			self.MANAGERIP_OID: self.getValue,
			self.ENABLE_BITRATE_OID: self.getValue,
			self.IP_OID: self.getValue,
			self.NETMASK_OID: self.getValue,
			self.GATEWAY_OID: self.getValue,
			self.ENABLE_EMM_OID: self.getValue,
			self.EMM_OID: self.getValue,
			self.CPU_USER: self.getValue,
			self.CPU_NICE: self.getValue,
			self.CPU_SYSTEM: self.getValue,
			self.CPU_IDLE: self.getValue,
			self.CPU_WAIT: self.getValue,
			self.LOAD_AVR1: self.getValue,
			self.LOAD_AVR5: self.getValue,
			self.LOAD_AVR15: self.getValue,
			self.MEM_TOTAL: self.getValue,
			self.MEM_TOTAL2: self.getValue,
			self.MEM_USED: self.getValue,
			self.MEM_FREE: self.getValue,
			self.MEM_BUFFER: self.getValue,
			self.MEM_CACHED: self.getValue,
			self.MEM_SWAPTOTAL: self.getValue,
			self.MEM_SWAPFREE: self.getValue,
			self.IF_NUMBER: self.getValue,
		})

		# Add disk info's
		totaldisks = GetDiskInfo(DiskInfoTypes.totalmounts, 0)
		for i in range(totaldisks):
			key = '%s.%d' % (self.DISK_INDEX, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.DISK_PATHNAME, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.DISK_DEVICENAME, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.DISK_AVAIL, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.DISK_USED, (i + 1))
			oids[key] = self.getValue

		# Add network info's
		totalnetworks = GetNetworkInfo(NetworkInfoTypes.total, 0)
		for i in range(totalnetworks):
			key = '%s.%d' % (self.IF_INDEX, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_DESC, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_TYPE, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_MTU, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_SPEED, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_HWADDR, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_STATUS, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_INOCTANTS, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_INDISCARD, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_INERRORS, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_OUTOCTANTS, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_OUTDISCARD, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_OUTERRORS, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_NAME, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_ALIAS, (i + 1))
			oids[key] = self.getValue
			key = '%s.%d' % (self.IF_HSPEED, (i + 1))
			oids[key] = self.getValue

			#special OID: IP address
			key = '%s.%s' % (self.IP_ADENTIFINDEX, GetNetworkInfo(NetworkInfoTypes.ipaddr, i))
			oids[key] = self.getValue
			self.ip_adentifindex_ref[key] = i + 1

			key = '%s.%s' % (self.IF_IPADENTADDR, GetNetworkInfo(NetworkInfoTypes.ipaddr, i))
			oids[key] = self.getValue
			self.ip_adentaddr_ref[key] = GetNetworkInfo(NetworkInfoTypes.ipaddr, i)


		bisectoidstore.BisectOIDStore.__init__(self, OIDs=oids)
		self.session.nav.event.append(self.gotServiceEvent)
		if config.plugins.SnmpAgent.measurebitrate.value:
			self.bitrate = Bitrate(session)
		else:
			self.bitrate = None
		if config.plugins.SnmpAgent.checkemm.value:
			self.emm = Emm(session)
		else:
			self.emm = None

	def timerPoll(self):
		data = ''
		try:
			file = open('/proc/stb/vmpeg/0/stat_picture_displayed', 'r')
			data = file.readline()
			file.close()
		except:
			pass
		if len(data):
			frames = int(data, 16)
			if self.oldframes <> frames:
				self.haspicture = True
				self.oldframes = frames
			else:
				self.haspicture = False

	def gotServiceEvent(self, event):
		if self.bitrate:
			if event is iPlayableService.evEnd or event is iPlayableService.evStopped:
				self.bitrate.stop()
			else:
				#don't start bitrate measurement when playing recordings
				if self.session and self.session.nav and self.session.nav.getCurrentService():
					feinfo = self.session.nav.getCurrentService().frontendInfo()
					fedata = feinfo and feinfo.getFrontendData()
					if fedata and 'tuner_number' in fedata:
						self.bitrate.start()
		if self.emm:
			if event is iPlayableService.evEnd or event is iPlayableService.evStopped:
				self.emm.stop()
			else:
				#don't start emm measurement when playing recordings
				if self.session and self.session.nav and self.session.nav.getCurrentService():
					feinfo = self.session.nav.getCurrentService().frontendInfo()
					fedata = feinfo and feinfo.getFrontendData()
					if fedata and 'tuner_number' in fedata:
						self.emm.start()

	def getValue(self, oid, storage):
		oidstring = bisectoidstore.sortableToOID(oid)
		strOID = str(oidstring)
		if oidstring == self.SYSTEMDESCRIPTION_OID:
			return v1.OctetString(str(config.plugins.SnmpAgent.systemdescription.value))
		elif oidstring == self.SYSUPTIME_OID:
			return self.getSysUpTime()
		elif oidstring == self.CPU_USER:
			return v1.Counter(GetCPUStatForType(CPUStatTypes.user))
		elif oidstring == self.CPU_NICE:
			return v1.Counter(GetCPUStatForType(CPUStatTypes.nice))
		elif oidstring == self.CPU_SYSTEM:
			return v1.Counter(GetCPUStatForType(CPUStatTypes.system))
		elif oidstring == self.CPU_IDLE:
			return v1.Counter(GetCPUStatForType(CPUStatTypes.idle))
		elif oidstring == self.CPU_WAIT:
			return v1.Counter(GetCPUStatForType(CPUStatTypes.iowait))
		elif oidstring == self.LOAD_AVR1:
			return v1.OctetString(GetCPULoadForType(CPULoadTypes.one))
		elif oidstring == self.LOAD_AVR5:
			return v1.OctetString(GetCPULoadForType(CPULoadTypes.five))
		elif oidstring == self.LOAD_AVR15:
			return v1.OctetString(GetCPULoadForType(CPULoadTypes.fifteen))
		elif oidstring == self.MEM_TOTAL:
			return v1.Integer(GetMemoryForType(MemoryTypes.total))
		elif oidstring == self.MEM_TOTAL2:
			return v1.Integer(GetMemoryForType(MemoryTypes.total))
		elif oidstring == self.MEM_USED:
			return v1.Integer(GetMemoryForType(MemoryTypes.used))
		elif oidstring == self.MEM_FREE:
			return v1.Integer(GetMemoryForType(MemoryTypes.free))
		elif oidstring == self.MEM_BUFFER:
			return v1.Integer(GetMemoryForType(MemoryTypes.buffers))
		elif oidstring == self.MEM_CACHED:
			return v1.Integer(GetMemoryForType(MemoryTypes.cached))
		elif oidstring == self.MEM_SWAPTOTAL:
			return v1.Integer(GetMemoryForType(MemoryTypes.swaptotal))
		elif oidstring == self.MEM_SWAPFREE:
			return v1.Integer(GetMemoryForType(MemoryTypes.swapfree))
		elif strOID.startswith(str(self.DISK_INDEX)):
			return v1.Integer(int(strOID[len(str(self.DISK_INDEX)) + 1:]))
		elif strOID.startswith(str(self.DISK_PATHNAME)):
			return v1.OctetString(GetDiskInfo(DiskInfoTypes.mountpoint, int(strOID[len(str(self.DISK_PATHNAME)) + 1:]) - 1))
		elif strOID.startswith(str(self.DISK_DEVICENAME)):
			return v1.OctetString(GetDiskInfo(DiskInfoTypes.filesystem, int(strOID[len(str(self.DISK_DEVICENAME)) + 1:]) - 1))
		elif strOID.startswith(str(self.DISK_AVAIL)):
			return v1.Integer(GetDiskInfo(DiskInfoTypes.avail, int(strOID[len(str(self.DISK_AVAIL)) + 1:]) - 1))
		elif strOID.startswith(str(self.DISK_USED)):
			return v1.Integer(GetDiskInfo(DiskInfoTypes.used, int(strOID[len(str(self.DISK_USED)) + 1:]) - 1))
		elif oidstring == self.IF_NUMBER:
			return v1.Integer(GetNetworkInfo(NetworkInfoTypes.total, 0))
		elif strOID.startswith(str(self.IP_ADENTIFINDEX)):
			return v1.Integer(self.ip_adentifindex_ref[strOID])
		elif strOID.startswith(str(self.IF_IPADENTADDR)):
			return v1.IpAddress(self.ip_adentaddr_ref[strOID])
		elif strOID.startswith(str(self.IF_INOCTANTS)):
			return v1.Counter(GetNetworkInfo(NetworkInfoTypes.inoctants, int(strOID[len(str(self.IF_INOCTANTS)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_INDISCARD)):
			return v1.Counter(GetNetworkInfo(NetworkInfoTypes.indiscard, int(strOID[len(str(self.IF_INDISCARD)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_INERRORS)):
			return v1.Counter(GetNetworkInfo(NetworkInfoTypes.inerrors, int(strOID[len(str(self.IF_INERRORS)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_OUTOCTANTS)):
			return v1.Counter(GetNetworkInfo(NetworkInfoTypes.outoctacts, int(strOID[len(str(self.IF_OUTOCTANTS)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_OUTDISCARD)):
			return v1.Counter(GetNetworkInfo(NetworkInfoTypes.outdiscard, int(strOID[len(str(self.IF_OUTDISCARD)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_OUTERRORS)):
			return v1.Counter(GetNetworkInfo(NetworkInfoTypes.outerrors, int(strOID[len(str(self.IF_OUTERRORS)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_ALIAS)):
			return v1.OctetString(GetNetworkInfo(NetworkInfoTypes.alias, int(strOID[len(str(self.IF_ALIAS)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_HSPEED)):
			return v1.Gauge(GetNetworkInfo(NetworkInfoTypes.hspeed, int(strOID[len(str(self.IF_HSPEED)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_INDEX)):
			return v1.Integer(int(strOID[len(str(self.IF_INDEX)) + 1:]))
		elif strOID.startswith(str(self.IF_DESC)):
			return v1.OctetString(GetNetworkInfo(NetworkInfoTypes.desc, int(strOID[len(str(self.IF_DESC)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_NAME)):
			return v1.OctetString(GetNetworkInfo(NetworkInfoTypes.desc, int(strOID[len(str(self.IF_NAME)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_TYPE)):
			return v1.Integer(GetNetworkInfo(NetworkInfoTypes.type, int(strOID[len(str(self.IF_TYPE)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_MTU)):
			return v1.Integer(GetNetworkInfo(NetworkInfoTypes.mtu, int(strOID[len(str(self.IF_MTU)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_SPEED)):
			return v1.Gauge(GetNetworkInfo(NetworkInfoTypes.speed, int(strOID[len(str(self.IF_SPEED)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_HWADDR)):
			return v1.OctetString(GetNetworkInfo(NetworkInfoTypes.hwaddr, int(strOID[len(str(self.IF_HWADDR)) + 1:]) - 1))
		elif strOID.startswith(str(self.IF_STATUS)):
			return v1.Integer(GetNetworkInfo(NetworkInfoTypes.status, int(strOID[len(str(self.IF_STATUS)) + 1:]) - 1))
		elif oidstring == self.SUPPORTADDRESS_OID:
			return v1.OctetString(str(config.plugins.SnmpAgent.supportaddress.value))
		elif oidstring == self.SYSTEMNAME_OID:
			return v1.OctetString(str(config.plugins.SnmpAgent.systemname.value))
		elif oidstring == self.LOCATION_OID:
			return v1.OctetString(str(config.plugins.SnmpAgent.location.value))
		elif oidstring == self.BER_OID:
			return self.getBER()
		elif oidstring == self.AGC_OID:
			return self.getAGC()
		elif oidstring == self.SNR_OID:
			return self.getSNR()
		elif oidstring == self.SNRDB_OID:
			return self.getSNRDB()
		elif oidstring == self.LOCK_OID:
			return self.getLock()
		elif oidstring == self.HASPICTURE_OID:
			return self.haspicture
		elif oidstring == self.VIDEO_BITRATE_OID:
			if self.bitrate:
				return self.bitrate.vcur
			else:
				return 0
		elif oidstring == self.AUDIO_BITRATE_OID:
			if self.bitrate:
				return self.bitrate.acur
			else:
				return 0
		elif oidstring == self.CHANNELNAME_OID:
			return v1.OctetString(self.getChannelName())
		elif oidstring == self.SERVICESTRING_OID:
			return v1.OctetString(self.getServiceString())
		elif oidstring == self.FASTSCANSTRING_OID:
			return v1.OctetString('')
		elif oidstring == self.SERVICEPARAMS_OID:
			return v1.OctetString(self.getServiceParams())
		elif oidstring == self.TUNERTYPE_OID:
			return self.getTunerType()
		elif oidstring == self.MANAGERIP_OID:
			return v1.OctetString(str(config.plugins.SnmpAgent.managerip.value))
		elif oidstring == self.ENABLE_BITRATE_OID:
			return config.plugins.SnmpAgent.measurebitrate.value
		elif oidstring == self.IP_OID:
			value = "%d.%d.%d.%d" % tuple(iNetwork.getAdapterAttribute(self.iface, "ip"))
			return v1.IpAddress(value)
		elif oidstring == self.NETMASK_OID:
			value = "%d.%d.%d.%d" % tuple(iNetwork.getAdapterAttribute(self.iface, "netmask"))
			return v1.IpAddress(value)
		elif oidstring == self.GATEWAY_OID:
			value = "%d.%d.%d.%d" % tuple(iNetwork.getAdapterAttribute(self.iface, "gateway"))
			return v1.IpAddress(value)
		elif oidstring == self.ENABLE_EMM_OID:
			return config.plugins.SnmpAgent.checkemm.value
		elif oidstring == self.EMM_OID:
			if self.emm:
				return v1.OctetString(self.emm.pids)
			else:
				return v1.OctetString('')

	def setValue(self, oid, value):
		#the first time we are called, we have to fill the bisect oid store, values are just values, no objects (we cannot call value.get)
		try:
			value.get()
		except:
			return bisectoidstore.BisectOIDStore.setValue(self, oid, value)

		oidstring = bisectoidstore.sortableToOID(oid)
		if oidstring == self.MANAGERIP_OID:
			if config.plugins.SnmpAgent.managerip.value <> value.get():
				config.plugins.SnmpAgent.managerip.value = value.get()
				config.plugins.SnmpAgent.managerip.save()
		elif oidstring == self.ENABLE_BITRATE_OID:
			if config.plugins.SnmpAgent.measurebitrate.value and not value.get():
				config.plugins.SnmpAgent.measurebitrate.value = False
				config.plugins.SnmpAgent.measurebitrate.save()
				if self.bitrate:
					self.bitrate.stop()
					self.bitrate = None
			elif not config.plugins.SnmpAgent.measurebitrate.value and value.get():
				config.plugins.SnmpAgent.measurebitrate.value = True
				config.plugins.SnmpAgent.measurebitrate.save()
				self.bitrate = Bitrate(self.session)
				self.bitrate.start()
		elif oidstring == self.SYSTEMNAME_OID:
			if config.plugins.SnmpAgent.systemname.value <> value.get():
				config.plugins.SnmpAgent.systemname.value = value.get()
				config.plugins.SnmpAgent.systemname.save()
		elif oidstring == self.SUPPORTADDRESS_OID:
			if config.plugins.SnmpAgent.supportaddress.value <> value.get():
				config.plugins.SnmpAgent.supportaddress.value = value.get()
				config.plugins.SnmpAgent.supportaddress.save()
		elif oidstring == self.SYSTEMDESCRIPTION_OID:
			if config.plugins.SnmpAgent.systemdescription.value <> value.get():
				config.plugins.SnmpAgent.systemdescription.value = value.get()
				config.plugins.SnmpAgent.systemdescription.save()
		elif oidstring == self.LOCATION_OID:
			if config.plugins.SnmpAgent.location.value <> value.get():
				config.plugins.SnmpAgent.location.value = value.get()
				config.plugins.SnmpAgent.location.save()
		elif oidstring == self.CHANNELNAME_OID:
			if self.getChannelName() <> value.get():
				root = config.tv.lastroot.value.split(';')
				fav = eServiceReference(root[-2])
				services = ServiceList(fav, command_func=self.zapTo, validate_commands=False)
				sub = services.getServicesAsList()

				if len(sub) > 0:
					for (ref, name) in sub:
						if name == value.get():
							self.zapTo(eServiceReference(ref))
							break
		elif oidstring == self.SERVICESTRING_OID:
			if self.getServiceString() <> value.get():
				self.zapTo(eServiceReference(value.get()))
		elif oidstring == self.FASTSCANSTRING_OID:
			refstring = ''
			fields = value.get().split(',')
			if len(fields) >= 15:
				onid, tsid, freq, id1, id2, sid, orbital_pos, f1, f2, f3, symbolrate, f4, name, provider, servicetype = fields[0:15]
				refstring = '%d:%d:%d:%x:%x:%x:%x:%x:%x:%x:' % (1, 0, int(servicetype), int(sid), int(tsid), int(onid), int(orbital_pos) * 65536, 0, 0, 0)
			if refstring is not '':
				self.zapTo(eServiceReference(refstring))
		elif oidstring == self.SERVICEPARAMS_OID:
			refstring = ''
			fields = value.get().split(',')
			if len(fields) >= 5:
				orbital_pos, tsid, onid, sid, servicetype = fields[0:5]
				refstring = '%d:%d:%d:%x:%x:%x:%x:%x:%x:%x:' % (1, 0, int(servicetype), int(sid), int(tsid), int(onid), int(orbital_pos) * 65536, 0, 0, 0)
			if refstring is not '':
				self.zapTo(eServiceReference(refstring))
		elif oidstring == self.IP_OID:
			ipstring = value.get().split('.')
			ipval = []
			for x in ipstring:
				ipval.append(int(x))
			if iNetwork.getAdapterAttribute(self.iface, "ip") <> ipval:
				iNetwork.setAdapterAttribute(self.iface, "dhcp", 0)
				iNetwork.setAdapterAttribute(self.iface, "ip", ipval)
				iNetwork.deactivateNetworkConfig()
				iNetwork.writeNetworkConfig()
				iNetwork.activateNetworkConfig()
		elif oidstring == self.IP_OID:
			ipstring = value.get().split('.')
			ipval = []
			for x in ipstring:
				ipval.append(int(x))
			if iNetwork.getAdapterAttribute(self.iface, "netmask") <> ipval:
				iNetwork.setAdapterAttribute(self.iface, "dhcp", 0)
				iNetwork.setAdapterAttribute(self.iface, "netmask", ipval)
				iNetwork.deactivateNetworkConfig()
				iNetwork.writeNetworkConfig()
				iNetwork.activateNetworkConfig()
		elif oidstring == self.GATEWAY_OID:
			ipstring = value.get().split('.')
			ipval = []
			for x in ipstring:
				ipval.append(int(x))
			if iNetwork.getAdapterAttribute(self.iface, "gateway") <> ipval:
				iNetwork.setAdapterAttribute(self.iface, "dhcp", 0)
				iNetwork.setAdapterAttribute(self.iface, "gateway", ipval)
				iNetwork.deactivateNetworkConfig()
				iNetwork.writeNetworkConfig()
				iNetwork.activateNetworkConfig()
		elif oidstring == self.ENABLE_EMM_OID:
			if config.plugins.SnmpAgent.checkemm.value and not value.get():
				config.plugins.SnmpAgent.checkemm.value = False
				config.plugins.SnmpAgent.checkemm.save()
				if self.emm:
					self.emm.stop()
					self.emm = None
			elif not config.plugins.SnmpAgent.checkemm.value and value.get():
				config.plugins.SnmpAgent.checkemm.value = True
				config.plugins.SnmpAgent.checkemm.save()
				self.emm = Emm(self.session)
				self.emm.start()
		else:
			print "oid not found!?"

		return None

	def zapTo(self, reftozap):
		self.session.nav.playService(reftozap)

	def getSysUpTime(self):
			seconds = time.time() - self.startTime
			return int(round(seconds * 100, 0))

	def getBER(self):
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			feinfo = self.session.nav.getCurrentService().frontendInfo()
			if feinfo:
				return feinfo.getFrontendInfo(iFrontendInformation.bitErrorRate)
		return 0

	def getAGC(self):
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			feinfo = self.session.nav.getCurrentService().frontendInfo()
			return feinfo.getFrontendInfo(iFrontendInformation.signalPower) * 100 / 65536
		return 0

	def getSNR(self):
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			feinfo = self.session.nav.getCurrentService().frontendInfo()
			if feinfo:
				return feinfo.getFrontendInfo(iFrontendInformation.signalQuality) * 100 / 65536
		return 0

	def getSNRDB(self):
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			feinfo = self.session.nav.getCurrentService().frontendInfo()
			if feinfo:
				retval = feinfo.getFrontendInfo(iFrontendInformation.signalQualitydB)
				if retval == 0x12345678:	#cable tuner? does not have SNR
					return v1.OctetString ( 0.0 )
				return v1.OctetString (str (int(retval) / 100.0))
		return 0

	def getTunerType(self):
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			feinfo = self.session.nav.getCurrentService().frontendInfo()
			frontendData = feinfo and feinfo.getAll(True)
			if frontendData is not None:
				ttype = frontendData.get("tuner_type", "UNKNOWN")
				return v1.OctetString ( ttype )
		return v1.OctetString ( "UNKNOWN" )

	def getLock(self):
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			feinfo = self.session.nav.getCurrentService().frontendInfo()
			if feinfo:
				return feinfo.getFrontendInfo(iFrontendInformation.lockState)
		return 0

	def getChannelName(self):
		name = "unknown"
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			name = self.session.nav.getCurrentService().info().getName()
		return name

	def getServiceString(self):
		name = "unknown"
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			name = self.session.nav.getCurrentService().info().getInfoString(iServiceInformation.sServiceref)
		return name

	def getServiceParams(self):
		orbital_pos = 0
		tsid = 0
		onid = 0
		sid = 0
		servicetype = 0
		if self.session and self.session.nav and self.session.nav.getCurrentService():
			info = self.session.nav.getCurrentService().info()
			serviceref = info.getInfoString(iServiceInformation.sServiceref)
			servicedata = serviceref.split(':')
			orbital_pos = int(servicedata[6], 16) / 65536
			tsid = int(servicedata[4], 16)
			onid = int(servicedata[5], 16)
			sid = int(servicedata[3], 16)
			servicetype = servicedata[2]
		params = str(orbital_pos) + "," + str(tsid) + "," + str(onid) + "," + str(sid) + "," + str(servicetype)
		return params

class Tuner:
	def __init__(self, frontend):
		self.frontend = frontend

	def tune(self, transponder):
		if self.frontend:
			print "tuning to transponder with data", transponder
			parm = eDVBFrontendParametersSatellite()
			parm.frequency = transponder[0] * 1000
			parm.symbol_rate = transponder[1] * 1000
			parm.polarisation = transponder[2]
			parm.fec = transponder[3]
			parm.inversion = transponder[4]
			parm.orbital_position = transponder[5]
			parm.system = 0  # FIXMEE !! HARDCODED DVB-S (add support for DVB-S2)
			parm.modulation = 1 # FIXMEE !! HARDCODED QPSK
			feparm = eDVBFrontendParameters()
			feparm.setDVBS(parm)
			self.lastparm = feparm
			self.frontend.tune(feparm)

	def retune(self):
		if self.frontend:
			self.frontend.tune(self.lastparm)

class ourTunerOIDStore(ourOIDStore):
	TRANSPONDERPARAMS_OID = '.1.3.6.1.2.1.1.10040.0'
	feid = 0 #TODO: different frontends?

	def __init__(self, session):
		oids = {
			self.TRANSPONDERPARAMS_OID: self.getTransponderParamsOIDValue,
		}
		ourOIDStore.__init__(self, session, oids)
		self.tuner = None
		self.frontend = None
		self.oldref = None
		self.transponderparams = 'freq(kHz),symbolrate(kHz),polarisation(H=0/V=1),fec(0=auto),inversion(0=no/1=yes/2=auto),orbitalpos(10ths of degrees)'

	def setServiceMode(self):
		self.tuner = None
		self.transponderparams = 'freq(kHz),symbolrate(kHz),polarisation(H=0/V=1),fec(0=auto),inversion(0=no/1=yes/2=auto),orbitalpos(10ths of degrees)'
		if self.frontend:
			self.frontend = None
			del self.raw_channel
		if self.session and self.session.nav:
			self.session.nav.playService(self.oldref)

	def setTransponderMode(self):
		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService() # try to disable foreground service
			if not self.openFrontend():
				if self.session.pipshown: # try to disable pip
					self.session.pipshown = False
					del self.session.pip
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen
		self.tuner = Tuner(self.frontend)

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def tune(self, transponder):
		self.setTransponderMode()
		if self.frontend and self.tuner:
			if transponder is not None:
				self.tuner.tune(transponder)

	def zapTo(self, reftozap):
		self.setServiceMode()
		ourOIDStore.zapTo(self, reftozap)

	def setValue(self, oid, value):
		#the first time we are called, we have to fill the bisect oid store, values are just values, no objects (we cannot call value.get)
		try:
			value.get()
		except:
			return ourOIDStore.setValue(self, oid, value)

		oidstring = bisectoidstore.sortableToOID(oid)
		if oidstring == self.TRANSPONDERPARAMS_OID:
			print value.get()
			self.transponderparams = value.get()
			transponder = value.get().split(',')
			if len(transponder) >= 6:
				for i in range(0, 6):
					transponder[i] = int(transponder[i])
				print transponder
				self.tune(transponder)
			return None
		else:
			return ourOIDStore.setValue(self, oid, value)

	def getBER(self):
		if self.frontend:
			return self.frontend.readFrontendData(iFrontendInformation.bitErrorRate)
		else:
			return ourOIDStore.getBER(self)

	def getAGC(self):
		if self.frontend:
			return self.frontend.readFrontendData(iFrontendInformation.signalQuality) * 100 / 65536
		else:
			return ourOIDStore.getAGC(self)

	def getSNR(self):
		if self.frontend:
			return self.frontend.readFrontendData(iFrontendInformation.signalPower) * 100 / 65536
		else:
			return ourOIDStore.getSNR(self)

	def getTransponderParamsOIDValue(self, oid, storage):
		value = self.transponderparams
		if not self.frontend:
			if self.session and self.session.nav and self.session.nav.getCurrentService():
				feinfo = self.session.nav.getCurrentService().frontendInfo()
				frontendData = feinfo and feinfo.getAll(True)
				if frontendData:
					value += ' example for current transponder: '
					value += str(frontendData["frequency"] / 1000)
					value += ','
					value += str(frontendData["symbol_rate"] / 1000)
					value += ','
					if frontendData["polarization"] == 'HORIZONTAL':
						value += '0'
					else:
						value += '1'
					value += ','
					#FEC: auto
					value += '0'
					value += ','
					#inversion: auto
					value += '2'
					value += ','
					value += str(frontendData["orbital_position"])
		return v1.OctetString(value)

class SnmpAgent:
    oldmanagerip = ""
    oldber = 0
    theAgent = None
    pollTimer = None
    startTime = time.time()
    oldmanagers = []
    agentObject = None

    def __init__(self, session, storetype):
        self.oidstore = storetype(session)
        self.storetype = storetype

        self.StartAgent()

    def createAgent(self):
        from twisted.internet import reactor
        port = 161
        try:
            self.agentObject = reactor.listenUDP(
	            port, agentprotocol.AgentProtocol(
		            snmpVersion='v2c',
		            agent=agent.Agent(dataStore=self.oidstore),
	            ),
            )
            self.theAgent = self.agentObject.protocol.agent
        except twisted_error.CannotListenError:
            pass
        else:
            return port

    def stopAgent(self):
        if self.agentObject != None:
            self.pollTimer.stop()
            self.agentObject.stopListening()

    def StartAgent(self):
        port = self.createAgent()
        if port is not None:
            print 'Listening on port', port
            agentrunning = 1
            self.pollTimer = eTimer()
            self.pollTimer.timeout.get().append(self.timerPoll)
            self.pollTimer.start(1000, False)

    def timerPoll(self):
        self.oidstore.timerPoll()

        if self.theAgent:
            managerip = config.plugins.SnmpAgent.managerip.value

            if managerip <> self.oldmanagerip:
                newmanagers = managerip.split(',')
                for oldmanager in self.oldmanagers:
                    self.theAgent.deregisterTrap(oldmanager)
                for newmanagerip in newmanagers:
                    handler = agent.TrapHandler(
		                    managerIP=(newmanagerip, 162),
	                    )
                    self.theAgent.registerTrap(handler)

                self.oldmanagerip = managerip
                self.oldmanagers = newmanagers

            if not len(managerip):
                return
            if managerip == '0.0.0.0':
                return

            ber = self.oidstore.getBER()
            if ber is not self.oldber:
                self.oldber = ber
                try:
                    self.theAgent.sendTrap(pdus=[(self.storetype.BER_OID, ber), ])
                except:
                    pass

#===============================================================================
# stopSNMPserver
# Actions to take place to stop the SNMPserver
#===============================================================================
def stopSNMPserver(session):
    global global_my_agent
    if global_my_agent != None:
        global_my_agent.stopAgent()
    print "[SNMPAgent] service stopped"


#===============================================================================
# startSNMPserver
# Actions to take place to start the SNMPserver
#===============================================================================
def startSNMPserver(session):
	global global_my_agent
	global_my_agent = SnmpAgent(session, ourTunerOIDStore)
	print "[SNMPAgent] started"


#===============================================================================
# sessionstart
# Actions to take place on Session start
#===============================================================================
def sessionstart(reason, session):
	global global_session
	global_session = session

#===============================================================================
# autostart
# Actions to take place in autostart (startup the SNMPAgent)
#===============================================================================
def autostartEntry(reason, **kwargs):
	global global_my_agent

	if reason == 1 and config.plugins.SnmpAgent.startuptype.value:
		startSNMPserver(global_session)
	elif reason == 0:
		stopSNMPserver(global_session)

#===============================================================================
# main
# Actions to take place when starting the plugin over extensions
#===============================================================================
def main(session, **kwargs):
	session.open(SNMPAgent_MainMenu)

#===============================================================================
# plugins
# Actions to take place in Plugins
#===============================================================================
def Plugins(**kwargs):
	return [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart),
			PluginDescriptor(where=[PluginDescriptor.WHERE_NETWORKCONFIG_READ], fnc=autostartEntry),
			PluginDescriptor(name="SnmpAgent", description=_("SNMP Agent for Enigma2"), icon="SNMPAgent.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
