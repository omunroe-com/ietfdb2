class LegacyRouter(object):
    def db_for_read(self, model, **hints):
        if model._meta.db_table in legacy_tables:
            return 'legacy'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.db_table in legacy_tables:
            raise Exception("You can't write to the legacy table %s" % model._meta.db_table)
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (obj1._meta.db_table in legacy_tables) != (obj2._meta.db_table in legacy_tables):
            return False
        return None

    def allow_syncdb(self, db, model):
        if db == 'legacy':
            return False
        if model._meta.db_table in legacy_tables:
            return False
        return None

legacy_tables = set((
    "acronym",
    "agenda_cat",
    "agenda_items",
    "all_id",
    "announced_from",
    "announced_to",
    "announcements",
    "area_directors",
    "area_group",
    "area_status",
    "areas",
    "ballot_info",
    "ballots",
    "ballots_comment",
    "ballots_discuss",
    "bash_agenda",
    "chairs",
    "chairs_history",
    "document_comments",
    "draft_versions_mirror",
    "dt_request",
    "email_addresses",
    "from_bodies",
    "g_chairs",
    "g_editors",
    "g_secretaries",
    "g_secretary",
    "g_status",
    "g_tech_advisors",
    "g_type",
    "general_info",
    "goals_milestones",
    "group_flag",
    "group_internal",
    "groups_ietf",
    "hit_counter",
    "id_approved_detail",
    "id_authors",
    "id_dates",
    "id_intended_status",
    "id_internal",
    "id_restricted_word",
    "id_status",
    "id_submission_detail",
    "id_submission_env",
    "id_submission_status",
    "idst_users",
    "iesg_history",
    "iesg_login",
    "iesg_password",
    "ietfauth_ietfuserprofile",
    "ietfauth_usermap",
    "ietfworkflows_annotationtag",
    "ietfworkflows_annotationtagobjectrelation",
    "ietfworkflows_objectannotationtaghistoryentry",
    "ietfworkflows_objecthistoryentry",
    "ietfworkflows_objectstreamhistoryentry",
    "ietfworkflows_objectworkflowhistoryentry",
    "ietfworkflows_statedescription",
    "ietfworkflows_stateobjectrelationmetadata",
    "ietfworkflows_stream",
    "ietfworkflows_streamdelegate",
    "ietfworkflows_streamedid",
    "ietfworkflows_wgworkflow",
    "ietfworkflows_wgworkflow_selected_states",
    "ietfworkflows_wgworkflow_selected_tags",
    "imported_mailing_list",
    "interim_info",
    "interim_meetings_acronym",
    "interim_meetings_groups_ietf",
    "interim_meetings_interim_info",
    "interim_meetings_interim_new",
    "interim_meetings_meetings",
    "interim_meetings_minutes",
    "interim_meetings_slides",
    "internet_drafts",
    "ipr_contacts",
    "ipr_detail",
    "ipr_ids",
    "ipr_licensing",
    "ipr_notifications",
    "ipr_rfcs",
    "ipr_selecttype",
    "ipr_updates",
    "irtf",
    "irtf_chairs",
    "liaison_detail",
    "liaison_detail_temp",
    "liaison_managers",
    "liaison_purpose",
    "liaisons_interim",
    "liaisons_members",
    "liaisons_outgoingliaisonapproval",
    "liaisons_sdoauthorizedindividual",
    "lists_email",
    "lists_email_refs",
    "lists_list",
    "mailing_list",
    "mailinglists_domain",
    "mailinglists_domain_approvers",
    "management_issues",
    "meeting_agenda_count",
    "meeting_attendees",
    "meeting_conflict",
    "meeting_conflict_groups",
    "meeting_hours",
    "meeting_rooms",
    "meeting_sessionstatusname",
    "meeting_times",
    "meeting_venues",
    "meetings",
    "messages",
    "migrate_stat",
    "minutes",
    "nomcom",
    "nomcom_members",
    "non_session",
    "non_session_ref",
    "none_wg_mailing_list",
    "not_meeting_groups",
    "old_document_comments",
    "outstanding_tasks",
    "permissions_objectpermission",
    "permissions_objectpermissioninheritanceblock",
    "permissions_permission",
    "permissions_permission_content_types",
    "permissions_principalrolerelation",
    "permissions_role",
    "person_or_org_info",
    "phone_numbers",
    "postal_addresses",
    "print_name",
    "prior_address",
    "proceedings",
    "pwg_cat",
    "ref_doc_states_new",
    "ref_next_states_new",
    "ref_resp",
    "replaced_ids",
    "request",
    "rfc_authors",
    "rfc_editor_queue_mirror",
    "rfc_editor_queue_mirror_refs",
    "rfc_index_mirror",
    "rfc_intend_status",
    "rfc_status",
    "rfcs",
    "rfcs_obsolete",
    "roll_call",
    "scheduled_announcements",
    "scheduled_announcements_temp",
    "sdo_chairs",
    "sdos",
    "secretariat_staff",
    "session_conflicts",
    "session_names",
    "session_request_activities",
    "session_status",
    "slide_types",
    "slides",
    "staff_work_detail",
    "staff_work_history",
    "sub_state",
    "switches",
    "task_status",
    "telechat",
    "telechat_dates",
    "telechat_minutes",
    "telechat_users",
    "temp_admins",
    "temp_agenda71166",
    "temp_id_authors",
    "temp_telechat_attendees",
    "temp_txt",
    "templates",
    "updated_ipr",
    "uploads",
    "uploads_temp",
    "users",
    "web_gm_chairs",
    "web_login_info",
    "web_user_info",
    "wg_agenda",
    "wg_meeting_sessions",
    "wg_meeting_sessions_temp",
    "wg_password",
    "wg_proceedings_activities",
    "wg_www_pages",
    "wgchairs_protowriteup",
    "wgchairs_wgdelegate",
    "workflows_state",
    "workflows_state_transitions",
    "workflows_stateinheritanceblock",
    "workflows_stateobjectrelation",
    "workflows_statepermissionrelation",
    "workflows_transition",
    "workflows_workflow",
    "workflows_workflowmodelrelation",
    "workflows_workflowobjectrelation",
    "workflows_workflowpermissionrelation",
))

