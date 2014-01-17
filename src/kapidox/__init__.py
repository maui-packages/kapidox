# -*- coding: utf-8 -*-

# Python 2/3 compatibility (NB: we require at least 2.7)
from __future__ import division, absolute_import, print_function, unicode_literals

import codecs
import datetime
import os
import re
import shutil
import subprocess
import sys

from fnmatch import fnmatch
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from .doxyfilewriter import DoxyfileWriter

DEPENDENCY_DIAGRAM_PAGE = 'dependencies'

def smartjoin(pathorurl1,*args):
    """Join paths or URLS

    It figures out which it is from whether the first contains a "://"
    """
    if '://' in pathorurl1:
        if not pathorurl1.endswith('/'):
            pathorurl1 += '/'
        return urljoin(pathorurl1,*args)
    else:
        return os.path.join(pathorurl1,*args)

def find_datadir(searchpaths, testentries, suggestion=None, complain=True):
    """Find data files

    Looks at suggestion and the elements of searchpaths to see if any of them
    is a directory that contains the entries listed in testentries.

    searchpaths -- directories to test
    testfiles   -- files to check for in the directory
    suggestion  -- the first place to look
    complain    -- print a warning if suggestion is not correct

    Returns a path to a directory containing everything in testentries, or None
    """

    def check_datadir_entries(directory):
        """Check for the existence of entries in a directory"""
        for e in testentries:
            if not os.path.exists(os.path.join(directory,e)):
                return False
        return True

    if not suggestion is None:
        if not os.path.isdir(suggestion):
            print(suggestion + " is not a directory")
        elif not check_datadir_entries(suggestion):
            print(suggestion + " does not contain the expected files")
        else:
            return suggestion


    for d in searchpaths:
        d = os.path.realpath(d)
        if os.path.isdir(d) and check_datadir_entries(d):
            return d

    return None

def find_tagfiles(docdir, doclink=None, flattenlinks=False, _depth=0):
    """Find Doxygen-generated tag files in a directory

    The tag files must have the extention .tags, and must be in the listed
    directory, a subdirectory or a subdirectory named html of a subdirectory.

    docdir       -- the directory to search
    doclink      -- the path or URL to use when creating the documentation
                    links; if None, this will default to docdir
    flattenlinks -- if this is True, generated links will assume all the html
                    files are directly under doclink; if False (the default),
                    the html files are assumed to be at the same relative
                    location to doclink as the tag file is to docdir; ignored
                    if doclink is not set

    Returns a list of pairs of (tag_file,link_path)
    """

    if not os.path.isdir(docdir):
        return []

    if doclink is None:
        doclink = docdir
        flattenlinks = False

    def nestedlink(subdir):
        if flattenlinks:
            return doclink
        else:
            return smartjoin(doclink,subdir)

    tagfiles = []

    entries = os.listdir(docdir)
    for e in entries:
        path = os.path.join(docdir,e)
        if os.path.isfile(path) and e.endswith('.tags'):
            tagfiles.append((path,doclink))
        elif (_depth == 0 or (_depth == 1 and e == 'html')) and os.path.isdir(path):
            tagfiles += find_tagfiles(path, nestedlink(e),
                          flattenlinks=flattenlinks, _depth=_depth+1)

    return tagfiles

def search_for_tagfiles(suggestion=None, doclink=None, flattenlinks=False, searchpaths=[]):
    """Find Doxygen-generated tag files

    See the find_tagfiles documentation for how the search is carried out in
    each directory; this just allows a list of directories to be searched.

    At least one of docdir or searchpaths must be given for it to find anything.

    suggestion   -- the first place to look (will complain if there are no
                    documentation tag files there)
    doclink      -- the path or URL to use when creating the documentation
                    links; if None, this will default to docdir
    flattenlinks -- if this is True, generated links will assume all the html
                    files are directly under doclink; if False (the default),
                    the html files are assumed to be at the same relative
                    location to doclink as the tag file is to docdir; ignored
                    if doclink is not set
    searchpaths  -- other places to look for documentation tag files

    Returns a list of pairs of (tag_file,link_path)
    """

    if not suggestion is None:
        if not os.path.isdir(suggestion):
            print(suggestion + " is not a directory")
        else:
            tagfiles = find_tagfiles(suggestion, doclink, flattenlinks)
            if len(tagfiles) == 0:
                print(suggestion + " does not contain any tag files")
            else:
                return tagfiles

    for d in searchpaths:
        tagfiles = find_tagfiles(d, doclink, flattenlinks)
        if len(tagfiles) > 0:
            print("Documentation tag files found at " + d)
            return tagfiles

    return []

