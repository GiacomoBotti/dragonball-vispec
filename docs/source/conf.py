# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

project = 'Dragonball Suite'
copyright = '2026, G.Botti G.Mandelli'
author = 'G.Botti G.Mandelli'
release = '0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
#    "sphinxfortran.fortran_domain",
#    "sphinxfortran.fortran_autodoc",
    "myst_parser",
    "sphinx.ext.mathjax",
    "matplotlib.sphinxext.plot_directive",
]

myst_enable_extensions = [
    "dollarmath",
    "amsmath",
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
#html_theme = 'alabaster'
html_static_path = ['_static']
