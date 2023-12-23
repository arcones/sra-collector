import setuptools

setuptools.setup(
    name='lambda_log_support',
    version='0.0.1',
    author='Marta Arcones',
    author_email='marta.arcones@alumnos.upm.es',
    description='Log function used across my lambdas',
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    python_requires='>=3.11',
    install_requires=['boto3'],
)