def copy_dir_contents(directory, dest):
    """Copy the contents of a directory

    directory -- the directory to copy the contents of
    dest      -- the directory to copy them into
    """
    ignored = ['CMakeLists.txt']
    ignore = shutil.ignore_patterns(*ignored)
    print("Copying contents of " + directory)
    for fn in os.listdir(directory):
        f = os.path.join(directory,fn)
        if os.path.isfile(f):
            docopy = True
            for i in ignored:
                if fnmatch(fn,i):
                    docopy = False
                    break
            if docopy:
                shutil.copy(f,dest)
        elif os.path.isdir(f):
            shutil.copytree(f,os.path.join(dest,fn),ignore=ignore)

def find_doxdatadir_or_exit(suggestion):
    """Finds the common documentation data directory

    Exits if not found.
    """
    # FIXME: use setuptools and pkg_resources?
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    doxdatadir = find_datadir(
            searchpaths=[os.path.join(scriptdir,'data')],
            testentries=['doxygen.css','header.html','footer.html','htmlresource'],
            suggestion=suggestion)
    if doxdatadir is None:
        print("Could not find a valid doxdatadir")
        sys.exit(1)
    else:
        print("Found doxdatadir at " + doxdatadir)
    return doxdatadir

def parse_fancyname(readme_file, default=None):
    """Parse the header text out of a Markdown file

    Extracts the first line of a file, stripping any Markdown formatting
    (actually, it just strips a starting # and any {#ref} at the end.

    readme_file -- the Markdown file to extract the text from
    default     -- a default value to use if the file does not exist

    Returns the header text found on the first line of readme_file if the file
    exists, of the value of default otherwise.
    """
    if os.path.isfile(readme_file):
        with codecs.open(readme_file, 'r', 'utf-8') as f:
            topline = f.readline(100)
        fancyname = re.sub(r'\s*{#.*}\s*$', '', topline.lstrip(' #')).rstrip()
        if len(fancyname) == 0:
            return default
        else:
            return fancyname
    else:
        print("The module does not provide a README.md file")
        return default

def menu_items(htmldir):
    """Menu items for standard Doxygen files

    Looks for a set of standard Doxygen files (like namespaces.html) and
    provides menu text for those it finds in htmldir.

    htmldir -- the directory the HTML files are contained in

    Returns a list of maps with 'text' and 'href' keys
    """
    entries = [
            {'text': 'Main Page', 'href': 'index.html'},
            {'text': 'Namespace List', 'href': 'namespaces.html'},
            {'text': 'Namespace Members', 'href': 'namespacemembers.html'},
            {'text': 'Alphabetical List', 'href': 'classes.html'},
            {'text': 'Class List', 'href': 'annotated.html'},
            {'text': 'Class Hierarchy', 'href': 'hierarchy.html'},
            {'text': 'Class Members', 'href': 'functions.html'},
            {'text': 'File List', 'href': 'files.html'},
            {'text': 'File Members', 'href': 'globals.html'},
            {'text': 'Modules', 'href': 'modules.html'},
            {'text': 'Directories', 'href': 'dirs.html'},
            {'text': 'Dependencies', 'href': DEPENDENCY_DIAGRAM_PAGE + '.html'},
            {'text': 'Related Pages', 'href': 'pages.html'},
            ]
    # NOTE In Python 3 filter() builtin returns an iterable, but not a list
    #      type, so explicit conversion is here!
    return list(filter(
            lambda e: os.path.isfile(os.path.join(htmldir, e['href'])),
            entries))

