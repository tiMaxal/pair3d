import os
from setuptools import setup, find_packages

data_files = [
    ('share/applications', ['pair3d.desktop']),
    ('share/icons/hicolor/64x64/apps', ['imgs/pair3d.sm.png']),
]

setup(
    name="pair3d",
    version="1.3.0",  # match your script version
    author="tiMaxal",
    author_email="timaxal@mail.com",
    description="A stereo image sorter using perceptual similarity and timestamp proximity.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tiMaxal/pair3d",
    license="MIT",
    data_files=data_files,
    packages=find_packages(),  # or use [] if it's a single-file script
    py_modules=["pair3d"],  # because it's a single script file
    install_requires=[
        "Pillow",
        "ImageHash",
    ],
    entry_points={
        'console_scripts': [
            'pair3d-cli = pair3d:main',
        ],
        'gui_scripts': [
            'pair3d = pair3d:main',
        ],
    },
    package_data={
        "": ["imgs/*.ico"],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Win32 (GUI)",
        "Environment :: MacOS X",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
)
