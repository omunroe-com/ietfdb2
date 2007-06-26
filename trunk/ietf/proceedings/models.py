from django.db import models
from ietf.idtracker.models import Acronym, PersonOrOrgInfo, IRTF, AreaGroup, Area, IETFWG
import datetime
#from ietf.utils import log

# group_acronym is either an IETF Acronym
#  or an IRTF one, depending on the value of irtf.
#  Multiple inheritance to the rescue.
#
# interim = i prefix (complicated because you have to check if self has
#    an interim attribute first)
class ResolveAcronym(object):
    def acronym(self):
	try:
	    interim = self.interim
	except AttributeError:
	    interim = False
	if self.irtf:
	    acronym = IRTF.objects.get(pk=self.group_acronym_id).acronym
	else:
	    acronym = Acronym.objects.get(pk=self.group_acronym_id).acronym
	if interim:
	    return "i" + acronym
	return acronym
    def acronym_lower(self):
        return self.acronym().lower()
    def acronym_name(self):
        try:
            interim = self.interim
        except AttributeError:
            interim = False
        if self.irtf:
            acronym_name = IRTF.objects.get(pk=self.group_acronym_id).name
        else:
            acronym_name = Acronym.objects.get(pk=self.group_acronym_id).name
        if interim:
            return acronym_name + " (interim)"
        return acronym_name
    def area(self):
        if self.irtf:
            area = "irtf"
        elif self.group_acronym_id < 0  and self.group_acronym_id > -3:
            area = "1plenary"
        elif self.group_acronym_id < -2:
            area = ""
        else:
            try:
                area = AreaGroup.objects.get(group=self.group_acronym_id).area.area_acronym.acronym
            except AreaGroup.DoesNotExist:
                area = ""
        return area
    def area_name(self):
        if self.irtf:
            area_name = "IRTF"
        elif self.group_acronym_id < 0  and self.group_acronym_id > -3:
            area_name = "Plenary Sessions"
        elif self.group_acronym_id < -2:
            area_name = "Training"
        else:
            try:
                area_name = AreaGroup.objects.get(group=self.group_acronym_id).area.area_acronym.name
            except AreaGroup.DoesNotExist:
                area_name = ""
        return area_name
    def isWG(self):
        if self.irtf:
              return False
        else:
            try:
                g_type_id = IETFWG.objects.get(pk=self.group_acronym_id).group_type_id == 1
                if g_type_id == 1:
                    return True
                else:
                    return False
            except IETFWG.DoesNotExist:
                return False
    def group_type_str(self):
        if self.irtf:
              return ""
        else:
            try:
                g_type_id = IETFWG.objects.get(pk=self.group_acronym_id).group_type_id 
                if g_type_id == 1:
                    return "WG"
                elif g_type_id == 3:
                    return "BOF"
                else:
                    return ""
            except IETFWG.DoesNotExist:
                return ""

class Meeting(models.Model):
    meeting_num = models.IntegerField(primary_key=True)
    start_date = models.DateField()
    end_date = models.DateField()
    city = models.CharField(blank=True, maxlength=255)
    state = models.CharField(blank=True, maxlength=255)
    country = models.CharField(blank=True, maxlength=255)
    ack = models.TextField(blank=True)
    agenda_html = models.TextField(blank=True)
    agenda_text = models.TextField(blank=True)
    future_meeting = models.TextField(blank=True)
    overview1 = models.TextField(blank=True)
    overview2 = models.TextField(blank=True)
    def __str__(self):
	return "IETF %d" % (self.meeting_num)
    def get_meeting_date (self,offset):
        return self.start_date + datetime.timedelta(days=offset) 
    class Meta:
        db_table = 'meetings'
    class Admin:
	pass