def postprocess(htmldir, mapping):
    """Substitute text in HTML files

    Performs text substitutions on each line in each .html file in a directory.

    htmldir -- the directory containing the .html files
    mapping -- a dict of mappings
    """
    import pystache
    renderer = pystache.Renderer(decode_errors='ignore',
                                 search_dirs=htmldir)

    for f in os.listdir(htmldir):
        if f.endswith('.html'):
            print("Postprocessing " + f)
            path = os.path.join(htmldir,f)
            newpath = path + '.new'
            with codecs.open(newpath, 'w', 'utf-8') as outf:
                outf.write(renderer.render_path(path, mapping))
            os.remove(path)
            os.rename(newpath,path)

def build_classmap(tagfile):
    """Parses a tagfile to get a map from classes to files

    tagfile -- the Doxygen-generated tagfile to parse

    Returns a list of maps (keys: classname and filename)
    """
    import xml.etree.ElementTree as ET
    tree = ET.parse(tagfile)
    tagfile_root = tree.getroot()
    mapping = []
    for compound in tagfile_root:
        kind = compound.get('kind')
        if kind == 'class' or kind == 'namespace':
            name_el = compound.find('name')
            filename_el = compound.find('filename')
            mapping.append({'classname': name_el.text,
                            'filename': filename_el.text})
    return mapping

def make_dir_list(topdir, paths):
    """Filters a list of directories based on whether they exist

    Looks for each path listed in paths (relative to topdir).  The absolute
    paths of the ones that exist are returned.

    topdir -- the directory to search for paths relative to
    paths  -- a list of paths to check for (these can be relative or absolute)

    Returns a list
    """
    lst = []
    for p in paths:
        if os.path.isdir(os.path.join(topdir,p)):
            lst.append(os.path.join(topdir,p))
    return lst

def write_mapping_to_php(mapping, outputfile, varname='map'):
    """Write a mapping out as PHP code

    Creates a PHP array as described by mapping.  For example, the mapping
      [("foo","bar"),("x","y")]
    would cause the file
      <?php $map = array('foo' => 'bar','x' => 'y') ?>
    to be written out.

    mapping    -- a list of pairs of strings
    outputfile -- the file to write to
    varname    -- override the PHP variable name (defaults to 'map')
    """
    print("Generating " + outputfile)
    with codecs.open(outputfile,'w','utf-8') as f:
        f.write('<?php $' + varname + ' = array(')
        first = True
        for entry in mapping:
            if first:
                first = False
            else:
                f.write(',')
            f.write("'" + entry['classname'] + "' => '" + entry['filename'] + "'")
        f.write(') ?>')

def generate_cmenu(mapping):
    """Generate a list of HTML option elements from a mapping

    mapping -- a list of (text,value) pairs

    Returns a string of HTML option tags
    """
    menu = ''
    for (name,filename) in mapping:
        menu += '<option value="' + filename + '">' + name + '</option>'
    return menu

def find_all_tagfiles(args):
    tagfiles = search_for_tagfiles(
            suggestion = args.qtdoc_dir,
            doclink = args.qtdoc_link,
            flattenlinks = args.qtdoc_flatten_links,
            searchpaths = ['/usr/share/doc/qt5', '/usr/share/doc/qt'])
    tagfiles += search_for_tagfiles(
            suggestion = args.kdedoc_dir,
            doclink = args.kdedoc_link,
            searchpaths = ['.', '/usr/share/doc/kf5', '/usr/share/doc/kde'])
    return tagfiles

