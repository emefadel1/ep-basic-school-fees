# config/settings/__init__.py

"""
Settings package for E.P Basic School Fee Management System.
Automatically loads appropriate settings based on environment.
"""

import os

environment = os.getenv('DJANGO_ENV', 'development')

if environment == 'production':
    from .production import *
elif environment == 'development':
    from .development import *
else:
    from .development import *