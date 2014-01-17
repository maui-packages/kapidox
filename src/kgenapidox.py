#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility (NB: we require at least 2.7)
from __future__ import division, absolute_import, print_function, unicode_literals

import argparse
import os

from kapidox import *

def main():
    parser = argparse.ArgumentParser(description='Generate API documentation in the KDE style')
    parser.add_argument('moduledir',
            help='Location of the module to build API documentation for; it ' +
                 'should contain a README.md file and a src/ subdirectory.')
    parser.add_argument('--title', default='KDE API Documentation',
            help='String to use for page titles.')
    parser.add_argument('--man-pages', action='store_true',
            help='Generate man page documentation.')
    parser.add_argument('--qhp', action='store_true',
            help='Generate Qt Compressed Help documentation.')
    parser.add_argument('--searchengine', action='store_true',
            help="Enable Doxygen's search engine feature.")
    parser.add_argument('--api-searchbox', action='store_true',
            help="Enable the API searchbox (only useful for api.kde.org).")
    parser.add_argument('--no-modulename', action='store_false',
            dest='use_modulename',
            help='Call the apidocs folder "apidocs" instead of ' +
                 '"<modulename>-apidocs".')
    parser.add_argument('--doxdatadir',
            help='Location of the HTML header files and support graphics.')
    parser.add_argument('--kdedoc-dir',
            help='Location of (local) KDE documentation; this is searched ' +
                 'for tag files to create links to KDE classes.')
    parser.add_argument('--kdedoc-link',
            help='Override KDE documentation location for the links in the ' +
                 'html files.  May be a path or URL.')
    parser.add_argument('--qtdoc-dir',
            help='Location of (local) Qt documentation; this is searched ' +
                 'for tag files to create links to Qt classes.')
    parser.add_argument('--dependency-diagram-dir',
            help='Location of framework diagram dirs; they will be included ' +
                 'the framework landing page if provided.')
    parser.add_argument('--qtdoc-link',
            help='Override Qt documentation location for the links in the ' +
                 'html files.  May be a path or URL.')
    parser.add_argument('--qtdoc-flatten-links', action='store_true',
            help='Whether to assume all Qt documentation html files ' +
                 'are immediately under QTDOC_LINK (useful if you set ' +
                 'QTDOC_LINK to the online Qt documentation).  Ignored ' +
                 'if QTDOC_LINK is not set.')
    parser.add_argument('--doxygen', default='doxygen',
            help='(Path to) the doxygen executable.')
    parser.add_argument('--qhelpgenerator', default='qhelpgenerator',
            help='(Path to) the qhelpgenerator executable.')
    args = parser.parse_args()

    doxdatadir = find_doxdatadir_or_exit(args.doxdatadir)
    tagfiles = find_all_tagfiles(args)

    if not os.path.isdir(args.moduledir):
        print(args.moduledir + " is not a directory")
        exit(2)

    modulename = os.path.basename(os.path.abspath(os.path.realpath(args.moduledir)))
    if args.use_modulename:
        outputdir = modulename + '-apidocs'
    else:
        outputdir = 'apidocs'

    if args.dependency_diagram_dir:
        if not os.path.isdir(args.dependency_diagram_dir):
            print(args.dependency_diagram_dir + " is not a directory")
            exit(2)

        dependency_diagram = os.path.join(args.dependency_diagram_dir, modulename + '.png')
        if not os.path.isfile(dependency_diagram):
            print('No file named {}.png in {}'.format(modulename, args.dependency_diagram_dir))
            exit(2)
    else:
        dependency_diagram = None

    readme_file = os.path.join(args.moduledir, 'README.md')

    generate_apidocs(
            modulename = modulename,
            srcdir = args.moduledir,
            outputdir = outputdir,
            doxdatadir = doxdatadir,
            dependency_diagram = dependency_diagram,
            tagfiles = tagfiles,
            man_pages = args.man_pages,
            qhp = args.qhp,
            searchengine = args.searchengine,
            api_searchbox = args.api_searchbox,
            doxygen = args.doxygen,
            qhelpgenerator = args.qhelpgenerator,
            title = args.title,
            fancyname = parse_fancyname(readme_file, default=modulename)
            )

if __name__ == "__main__":
    main()