class MeetingVenue(models.Model):
    meeting_num = models.ForeignKey(Meeting, db_column='meeting_num', unique=True)
    break_area_name = models.CharField(maxlength=255)
    reg_area_name = models.CharField(maxlength=255)
    def __str__(self):
	return "IETF %d" % (self.meeting_num_id)
    class Meta:
        db_table = 'meeting_venues'
    class Admin:
	pass

class NonSessionRef(models.Model):
    name = models.CharField(maxlength=255)
    def __str__(self):
	return self.name
    class Meta:
        db_table = 'non_session_ref'

class NonSession(models.Model):
    non_session_id = models.AutoField(primary_key=True)
    day_id = models.IntegerField(blank=True, null=True)
    non_session_ref = models.ForeignKey(NonSessionRef)
    meeting = models.ForeignKey(Meeting, db_column='meeting_num')
    time_desc = models.CharField(blank=True, maxlength=75)
    def __str__(self):
	if self.day_id:
	    return "%s %s %s @%d" % ((self.meeting.start_date + datetime.timedelta(self.day_id)).strftime('%A'), self.time_desc, self.non_session_ref, self.meeting_id)
	else:
	    return "** %s %s @%d" % (self.time_desc, self.non_session_ref, self.meeting_id)
    class Meta:
	db_table = 'non_session'

class Proceeding(models.Model):
    meeting_num = models.ForeignKey(Meeting, db_column='meeting_num', unique=True, primary_key=True)
    dir_name = models.CharField(blank=True, maxlength=25)
    sub_begin_date = models.DateField(null=True, blank=True)
    sub_cut_off_date = models.DateField(null=True, blank=True)
    frozen = models.IntegerField(null=True, blank=True)
    c_sub_cut_off_date = models.DateField(null=True, blank=True)
    pr_from_date = models.DateField(null=True, blank=True)
    pr_to_date = models.DateField(null=True, blank=True)
    def __str__(self):
	return "IETF %d" % (self.meeting_num_id)
    class Meta:
        db_table = 'proceedings'
	ordering = ['?']	# workaround for FK primary key
    #class Admin:
    #    pass		# admin site doesn't like something about meeting_num

class SessionConflict(models.Model):
    group_acronym = models.ForeignKey(Acronym, raw_id_admin=True, related_name='conflicts_set')
    conflict_gid = models.ForeignKey(Acronym, raw_id_admin=True, related_name='conflicts_with_set', db_column='conflict_gid')
    meeting_num = models.ForeignKey(Meeting, db_column='meeting_num')
    def __str__(self):
	return "At IETF %d, %s conflicts with %s" % ( self.meeting_num_id, self.group_acronym.acronym, self.conflict_gid.acronym)
    class Meta:
        db_table = 'session_conflicts'
    class Admin:
	pass

class SessionName(models.Model):
    session_name_id = models.AutoField(primary_key=True)
    session_name = models.CharField(blank=True, maxlength=255)
    def __str__(self):
	return self.session_name
    class Meta:
        db_table = 'session_names'
    class Admin:
	pass
class IESGHistory(models.Model):
    meeting = models.ForeignKey(Meeting, db_column='meeting_num', core=True)
    area = models.ForeignKey(Area, db_column='area_acronym_id', core=True)
    person = models.ForeignKey(PersonOrOrgInfo, db_column='person_or_org_tag', raw_id_admin=True, core=True)
    def __str__(self):
        return "%s (%s)" % (self.person,self.area)
    class Meta:
        db_table = 'iesg_history'
    class Admin:
        pass
    
