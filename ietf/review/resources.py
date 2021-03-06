# Autogenerated by the makeresources management command 2016-06-14 04:21 PDT
from tastypie.resources import ModelResource
from tastypie.fields import ToManyField                 # pyflakes:ignore
from tastypie.constants import ALL, ALL_WITH_RELATIONS  # pyflakes:ignore
from tastypie.cache import SimpleCache

from ietf import api
from ietf.api import ToOneField                         # pyflakes:ignore

from ietf.review.models import (ReviewerSettings, ReviewRequest,
                                UnavailablePeriod, ReviewWish, NextReviewerInTeam,
                                ReviewSecretarySettings, ReviewTeamSettings )


from ietf.person.resources import PersonResource
from ietf.group.resources import GroupResource
class ReviewerSettingsResource(ModelResource):
    team             = ToOneField(GroupResource, 'team')
    person           = ToOneField(PersonResource, 'person')
    class Meta:
        queryset = ReviewerSettings.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'reviewer'
        filtering = { 
            "id": ALL,
            "min_interval": ALL,
            "filter_re": ALL,
            "skip_next": ALL,
            "team": ALL_WITH_RELATIONS,
            "person": ALL_WITH_RELATIONS,
        }
api.review.register(ReviewerSettingsResource())



from ietf.doc.resources import DocumentResource
from ietf.group.resources import GroupResource
from ietf.name.resources import ReviewRequestStateNameResource, ReviewResultNameResource, ReviewTypeNameResource
from ietf.person.resources import PersonResource, EmailResource
class ReviewRequestResource(ModelResource):
    state            = ToOneField(ReviewRequestStateNameResource, 'state')
    type             = ToOneField(ReviewTypeNameResource, 'type')
    doc              = ToOneField(DocumentResource, 'doc')
    team             = ToOneField(GroupResource, 'team')
    requested_by     = ToOneField(PersonResource, 'requested_by')
    reviewer         = ToOneField(EmailResource, 'reviewer', null=True)
    review           = ToOneField(DocumentResource, 'review', null=True)
    result           = ToOneField(ReviewResultNameResource, 'result', null=True)
    class Meta:
        queryset = ReviewRequest.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'reviewrequest'
        filtering = { 
            "id": ALL,
            "old_id": ALL,
            "time": ALL,
            "deadline": ALL,
            "requested_rev": ALL,
            "comment": ALL,
            "reviewed_rev": ALL,
            "state": ALL_WITH_RELATIONS,
            "type": ALL_WITH_RELATIONS,
            "doc": ALL_WITH_RELATIONS,
            "team": ALL_WITH_RELATIONS,
            "requested_by": ALL_WITH_RELATIONS,
            "reviewer": ALL_WITH_RELATIONS,
            "review": ALL_WITH_RELATIONS,
            "result": ALL_WITH_RELATIONS,
        }
api.review.register(ReviewRequestResource())

from ietf.person.resources import PersonResource
from ietf.group.resources import GroupResource
class UnavailablePeriodResource(ModelResource):
    team             = ToOneField(GroupResource, 'team')
    person           = ToOneField(PersonResource, 'person')
    class Meta:
        queryset = UnavailablePeriod.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'unavailableperiod'
        filtering = { 
            "id": ALL,
            "start_date": ALL,
            "end_date": ALL,
            "availability": ALL,
	    "reason": ALL,
            "team": ALL_WITH_RELATIONS,
            "person": ALL_WITH_RELATIONS,
        }
api.review.register(UnavailablePeriodResource())

from ietf.person.resources import PersonResource
from ietf.group.resources import GroupResource
from ietf.doc.resources import DocumentResource
class ReviewWishResource(ModelResource):
    team             = ToOneField(GroupResource, 'team')
    person           = ToOneField(PersonResource, 'person')
    doc              = ToOneField(DocumentResource, 'doc')
    class Meta:
        queryset = ReviewWish.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'reviewwish'
        filtering = { 
            "id": ALL,
            "time": ALL,
            "team": ALL_WITH_RELATIONS,
            "person": ALL_WITH_RELATIONS,
            "doc": ALL_WITH_RELATIONS,
        }
api.review.register(ReviewWishResource())



from ietf.person.resources import PersonResource
from ietf.group.resources import GroupResource
class NextReviewerInTeamResource(ModelResource):
    team             = ToOneField(GroupResource, 'team')
    next_reviewer    = ToOneField(PersonResource, 'next_reviewer')
    class Meta:
        queryset = NextReviewerInTeam.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'nextreviewerinteam'
        filtering = { 
            "id": ALL,
            "team": ALL_WITH_RELATIONS,
            "next_reviewer": ALL_WITH_RELATIONS,
        }
api.review.register(NextReviewerInTeamResource())

from ietf.person.resources import PersonResource
from ietf.group.resources import GroupResource
class ReviewSecretarySettingsResource(ModelResource):
    team             = ToOneField(GroupResource, 'team')
    person           = ToOneField(PersonResource, 'person')
    class Meta:
        queryset = ReviewSecretarySettings.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'reviewsecretarysettings'
        filtering = { 
            "id": ALL,
            "remind_days_before_deadline": ALL,
            "team": ALL_WITH_RELATIONS,
            "person": ALL_WITH_RELATIONS,
        }
api.review.register(ReviewSecretarySettingsResource())


from ietf.group.resources import GroupResource
from ietf.name.resources import ReviewResultNameResource, ReviewTypeNameResource
class ReviewTeamSettingsResource(ModelResource):
    group            = ToOneField(GroupResource, 'group')
    review_types     = ToManyField(ReviewTypeNameResource, 'review_types', null=True)
    review_results   = ToManyField(ReviewResultNameResource, 'review_results', null=True)
    notify_ad_when   = ToManyField(ReviewResultNameResource, 'notify_ad_when', null = True)
    class Meta:
        queryset = ReviewTeamSettings.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'reviewteamsettings'
        filtering = { 
            "id": ALL,
            "autosuggest": ALL,
            "group": ALL_WITH_RELATIONS,
            "review_types": ALL_WITH_RELATIONS,
            "review_results": ALL_WITH_RELATIONS,
            "notify_ad_when": ALL_WITH_RELATIONS,
        }
api.review.register(ReviewTeamSettingsResource())

