from django.db import models
from ietf.idtracker.models import Acronym, Areas, PersonOrOrgInfo
import random

class ImportedMailingList(models.Model):
    group_acronym = models.ForeignKey(Acronym, null=True)
    acronym = models.CharField(maxlength=255, db_column='list_acronym')
    name = models.CharField(blank=True, maxlength=255, db_column='list_name')
    domain = models.CharField(blank=True, maxlength=25, db_column='list_domain')
    def __str__(self):
	return self.name or self.group_acronym
    def choices(dname):
	objects = ImportedMailingList.objects.all().filter(domain__icontains=dname).exclude(acronym__iendswith='announce')
	if dname == "ietf.org":
	    objects = objects.exclude(acronym__istartswith='ietf').exclude(acronym__icontains='iesg')
	return [(list.acronym, list.acronym) for list in objects]
    choices = staticmethod(choices)
    class Meta:
        db_table = 'imported_mailing_list'
    class Admin:
	pass

class MailingList(models.Model):
    SUBSCRIPTION_CHOICES = (
	('1', 'Confirm'),
	('2', 'Approval'),
	('3', 'Confirm+Approval'),
    )
    MAILTYPE_CHOICES = (
	('1', 'Create new WG email list at ietf.org'),
	('2', 'Move existing WG email list to ietf.org'),
	('3', 'Move existing non-WG email list to selected domain'),
	('4', 'Create new non-WG email list at selected domain'),
	('5', 'Close existing WG email list at ietf.org'),
	('6', 'Close existing non-WG email list at selected domain'),
    )
    # I don't understand the reasoning behind 2 vs 3.
    # this is set in the javascript and not editable,
    # so I think there's a 1:1 mapping from mail_type -> mail_cat.
    # The existing database doesn't help much since many
    # mail_cat values are NULL.
    MAILCAT_CHOICES = (
	('1', 'WG Mailing List'),
	('2', 'Non-WG Mailing List'),
	('3', 'Close Non-WG Mailing List'),
    )
    mailing_list_id = models.CharField('Unique ID', primary_key=True, maxlength=25)
    request_date = models.DateField()
    mlist_name = models.CharField('Mailing list name', maxlength=250)
    short_desc = models.CharField(maxlength=250)
    long_desc = models.TextField(blank=True)
    requestor = models.CharField(maxlength=250)
    requestor_email = models.CharField(maxlength=250)
    # admins is a VARCHAR but can have multiple lines
    admins = models.TextField(blank=True, maxlength=250)
    archive_remote = models.TextField(blank=True)
    archive_private = models.BooleanField()
    initial = models.TextField('Initial members',blank=True)
    welcome_message = models.TextField(blank=True)
    subscription = models.IntegerField(choices=SUBSCRIPTION_CHOICES)
    post_who = models.BooleanField('Only members can post')
    post_admin = models.BooleanField('Administrator approval required for posts')
    add_comment = models.TextField(blank=True)
    mail_type = models.IntegerField(choices=MAILTYPE_CHOICES)
    mail_cat = models.IntegerField(choices=MAILCAT_CHOICES)
    auth_person = models.ForeignKey(PersonOrOrgInfo, db_column='auth_person_or_org_tag', raw_id_admin=True)
    welcome_new = models.TextField(blank=True)
    approved = models.BooleanField()
    approved_date = models.DateField(null=True, blank=True)
    reason_to_delete = models.TextField(blank=True)
    domain_name = models.CharField(blank=True, maxlength=10)
    def __str__(self):
	return self.mlist_name
    def save(self, *args, **kwargs):
	if self.mailing_list_id is None:
	    generate = True
	    while generate:
		self.mailing_list_id = ''.join([random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for i in range(35)])
		try:
		    MailingList.objects.get(pk=self.mailing_list_id)
		except MailingList.DoesNotExist:
		    generate = False
	super(MailingList, self).save(*args, **kwargs)
    class Meta:
        db_table = 'mailing_list'
    class Admin:
	pass

class NonWgMailingList(models.Model):
    id = models.CharField(primary_key=True, maxlength=35)
    s_name = models.CharField("Submitter's Name", blank=True, maxlength=255)
    s_email = models.EmailField("Submitter's Email Address", blank=True, maxlength=255)
    list_name = models.CharField("Mailing List Name", unique=True, maxlength=255)
    list_url = models.CharField("List URL", maxlength=255)
    admin = models.TextField("Administrator(s)' Email Address(es)", blank=True)
    purpose = models.TextField(blank=True)
    area = models.ForeignKey(Areas, db_column='area_acronym_id')
    subscribe_url = models.CharField("Subscribe URL", blank=True, maxlength=255)
    subscribe_other = models.TextField("Subscribe Other", blank=True)
    # Can be 0, 1, -1, or what looks like a person_or_org_tag, positive or neg.
    # The values less than 1 don't get displayed on the list of lists.
    status = models.IntegerField()
    ds_name = models.CharField(blank=True, maxlength=255)
    ds_email = models.EmailField(blank=True, maxlength=255)
    msg_to_ad = models.TextField(blank=True)
    def __str__(self):
	return self.list_name 
    def save(self, *args, **kwargs):
	if self.id is None:
	    generate = True
	    while generate:
		self.id = ''.join([random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for i in range(35)])
		try:
		    NonWgMailingList.objects.get(pk=self.id)
		except NonWgMailingList.DoesNotExist:
		    generate = False
	super(NonWgMailingList, self).save(*args, **kwargs)
    def choices():
	return [(list.id, list.list_name) for list in NonWgMailingList.objects.all().filter(status__gt=0)]
    choices = staticmethod(choices)
    class Meta:
        db_table = 'none_wg_mailing_list'
	ordering = ['list_name']
    class Admin:
	pass

