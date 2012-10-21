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

import socket

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.test.simple import run_tests as django_run_tests

import debug

import ietf.utils.mail

loaded_templates = set()
test_database_name = None
old_destroy = None
old_create = None

def safe_create_1(self, verbosity, *args, **kwargs):
    global test_database_name, old_create
    print "     Creating test database..."
    x = old_create(self, 0, *args, **kwargs)
    print "     Saving test database name "+settings.DATABASES["default"]["NAME"]+"..."
    test_database_name = settings.DATABASES["default"]["NAME"]
    return x

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

def run_tests_1(test_labels, *args, **kwargs):
    global old_destroy, old_create, test_database_name
    from django.db import connection
    old_create = connection.creation.__class__.create_test_db
    connection.creation.__class__.create_test_db = safe_create_1
    old_destroy = connection.creation.__class__.destroy_test_db
    connection.creation.__class__.destroy_test_db = safe_destroy_0_1
    if not test_labels:
        settings.TEMPLATE_LOADERS = ('ietf.utils.test_runner.template_coverage_loader',) + settings.TEMPLATE_LOADERS
        test_labels = [x.split(".")[-1] for x in settings.INSTALLED_APPS if x.startswith("ietf")] + ['redirects.TemplateCoverageTestCase',]
    if settings.SITE_ID != 1:
        print "     Changing SITE_ID to '1' during testing."
        settings.SITE_ID = 1
    assert(not settings.IDTRACKER_BASE_URL.endswith('/'))
    kwargs["verbosity"] = 0
    django_run_tests(test_labels, *args, **kwargs)

def run_tests(*args, **kwargs):
    # Tests that involve switching back and forth between the real
    # database and the test database are way too dangerous to run
    # against the production database
    if socket.gethostname().split('.')[0] in ['core3', 'ietfa', 'ietfb', 'ietfc', ]:
        raise EnvironmentError("Refusing to run tests on production server")
    ietf.utils.mail.test_mode = True
    run_tests_1(*args, **kwargs)
    
