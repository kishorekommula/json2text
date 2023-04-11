from setuptools import setup, find_packages

VERSION = '1.0.0'
DESCRIPTION = 'Transform Json to natural text'
LONG_DESCRIPTION = 'A package to transform Json to natural text using predefined templates'

setup(
    name="json2text",
    version=VERSION,
    author="Ashwin Prabhu",
    license="MIT",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    package_data={'json2text': ['README.md', 'sample_template.json', 'sample_module.py']},
    install_requires=[],
    keywords=['json2text', 'json to text',  'json', 'natural-text', 'json2text transformer', 'transform json to text'],
    classifiers=[
        "Development Status :: Pilot",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
    zip_safe=False
)