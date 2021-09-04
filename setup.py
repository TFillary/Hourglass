from setuptools import setup
from Cython.Build import cythonize

setup(
    name='Hourglass modules',
    ext_modules=cythonize(
        ["my_globals.pyx",
         "grains.pyx"],
         annotate=True),
    zip_safe=False,
)