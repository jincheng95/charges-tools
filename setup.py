try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="ChargesTools",
    version="0.1",
    packages=['charges'], install_requires=['numpy', 'periodictable']
)
