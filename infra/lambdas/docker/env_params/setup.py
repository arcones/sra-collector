import setuptools

setuptools.setup(
    name='env_params',
    version='0.0.1',
    author='Marta Arcones',
    author_email='marta.arcones@alumnos.upm.es',
    description='Provide environment configuration to my lambdas',
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    python_requires='>=3.11',
    install_requires=['boto3'],
)
