from django.db import models
from ietf.utils import FKAsOneToOne

class Acronym(models.Model):
    acronym_id = models.AutoField(primary_key=True)
    acronym = models.CharField(maxlength=12)
    name = models.CharField(maxlength=100)
    name_key = models.CharField(maxlength=50, editable=False)
    def save(self):
        self.name_key = self.name.upper()
	super(Acronym, self).save()
    def __str__(self):
        return self.acronym
    class Meta:
        db_table = "acronym"
    class Admin:
        list_display = ('acronym', 'name')
        pass

class AreaStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status = models.CharField(maxlength=25, db_column='status_value')
    def __str__(self):
	return self.status
    class Meta:
        db_table = 'area_status'
    class Admin:
        pass

# I think equiv_group_flag is historical.
class IDState(models.Model):
    document_state_id = models.AutoField(primary_key=True)
    state = models.CharField(maxlength=50, db_column='document_state_val')
    equiv_group_flag = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, db_column='document_desc')
    def __str__(self):
        return self.state
    def choices():
	return [(state.document_state_id, state.state) for state in IDState.objects.all()]
    choices = staticmethod(choices)
    class Meta:
        db_table = 'ref_doc_states_new'
    class Admin:
	pass

class IDNextState(models.Model):
    cur_state = models.ForeignKey(IDState, related_name='nextstate')
    next_state = models.ForeignKey(IDState, related_name='prevstate', core=True)
    condition = models.CharField(blank=True, maxlength=255)
    def __str__(self):
	return "%s -> %s" % (self.cur_state.state, self.next_state.state )
    class Meta:
        db_table = 'ref_next_states_new'
    class Admin:
	pass

class IDSubState(models.Model):
    sub_state_id = models.AutoField(primary_key=True)
    sub_state = models.CharField(maxlength=55, db_column='sub_state_val')
    description = models.TextField(blank=True, db_column='sub_state_desc')
    def __str__(self):
        return self.sub_state
    class Meta:
        db_table = 'sub_state'
    class Admin:
	pass

class Area(models.Model):
    ACTIVE=1
    area_acronym = models.ForeignKey(Acronym, primary_key=True, unique=True)
    start_date = models.DateField(auto_now_add=True)
    concluded_date = models.DateField(null=True, blank=True)
    status = models.ForeignKey(AreaStatus)
    comments = models.TextField(blank=True)
    last_modified_date = models.DateField(auto_now=True)
    extra_email_addresses = models.TextField(blank=True)
    def __str__(self):
	return self.area_acronym.acronym
    def active_area_choices():
	return [(area.area_acronym_id, area.area_acronym.acronym) for area in Area.objects.filter(status=1).select_related().order_by('acronym.acronym')]
    active_area_choices = staticmethod(active_area_choices)
    class Meta:
        db_table = 'areas'
	verbose_name="area"
    class Admin:
        list_display = ('area_acronym', 'status')
	pass

class IDStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status = models.CharField(maxlength=25, db_column='status_value')
    def __str__(self):
        return self.status
    class Meta:
        db_table = "id_status"
	verbose_name="I-D Status"
	verbose_name_plural="I-D Statuses"
    class Admin:
        pass

class IDIntendedStatus(models.Model):
    intended_status_id = models.AutoField(primary_key=True)
    intended_status = models.CharField(maxlength=25, db_column='status_value')
    def __str__(self):
        return self.intended_status
    class Meta:
        db_table = "id_intended_status"
	verbose_name="I-D Intended Publication Status"
	verbose_name_plural="I-D Intended Publication Statuses"
    class Admin:
        pass

