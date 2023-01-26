import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="terka",
    version="0.0.4",
    description="CLI utility for creating and managing tasks in a terminal",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Andrei Markin",
    author_email="andrey.markin.ppc@gmail.com",
    license="Apache 2.0",
    url="https://github.com/AndreyMarkinPPC/terka",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy", "pyaml", "rich", "textual==0.5.0"
    ],
    setup_requires=["pytest-runner"],
    tests_requires=["pytest"],
    entry_points={
        "console_scripts": [
            "terka=src.entrypoints.cli:main"
        ]
    }
)
