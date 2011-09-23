from distutils.core import setup, Extension

pkg = 'Extensions.SnmpAgent'
setup (name = 'enigma2-plugin-extensions-snmpagent',
       version = '0.1',
       description = 'SnmpAgent',
       packages = [pkg],
       package_dir = {pkg: 'plugin'}
      )