class InternetDraft(models.Model):
    id_document_tag = models.AutoField(primary_key=True)
    title = models.CharField(maxlength=255, db_column='id_document_name')
    id_document_key = models.CharField(maxlength=255, editable=False)
    group = models.ForeignKey(Acronym, db_column='group_acronym_id')
    filename = models.CharField(maxlength=255, unique=True)
    revision = models.CharField(maxlength=2)
    revision_date = models.DateField()
    file_type = models.CharField(maxlength=20)
    txt_page_count = models.IntegerField()
    local_path = models.CharField(maxlength=255, blank=True)
    start_date = models.DateField()
    expiration_date = models.DateField()
    abstract = models.TextField()
    dunn_sent_date = models.DateField()
    extension_date = models.DateField(null=True, blank=True)
    status = models.ForeignKey(IDStatus)
    intended_status = models.ForeignKey(IDIntendedStatus)
    lc_sent_date = models.DateField(null=True, blank=True)
    lc_changes = models.CharField(maxlength=3)
    lc_expiration_date = models.DateField(null=True, blank=True)
    b_sent_date = models.DateField(null=True, blank=True)
    b_discussion_date = models.DateField(null=True, blank=True)
    b_approve_date = models.DateField(null=True, blank=True)
    wgreturn_date = models.DateField(null=True, blank=True)
    rfc_number = models.IntegerField(null=True, blank=True)
    comments = models.TextField(blank=True)
    last_modified_date = models.DateField()
    replaced_by = models.ForeignKey('self', db_column='replaced_by', raw_id_admin=True, blank=True, null=True, related_name='replaces_set')
    replaces = FKAsOneToOne('replaces', reverse=True)
    review_by_rfc_editor = models.BooleanField()
    expired_tombstone = models.BooleanField()
    idinternal = FKAsOneToOne('idinternal', reverse=True, query=models.Q(rfc_flag = 0))
    def save(self):
        self.id_document_key = self.title.upper()
        super(InternetDraft, self).save()
    def displayname(self):
	return "%s-%s.txt" % ( self.filename, self.revision )
    def doclink(self):
	return "http://www.ietf.org/internet-drafts/%s" % ( self.displayname() )
    def group_acronym(self):
	return self.group.acronym
    def __str__(self):
        return self.filename
    def idstate(self):
	idinternal = self.idinternal
	if idinternal:
	    return idinternal.docstate()
	else:
	    return "I-D Exists"
    def revision_display(self):
	r = int(self.revision)
	if self.status.status != 'Active' and not self.expired_tombstone:
	   r = max(r - 1, 0)
	return "%02d" % r

    class Meta:
        db_table = "internet_drafts"
    class Admin:
        search_fields = ['filename']
        list_display = ('filename', 'revision', 'status')
	list_filter = ['status']
        pass
        #date_hierarchy = 'revision_date'
        #list_filter = ['revision_date']

class PersonOrOrgInfo(models.Model):
    person_or_org_tag = models.AutoField(primary_key=True)
    record_type = models.CharField(blank=True, maxlength=8)
    name_prefix = models.CharField(blank=True, maxlength=10)
    first_name = models.CharField(blank=True, maxlength=20)
    first_name_key = models.CharField(blank=True, maxlength=20, editable=False)
    middle_initial = models.CharField(blank=True, maxlength=4)
    middle_initial_key = models.CharField(blank=True, maxlength=4, editable=False)
    last_name = models.CharField(blank=True, maxlength=50)
    last_name_key = models.CharField(blank=True, maxlength=50, editable=False)
    name_suffix = models.CharField(blank=True, maxlength=10)
    date_modified = models.DateField(null=True, blank=True, auto_now=True)
    modified_by = models.CharField(blank=True, maxlength=8)
    date_created = models.DateField(auto_now_add=True)
    created_by = models.CharField(blank=True, maxlength=8)
    address_type = models.CharField(blank=True, maxlength=4)
    def save(self):
        self.first_name_key = self.first_name.upper()
        self.middle_initial_key = self.middle_initial.upper()
        self.last_name_key = self.last_name.upper()
        super(PersonOrOrgInfo, self).save()
    def __str__(self):
	if self.first_name == '' and self.last_name == '':
	    return self.affiliation()
        return "%s %s" % ( self.first_name or "<nofirst>", self.last_name or "<nolast>")
    def email(self, priority=1, type='INET'):
	name = str(self)
	try:
	    email = self.emailaddress_set.get(priority=priority, type=type).address
	except EmailAddress.DoesNotExist:
	    email = ''
	return (name, email)
    # Added by Sunny Lee to display person's affiliation - 5/26/2007
    def affiliation(self, priority=1):
        try:
            postal = self.postaladdress_set.get(address_priority=priority)
        except PostalAddress.DoesNotExist:
            return "PersonOrOrgInfo with no postal address!"
        except AssertionError:
            return "PersonOrOrgInfo with multiple priority-%d addresses!" % priority
        return "%s" % ( postal.affiliated_company or postal.department or "???" )
    class Meta:
        db_table = 'person_or_org_info'
	ordering = ['last_name']
	verbose_name="Rolodex Entry"
	verbose_name_plural="Rolodex"
    class Admin:
        search_fields = ['first_name','last_name']
        pass

