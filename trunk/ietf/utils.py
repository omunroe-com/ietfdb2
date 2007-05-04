import operator
# look at snippets 59, 148, 99 for newforms helpers

# http://www.djangosnippets.org/snippets/59/
def form_decorator(fields = {}, attrs = {}, widgets = {}, 
    labels = {}, choices = {}):
    
    """
    This function helps to add overrides when creating forms from models/instances.
    Pass in dictionary of fields to override certain fields altogether, otherwise
    add widgets or labels as desired.
    
    For example:
    
    class Project(models.Model):
    
        name = models.CharField(maxlength = 100)
        description = models.TextField()
        owner = models.ForeignKey(User)
   
    project_fields = dict(
        owner = None
    )
    
    project_widgets = dict(
        name = forms.TextInput({"size":40}),
        description = forms.Textarea({"rows":5, "cols":40}))
    
    project_labels = dict(
        name = "Enter your project name here"
    )
    
    callback = form_decorator(project_fields, project_widgets, project_labels)
    project_form = forms.form_for_model(Project, formfield_callback = callback)
    
    This saves having to redefine whole fields for example just to change a widget
    setting or label.
    """
    
    def formfields_callback(f, **kw):
    
        if f.name in fields:
            
            # replace field altogether
            field = fields[f.name]
            f.initial = kw.pop("initial", None)
            return field
        
        if f.name in widgets:
            
            kw["widget"] = widgets[f.name]

        if f.name in attrs:
            
            widget = kw.pop("widget", f.formfield().widget)
            if widget :
                widget.attrs.update(attrs[f.name])
                kw["widget"] = widget

        if f.name in labels:
        
            kw["label"] = labels[f.name]
        
        if f.name in choices:
        
            choice_set = choices[f.name]
            if callable(choice_set) : choice_set = choice_set()
            kw["choices"] = choice_set
            
                
        return f.formfield(**kw)
    
    return formfields_callback


# Caching accessor for the reverse of a ForeignKey relatinoship
# Started by axiak on #django
class FKAsOneToOne(object):
    def __init__(self, field, reverse = False, query = None):
        self.field = field
        self.reverse = reverse
	self.query = query
    
    def __get_attr(self, instance):
        if self.reverse:
            field_name = '%s_set' % self.field
        else:
            field_name = self.field
        return getattr(instance, field_name)

    def __get__(self, instance, Model):
        if not hasattr(instance, '_field_values'):
            instance._field_values = {}
        try:
            return instance._field_values[self.field]
	except KeyError:
	    pass

        if self.reverse:
            value_set = self.__get_attr(instance).all()
	    if self.query:
		value_set = value_set.filter(self.query)
	    try:
                instance._field_values[self.field] = value_set[0]
	    except IndexError:
                instance._field_values[self.field] = None
        else:
            instance._field_values[self.field] = self.__get_attr(instance)

        return instance._field_values[self.field]

    def __set__(self, instance, value):
        if self.reverse:
            # this is dangerous
            #other_instance = self.__get_attr(instance).all()[0]
            #setattr(other_instance, self.field, value)
            #other_instance.save()
	    raise NotImplemented
        else:
            setattr(instance, self.field, value)


def orl(list):
    """ Return the "or" of every element in a list.
    Used to generate "or" queries with a list of Q objects. """
    return reduce(operator.__or__, list)

def flattenl(list):
    """ Flatten a list one level, e.g., turn
	[ ['a'], ['b'], ['c', 'd'] ] into
	[ 'a', 'b', 'c', 'd' ]
    """
    return reduce(operator.__concat__, list)


def split_form(html, blocks):
    """Split the rendering of a form into a dictionary of named blocks.

    Takes the html of the rendered form as the first argument.

    Expects a dictionary as the second argument, with desired block
    name and a field specification as key:value pairs.

    The field specification can be either a list of field names, or
    a string with the field names separated by whitespace.

    The return value is a new dictionary, with the same keys as the
    block specification dictionary, and the form rendering matching
    the specified keys as the value.

    Any line in the rendered form which doesn't match any block's
    field list will cause an exception to be raised.
    """
    import re
    output = dict([(block,[]) for block in blocks])
    # handle field lists in string form
    for block in blocks:
        if type(blocks[block]) == type(""):
            blocks[block] = blocks[block].split()

    # collapse radio button html to one line
    html = re.sub('\n(.*type="radio".*\n)', "\g<1>", html)
    html = re.sub('(?m)^(.*type="radio".*)\n', "\g<1>", html)

    for line in html.split('\n'):
        found = False
        for block in blocks:
            for field in blocks[block]:
                if ('name="%s"' % field) in line:
                    output[block].append(line)
                    found = True
        if not found:
            raise LookupError("Could not place line in any section: '%s'" % line)

    for block in output:
        output[block] = "\n".join(output[block])

    return output
