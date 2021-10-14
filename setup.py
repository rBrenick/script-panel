import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="script-panel",
    version="1.0.0",
    author="Richard Brenick",
    author_email="RichardBrenick@gmail.com",
    description="list of scripts from a folder",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rBrenick/script-panel",
    packages=setuptools.find_packages(),
    package_data={'': ['*.*']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)


