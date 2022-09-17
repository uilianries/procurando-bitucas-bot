import re
import os
from setuptools import setup, find_packages
from codecs import open


def get_requires(filename):
    requirements = []
    with open(filename, 'rt') as req_file:
        for line in req_file.read().splitlines():
            if not line.strip().startswith("#"):
                requirements.append(line)
    return requirements


def load_version():
    filename = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "pb", "__init__.py"))
    with open(filename, "rt") as version_file:
        file_init = version_file.read()
        version = re.search("__version__ = '([0-9a-z.-]+)'", file_init).group(1)
        return version


project_requirements = get_requires("pb/requirements.txt")

setup(
    name='procurando_bitucas_bot',
    version=load_version(),
    python_requires='>=3.7',
    description='A Telegram bot made for the podcast Procurando Bitucas',
    url='https://github.com/uilianries/procurando-bitucas-bot',
    author='Uilian Ries',
    author_email='uilianries@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Communications :: Chat',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Natural Language :: Portuguese',
    ],
    keywords=['podcast', 'hobby', 'music', 'movie', 'comics', 'chat'],
    packages=find_packages(),
    install_requires=project_requirements,
    extras_require={},
    package_data={'pb': ['*.txt']},
    entry_points={'console_scripts': ['procurando-bitucas=pb.procurando_bitucas:main']}
)
