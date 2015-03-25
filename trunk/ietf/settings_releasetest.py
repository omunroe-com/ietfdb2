# Standard settings except we use SQLite, this is useful for speeding
# up tests that depend on the test database, try for instance:
#
#   ./manage.py test --settings=settings_sqlitetest doc.ChangeStateTestCase
#

from settings import *                  # pyflakes:ignore

# Workaround to avoid spending minutes stepping through the migrations in
# every test run.  The result of this is to use the 'syncdb' way of creating
# the test database instead of doing it through the migrations.  Taken from
# https://gist.github.com/NotSqrt/5f3c76cd15e40ef62d09

## To be removed after upgrade to Django 1.8 ##

class DisableMigrations(object):
 
    def __contains__(self, item):
        return True
 
    def __getitem__(self, item):
        # The string below is significant.  It has to include the value of
        # django.db.migrations.loader.MIGRATIONS_MODULE_NAME.  Used by django
        # 1.7 code in django.db.migrations.loader.MigrationLoader to
        # determine whether or not to run migrations for a given module
        from django.db.migrations.loader import MIGRATIONS_MODULE_NAME
        return "no " + MIGRATIONS_MODULE_NAME

MIGRATION_MODULES = DisableMigrations()

# Set the SKIP_* variables to True in order to disable tests which won't
# normally run on developer's laptop, in order to not create
# release-coverage.json data which sets people up for test suite failures on a
# clean checkout

SKIP_DOT_TO_PDF = True
SKIP_SELENIUM = True

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
        },
    }
