from setuptools import setup, find_packages

setup(
    name='tools_Houdini',
    version='0.1.0',
    description='Houdini Agentic Mode tooling for Copilot/GPT integration',
    packages=find_packages(include=['tools_Houdini', 'tools_Houdini.*']),
    install_requires=[],
    python_requires='>=3.8',
)
