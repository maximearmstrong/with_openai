from setuptools import find_packages, setup

setup(
    name="with_openai",
    packages=find_packages(exclude=["with_openai_tests"]),
    install_requires=["dagster", "dagster-openai", "langchain==0.1.11", "dagster-cloud", "filelock", "langchain-community==0.0.34", "langchain-openai==0.1.3", "faiss-cpu==1.8.0"],
    extras_require={"dev": ["dagster-webserver", "pytest"]},
)