# could use a mapping for user_level
class IESGLogin(models.Model):
    USER_LEVEL_CHOICES = (
	('0', 'Secretariat'),
	('1', 'IESG'),
	('2', 'ex-IESG'),
	('3', 'Level 3'),
	('4', 'Comment Only(?)'),
    )
    id = models.AutoField(primary_key=True)
    login_name = models.CharField(blank=True, maxlength=255)
    password = models.CharField(maxlength=25)
    user_level = models.IntegerField(choices=USER_LEVEL_CHOICES)
    first_name = models.CharField(blank=True, maxlength=25)
    last_name = models.CharField(blank=True, maxlength=25)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, unique=True)
    pgp_id = models.CharField(blank=True, maxlength=20)
    default_search = models.IntegerField(null=True)
    def __str__(self):
        #return "%s, %s" % ( self.last_name, self.first_name)
        return "%s %s" % ( self.first_name, self.last_name)
    class Meta:
        db_table = 'iesg_login'
    class Admin:
	list_display = ('login_name', 'first_name', 'last_name', 'user_level')
        ordering = ['user_level','last_name']
	pass

class AreaDirector(models.Model):
    area = models.ForeignKey(Area, db_column='area_acronym_id', edit_inline=models.STACKED, num_in_admin=2, null=True)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, core=True)
    def __str__(self):
        return "%s (%s)" % ( self.person, self.role() )
    def role(self):
	try:
	    return "%s AD" % self.area
	except Area.DoesNotExist:
	    return "?%d? AD" % self.area_id
    class Meta:
        db_table = 'area_directors'
    class Admin:
	pass

###
# RFC tables

class RfcIntendedStatus(models.Model):
    intended_status_id = models.AutoField(primary_key=True)
    status = models.CharField(maxlength=25, db_column='status_value')
    def __str__(self):
        return self.status
    class Meta:
        db_table = 'rfc_intend_status'
	verbose_name = 'RFC Intended Status Field'
    class Admin:
	pass

class RfcStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status = models.CharField(maxlength=25, db_column='status_value')
    def __str__(self):
        return self.status
    class Meta:
        db_table = 'rfc_status'
	verbose_name = 'RFC Status'
	verbose_name_plural = 'RFC Statuses'
    class Admin:
	pass

class Rfc(models.Model):
    rfc_number = models.IntegerField(primary_key=True)
    title = models.CharField(maxlength=200, db_column='rfc_name')
    rfc_name_key = models.CharField(maxlength=200, editable=False)
    group_acronym = models.CharField(blank=True, maxlength=8)
    area_acronym = models.CharField(blank=True, maxlength=8)
    status = models.ForeignKey(RfcStatus, db_column="status_id")
    intended_status = models.ForeignKey(RfcIntendedStatus, db_column="intended_status_id")
    fyi_number = models.CharField(blank=True, maxlength=20)
    std_number = models.CharField(blank=True, maxlength=20)
    txt_page_count = models.IntegerField(null=True, blank=True)
    online_version = models.CharField(blank=True, maxlength=3)
    rfc_published_date = models.DateField(null=True, blank=True)
    proposed_date = models.DateField(null=True, blank=True)
    draft_date = models.DateField(null=True, blank=True)
    standard_date = models.DateField(null=True, blank=True)
    historic_date = models.DateField(null=True, blank=True)
    lc_sent_date = models.DateField(null=True, blank=True)
    lc_expiration_date = models.DateField(null=True, blank=True)
    b_sent_date = models.DateField(null=True, blank=True)
    b_approve_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)
    last_modified_date = models.DateField()
    def __str__(self):
	return "RFC%04d" % ( self.rfc_number )        
    def save(self):
	self.rfc_name_key = self.title.upper()
	super(Rfc, self).save()
    def displayname(self):
        return "%s.txt" % ( self.filename() )
    def filename(self):
	return "rfc%d" % ( self.rfc_number )
    def revision(self):
	return "RFC"
    def doclink(self):
	return "http://www.ietf.org/rfc/%s" % ( self.displayname() )
    class Meta:
        db_table = 'rfcs'
	verbose_name = 'RFC'
	verbose_name_plural = 'RFCs'
    class Admin:
	search_fields = ['title', 'group', 'area']
	list_display = ['rfc_number', 'title']
	pass