class MeetingTime(models.Model):
    time_id = models.AutoField(primary_key=True)
    time_desc = models.CharField(maxlength=100)
    meeting = models.ForeignKey(Meeting, db_column='meeting_num', unique=True)
    day_id = models.IntegerField()
    session_name = models.ForeignKey(SessionName)
    def __str__(self):
	return "[%d] |%s| %s" % (self.meeting_id, (self.meeting.start_date + datetime.timedelta(self.day_id)).strftime('%A'), self.time_desc)
    def sessions(self):
	"""
	Get all sessions that are scheduled at this time.
	"""
	sessions = WgMeetingSession.objects.filter(
	    models.Q(sched_time_id1=self.time_id) |
	    models.Q(sched_time_id2=self.time_id) |
	    models.Q(sched_time_id3=self.time_id) |
            models.Q(combined_time_id1=self.time_id) |
            models.Q(combined_time_id2=self.time_id))
	for s in sessions:
	    if s.sched_time_id1_id == self.time_id:
		s.room_id = s.sched_room_id1
	    elif s.sched_time_id2_id == self.time_id:
		s.room_id = s.sched_room_id2
	    elif s.sched_time_id3_id == self.time_id:
		s.room_id = s.sched_room_id3
            elif s.combined_time_id1_id == self.time_id:
                s.room_id = s.combined_room_id1
            elif s.combined_time_id2_id == self.time_id:
                s.room_id = s.combined_room_id2
	    else:
		s.room_id = 0
	return sessions
    def meeting_date(self):
        return self.meeting.get_meeting_date(self.day_id)
    def reg_info(self):
	reg_info = NonSession.objects.get(meeting=self.meeting, day_id=self.day_id, non_session_ref=1)
        if reg_info.time_desc:
            return "%s %s" % (reg_info.time_desc, reg_info.non_session_ref)
        else:
            return ""
    def morning_br_info(self):
	br_info = NonSession.objects.get(models.Q(day_id=self.day_id) | models.Q(day_id__isnull=True), meeting=self.meeting, non_session_ref=2)
        return "%s %s" % (br_info.time_desc, br_info.non_session_ref)
    def lunch_br_info(self):
        return NonSession.objects.get(meeting=self.meeting, non_session_ref=3).time_desc
    def an_br1_info(self):
	an_br1_info = NonSession.objects.exclude(time_desc="").get(meeting=self.meeting, day_id=self.day_id, non_session_ref=4)
        if an_br1_info:
          return "%s %s" % (an_br1_info.time_desc, an_br1_info.non_session_ref)
        else:
          return ""
    def an_br2_info(self):
	an_br2_info = NonSession.objects.exclude(time_desc="").get(meeting=self.meeting, day_id=self.day_id, non_session_ref=5)
        if an_br2_info:
          return "%s %s" % (an_br2_info.time_desc, an_br2_info.non_session_ref)
        else:
          return ""
    def fbreak_info(self):
        fbreak_info = NonSession.objects.get(meeting=self.meeting, day_id=5, non_session_ref=6)
        return "%s %s" % (fbreak_info.time_desc, fbreak_info.non_session_ref)
    class Meta:
        db_table = 'meeting_times'
    class Admin:
	pass

class MeetingRoom(models.Model):
    room_id = models.AutoField(primary_key=True)
    meeting = models.ForeignKey(Meeting, db_column='meeting_num')
    room_name = models.CharField(maxlength=255)
    def __str__(self):
	return "[%d] %s" % (self.meeting_id, self.room_name)
    class Meta:
        db_table = 'meeting_rooms'
    class Admin:
	pass

