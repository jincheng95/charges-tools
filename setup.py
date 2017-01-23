try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

setup(
    name="ChargesTools",
    version="0.1",
    packages=['charges'],
)
