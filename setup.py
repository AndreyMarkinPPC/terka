from __future__ import annotations

import pathlib
from itertools import chain

from setuptools import find_packages
from setuptools import setup

HERE = pathlib.Path(__file__)
README = (HERE.parent / 'README.md').read_text()
EXTRAS_REQUIRE = {'asana': ['asana==5.0.0']}

EXTRAS_REQUIRE['all'] = list(set(chain(*EXTRAS_REQUIRE.values())))

setup(
    name='terka',
    version='2.9.1',
    description='CLI utility for creating and managing tasks in a terminal',
    long_description=README,
    long_description_content_type='text/markdown',
    author='Andrei Markin',
    author_email='andrey.markin.ppc@gmail.com',
    license='Apache 2.0',
    url='https://github.com/AndreyMarkinPPC/terka',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['presentations/text_ui/css/*.css']},
    install_requires=[
        'sqlalchemy==1.4.0',
        'pyaml',
        'rich',
        'textual==0.41.0',
        'plotext==5.2.8',
        'textual-plotext==0.2.1',
        'pandas',
        'matplotlib',
    ],
    setup_requires=['pytest-runner'],
    tests_requires=['pytest'],
    extras_require=EXTRAS_REQUIRE,
    entry_points={'console_scripts': ['terka=terka.entrypoints.cli:main']},
)
