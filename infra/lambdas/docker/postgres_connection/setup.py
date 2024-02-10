import setuptools

setuptools.setup(
    name='postgres_connection',
    version='0.0.2',
    author='Marta Arcones',
    author_email='marta.arcones@alumnos.upm.es',
    description='Postgres connection used in my lambdas',
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    python_requires='>=3.11',
    install_requires=['boto3'],
)
