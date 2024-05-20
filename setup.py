import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="codedepot-git-ai",
    version="0.1.0",
    author="CodeDepot",
    author_email="contact@codedepot.ai",
    description="Dataset and model support for git",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/codedepotai/git-ai",
    project_urls={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['git-ai=git_ai.main.main:main'],
    },
    install_requires=[
        'tensorboard',
        'torch',
        'pygit2>=1.4.1',
        'paramiko',
        'prompt_toolkit'
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.10",
)
