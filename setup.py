#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from setuptools import setup, find_packages
import os
import glob
import sys

args = {}

try:
    from babel.messages import frontend as babel

    args['cmdclass'] = {
            'compile_catalog': babel.compile_catalog,
            'extract_messages': babel.extract_messages,
            'init_catalog': babel.init_catalog,
            'update_catalog': babel.update_catalog,
        }

    args['message_extractors'] = {
            'tryton': [
                ('**.py', 'python', None),
            ],
        }

except ImportError:
        pass

if os.name == 'nt':
    import py2exe
    origIsSystemDLL = py2exe.build_exe.isSystemDLL
    def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() in ("msvcp71.dll", "dwmapi.dll"):
            return 0
        return origIsSystemDLL(pathname)
    py2exe.build_exe.isSystemDLL = isSystemDLL

    args['windows'] = [{
        'script': os.path.join('bin', 'tryton'),
    }]
    args['options'] = {
        'py2exe': {
            'optimize': 0,
            'bundle_files': 3, #don't bundle because gtk doesn't support it
            'packages': [
                'encodings',
                'gtk',
                'pytz',
            ],
            'includes': 'pango,atk,gobject,cairo,pangocairo',
            'dll_excludes': [
                'iconv.dll',
                'intl.dll',
                'libatk-1.0-0.dll',
                'libgdk_pixbuf-2.0-0.dll',
                'libgdk-win32-2.0-0.dll',
                'libglib-2.0-0.dll',
                'libgmodule-2.0-0.dll',
                'libgobject-2.0-0.dll',
                'libgthread-2.0-0.dll',
                'libgtk-win32-2.0-0.dll',
                'libpango-1.0-0.dll',
                'libpangowin32-1.0-0.dll',
                'libcairo-2.dll',
                'libfontconfig-1.dll',
                'libfreetype-6.dll',
                'libgdkglext-win32-1.0.0.dll',
                'libglade-2.0-0.dll',
                'libgtkglext-win32-1.0-0.dll',
                'libpangocairo-1.0-0.dll',
                'libpangoft2-1.0-0.dll',
                'libxml2.dll',
                'zlib1.dll',
            ],
        }
    }
    args['zipfile'] = None

execfile(os.path.join('tryton', 'version.py'))

setup(name=PACKAGE,
    version=VERSION,
    description='Tryton client',
    author='B2CK',
    author_email='info@b2ck.com',
    url=WEBSITE,
    packages=find_packages(),
    data_files=[
        ('share/pixmaps', glob.glob('share/pixmaps/*.png') + \
                glob.glob('share/pixmaps/*.svg')),
        ('share/locale/fr_FR/LC_MESSAGES', glob.glob('share/locale/fr_FR/LC_MESSAGES/*.mo')),
        ('share/locale/de_DE/LC_MESSAGES', glob.glob('share/locale/de_DE/LC_MESSAGES/*.mo')),
        ('share/locale/es_ES/LC_MESSAGES', glob.glob('share/locale/es_ES/LC_MESSAGES/*.mo')),
    ],
    scripts=['bin/tryton'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License Version 2 (GPL-2)',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Natural Language :: French',
        'Natural Language :: German',
        'Natural Language :: Spanish',
        'Programming Language :: Python',
        'Topic :: Office/Business',
    ],
    license=LICENSE,
    install_requires=[
        "pygtk >= 2.0",
        "egenix-mx-base",
    ],
    **args
)
