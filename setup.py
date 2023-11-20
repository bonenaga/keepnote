#!/usr/bin/env python
# 
# setup for KeepNote
#
# use the following command to install KeepNote:
#   python setup.py install
#
#=============================================================================

#
#  KeepNote
#  Copyright (c) 2008-2011 Matt Rasmussen
#  Author: Matt Rasmussen <rasmus@alum.mit.edu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.
#




#=============================================================================
# constants

import keepnote
KEEPNOTE_VERSION = keepnote.PROGRAM_VERSION_TEXT


#=============================================================================
# python and distutils imports
import os
import sys
import shutil
from setuptools import setup

# cx_Freeze module (if building on windows)
try:
    import cx_Freeze
except ImportError:
    pass


#=============================================================================
# helper functions

def split_path(path):
    """Splits a path into all of its directories"""

    pathlist = []
    while path != "":
        path, tail = os.path.split(path)
        pathlist.append(tail)
    pathlist.reverse()
    return pathlist
    


def get_files(path, exclude_func=lambda f: False):
    """Recursively get files from a directory"""
    files = []

    def exclude(filename):
        for ext in exclude_func(filename):
            if filename.endswith(ext):
                return True
        return False
	

def walk(path):
    files = []  # Declare the 'files' list variable

    for f in os.listdir(path):
        filename = os.path.join(path, f)
        if exclude(filename):
            # exclude certain files
            continue
        elif os.path.isdir(filename):
            # recurse directories
            walk(filename)  # Update recursive call to 'walk'
        else:
            # record all other files
            files.append(filename)

    return files  # Move the return statement inside the function scope

files = walk(path)  # Call the function with the initial path



def get_file_lookup(files, prefix_old, prefix_new, exclude_func=lambda f: False):
    """Create a dictionary lookup of files"""

    if files is None:
        files = get_files(prefix_old, exclude=exclude_func)

    prefix_old = split_path(prefix_old)
    prefix_new = split_path(prefix_new)
    lookup = {}

    def exclude(filename):
        for ext in exclude_func(filename):
            if filename.endswith(ext):
                return True
        return False

    for f in files:
        path = prefix_new + split_path(f)[len(prefix_old):]
        dirpath = os.path.join(*path[:-1])
        lookup.setdefault(dirpath, []).append(f)

    return lookup


def remove_package_dir(filename):
    i = filename.index("/")
    return filename[i+1:]


#=============================================================================
# resource files/data

# Import the appropriate module where get_file_lookup is defined or imported from
from <module_name> import get_file_lookup

# Update the exclude function to match the desired exclusion behavior
def exclude_func(filename):
    exclude_list = [".pyc"]
    return any(filename.endswith(ext) for ext in exclude_list)

# get resources
rc_files = get_file_lookup(None, "keepnote/rc", "rc", exclude_func)
image_files = get_file_lookup(None, "keepnote/images", "images", exclude_func)
efiles = get_file_lookup(None, "keepnote/extensions", "extensions", exclude_func)
freedesktop_files = [
    # application icon
    ("share/icons/hicolor/48x48/apps", ["desktop/keepnote.png"]),

    # desktop menu entry
    ("share/applications", ["desktop/keepnote.desktop"])
]


if "py2exe" in sys.argv:
    data_files = {}
    data_files.update(rc_files)
    data_files.update(efiles)
    data_files.update(image_files)
    package_data = {}

else:
    data_files = freedesktop_files
    package_data = {'keepnote': []}
    for files_dict in [rc_files, image_files, efiles]:
        for v in files_dict.values():
            package_data['keepnote'].extend(map(remove_package_dir, v))


#=============================================================================
# setup

setup(
    name='keepnote',
    version=KEEPNOTE_VERSION,
    description='A cross-platform note taking application',
    long_description="""
        KeepNote is a cross-platform note taking application.  Its features 
        include:
        
        - rich text editing
        
          - bullet points
          - fonts/colors
          - hyperlinks
          - inline images
          
        - hierarchical organization for notes
        - full text search
        - integrated screenshot
        - spell checking (via gtkspell)
        - backup and restore
        - HTML export
    """,
    author='Matt Rasmussen',
    author_email='rasmus@alum.mit.edu',
    url='http://keepnote.org',
    download_url='http://keepnote.org/download/keepnote-%s.tar.gz' % KEEPNOTE_VERSION,
    
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
    ],
    license="GPL",
    
    packages=['keepnote',
              'keepnote.gui',
              'keepnote.gui.richtext',
              'keepnote.notebook',
              'keepnote.notebook.connection',
              'keepnote.notebook.connection.fs',
              'keepnote.compat',
              'keepnote.mswin'],
    scripts=['bin/keepnote'],
    data_files=data_files,
    package_data=package_data,
    
    windows=[{
        'script': 'bin/keepnote',
        'icon_resources': [(1, 'keepnote/images/keepnote.ico')],
    }],
    options={
        'py2exe': {
            'packages': 'encodings',
            'includes': 'cairo,pango,pangocairo,atk,gobject,win32com.shell,win32api,win32com,win32ui,win32gui',
            'dist_dir': 'dist/keepnote-%s.win' % KEEPNOTE_VERSION
        }
    }
)

# Execute post-build script
if "py2exe" in sys.argv:
    with open("pkg/win/post_py2exe.py") as f:
        code = compile(f.read(), "post_py2exe.py", 'exec')
        exec(code)