class RfcAuthor(models.Model):
    rfc = models.ForeignKey(Rfc, unique=True, db_column='rfc_number', related_name='authors', edit_inline=models.TABULAR)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, core=True)
    def __str__(self):
        return "%s, %s" % ( self.person.last_name, self.person.first_name)
    class Meta:
        db_table = 'rfc_authors'
	verbose_name = 'RFC Author'

class RfcObsolete(models.Model):
    rfc = models.ForeignKey(Rfc, db_column='rfc_number', raw_id_admin=True, related_name='updates_or_obsoletes')
    action = models.CharField(maxlength=20, core=True)
    rfc_acted_on = models.ForeignKey(Rfc, db_column='rfc_acted_on', raw_id_admin=True, related_name='updated_or_obsoleted_by')
    def __str__(self):
        return "RFC%04d %s RFC%04d" % (self.rfc_id, self.action, self.rfc_acted_on_id)
    class Meta:
        db_table = 'rfcs_obsolete'
	verbose_name = 'RFC updates or obsoletes'
	verbose_name_plural = verbose_name
    class Admin:
	pass

## End RFC Tables

class BallotInfo(models.Model):   # Added by Michael Lee
    ballot = models.AutoField(primary_key=True, db_column='ballot_id')
    active = models.BooleanField()
    an_sent = models.BooleanField()
    an_sent_date = models.DateField(null=True, blank=True)
    an_sent_by = models.ForeignKey(IESGLogin, db_column='an_sent_by', related_name='ansent') 
    defer = models.BooleanField(null=True, blank=True)
    defer_by = models.ForeignKey(IESGLogin, db_column='defer_by', related_name='deferred')
    defer_date = models.DateField(null=True, blank=True)
    approval_text = models.TextField(blank=True)
    last_call_text = models.TextField(blank=True)
    ballot_writeup = models.TextField(blank=True)
    ballot_issued = models.IntegerField(null=True, blank=True)
    def __str__(self):
	try:
	    return "Ballot for %s" % self.drafts.filter(primary_flag=1)
	except IDInternal.DoesNotExist:
	    return "Ballot ID %d (no I-D?)" % (self.ballot)
    def remarks(self):
        remarks = list(self.discusses.all()) + list(self.comments.all())
        return remarks
    class Meta:
        db_table = 'ballot_info'
    class Admin:
	pass

