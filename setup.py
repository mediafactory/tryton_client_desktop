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
        'icon_resources': [(1, os.path.join('share', 'pixmaps', 'tryton', 'tryton.ico'))],
    }]
    args['options'] = {
        'py2exe': {
            'optimize': 0,
            'bundle_files': 3, #don't bundle because gtk doesn't support it
            'packages': [
                'encodings',
                'gtk',
                'pytz',
                'atk',
                'pango',
                'pangocairo',
            ],
        }
    }
    args['zipfile'] = None
elif os.name == 'mac' \
        or (hasattr(os, 'uname') and os.uname()[0] == 'Darwin'):
    import py2app
    from modulegraph.find_modules import PY_SUFFIXES
    PY_SUFFIXES.append('')
    args['app'] = [os.path.join('bin', 'tryton')]
    args['options'] = {
        'py2app': {
            'argv_emulation': True,
            'includes': 'pygtk, gtk, glib, cairo, pango, pangocairo, atk, ' \
                    'gobject, gio, gtk.keysyms',
            'resources': 'tryton/plugins',
            'frameworks': 'librsvg-2.2.dylib',
            'plist': {
                'CFBundleIdentifier': 'org.tryton',
            },
            'iconfile': os.path.join('share', 'pixmaps', 'tryton',
                'tryton.icns'),
        },
    }

execfile(os.path.join('tryton', 'version.py'))

dist = setup(name=PACKAGE,
    version=VERSION,
    description='Tryton client',
    author='B2CK',
    author_email='info@b2ck.com',
    url=WEBSITE,
    download_url="http://downloads.tryton.org/" + \
            VERSION.rsplit('.', 1)[0] + '/',
    packages=find_packages(),
    data_files=[
        ('share/pixmaps', glob.glob('share/pixmaps/tryton-icon.png')),
        ('share/pixmaps/tryton', glob.glob('share/pixmaps/tryton/*.png') + \
                glob.glob('share/pixmaps/tryton/*.svg')),
        ('share/locale/cs_CZ/LC_MESSAGES', glob.glob('share/locale/cs_CZ/LC_MESSAGES/*.mo')),
        ('share/locale/de_DE/LC_MESSAGES', glob.glob('share/locale/de_DE/LC_MESSAGES/*.mo')),
        ('share/locale/es_CO/LC_MESSAGES', glob.glob('share/locale/es_CO/LC_MESSAGES/*.mo')),
        ('share/locale/es_ES/LC_MESSAGES', glob.glob('share/locale/es_ES/LC_MESSAGES/*.mo')),
        ('share/locale/fr_FR/LC_MESSAGES', glob.glob('share/locale/fr_FR/LC_MESSAGES/*.mo')),
    ],
    scripts=['bin/tryton'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
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
#        "pygtk >= 2.0",
        "egenix-mx-base",
    ],
    extras_require={
        'timezone': ['pytz'],
    },
    **args
)

if os.name == 'nt':
    def find_gtk_dir():
        for directory in os.environ['PATH'].split(';'):
            if not os.path.isdir(directory):
                continue
            for file in ('gtk-demo.exe', 'gdk-pixbuf-query-loaders.exe'):
                if os.path.isfile(os.path.join(directory, file)):
                    return os.path.dirname(directory)
        return None

    def find_makensis():
        for directory in os.environ['PATH'].split(';'):
            if not os.path.isdir(directory):
                continue
            path = os.path.join(directory, 'makensis.exe')
            if os.path.isfile(path):
                return path
        return None

    if 'py2exe' in dist.commands:
        import shutil
        gtk_dir = find_gtk_dir()

        dist_dir = dist.command_obj['py2exe'].dist_dir

        if os.path.isdir(os.path.join(dist_dir, 'plugins')):
            shutil.rmtree(os.path.join(dist_dir, 'plugins'))
        shutil.copytree(os.path.join(os.path.dirname(__file__), 'tryton', 'plugins'),
            os.path.join(dist_dir, 'plugins'))

        if os.path.isdir(os.path.join(dist_dir, 'etc')):
            shutil.rmtree(os.path.join(dist_dir, 'etc'))
        shutil.copytree(os.path.join(gtk_dir, 'etc'),
            os.path.join(dist_dir, 'etc'))

        if os.path.isdir(os.path.join(dist_dir, 'lib')):
            shutil.rmtree(os.path.join(dist_dir, 'lib'))
        shutil.copytree(os.path.join(gtk_dir, 'lib'),
            os.path.join(dist_dir, 'lib'))

        for lang in ('de', 'es', 'fr'):
            if os.path.isdir(os.path.join(dist_dir, 'share', 'locale', lang)):
                shutil.rmtree(os.path.join(dist_dir, 'share', 'locale', lang))
            shutil.copytree(os.path.join(gtk_dir, 'share', 'locale', lang),
                os.path.join(dist_dir, 'share', 'locale', lang))

        if os.path.isdir(os.path.join(dist_dir, 'share', 'themes', 'MS-Windows')):
            shutil.rmtree(os.path.join(dist_dir, 'share', 'themes', 'MS-Windows'))
        shutil.copytree(os.path.join(gtk_dir, 'share', 'themes', 'MS-Windows'),
            os.path.join(dist_dir, 'share', 'themes', 'MS-Windows'))

        makensis = find_makensis()
        if makensis:
            from subprocess import Popen
            Popen([makensis, "/DVERSION=" + VERSION,
                str(os.path.join(os.path.dirname(__file__),
                    'setup.nsi'))]).wait()
            Popen([makensis, "/DVERSION=" + VERSION,
                str(os.path.join(os.path.dirname(__file__),
                    'setup-single.nsi'))]).wait()
