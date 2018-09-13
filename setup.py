from setuptools import setup

setup(
    name='switchcon',
    keywords='linux usb gadget functionfs hid',
    version='0.1',
    author='Alistair Buxton',
    author_email='a.j.buxton@gmail.com',
    url='http://github.com/ali1234/switch-controller',
    license='GPLv3+',
    platforms=['linux'],
    packages=['switchcon'],
    install_requires=[
        'functionfs', 'tqdm', 'pyserial', 'pysdl2'
    ],
    entry_points={
        'console_scripts': [
            'switchcon = switchcon.__main__:main'
        ]
    },
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Hardware :: Hardware Drivers',
    ],
)
