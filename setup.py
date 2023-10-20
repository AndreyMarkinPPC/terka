import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__)
README = (HERE.parent / "README.md").read_text()

setup(
    name="terka",
    version="1.18.1",
    description="CLI utility for creating and managing tasks in a terminal",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Andrei Markin",
    author_email="andrey.markin.ppc@gmail.com",
    license="Apache 2.0",
    url="https://github.com/AndreyMarkinPPC/terka",
    packages=find_packages(),
    include_package_data=True,
    package_data={"": ["service_layer/*.css"]},
    install_requires=[
        "sqlalchemy==1.4.0",
        "pyaml",
        "rich",
        "textual==0.5.0",
        "plotext==5.2.8",
        "pandas",
        "matplotlib",
    ],
    setup_requires=["pytest-runner"],
    tests_requires=["pytest"],
    entry_points={"console_scripts": ["terka=terka.entrypoints.cli:main"]},
)
