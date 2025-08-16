from setuptools import setup, find_packages

setup(name="tradingsetup",
    version="0.1",
    description="A trading setup for automated stock trading",
    author="Shivdatta Redekar",
    packages=find_packages(),
    install_requires=[
        'langchain_groq',
        'langchain_community',
        'fyers-apiv3',
        'schedule',
        'flask',
        'pandas',
        'openpyxl',
        'python-dotenv',
        'ipykernel',

    ])

import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


__version__ = "0.0.0"

REPO_NAME = "Trading_Bot"
AUTHOR_USER_NAME = "shivdatta"
SRC_REPO = "tradingsetup"
AUTHOR_EMAIL = "shivdattaredekar@gmail.com"


setuptools.setup(
    name=SRC_REPO,
    version=__version__,
    author=AUTHOR_USER_NAME,
    author_email=AUTHOR_EMAIL,
    description="A small python package for trading app",
    long_description=long_description,
    long_description_content="text/markdown",
    url=f"https://github.com/{AUTHOR_USER_NAME}/{REPO_NAME}",
    project_urls={
        "Bug Tracker": f"https://github.com/{AUTHOR_USER_NAME}/{REPO_NAME}/issues",
    },
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src")
)