# Copyright The IETF Trust 2007, All Rights Reserved

from django.db import models
from ietf.idtracker.models import Acronym,PersonOrOrgInfo
from django.core.exceptions import ObjectDoesNotExist

class LiaisonPurpose(models.Model):
    purpose_id = models.AutoField(primary_key=True)
    purpose_text = models.CharField(blank=True, maxlength=50)
    def __str__(self):
	return self.purpose_text
    class Meta:
        db_table = 'liaison_purpose'
    class Admin:
	pass

class FromBodies(models.Model):
    from_id = models.AutoField(primary_key=True)
    body_name = models.CharField(blank=True, maxlength=35)
    poc = models.ForeignKey(PersonOrOrgInfo, db_column='poc', raw_id_admin=True, null=True)
    is_liaison_manager = models.BooleanField()
    other_sdo = models.BooleanField()
    email_priority = models.IntegerField(null=True, blank=True)
    def __str__(self):
	return self.body_name
    class Meta:
        db_table = 'from_bodies'
    class Admin:
	pass

class LiaisonDetail(models.Model):
    detail_id = models.AutoField(primary_key=True)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
    submitted_date = models.DateField(null=True, blank=True)
    last_modified_date = models.DateField(null=True, blank=True)
    from_id = models.IntegerField(null=True, blank=True)
    to_body = models.CharField(blank=True, maxlength=255)
    title = models.CharField(blank=True, maxlength=255)
    response_contact = models.CharField(blank=True, maxlength=255)
    technical_contact = models.CharField(blank=True, maxlength=255)
    purpose_text = models.TextField(blank=True, db_column='purpose')
    body = models.TextField(blank=True)
    deadline_date = models.DateField(null=True, blank=True)
    cc1 = models.TextField(blank=True)
    # unclear why cc2 is a CharField, but it's always
    # either NULL or blank.
    cc2 = models.CharField(blank=True, maxlength=50)
    submitter_name = models.CharField(blank=True, maxlength=255)
    submitter_email = models.CharField(blank=True, maxlength=255)
    by_secretariat = models.IntegerField(null=True, blank=True)
    to_poc = models.CharField(blank=True, maxlength=255)
    to_email = models.CharField(blank=True, maxlength=255)
    purpose = models.ForeignKey(LiaisonPurpose)
    replyto = models.CharField(blank=True, maxlength=255)
    def __str__(self):
	return self.title or "<no title>"
    def from_body(self):
	"""The from_id field is a foreign key for either
	FromBodies or Acronyms, depending on whether it's
	the IETF or not.  There is no flag field saying
	which, so we just try it.  If the index values
	overlap, then this function will be ambiguous
	and will return the value from FromBodies.  Current
	acronym IDs start at 925 so the day of reckoning
	is not nigh."""
	try:
	    from_body = FromBodies.objects.get(pk=self.from_id)
	    return from_body.body_name
	except ObjectDoesNotExist:
	    pass
	try:
	    acronym = Acronym.objects.get(pk=self.from_id)
	    if acronym.area_set.count():
		type = "AREA"
	    else:
		type = "WG"
	    return "IETF %s %s" % ( acronym.acronym.upper(), type )
	except ObjectDoesNotExist:
	    pass
	return "<unknown body %d>" % self.from_id
    def from_email(self):
	"""If there is an entry in from_bodies, it has
	the desired email priority.  However, if it's from
	an IETF WG, there is no entry in from_bodies, so
	default to 1."""
	try:
	    from_body = FromBodies.objects.get(pk=self.from_id)
	    email_priority = from_body.email_priority
	except FromBodies.DoesNotExist:
	    email_priority = 1
	return self.person.emailaddress_set.all().get(priority=email_priority)
    class Meta:
        db_table = 'liaison_detail'
    class Admin:
	pass

class SDOs(models.Model):
    sdo_id = models.AutoField(primary_key=True)
    sdo_name = models.CharField(blank=True, maxlength=255)
    def __str__(self):
	return self.sdo_name
    def liaisonmanager(self):
	try:
	    return self.liaisonmanagers_set.all()[0]
	except:
	    return None
    class Meta:
        db_table = 'sdos'
    class Admin:
	pass

class LiaisonManagers(models.Model):
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
    email_priority = models.IntegerField(null=True, blank=True, core=True)
    sdo = models.ForeignKey(SDOs, edit_inline=models.TABULAR, num_in_admin=1)
    def email(self):
	try:
	    return self.person.emailaddress_set.get(priority=self.email_priority)
	except ObjectDoesNotExist:
	    return None
    class Meta:
        db_table = 'liaison_managers'

class LiaisonsInterim(models.Model):
    title = models.CharField(blank=True, maxlength=255)
    submitter_name = models.CharField(blank=True, maxlength=255)
    submitter_email = models.CharField(blank=True, maxlength=255)
    submitted_date = models.DateField(null=True, blank=True)
    from_id = models.IntegerField(null=True, blank=True)
    def __str__(self):
	return self.title
    class Meta:
        db_table = 'liaisons_interim'
    class Admin:
	pass

class Uploads(models.Model):
    file_id = models.AutoField(primary_key=True)
    file_title = models.CharField(blank=True, maxlength=255, core=True)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
    file_extension = models.CharField(blank=True, maxlength=10)
    detail = models.ForeignKey(LiaisonDetail, raw_id_admin=True, edit_inline=models.TABULAR, num_in_admin=1)
    def __str__(self):
	return self.file_title
    class Meta:
        db_table = 'uploads'

# empty table
#class SdoChairs(models.Model):
#    sdo = models.ForeignKey(SDOs)
#    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
#    email_priority = models.IntegerField(null=True, blank=True)
#    class Meta:
#        db_table = 'sdo_chairs'
#    class Admin:
#	pass
