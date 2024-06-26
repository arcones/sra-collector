import setuptools

setuptools.setup(
    name='s3_helper',
    version='0.0.1',
    author='Marta Arcones',
    author_email='marta.arcones@gmail.com',
    description='S3 utility functions',
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    python_requires='>=3.10',
    install_requires=['boto3'],
)
