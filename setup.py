from setuptools import setup, find_packages

setup(
    name="tinkoff_client",             
    version="1.0.0",                   
    packages=find_packages(),          
    install_requires=[              
        "pandas",
        "tinkoff-invest>=0.2.0-beta108",     
    ],
    python_requires=">=3.10",         
    description="Python client for Tinkoff Invest API",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/makarsemyonov/TinkoffClient", 
    author="Makar Semyonov",
    classifiers=[                     
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
