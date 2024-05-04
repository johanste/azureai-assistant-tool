# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

from setuptools import setup, find_packages
import os
from io import open
import re


PACKAGE_NAME = "azure-ai-assistant"
PACKAGE_PPRINT_NAME = "AI Assistant"

# a-b-c => a/b/c
PACKAGE_FOLDER_PATH = "sdk/azure-ai-assistant/azure/ai/assistant"
# a-b-c => a.b.c
NAMESPACE_NAME = PACKAGE_NAME.replace("-", ".")

# Version extraction inspired from 'requests'
with open(os.path.join(PACKAGE_FOLDER_PATH, "_version.py"), "r") as fd:
    version = re.search(r'^VERSION\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)
if not version:
    raise RuntimeError("Cannot find version information")

with open("sdk/azure-ai-assistant/README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name=PACKAGE_NAME,
    version=version,
    description="Microsoft Azure {} Client Library for Python".format(PACKAGE_PPRINT_NAME),
    # ensure that these are updated to reflect the package owners' information
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Azure/azure-sdk-for-python",
    keywords="azure, azure sdk, assistant",  # update with search keywords relevant to the azure service / product
    author="Microsoft Corporation",
    author_email="azuresdkengsysadmins@microsoft.com",
    license="MIT License",
    # ensure that the development status reflects the status of your package
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
    ],
    packages=find_packages(
        where="sdk/azure-ai-assistant",
        exclude=[
            # Exclude packages that will be covered by PEP420 or nspkg
            # This means any folder structure that only consists of a __init__.py.
            # For example, for storage, this would mean adding 'azure.storage'
            # in addition to the default 'azure' that is seen here.
            "azure",
            "azure.ai"
        ]
    ),
    package_dir={'': 'sdk/azure-ai-assistant'},
    package_data={
        'azure.ai.assistant': ['py.typed'],
    },
    entry_points = {
        'console_scripts': [
            'openaiassistants=azure.ai.assistant.__main__:main'
        ],
    },
    extras_require={
        "UI": ["PySide6>=6.7" ],
    },
    install_requires=[
        "openai>=1.23.2",
        "python-Levenshtein>=0.20.0,<=0.23.0",
        "fuzzywuzzy>=0.17.0,<=0.18.0",
        "Pillow>=10.1.0,<=10.2.0",
        "PyYAML>=5.3, <=6.0.1",
    ],
    python_requires=">=3.8",
    project_urls={
        "Bug Reports": "https://github.com/Azure/azure-sdk-for-python/issues",
        "Source": "https://github.com/Azure/azure-sdk-python",
    },
)