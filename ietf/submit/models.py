import re, datetime                     # 

from django.conf import settings
from django.db import models
from django.utils.hashcompat import md5_constructor

from ietf.idtracker.models import InternetDraft, IETFWG
from ietf.person.models import Person


class IdSubmissionStatus(models.Model):
    status_id = models.IntegerField(primary_key=True)
    status_value = models.CharField(blank=True, max_length=255)

    def __unicode__(self):
        return self.status_value

class IdSubmissionDetail(models.Model):
    submission_id = models.AutoField(primary_key=True)
    temp_id_document_tag = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(IdSubmissionStatus, db_column='status_id', null=True, blank=True)
    last_updated_date = models.DateField(null=True, blank=True)
    last_updated_time = models.CharField(null=True, blank=True, max_length=25)
    id_document_name = models.CharField(null=True, blank=True, max_length=255)
    group_acronym = models.ForeignKey(IETFWG, null=True, blank=True)
    filename = models.CharField(null=True, blank=True, max_length=255, db_index=True)
    creation_date = models.DateField(null=True, blank=True)
    submission_date = models.DateField(null=True, blank=True)
    remote_ip = models.CharField(null=True, blank=True, max_length=100)
    revision = models.CharField(null=True, blank=True, max_length=3)
    submitter_tag = models.IntegerField(null=True, blank=True)
    auth_key = models.CharField(null=True, blank=True, max_length=255)
    idnits_message = models.TextField(null=True, blank=True)
    file_type = models.CharField(null=True, blank=True, max_length=50)
    comment_to_sec = models.TextField(null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    txt_page_count = models.IntegerField(null=True, blank=True)
    error_message = models.CharField(null=True, blank=True, max_length=255)
    warning_message = models.TextField(null=True, blank=True)
    wg_submission = models.IntegerField(null=True, blank=True)
    filesize = models.IntegerField(null=True, blank=True)
    man_posted_date = models.DateField(null=True, blank=True)
    man_posted_by = models.CharField(null=True, blank=True, max_length=255)
    first_two_pages = models.TextField(null=True, blank=True)
    sub_email_priority = models.IntegerField(null=True, blank=True)
    invalid_version = models.IntegerField(null=True, blank=True)
    idnits_failed = models.IntegerField(null=True, blank=True)
    submission_hash = models.CharField(null=True, blank=True, max_length=255)

    def __unicode__(self):
        return u"%s-%s" % (self.filename, self.revision)

    def create_hash(self):
        self.submission_hash = md5_constructor(settings.SECRET_KEY + self.filename).hexdigest()

    def get_hash(self):
        if not self.submission_hash:
            self.create_hash()
            self.save()
        return self.submission_hash
    def draft_link(self):
        if self.status_id == -1:
            return '<a href="http://www.ietf.org/id/%s-%s.txt">%s</a>' % (self.filename, self.revision, self.filename)
        else:
            return self.filename
    draft_link.allow_tags = True
    def status_link(self):
        return '<a href="http://datatracker.ietf.org/submit/status/%s/%s/">%s</a>' % (self.submission_id, self.submission_hash, self.status)
    status_link.allow_tags = True

    def confirmation_email_list(self):
        try:
            draft = InternetDraft.objects.get(filename=self.filename)
            email_list = list(set(u'%s <%s>' % (i.person.ascii, i.email()) for i in draft.authors))
        except InternetDraft.DoesNotExist:
            email_list = list(set(u'%s <%s>' % i.email() for i in self.tempidauthors_set.all()))
        return email_list

def create_submission_hash(sender, instance, **kwargs):
    instance.create_hash()

models.signals.pre_save.connect(create_submission_hash, sender=IdSubmissionDetail)

class Preapproval(models.Model):
    """Pre-approved draft submission name."""
    name = models.CharField(max_length=255, db_index=True)
    by = models.ForeignKey(Person)
    time = models.DateTimeField(default=datetime.datetime.now)

    def __unicode__(self):
        return self.name

class TempIdAuthors(models.Model):
    id_document_tag = models.IntegerField()
    first_name = models.CharField(blank=True, max_length=255) # with new schema, this contains the full name while the other name fields are empty to avoid loss of information
    last_name = models.CharField(blank=True, max_length=255)
    email_address = models.CharField(blank=True, max_length=255)
    last_modified_date = models.DateField(null=True, blank=True)
    last_modified_time = models.CharField(blank=True, max_length=100)
    author_order = models.IntegerField(null=True, blank=True)
    submission = models.ForeignKey(IdSubmissionDetail)
    middle_initial = models.CharField(blank=True, max_length=255, null=True)
    name_suffix = models.CharField(blank=True, max_length=255, null=True)

    class Meta:
        if not settings.USE_DB_REDESIGN_PROXY_CLASSES:
            db_table = 'temp_id_authors'

    def email(self):
        return (self.get_full_name(), self.email_address)

    def get_full_name(self):
        parts = (self.first_name or '', self.middle_initial or '', self.last_name or '', self.name_suffix or '')
        return u" ".join(x.strip() for x in parts if x.strip())

    def __unicode__(self):
        return u"%s <%s>" % self.email()