def generate_apidocs(modulename, fancyname, srcdir, outputdir, doxdatadir,
        tagfiles=[], man_pages=False, qhp=False, searchengine=False,
        api_searchbox=False, doxygen='doxygen', qhelpgenerator='qhelpgenerator',
        title='KDE API Documentation', template_mapping=[],
        doxyfile_entries={},resourcedir=None, dependency_diagram=None):
    """Generate the API documentation for a single directory"""

    # Paths and basic project info
    html_subdir = 'html'

    # FIXME: preprocessing?
    # What about providing the build directory? We could get the version
    # as well, then.

    htmldir = os.path.join(outputdir,html_subdir)
    moduletagfile = os.path.join(htmldir, modulename + '.tags')

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
    if not os.path.exists(htmldir):
        os.makedirs(htmldir)

    if resourcedir is None:
        copy_dir_contents(os.path.join(doxdatadir,'htmlresource'),htmldir)
        resourcedir = '.'
    if os.path.isdir(os.path.join(srcdir,'docs/api/htmlresource')):
        copy_dir_contents(os.path.join(srcdir,'docs/api/htmlresource'),htmldir)

    shutil.copy(os.path.join(doxdatadir,'Doxyfile.global'), 'Doxyfile')

    input_list = [srcdir]
    image_path_list = []
    if dependency_diagram:
        name = os.path.join(doxdatadir, DEPENDENCY_DIAGRAM_PAGE + '.md')
        input_list.append(name)

        # We must copy the diagram because dependencies.md refers to it as
        # dependencies.png
        tmp_dependency_diagram = os.path.join(os.getcwd(), 'dependencies.png')
        shutil.copy(dependency_diagram, tmp_dependency_diagram)
        image_path_list.append(tmp_dependency_diagram)

    with codecs.open('Doxyfile','a','utf-8') as doxyfile:
        writer = DoxyfileWriter(doxyfile)
        writer.write_entry('PROJECT_NAME', fancyname)
        # FIXME: can we get the project version from CMake?

        # Input locations
        image_path_list.extend(
                make_dir_list(srcdir, ['docs/api','docs/api/pics','docs/pics']))
        writer.write_entries(
                INPUT=input_list,
                DOTFILE_DIRS=make_dir_list(srcdir, ['docs/api','docs/api/dot']),
                EXAMPLE_PATH=make_dir_list(srcdir, ['docs/api/examples','docs/examples']),
                IMAGE_PATH=image_path_list)

        # Other input settings
        writer.write_entry('TAGFILES', [f + '=' + loc for f, loc in tagfiles])

        # Output locations
        writer.write_entries(
                OUTPUT_DIRECTORY=outputdir,
                GENERATE_TAGFILE=moduletagfile,
                HTML_OUTPUT=html_subdir)

        # Other output settings
        writer.write_entries(
                HTML_HEADER=doxdatadir + '/header.html',
                HTML_FOOTER=doxdatadir + '/footer.html',
                HTML_STYLESHEET=doxdatadir + '/doxygen.css')

        # Always write these, even if QHP is disabled, in case Doxygen.local
        # overrides it
        writer.write_entries(
                QHP_VIRTUAL_FOLDER=modulename,
                QHG_LOCATION=qhelpgenerator)

        writer.write_entries(
                GENERATE_MAN=man_pages,
                GENERATE_QHP=qhp,
                SEARCHENGINE=searchengine)

        writer.write_entries(**doxyfile_entries)

        # Module-specific overrides
        localdoxyfile = os.path.join(srcdir, 'docs/api/Doxyfile.local')
        if os.path.isfile(localdoxyfile):
            with open(localdoxyfile) as f:
                for line in f:
                    doxyfile.write(line)

    subprocess.call([doxygen,'Doxyfile'])
    os.remove('Doxyfile')
    if dependency_diagram:
        os.remove(tmp_dependency_diagram)

    classmap = build_classmap(moduletagfile)
    write_mapping_to_php(classmap, os.path.join(outputdir, 'classmap.inc'))

    copyright = '1996-' + str(datetime.date.today().year) + ' The KDE developers'
    mapping = {
            'resources': resourcedir,
            'title': title,
            'copyright': copyright,
            'api_searchbox': api_searchbox,
            'doxygen_menu': {'entries': menu_items(htmldir)},
            'class_map': {'classes': classmap}
        }
    mapping.update(template_mapping)
    postprocess(htmldir, mapping)

