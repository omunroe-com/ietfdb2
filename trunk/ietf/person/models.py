# Copyright The IETF Trust 2007, All Rights Reserved

import datetime
from urlparse import urljoin

from django.db import models
from django.contrib.auth.models import User

from ietf.person.name import name_parts, initials

class PersonInfo(models.Model):
    time = models.DateTimeField(default=datetime.datetime.now)      # When this Person record entered the system
    name = models.CharField(max_length=255, db_index=True) # The normal unicode form of the name.  This must be
                                                        # set to the same value as the ascii-form if equal.
    ascii = models.CharField(max_length=255)            # The normal ascii-form of the name.
    ascii_short = models.CharField(max_length=32, null=True, blank=True)      # The short ascii-form of the name.  Also in alias table if non-null
    address = models.TextField(max_length=255, blank=True)
    affiliation = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return self.plain_name()
    def name_parts(self):
        return name_parts(self.name)
    def ascii_parts(self):
        return name_parts(self.ascii)
    def short(self):
        if self.ascii_short:
            return self.ascii_short
        else:
            prefix, first, middle, last, suffix = self.ascii_parts()
            return (first and first[0]+"." or "")+(middle or "")+" "+last+(suffix and " "+suffix or "")
    def plain_name(self):
        if self.ascii_short:
            return self.ascii_short
        prefix, first, middle, last, suffix = name_parts(self.name)
        return u" ".join([first, last])
    def initials(self):
        return initials(self.ascii or self.name)
    def last_name(self):
        return name_parts(self.name)[3]
    def role_email(self, role_name, group=None):
        """Lookup email for role for person, optionally on group which
        may be an object or the group acronym."""
        if group:
            if isinstance(group, str) or isinstance(group, unicode):
                group = Group.objects.get(acronym=group)
            e = Email.objects.filter(person=self, role__group=group, role__name=role_name)
        else:
            e = Email.objects.filter(person=self, role__group__state="active", role__name=role_name)
        if e:
            return e[0]
        # no cigar, try the complete set before giving up
        e = self.email_set.order_by("-active", "-time")
        if e:
            return e[0]
        return None
    def email_address(self):
        e = self.email_set.filter(active=True).order_by("-time")
        if e:
            return e[0].address
        else:
            return ""
    def formatted_email(self):
        e = self.email_set.order_by("-active", "-time")
        if e:
            return e[0].formatted_email()
        else:
            return ""
    def full_name_as_key(self):
        # this is mostly a remnant from the old views, needed in the menu
        return self.plain_name().lower().replace(" ", ".")
    class Meta:
        abstract = True

class PersonManager(models.Manager):
    def by_email(self, email):
        results = self.get_query_set().filter(user__email = email)
        if len(results)>0:
            return results[0]
        else:
            return None
    def by_username(self, username):
        results = self.get_query_set().filter(user__username = username)
        if len(results)>0:
            return results[0]
        else:
            return None

class Person(PersonInfo):
    objects = PersonManager()
    user = models.OneToOneField(User, blank=True, null=True)

    #this variable, if not None, may be used by url() to keep the sitefqdn.
    default_hostscheme = None

    @property
    def defurl(self):
        return urljoin(self.default_hostscheme,self.json_url())

    def json_url(self):
        return "/person/%s.json" % (self.id, )

    # return info about the person
    def json_dict(self, hostscheme):
        ct1 = dict()
        ct1['person_id'] = self.id
        ct1['href']      = urljoin(hostscheme, self.json_url())
        ct1['name']      = self.name
        ct1['ascii']     = self.ascii
        ct1['affiliation']= self.affiliation
        return ct1

class PersonHistory(PersonInfo):
    person = models.ForeignKey(Person, related_name="history_set")
    user = models.ForeignKey(User, blank=True, null=True)

class Alias(models.Model):
    """This is used for alternative forms of a name.  This is the
    primary lookup point for names, and should always contain the
    unicode form (and ascii form, if different) of a name which is
    recorded in the Person record.
    """
    person = models.ForeignKey(Person)
    name = models.CharField(max_length=255, db_index=True)
    def __unicode__(self):
        return self.name
    class Meta:
        verbose_name_plural = "Aliases"

class Email(models.Model):
    address = models.CharField(max_length=64, primary_key=True)
    person = models.ForeignKey(Person, null=True)
    time = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)      # Old email addresses are *not* purged, as history
                                        # information points to persons through these
    def __unicode__(self):
        return self.address

    def get_name(self):
        return self.person.plain_name() if self.person else self.address

    def formatted_email(self):
        if self.person and self.person.ascii:
            return u'"%s" <%s>' % (self.person.ascii, self.address)
        else:
            return self.address

    def invalid_address(self):
        # we have some legacy authors with unknown email addresses
        return self.address.startswith("unknown-email") and "@" not in self.address

    def email_address(self):
        """Get valid, current email address; in practise, for active,
        non-invalid addresses it is just the address field. In other
        cases, we default to person's email address."""
        if self.invalid_address() or not self.active:
            if self.person:
                return self.person.email_address()
            return
        return self.address

