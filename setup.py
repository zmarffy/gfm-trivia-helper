import re
from os.path import join as join_path

import setuptools

with open(join_path("gfm_trivia_helper", "__init__.py"), encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setuptools.setup(
    name='gfm-trivia-helper',
    version=version,
    author='Zeke Marffy',
    author_email='zmarffy@yahoo.com',
    packages=setuptools.find_packages(),
    url='https://github.com/zmarffy/gfm-trivia-helper',
    license='MIT',
    description="Utilized to streamline the creation of quizzes and checking of users' answers to quizzes on https://thegfmband.com",
    python_requires='>=3.2',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        "requests",
        "zmtools"
    ],
    entry_points={
        'console_scripts': [
            'gfm-trivia-helper = gfm_trivia_helper.cli:main',
            'gfm-trivia-helper-gui = gfm_trivia_helper.gui:main'
        ],
    },
)