class IDInternal(models.Model):
    """
    An IDInternal represents a document that has been added to the
    I-D tracker.  It can be either an Internet Draft or an RFC.
    The table has only a single primary key field, meaning that
    there is the danger of RFC number collision with low-numbered
    Internet Drafts.

    Since it's most common to be an Internet Draft, the draft
    field is defined as a FK to InternetDrafts.  One side effect
    of this is that select_related() will only work with
    rfc_flag=0.

    When searching where matches may be either I-Ds or RFCs,
    you cannot use draft__ as that will cause an INNER JOIN
    which will limit the responses to I-Ds.
    """
    draft = models.ForeignKey(InternetDraft, primary_key=True, unique=True, db_column='id_document_tag')
    rfc_flag = models.IntegerField(null=True)
    ballot = models.ForeignKey(BallotInfo, related_name='drafts', db_column="ballot_id")
    primary_flag = models.IntegerField(blank=True, null=True)
    group_flag = models.IntegerField(blank=True)
    token_name = models.CharField(blank=True, maxlength=25)
    token_email = models.CharField(blank=True, maxlength=255)
    note = models.TextField(blank=True)
    status_date = models.DateField(null=True)
    email_display = models.CharField(blank=True, maxlength=50)
    agenda = models.IntegerField(null=True, blank=True)
    cur_state = models.ForeignKey(IDState, db_column='cur_state', related_name='docs')
    prev_state = models.ForeignKey(IDState, db_column='prev_state', related_name='docs_prev')
    assigned_to = models.CharField(blank=True, maxlength=25)
    mark_by = models.ForeignKey(IESGLogin, db_column='mark_by', related_name='marked')
    job_owner = models.ForeignKey(IESGLogin, db_column='job_owner', related_name='documents')
    event_date = models.DateField(null=True)
    area_acronym = models.ForeignKey(Area)
    cur_sub_state = models.ForeignKey(IDSubState, related_name='docs', null=True, blank=True)
    prev_sub_state = models.ForeignKey(IDSubState, related_name='docs_prev', null=True, blank=True)
    returning_item = models.IntegerField(null=True, blank=True)
    telechat_date = models.DateField(null=True, blank=True)
    via_rfc_editor = models.IntegerField(null=True, blank=True)
    state_change_notice_to = models.CharField(blank=True, maxlength=255)
    dnp = models.IntegerField(null=True, blank=True)
    dnp_date = models.DateField(null=True, blank=True)
    noproblem = models.IntegerField(null=True, blank=True)
    resurrect_requested_by = models.ForeignKey(IESGLogin, db_column='resurrect_requested_by', related_name='docsresurrected', null=True, blank=True)
    approved_in_minute = models.IntegerField(null=True, blank=True)
    def __str__(self):
        if self.rfc_flag:
	    return "RFC%04d" % ( self.draft_id )
	else:
	    return self.draft.filename
    def get_absolute_url(self):
	if self.rfc_flag:
	    return "/idtracker/rfc%d/" % ( self.draft_id )
	else:
	    return "/idtracker/%s/" % ( self.draft.filename )
    _cached_rfc = None
    def document(self):
	if self.rfc_flag:
	    if self._cached_rfc is None:
		self._cached_rfc = Rfc.objects.get(rfc_number=self.draft_id)
	    return self._cached_rfc
	else:
	    return self.draft
    def comments(self):
	return self.documentcomment_set.all().filter(rfc_flag=self.rfc_flag).order_by('-comment_date','-comment_time')
    def ballot_set(self):
	return IDInternal.objects.filter(ballot=self.ballot_id)
    def ballot_primary(self):
	return IDInternal.objects.filter(ballot=self.ballot_id,primary_flag=1)
    def ballot_others(self):
	return IDInternal.objects.filter(models.Q(primary_flag=0)|models.Q(primary_flag__isnull=True), ballot=self.ballot_id)
    def docstate(self):
	if self.cur_sub_state_id > 0:
	    return "%s :: %s" % ( self.cur_state, self.cur_sub_state )
	else:
	    return self.cur_state
    class Meta:
        db_table = 'id_internal'
	verbose_name = 'IDTracker Draft'
    class Admin:
	pass

class DocumentComment(models.Model):
    BALLOT_CHOICES = (
	(1, 'discuss'),
	(2, 'comment'),
    )
    document = models.ForeignKey(IDInternal)
    rfc_flag = models.IntegerField(null=True, blank=True)
    public_flag = models.IntegerField()
    date = models.DateField(db_column='comment_date')
    time = models.CharField(db_column='comment_time', maxlength=20)
    version = models.CharField(blank=True, maxlength=3)
    comment_text = models.TextField(blank=True)
    created_by = models.ForeignKey(IESGLogin, db_column='created_by', null=True)
    result_state = models.ForeignKey(IDState, db_column='result_state', null=True, related_name="comments_leading_to_state")
    origin_state = models.ForeignKey(IDState, db_column='origin_state', null=True, related_name="comments_coming_from_state")
    ballot = models.IntegerField(null=True, choices=BALLOT_CHOICES)
    def get_absolute_url(self):
	if self.rfc_flag:
	    return "/idtracker/rfc%d/comment/%d/" % (self.document_id, self.id)
	else:
	    return "/idtracker/%s/comment/%d/" % (self.document.draft.filename, self.id)
    def get_author(self):
	if self.created_by:
	    return self.created_by.__str__()
	else:
	    return "system"
    def get_username(self):
	if self.created_by:
	    return self.created_by.login_name
	else:
	    return "system"
    class Meta:
        db_table = 'document_comments'

