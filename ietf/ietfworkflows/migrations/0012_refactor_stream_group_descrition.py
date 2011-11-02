
from south.db import db
from django.db import models
from ietf.ietfworkflows.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'Stream.group_chair_attribute'
        db.add_column('ietfworkflows_stream', 'group_chair_attribute', orm['ietfworkflows.stream:group_chair_attribute'])
        
        # Adding field 'Stream.document_group_attribute'
        db.add_column('ietfworkflows_stream', 'document_group_attribute', orm['ietfworkflows.stream:document_group_attribute'])
        
        # Deleting field 'Stream.group_chair_model'
        db.delete_column('ietfworkflows_stream', 'group_chair_model')
        
        # Deleting field 'Stream.with_groups'
        db.delete_column('ietfworkflows_stream', 'with_groups')
        
        # Deleting field 'Stream.group_model'
        db.delete_column('ietfworkflows_stream', 'group_model')
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'Stream.group_chair_attribute'
        db.delete_column('ietfworkflows_stream', 'group_chair_attribute')
        
        # Deleting field 'Stream.document_group_attribute'
        db.delete_column('ietfworkflows_stream', 'document_group_attribute')
        
        # Adding field 'Stream.group_chair_model'
        db.add_column('ietfworkflows_stream', 'group_chair_model', orm['ietfworkflows.stream:group_chair_model'])
        
        # Adding field 'Stream.with_groups'
        db.add_column('ietfworkflows_stream', 'with_groups', orm['ietfworkflows.stream:with_groups'])
        
        # Adding field 'Stream.group_model'
        db.add_column('ietfworkflows_stream', 'group_model', orm['ietfworkflows.stream:group_model'])
        
    
    
    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'idtracker.acronym': {
            'Meta': {'db_table': "'acronym'"},
            'acronym': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'acronym_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name_key': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'idtracker.idintendedstatus': {
            'Meta': {'db_table': "'id_intended_status'"},
            'intended_status': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_column': "'status_value'"}),
            'intended_status_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'idtracker.idstatus': {
            'Meta': {'db_table': "'id_status'"},
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_column': "'status_value'"}),
            'status_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'idtracker.internetdraft': {
            'Meta': {'db_table': "'internet_drafts'"},
            'abstract': ('django.db.models.fields.TextField', [], {}),
            'b_approve_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'b_discussion_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'b_sent_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'dunn_sent_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'expired_tombstone': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'extension_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'file_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'filename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['idtracker.Acronym']", 'db_column': "'group_acronym_id'"}),
            'id_document_key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id_document_tag': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intended_status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['idtracker.IDIntendedStatus']"}),
            'last_modified_date': ('django.db.models.fields.DateField', [], {}),
            'lc_changes': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True'}),
            'lc_expiration_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'lc_sent_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'local_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'replaced_by': ('django.db.models.fields.related.ForeignKey', ["orm['idtracker.InternetDraft']"], {'related_name': "'replaces_set'", 'null': 'True', 'db_column': "'replaced_by'", 'blank': 'True'}),
            'review_by_rfc_editor': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'revision_date': ('django.db.models.fields.DateField', [], {}),
            'rfc_number': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'shepherd': ('django.db.models.fields.related.ForeignKey', ["orm['idtracker.PersonOrOrgInfo']"], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['idtracker.IDStatus']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_column': "'id_document_name'"}),
            'txt_page_count': ('django.db.models.fields.IntegerField', [], {}),
            'wgreturn_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'idtracker.personororginfo': {
            'Meta': {'db_table': "'person_or_org_info'"},
            'address_type': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'first_name_key': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_name_key': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'middle_initial': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'middle_initial_key': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'name_prefix': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'name_suffix': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'person_or_org_tag': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'})
        },
        'ietfworkflows.annotationtag': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['permissions.Permission']", 'null': 'True', 'blank': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'annotation_tags'", 'to': "orm['workflows.Workflow']"})
        },
        'ietfworkflows.annotationtagobjectrelation': {
            'annotation_tag': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ietfworkflows.AnnotationTag']"}),
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'annotation_tags'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'ietfworkflows.objectannotationtaghistoryentry': {
            'objecthistoryentry_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ietfworkflows.ObjectHistoryEntry']", 'unique': 'True', 'primary_key': 'True'}),
            'setted': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'unsetted': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'ietfworkflows.objecthistoryentry': {
            'comment': ('django.db.models.fields.TextField', [], {}),
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_history'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['idtracker.PersonOrOrgInfo']"})
        },
        'ietfworkflows.objectstreamhistoryentry': {
            'from_stream': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'objecthistoryentry_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ietfworkflows.ObjectHistoryEntry']", 'unique': 'True', 'primary_key': 'True'}),
            'to_stream': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'ietfworkflows.objectworkflowhistoryentry': {
            'from_state': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'objecthistoryentry_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ietfworkflows.ObjectHistoryEntry']", 'unique': 'True', 'primary_key': 'True'}),
            'to_state': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ietfworkflows.statedescription': {
            'definition': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['workflows.State']"})
        },
        'ietfworkflows.stateobjectrelationmetadata': {
            'estimated_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'from_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['workflows.StateObjectRelation']"})
        },
        'ietfworkflows.stream': {
            'document_group_attribute': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'group_chair_attribute': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ietfworkflows.WGWorkflow']"})
        },
        'ietfworkflows.streamedid': {
            'draft': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['idtracker.InternetDraft']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stream': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ietfworkflows.Stream']", 'null': 'True', 'blank': 'True'})
        },
        'ietfworkflows.wgworkflow': {
            'selected_states': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['workflows.State']", 'null': 'True', 'blank': 'True'}),
            'selected_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ietfworkflows.AnnotationTag']", 'null': 'True', 'blank': 'True'}),
            'workflow_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['workflows.Workflow']", 'unique': 'True', 'primary_key': 'True'})
        },
        'permissions.permission': {
            'codename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'content_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'workflows.state': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'transitions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['workflows.Transition']", 'null': 'True', 'blank': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'states'", 'to': "orm['workflows.Workflow']"})
        },
        'workflows.stateobjectrelation': {
            'Meta': {'unique_together': "(('content_type', 'content_id', 'state'),)"},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'state_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['workflows.State']"})
        },
        'workflows.transition': {
            'condition': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'destination_state'", 'null': 'True', 'to': "orm['workflows.State']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['permissions.Permission']", 'null': 'True', 'blank': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'transitions'", 'to': "orm['workflows.Workflow']"})
        },
        'workflows.workflow': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_state'", 'null': 'True', 'to': "orm['workflows.State']"}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['permissions.Permission']", 'symmetrical': 'False'})
        }
    }
    
    complete_apps = ['ietfworkflows']
