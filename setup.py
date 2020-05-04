from os import path
from setuptools import setup, find_packages
from io import open

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="b-ga-covid-dash",
    version="0.1",
    description='Georgia Covid-19 Cases visualized using Dash',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/briannaleilani/ga_covid_dash',
    author='Brianna Wilkin',
    author_email='brileilani@gmail.com',
    classifiers=[],
    keywords='Plotly Dash Flask Data',
    packages=find_packages(),
     install_requires=['pandas',
                      'numpy',
                      'geopandas',
                      'plotly',
                      'dash',
                      'gunicorn',
                      'flask'],
    entry_points={
        'console_scripts': [
            'run = wsgi:main',
        ],
    },
    project_urls={
        'Source': 'https://github.com/briannaleilani/ga_covid_dash',
    },
)