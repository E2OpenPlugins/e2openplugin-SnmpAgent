from distutils.core import setup
import setup_translate

pkg = 'Extensions.SnmpAgent'
setup(name='enigma2-plugin-extensions-snmpagent',
       version='2.0.4',
       description='Snmp Agent to monitor your Enigma2 with a management system',
       package_dir={pkg: 'plugin'},
       packages=[pkg],
       package_data={pkg: ['SNMPAgent.png', 'locale/*/LC_MESSAGES/*.mo']},
       cmdclass=setup_translate.cmdclass, # for translation
      )