class Position(models.Model):
    ballot = models.ForeignKey(BallotInfo, raw_id_admin=True, related_name='positions')
    ad = models.ForeignKey(IESGLogin, raw_id_admin=True)
    yes = models.IntegerField(db_column='yes_col')
    noobj = models.IntegerField(db_column='no_col')
    abstain = models.IntegerField()
    approve = models.IntegerField()
    discuss = models.IntegerField()
    recuse = models.IntegerField()
    def __str__(self):
	return "Position for %s on %s" % ( self.ad, self.ballot )
    def abstain_ind(self):
        if self.recuse:
            return 'R'
        if self.abstain:
            return 'X'
        else:
            return ' '
    class Meta:
        db_table = 'ballots'
	unique_together = (('ballot', 'ad'), )
	verbose_name = "IESG Ballot Position"
    class Admin:
	pass

class IESGComment(models.Model):
    ballot = models.ForeignKey(BallotInfo, raw_id_admin=True, related_name="comments")
    ad = models.ForeignKey(IESGLogin, raw_id_admin=True)
    date = models.DateField(db_column="comment_date")
    revision = models.CharField(maxlength=2)
    active = models.IntegerField()
    text = models.TextField(blank=True, db_column="comment_text")
    def __str__(self):
	return "Comment text by %s on %s" % ( self.ad, self.ballot )
    def is_comment(self):
        return True
    class Meta:
        db_table = 'ballots_comment'
	unique_together = (('ballot', 'ad'), )
	verbose_name = 'IESG Comment Text'
	verbose_name_plural = 'IESG Comments'
    class Admin:
	pass

class IESGDiscuss(models.Model):
    ballot = models.ForeignKey(BallotInfo, raw_id_admin=True, related_name="discusses")
    ad = models.ForeignKey(IESGLogin, raw_id_admin=True)
    date = models.DateField(db_column="discuss_date")
    revision = models.CharField(maxlength=2)
    active = models.IntegerField()
    text = models.TextField(blank=True, db_column="discuss_text")
    def __str__(self):
	return "Discuss text by %s on %s" % ( self.ad, self.ballot )
    def is_discuss(self):
        return True
    class Meta:
        db_table = 'ballots_discuss'
	unique_together = (('ballot', 'ad'), )
	verbose_name = 'IESG Discuss Text'
	verbose_name_plural = 'IESG Discusses'
    class Admin:
	pass

class IDAuthor(models.Model):
    document = models.ForeignKey(InternetDraft, db_column='id_document_tag', related_name='authors', edit_inline=models.TABULAR, raw_id_admin=True)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, core=True)
    author_order = models.IntegerField(null=True, blank=True)
    def __str__(self):
	return "%s authors %s" % ( self.person, self.document.filename )
    def email(self):
	try:
	    return self.person.emailaddress_set.filter(type='I-D').get(priority=self.document_id).address
	except EmailAddress.DoesNotExist:
	    return None
    class Meta:
        db_table = 'id_authors'
	verbose_name = "I-D Author"
        ordering = ['document','author_order']

# PostalAddress, EmailAddress and PhoneNumber are edited in
#  the admin for the Rolodex.
# The unique_together constraint is commented out for now, because
#  of a bug in oldforms and AutomaticManipulator which fails to
#  create the isUniquefoo_bar method properly.  Since django is
#  moving away from oldforms, I have to assume that this is going
#  to be fixed by moving admin to newforms.
# A table without a unique primary key!
# must decide which field is/are core.
class PostalAddress(models.Model):
    address_type = models.CharField(maxlength=4)
    address_priority = models.IntegerField(null=True)
    person_or_org = models.ForeignKey(PersonOrOrgInfo, primary_key=True, db_column='person_or_org_tag', edit_inline=models.STACKED)
    person_title = models.CharField(maxlength=50, blank=True)
    affiliated_company = models.CharField(maxlength=70, blank=True)
    aff_company_key = models.CharField(maxlength=70, blank=True, editable=False)
    department = models.CharField(maxlength=100, blank=True)
    staddr1 = models.CharField(maxlength=40, core=True)
    staddr2 = models.CharField(maxlength=40, blank=True)
    mail_stop = models.CharField(maxlength=20, blank=True)
    city = models.CharField(maxlength=20, blank=True)
    state_or_prov = models.CharField(maxlength=20, blank=True)
    postal_code = models.CharField(maxlength=20, blank=True)
    country = models.CharField(maxlength=20, blank=True)
    def save(self):
	self.aff_company_key = self.affiliated_company.upper()
	super(PostalAddress, self).save()
    class Meta:
        db_table = 'postal_addresses'
	#unique_together = (('address_type', 'person_or_org'), )
	verbose_name_plural = 'Postal Addresses'

