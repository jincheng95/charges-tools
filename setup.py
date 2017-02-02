try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="ChargeTools",
    version="0.1",
    packages=['chargetools'],
    install_requires=['numpy', 'periodictable', 'scipy']
)
