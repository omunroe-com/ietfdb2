# Copyright The IETF Trust 2007, All Rights Reserved

# Portion Copyright (C) 2009 Nokia Corporation and/or its subsidiary(-ies).
# All rights reserved. Contact: Pasi Eronen <pasi.eronen@nokia.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
#  * Neither the name of the Nokia Corporation and/or its
#    subsidiary(-ies) nor the names of its contributors may be used
#    to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import socket, re, os

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.test.simple import run_tests as django_run_tests
from django.core.management import call_command

import debug

import ietf.utils.mail

loaded_templates = set()
visited_urls = set()
test_database_name = None
old_destroy = None
old_create = None

def safe_create_1(self, verbosity, *args, **kwargs):
    global test_database_name, old_create
    print "     Creating test database..."
    if settings.DATABASES["default"]["ENGINE"] == 'django.db.backends.mysql':
        settings.DATABASES["default"]["OPTIONS"] = settings.DATABASE_TEST_OPTIONS
        print "     Using OPTIONS: %s" % settings.DATABASES["default"]["OPTIONS"]
    test_database_name = old_create(self, 0, *args, **kwargs)
    if settings.GLOBAL_TEST_FIXTURES:
        print "     Loading global test fixtures: %s" % ", ".join(settings.GLOBAL_TEST_FIXTURES) 
        call_command('loaddata', *settings.GLOBAL_TEST_FIXTURES, verbosity=0, commit=False, database="default")
    return test_database_name

def safe_destroy_0_1(*args, **kwargs):
    global test_database_name, old_destroy
    print "     Checking that it's safe to destroy test database..."
    if settings.DATABASES["default"]["NAME"] != test_database_name:
        print '     NOT SAFE; Changing settings.DATABASES["default"]["NAME"] from %s to %s' % (settings.DATABASES["default"]["NAME"], test_database_name)
        settings.DATABASES["default"]["NAME"] = test_database_name
    return old_destroy(*args, **kwargs)

def template_coverage_loader(template_name, dirs):
    loaded_templates.add(str(template_name))
    raise TemplateDoesNotExist

template_coverage_loader.is_usable = True

class RecordUrlsMiddleware(object):
    def process_request(self, request):
        visited_urls.add(request.path)

def get_patterns(module):
    all = []
    try:
        patterns = module.urlpatterns
    except AttributeError:
        patterns = []
    for item in patterns:
        try:
            subpatterns = get_patterns(item.urlconf_module)
        except:
            subpatterns = [""]
        for sub in subpatterns:
            if not sub:
                all.append(item.regex.pattern)
            elif sub.startswith("^"):
                all.append(item.regex.pattern + sub[1:])
            else:
                all.append(item.regex.pattern + ".*" + sub)
    return all

def check_url_coverage():
    patterns = get_patterns(ietf.urls)

    IGNORED_PATTERNS = ("admin",)

    patterns = [(p, re.compile(p)) for p in patterns if p[1:].split("/")[0] not in IGNORED_PATTERNS]

    covered = set()
    for url in visited_urls:
        for pattern, compiled in patterns:
            if pattern not in covered and compiled.match(url[1:]): # strip leading /
                covered.add(pattern)
                break

    missing = list(set(p for p, compiled in patterns) - covered)

    if missing:
        print "The following URL patterns were not tested"
        for pattern in sorted(missing):
            print "     Not tested", pattern

def get_templates():
    templates = set()
    # Should we teach this to use TEMPLATE_DIRS?
    templatepath = os.path.join(settings.BASE_DIR, "templates")
    for root, dirs, files in os.walk(templatepath):
        if ".svn" in dirs:
            dirs.remove(".svn")
        relative_path = root[len(templatepath)+1:]
        for file in files:
            if file.endswith("~") or file.startswith("#"):
                continue
            if relative_path == "":
                templates.add(file)
            else:
                templates.add(os.path.join(relative_path, file))
    return templates

def check_template_coverage():
    all_templates = get_templates()

    not_loaded = list(all_templates - loaded_templates)
    if not_loaded:
        print "The following templates were never loaded during test"
        for t in sorted(not_loaded):
            print "     Not loaded", t

def run_tests_1(test_labels, *args, **kwargs):
    global old_destroy, old_create, test_database_name
    from django.db import connection
    old_create = connection.creation.__class__.create_test_db
    connection.creation.__class__.create_test_db = safe_create_1
    old_destroy = connection.creation.__class__.destroy_test_db
    connection.creation.__class__.destroy_test_db = safe_destroy_0_1

    check_coverage = not test_labels

    if check_coverage:
        settings.TEMPLATE_LOADERS = ('ietf.utils.test_runner.template_coverage_loader',) + settings.TEMPLATE_LOADERS
        settings.MIDDLEWARE_CLASSES = ('ietf.utils.test_runner.RecordUrlsMiddleware',) + settings.MIDDLEWARE_CLASSES

    if not test_labels:
        test_labels = [x.split(".")[-1] for x in settings.INSTALLED_APPS if x.startswith("ietf")]

    if settings.SITE_ID != 1:
        print "     Changing SITE_ID to '1' during testing."
        settings.SITE_ID = 1

    if settings.TEMPLATE_STRING_IF_INVALID != '':
        print "     Changing TEMPLATE_STRING_IF_INVALID to '' during testing."
        settings.TEMPLATE_STRING_IF_INVALID = ''

    assert(not settings.IDTRACKER_BASE_URL.endswith('/'))

    results = django_run_tests(test_labels, *args, **kwargs)

    if check_coverage:
        check_url_coverage()
        check_template_coverage()

    return results

def run_tests(*args, **kwargs):
    # Tests that involve switching back and forth between the real
    # database and the test database are way too dangerous to run
    # against the production database
    if socket.gethostname().split('.')[0] in ['core3', 'ietfa', 'ietfb', 'ietfc', ]:
        raise EnvironmentError("Refusing to run tests on production server")
    ietf.utils.mail.test_mode = True
    failures = run_tests_1(*args, **kwargs)
    # Record the test result in a file, in order to be able to check the
    # results and avoid re-running tests if we've alread run them with OK
    # result after the latest code changes:
    import os, time, ietf.settings as config
    topdir = os.path.dirname(os.path.dirname(config.__file__))
    tfile = open(os.path.join(topdir,"testresult"), "a")
    timestr = time.strftime("%Y-%m-%d %H:%M:%S")
    if failures:
        tfile.write("%s FAILED (failures=%s)\n" % (timestr, failures))
    else:
        if list(*args):
            tfile.write("%s SUCCESS (tests=%s)\n" % (timestr, repr(list(*args))))
        else:
            tfile.write("%s OK\n" % (timestr, ))
    tfile.close()
    return failures
