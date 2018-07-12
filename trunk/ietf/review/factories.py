import factory
import datetime

from ietf.review.models import ReviewTeamSettings, ReviewRequest
from ietf.name.models import ReviewTypeName, ReviewResultName

class ReviewTeamSettingsFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReviewTeamSettings

    group = factory.SubFactory('ietf.group.factories.GroupFactory',type_id='review')

    @factory.post_generation
    def review_types(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            obj.review_types.set(ReviewTypeName.objects.filter(slug__in=extracted))
        else:
            obj.review_types.set(ReviewTypeName.objects.filter(slug__in=('early','lc','telechat')))

    @factory.post_generation
    def review_results(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            obj.review_results.set(ReviewResultName.objects.filter(slug__in=extracted))
        else:
            obj.review_results.set(ReviewResultName.objects.filter(slug__in=('not-ready','right-track','almost-ready','ready-issues','ready-nits','ready')))

class ReviewRequestFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReviewRequest

    state_id = 'requested'
    type_id = 'lc'
    doc = factory.SubFactory('ietf.doc.factories.DocumentFactory',type_id='draft')
    team = factory.SubFactory('ietf.group.factories.ReviewTeamFactory',type_id='review')
    deadline = datetime.datetime.today()+datetime.timedelta(days=14)
    requested_by = factory.SubFactory('ietf.person.factories.PersonFactory')