class EmailAddress(models.Model):
    person_or_org = models.ForeignKey(PersonOrOrgInfo, primary_key=True, db_column='person_or_org_tag', edit_inline=models.TABULAR)
    type = models.CharField(maxlength=12, db_column='email_type')
    priority = models.IntegerField(db_column='email_priority')
    address = models.CharField(maxlength=255, core=True, db_column='email_address')
    comment = models.CharField(blank=True, maxlength=255, db_column='email_comment')
    def __str__(self):
	return self.address
    class Meta:
        db_table = 'email_addresses'
	#unique_together = (('email_priority', 'person_or_org'), )
	# with this, I get 'ChangeManipulator' object has no attribute 'isUniqueemail_priority_person_or_org'

class PhoneNumber(models.Model):
    person_or_org = models.ForeignKey(PersonOrOrgInfo, primary_key=True, db_column='person_or_org_tag', edit_inline=models.TABULAR)
    phone_type = models.CharField(maxlength=3)
    phone_priority = models.IntegerField()
    phone_number = models.CharField(blank=True, maxlength=255, core=True)
    phone_comment = models.CharField(blank=True, maxlength=255)
    class Meta:
        db_table = 'phone_numbers'
	#unique_together = (('phone_priority', 'person_or_org'), )

### Working Groups

class WGType(models.Model):
    group_type_id = models.AutoField(primary_key=True)
    type = models.CharField(maxlength=25, db_column='group_type')
    def __str__(self):
	return self.type
    class Meta:
        db_table = 'g_type'
    class Admin:
	pass

class WGStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status = models.CharField(maxlength=25, db_column='status_value')
    def __str__(self):
	return self.status
    class Meta:
        db_table = 'g_status'
    class Admin:
	pass

class IETFWG(models.Model):
    ACTIVE = 1
    group_acronym = models.ForeignKey(Acronym, primary_key=True, unique=True, editable=False)
    group_type = models.ForeignKey(WGType)
    proposed_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    dormant_date = models.DateField(null=True, blank=True)
    concluded_date = models.DateField(null=True, blank=True)
    status = models.ForeignKey(WGStatus)
    area_director = models.ForeignKey(AreaDirector, null=True)
    meeting_scheduled = models.CharField(blank=True, maxlength=3)
    email_address = models.CharField(blank=True, maxlength=60)
    email_subscribe = models.CharField(blank=True, maxlength=120)
    email_keyword = models.CharField(blank=True, maxlength=50)
    email_archive = models.CharField(blank=True, maxlength=95)
    comments = models.TextField(blank=True)
    last_modified_date = models.DateField()
    meeting_scheduled_old = models.CharField(blank=True, maxlength=3)
    area = FKAsOneToOne('areagroup', reverse=True)
    def __str__(self):
	return self.group_acronym.acronym
    def active_drafts(self):
	return self.group_acronym.internetdraft_set.all().filter(status__status="Active")
    def choices():
	return [(wg.group_acronym_id, wg.group_acronym.acronym) for wg in IETFWG.objects.all().select_related().order_by('acronym.acronym')]
    choices = staticmethod(choices)
    def area_acronym(self):
        return AreaGroup.objects.filter(group_acronym_id=self.group_acronym_id).area 
    class Meta:
        db_table = 'groups_ietf'
	ordering = ['?']	# workaround django wanting to sort by acronym but not joining with it
	verbose_name = 'IETF Working Group'
    class Admin:
	search_fields = ['group_acronym__acronym', 'group_acronym__name']
	list_display = ('group_acronym', 'group_type', 'status', 'area_director')
	list_filter = ['status', 'group_type', 'area_director']
	pass

class WGChair(models.Model):
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, unique=True, core=True)
    group_acronym = models.ForeignKey(IETFWG, edit_inline=models.TABULAR)
    def __str__(self):
	return "%s (%s)" % ( self.person, self.role() )
    def role(self):
	return "%s %s Chair" % ( self.group_acronym.acronym, self.group_acronym.group_type )
    class Meta:
        db_table = 'g_chairs'
	verbose_name = "WG Chair"

class WGEditor(models.Model):
    group_acronym = models.ForeignKey(IETFWG, edit_inline=models.TABULAR)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, unique=True, core=True)
    class Meta:
        db_table = 'g_editors'
	verbose_name = "WG Editor"

