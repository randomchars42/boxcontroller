#!/usr/bin/env python3

# get some more information:
# https://packaging.python.org/guides/distributing-packages-using-setuptools/#setup-py
# https://packaging.python.org/tutorials/packaging-projects/
# https://github.com/pypa/sampleproject

from setuptools import setup, find_packages
import pathlib

path = pathlib.Path(__file__).parent.resolve()

setup(
    name='boxcontroller',
    description='',
    version='0.1.0',
    long_description = (path / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type="text/markdown",
    author='Eike Kühn',
    author_email='eike.kuehn@pixelwoelkchen.de',
    license='The Unlicense',
    url='https://github.com/randomchars42/boxcontroller',
    project_urls={
        'Documentation': 'https://github.com/randomchars42/boxcontroller',
        'Source': 'https://github.com/randomchars42/boxcontroller',
        'Tracker': 'https://github.com/randomchars42/boxcontroller/issues',
    },
    keywords='',
    classifiers=[
        # see https://pypi.org/classifiers/
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        # Pick your license as you wish
        'License :: OSI Approved :: The Unlicense (Unlicense)',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate you support Python 3. These classifiers are *not*
        # checked by 'pip install'. See instead 'python_requires' below.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={  # Optional
        'boxcontroller': ['FILE'],
    }
    python_requires='>=3.6, < 4',
    setup_requires=[
        'docutils>=0.3',
        'wheel',
        'setuptools',
    ],
    install_requires=[
        'gpiodmonitor>=0.2.0',
        'evdev >= 1.4.0'
    ],
    entry_points={
        'console_scripts':['main=boxcontroller.boxcontroller:main']
    }
)