elif os.name == 'mac' \
        or (hasattr(os, 'uname') and os.uname()[0] == 'Darwin'):
    def find_gtk_dir():
        for directory in os.environ['PATH'].split(':'):
            if not os.path.isdir(directory):
                continue
            for file in ('gtk-demo',):
                if os.path.isfile(os.path.join(directory, file)):
                    return os.path.dirname(directory)
        return None

    if 'py2app' in dist.commands:
        import shutil
        from subprocess import Popen, PIPE
        from itertools import chain
        from glob import iglob
        gtk_dir = find_gtk_dir()
        gtk_binary_version = Popen(['pkg-config', '--variable=gtk_binary_version',
            'gtk+-2.0'], stdout=PIPE).stdout.read().strip()

        dist_dir = dist.command_obj['py2app'].dist_dir
        resources_dir = os.path.join(dist_dir, 'tryton.app', 'Contents', 'Resources')
        gtk_2_dist_dir = os.path.join(resources_dir, 'lib', 'gtk-2.0')
        pango_dist_dir = os.path.join(resources_dir, 'lib', 'pango')

        if os.path.isdir(pango_dist_dir):
            shutil.rmtree(pango_dist_dir)
        shutil.copytree(os.path.join(gtk_dir, 'lib', 'pango'), pango_dist_dir)

        query_pango = Popen(os.path.join(gtk_dir, 'bin', 'pango-querymodules'),
                stdout=PIPE).stdout.read()
        query_pango = query_pango.replace(gtk_dir, '@executable_path/../Resources')
        pango_modules = open(os.path.join(resources_dir, 'pango.modules'), 'w')
        pango_modules.write(query_pango)
        pango_modules.close()

        pangorc = open(os.path.join(resources_dir, 'pangorc'), 'w')
        pangorc.write('[Pango]\n')
        pangorc.write('ModuleFiles=./pango.modules\n')
        pangorc.close()

        if os.path.isdir(os.path.join(gtk_2_dist_dir, gtk_binary_version, 'loaders')):
            shutil.rmtree(os.path.join(gtk_2_dist_dir, gtk_binary_version, 'loaders'))
        shutil.copytree(os.path.join(gtk_dir, 'lib', 'gtk-2.0', gtk_binary_version,
                'loaders'), os.path.join(gtk_2_dist_dir, gtk_binary_version, 'loaders'))
        if not os.path.isdir(os.path.join(gtk_2_dist_dir, gtk_binary_version, 'engines')):
            os.makedirs(os.path.join(gtk_2_dist_dir, gtk_binary_version, 'engines'))
        shutil.copyfile(os.path.join(gtk_dir, 'lib', 'gtk-2.0', gtk_binary_version,
                'engines', 'libclearlooks.so'), os.path.join(gtk_2_dist_dir,
                gtk_binary_version, 'engines', 'libclearlooks.so'))

        query_loaders = Popen(os.path.join(gtk_dir,'bin','gdk-pixbuf-query-loaders'),
                stdout=PIPE).stdout.read()
        query_loaders = query_loaders.replace(gtk_dir, '@executable_path/../Resources')
        loaders = open(os.path.join(resources_dir, 'gdk-pixbuf.loaders'), 'w')
        loaders.write(query_loaders)
        loaders.close()

        shutil.copy(os.path.join(gtk_dir, 'share', 'themes', 'Clearlooks',
            'gtk-2.0', 'gtkrc'), os.path.join(resources_dir, 'gtkrc'))

        # fix pathes within shared libraries
        for library in chain(
                iglob(os.path.join(gtk_2_dist_dir, gtk_binary_version, 'loaders', '*.so')),
                iglob(os.path.join(gtk_2_dist_dir, gtk_binary_version, 'engines', '*.so')),
                iglob(os.path.join(pango_dist_dir,'*','modules','*.so'))):
            libs = [lib.split('(')[0].strip()
                    for lib in Popen(['otool', '-L', library],
                            stdout=PIPE).communicate()[0].splitlines()
                    if 'compatibility' in lib]
            libs = dict(((lib, None) for lib in libs if gtk_dir in lib))
            for lib in libs.keys():
                fixed = lib.replace(gtk_dir + '/lib',
                        '@executable_path/../Frameworks')
                Popen(['install_name_tool', '-change', lib, fixed,
                    library]).wait()

        for file in ('CHANGELOG', 'COPYRIGHT', 'LICENSE', 'README', 'TODO'):
            shutil.copyfile(os.path.join(os.path.dirname(__file__), file),
                os.path.join(dist_dir, file + '.txt'))

        doc_dist_dir = os.path.join(dist_dir, 'doc')
        if os.path.isdir(doc_dist_dir):
            shutil.rmtree(doc_dist_dir)
        shutil.copytree(os.path.join(os.path.dirname(__file__), 'doc'),
                doc_dist_dir)

        dmg_file = os.path.join(os.path.dirname(__file__), 'tryton-' + VERSION
                + '.dmg')
        if os.path.isfile(dmg_file):
            os.remove(dmg_file)
        Popen(['hdiutil', 'create', dmg_file, '-volname', '"Tryton Client ' +
            VERSION + '"', '-fs', 'HFS+', '-srcfolder', dist_dir]).wait()
