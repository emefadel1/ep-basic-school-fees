# utils/exceptions.py

"""
Custom DRF exception handlers.
"""

from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    return response


def exception_handler(exc, context):
    return custom_exception_handler(exc, context)