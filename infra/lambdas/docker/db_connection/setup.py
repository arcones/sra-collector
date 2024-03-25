import setuptools

setuptools.setup(
    name='db_connection',
    version='0.0.5',
    author='Marta Arcones',
    author_email='marta.arcones@gmail.com',
    description='DB connection used in my lambdas',
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    python_requires='>=3.10',
    install_requires=['boto3'],
)