class WgMeetingSession(models.Model, ResolveAcronym):
    session_id = models.AutoField(primary_key=True)
    meeting = models.ForeignKey(Meeting, db_column='meeting_num')
    group_acronym_id = models.IntegerField()
    irtf = models.BooleanField()
    num_session = models.IntegerField()
    length_session1 = models.CharField(blank=True, maxlength=100)
    length_session2 = models.CharField(blank=True, maxlength=100)
    length_session3 = models.CharField(blank=True, maxlength=100)
    conflict1 = models.CharField(blank=True, maxlength=255)
    conflict2 = models.CharField(blank=True, maxlength=255)
    conflict3 = models.CharField(blank=True, maxlength=255)
    conflict_other = models.TextField(blank=True)
    special_req = models.TextField(blank=True)
    number_attendee = models.IntegerField(null=True, blank=True)
    approval_ad = models.IntegerField(null=True, blank=True)
    status_id = models.IntegerField(null=True, blank=True)
    ts_status_id = models.IntegerField(null=True, blank=True)
    requested_date = models.DateField(null=True, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    requested_by = models.ForeignKey(PersonOrOrgInfo, raw_id_admin=True, db_column='requested_by')
    scheduled_date = models.DateField(null=True, blank=True)
    last_modified_date = models.DateField(null=True, blank=True)
    ad_comments = models.TextField(blank=True)
    sched_room_id1 = models.ForeignKey(MeetingRoom, db_column='sched_room_id1', null=True, blank=True, related_name='here1')
    sched_time_id1 = models.ForeignKey(MeetingTime, db_column='sched_time_id1', null=True, blank=True, related_name='now1')
    sched_date1 = models.DateField(null=True, blank=True)
    sched_room_id2 = models.ForeignKey(MeetingRoom, db_column='sched_room_id2', null=True, blank=True, related_name='here2')
    sched_time_id2 = models.ForeignKey(MeetingTime, db_column='sched_time_id2', null=True, blank=True, related_name='now2')
    sched_date2 = models.DateField(null=True, blank=True)
    sched_room_id3 = models.ForeignKey(MeetingRoom, db_column='sched_room_id3', null=True, blank=True, related_name='here3')
    sched_time_id3 = models.ForeignKey(MeetingTime, db_column='sched_time_id3', null=True, blank=True, related_name='now3')
    sched_date3 = models.DateField(null=True, blank=True)
    special_agenda_note = models.CharField(blank=True, maxlength=255)
    combined_room_id1 = models.ForeignKey(MeetingRoom, db_column='combined_room_id1', null=True, blank=True, related_name='here4')
    combined_time_id1 = models.ForeignKey(MeetingTime, db_column='combined_time_id1', null=True, blank=True, related_name='now4')
    combined_room_id2 = models.ForeignKey(MeetingRoom, db_column='combined_room_id2', null=True, blank=True, related_name='here5')
    combined_time_id2 = models.ForeignKey(MeetingTime, db_column='combined_time_id2', null=True, blank=True, related_name='now5')
    def __str__(self):
	return "%s at %s" % (self.acronym(), self.meeting)
    def agenda_file(self,interimvar=0):
        irtfvar = 0
        if self.irtf:
            irtfvar = self.group_acronym_id 
        if interimvar == 0:
            try:
                if self.interim:
                    interimvar = 1
            except AttributeError:
                    interimvar = 0
        try:
            filename = WgAgenda.objects.get(meeting=self.meeting, group_acronym_id=self.group_acronym_id,irtf=irtfvar,interim=interimvar).filename
            dir = Proceeding.objects.get(meeting_num=self.meeting).dir_name
            retvar = "%s/agenda/%s" % (dir,filename) 
        except WgAgenda.DoesNotExist:
            retvar = ""
        return retvar
    def minute_file(self,interimvar=0):
        irtfvar = 0
        if self.irtf:
            irtfvar = self.group_acronym_id
        if interimvar == 0:
            try:
                if self.interim:
                    interimvar = 1
            except AttributeError:
                    interimvar = 0
        try:
            filename = Minute.objects.get(meeting=self.meeting, group_acronym_id=self.group_acronym_id,irtf=irtfvar,interim=interimvar).filename
            dir = Proceeding.objects.get(meeting_num=self.meeting).dir_name
            retvar = "%s/minutes/%s" % (dir,filename)
        except Minute.DoesNotExist:
            retvar = ""
        return retvar
    def slides(self,interimvar=0):
        """
        Get all slides of this session.
        """
        irtfvar = 0
        if self.irtf:
            irtfvar = self.group_acronym_id
        if interimvar == 0:
            try:
                if self.interim:
                    interimvar = 1
            except AttributeError:
                    interimvar = 0
        slides = Slide.objects.filter(meeting=self.meeting,group_acronym_id=self.group_acronym_id,irtf=irtfvar,interim=interimvar).order_by("order_num")
        return slides
    def interim_meeting (self):
        if self.minute_file(1):
            return True
        elif self.agenda_file(1):
            return True
        elif self.slides(1):
            return True
        else:
            return False
    class Meta:
        db_table = 'wg_meeting_sessions'
    class Admin:
	pass

class WgAgenda(models.Model, ResolveAcronym):
    meeting = models.ForeignKey(Meeting, db_column='meeting_num')
    group_acronym_id = models.IntegerField()
    filename = models.CharField(maxlength=255)
    irtf = models.BooleanField()
    interim = models.BooleanField()
    def __str__(self):
	return "Agenda for %s at IETF %d" % (self.acronym(), self.meeting_id)
    class Meta:
        db_table = 'wg_agenda'
    class Admin:
	pass

class Minute(models.Model, ResolveAcronym):
    meeting = models.ForeignKey(Meeting, db_column='meeting_num')
    group_acronym_id = models.IntegerField()
    filename = models.CharField(blank=True, maxlength=255)
    irtf = models.BooleanField()
    interim = models.BooleanField()
    def __str__(self):
	return "Minutes for %s at IETF %d" % (self.acronym(), self.meeting_id)
    class Meta:
        db_table = 'minutes'
    class Admin:
	pass

# It looks like Switches was meant for something bigger, but
# is only used for the agenda generation right now so we'll
# put it here.
class Switches(models.Model):
    name = models.CharField(maxlength=100)
    val = models.IntegerField(null=True, blank=True)
    updated_date = models.DateField(null=True, blank=True)
    updated_time = models.TimeField(null=True, blank=True)
    def __str__(self):
	return self.name
    class Meta:
        db_table = 'switches'
    class Admin:
	pass

# Empty table, don't pretend that it exists.
#class SlideTypes(models.Model):
#    type_id = models.AutoField(primary_key=True)
#    type = models.CharField(maxlength=255, db_column='type_name')
#    def __str__(self):
#	return self.type
#    class Meta:
#        db_table = 'slide_types'
#    class Admin:
#	pass

class Slide(models.Model, ResolveAcronym):
    SLIDE_TYPE_CHOICES=(
	('1', '(converted) HTML'),
	('2', 'PDF'),
	('3', 'Text'),
	('4', 'PowerPoint'),
	('5', 'Microsoft Word'),
    )
    meeting = models.ForeignKey(Meeting, db_column='meeting_num')
    group_acronym_id = models.IntegerField(null=True, blank=True)
    slide_num = models.IntegerField(null=True, blank=True)
    slide_type_id = models.IntegerField(choices=SLIDE_TYPE_CHOICES)
    slide_name = models.CharField(blank=True, maxlength=255)
    irtf = models.BooleanField()
    interim = models.BooleanField()
    order_num = models.IntegerField(null=True, blank=True)
    in_q = models.IntegerField(null=True, blank=True)
    def __str__(self):
	return "IETF%d: %s slides (%s)" % (self.meeting_id, self.acronym(), self.slide_name)
    def file_loc(self):
        dir = Proceeding.objects.get(meeting_num=self.meeting).dir_name
        if self.slide_type_id==1:
            return "%s/slides/%s-%s/sld1.htm" % (dir,self.acronym(),self.slide_num)
        else:
            if self.slide_type_id == 2:
                ext = ".pdf"
            elif self.slide_type_id == 3:
                ext = ".txt"
            elif self.slide_type_id == 4:
                ext = ".ppt"
            elif self.slide_type_id == 5:
                ext = ".doc"
            else:
                ext = ""
            return "%s/slides/%s-%s%s" % (dir,self.acronym(),self.slide_num,ext)
    class Meta:
        db_table = 'slides'
    class Admin:
	pass
