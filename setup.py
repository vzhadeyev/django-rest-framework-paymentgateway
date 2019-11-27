#!/usr/bin/env python3
from io import open

from setuptools import find_packages, setup


def read(f):
    return open(f, 'r', encoding='utf-8').read()


setup(
    name='djangorestframework_paymentgateway',
    version='0.0.1',
    url='https://github.com/vzhadeyev/django-rest-framework-paymentgateway',
    license='',
    description='Payments gateway plugin for Django REST Framework',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Vyacheslav Zhadeyev',
    author_email='vzhadeyev@gmail.com',
    packages=find_packages(exclude=['tests', 'tests.*', 'licenses', 'requirements']),
    include_package_data=True,
    install_requires=[
        'django',
        'djangorestframework',
    ],
    python_requires=">=3.6",
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
