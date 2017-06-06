# Autogenerated by the makeresources management command 2017-02-15 10:10 PST
from tastypie.resources import ModelResource
from tastypie.fields import ToManyField                 # pyflakes:ignore
from tastypie.constants import ALL, ALL_WITH_RELATIONS  # pyflakes:ignore
from tastypie.cache import SimpleCache

from ietf import api
from ietf.api import ToOneField                         # pyflakes:ignore

from ietf.stats.models import CountryAlias, AffiliationIgnoredEnding, AffiliationAlias, MeetingRegistration


from ietf.name.resources import CountryNameResource
class CountryAliasResource(ModelResource):
    country          = ToOneField(CountryNameResource, 'country')
    class Meta:
        queryset = CountryAlias.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'countryalias'
        filtering = { 
            "id": ALL,
            "alias": ALL,
            "country": ALL_WITH_RELATIONS,
        }
api.stats.register(CountryAliasResource())

class AffiliationIgnoredEndingResource(ModelResource):
    class Meta:
        queryset = AffiliationIgnoredEnding.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'affiliationignoredending'
        filtering = { 
            "id": ALL,
            "ending": ALL,
        }
api.stats.register(AffiliationIgnoredEndingResource())

class AffiliationAliasResource(ModelResource):
    class Meta:
        queryset = AffiliationAlias.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'affiliationalias'
        filtering = { 
            "id": ALL,
            "alias": ALL,
            "name": ALL,
        }
api.stats.register(AffiliationAliasResource())

class MeetingRegistrationResource(ModelResource):
    class Meta:
        queryset = MeetingRegistration.objects.all()
        serializer = api.Serializer()
        cache = SimpleCache()
        #resource_name = 'meetingregistration'
        filtering = { 
            "id": ALL,
            "meeting": ALL_WITH_RELATIONS,
            "first_name": ALL,
            "last_name": ALL,
            "affiliation": ALL,
            "country_code": ALL,
            "email": ALL,
            "person": ALL_WITH_RELATIONS
        }
api.stats.register(MeetingRegistrationResource())