# Note: there is an empty table 'g_secretary'.
# This uses the 'g_secretaries' table but is called 'GSecretary' to
# match the model naming scheme.
class WGSecretary(models.Model):
    group_acronym = models.ForeignKey(IETFWG, edit_inline=models.TABULAR)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, unique=True, core=True)
    def __str__(self):
	return "%s (%s)" % ( self.person, self.role() )
    def role(self):
	return "%s %s Secretary" % ( self.group_acronym.acronym, self.group_acronym.group_type )
    class Meta:
        db_table = 'g_secretaries'
	verbose_name = "WG Secretary"
	verbose_name_plural = "WG Secretaries"

class WGTechAdvisor(models.Model):
    group_acronym = models.ForeignKey(IETFWG, edit_inline=models.TABULAR)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, core=True)
    def __str__(self):
	return "%s (%s)" % ( self.person, self.role() )
    def role(self):
	return "%s Technical Advisor" % self.group_acronym.acronym
    class Meta:
        db_table = 'g_tech_advisors'
	verbose_name = "WG Technical Advisor"

class AreaGroup(models.Model):
    area = models.ForeignKey(Area, db_column='area_acronym_id', related_name='areagroup', core=True)
    group = models.ForeignKey(IETFWG, db_column='group_acronym_id', edit_inline=models.TABULAR, num_in_admin=1, max_num_in_admin=1, unique=True)
    def __str__(self):
	return "%s is in %s" % ( self.group, self.area )
    class Meta:
        db_table = 'area_group'
	verbose_name = 'Area this group is in'
	verbose_name_plural = 'Area to Group mappings'

class GoalMilestone(models.Model):
    DONE_CHOICES = (
        ('Done', 'Done'),
        ('No', 'Not Done'),
    )
    gm_id = models.AutoField(primary_key=True)
    group_acronym = models.ForeignKey(IETFWG, raw_id_admin=True)
    description = models.TextField()
    expected_due_date = models.DateField()
    done_date = models.DateField(null=True, blank=True)
    done = models.CharField(blank=True, choices=DONE_CHOICES, maxlength=4)
    last_modified_date = models.DateField()
    def __str__(self):
	return self.description
    class Meta:
        db_table = 'goals_milestones'
	verbose_name = 'IETF WG Goal or Milestone'
	verbose_name_plural = 'IETF WG Goals or Milestones'
	ordering = ['expected_due_date']
    class Admin:
	list_display = ('group', 'description', 'expected_due_date', 'done')
	date_hierarchy = 'expected_due_date'
	list_filter = ['done']
	pass

#### end wg stuff

class Role(models.Model):
    '''This table is named 'chairs' in the database, as its original
    role was to store "who are IETF, IAB and IRTF chairs?".  It has
    since expanded to store roles, such as "IAB Exec Dir" and "IAD",
    so the model is renamed.
    '''
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
    role_name = models.CharField(maxlength=25, db_column='chair_name')
    def __str__(self):
	return "%s (%s)" % (self.person, self.role())
    def role(self):
	if self.role_name in ('IETF', 'IAB', 'IRTF', 'NomCom'):
	    return "%s Chair" % self.role_name
	else:
	    return self.role_name
    class Meta:
        db_table = 'chairs'
    class Admin:
	pass

class ChairsHistory(models.Model):
    CHAIR_CHOICES = (
	( '1', 'IETF' ),
	( '2', 'IAB' ),
	( '3', 'NOMCOM' ),
    )
    chair_type_id = models.IntegerField(choices=CHAIR_CHOICES)
    present_chair = models.BooleanField()
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'chairs_history'

#
# IRTF RG info
class IRTF(models.Model):
    irtf_id = models.AutoField(primary_key=True)
    acronym = models.CharField(blank=True, maxlength=25, db_column='irtf_acronym')
    name = models.CharField(blank=True, maxlength=255, db_column='irtf_name')
    charter_text = models.TextField(blank=True)
    meeting_scheduled = models.BooleanField(null=True, blank=True)
    class Meta:
        db_table = 'irtf'
    class Admin:
	pass

class IRTFChair(models.Model):
    irtf = models.ForeignKey(IRTF)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True)
    class Meta:
        db_table = 'irtf_chairs'
    class Admin:
	pass
