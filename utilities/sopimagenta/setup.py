import setuptools

setuptools.setup(
    name="sopimagenta",
    version="0.1.0",
    author="sopi.aalto.fi",
    description="A small example package",
    url="https://github.com/SopiMlab/DeepLearningWithAudio",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "magenta>=1.3"
    ]
)
