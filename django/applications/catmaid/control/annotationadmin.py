from django import forms
from django.conf import settings
from django.contrib.formtools.wizard.views import SessionWizardView
from django.db import connection
from django.shortcuts import render_to_response

from catmaid.models import Class, ClassInstance, ClassInstanceClassInstance
from catmaid.models import Connector, Project, Relation, Treenode

SOURCE_TYPE_CHOICES = [
    ('file', 'Local file'),
    ('project', 'CATMAID project'),
]

IMPORT_TEMPLATES = {
    "sourcetypeselection": "catmaid/import/annotations/setup_source.html",
    "projectimport": "catmaid/import/annotations/setup.html",
    "fileimport": "catmaid/import/annotations/setup.html",
    "confirmation": "catmaid/import/annotations/confirmation.html",
    "done": "catmaid/import/annotations/done.html",
}


class SourceTypeForm(forms.Form):
    """ A form to select basic properties on the data to be
    imported.
    """
    source_type = forms.ChoiceField(choices=SOURCE_TYPE_CHOICES,
            widget=forms.RadioSelect(), help_text="The source type defines "
            "where the data to import comes from")
    target_project = forms.ModelChoiceField(required=True,
        help_text="The project the data will be imported into.",
        queryset=Project.objects.all().exclude(pk=settings.ONTOLOGY_DUMMY_PROJECT_ID))
    import_treenodes = forms.BooleanField(initial=True, required=False,
            help_text="Should treenodes be imported?")
    import_connectors = forms.BooleanField(initial=True, required=False,
            help_text="Should connectors be imported?")
    import_annotations = forms.BooleanField(initial=True, required=False,
            help_text="Should neuron annotations be imported?")
    import_tags = forms.BooleanField(initial=True, required=False,
            help_text="Should neuron node tags be imported?")


class FileBasedImportForm(forms.Form):
    pass


class ProjectBasedImportForm(forms.Form):
    """ Display a list of available projects."""
    projects = forms.ModelMultipleChoiceField(required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'autoselectable'}),
        help_text="Only data from selected projects will be imported.",
        queryset=Project.objects.all().exclude(pk=settings.ONTOLOGY_DUMMY_PROJECT_ID))

    # TODO: check administer or super user permissions for validation


class ConfirmationForm(forms.Form):
    """ Displays a summary of the data to be imported.
    """
    pass

def get_source_type(wizard):
    """ Test whether the project import form should be shown."""
    cleaned_data = wizard.get_cleaned_data_for_step('sourcetypeselection') \
        or {'source_type': SOURCE_TYPE_CHOICES[0]}
    return cleaned_data['source_type']

class ImportingWizard(SessionWizardView):
    """ With the help of the importing wizard it is possible to import neurons
    and their annotations as well as the linked skeletons and their treenodes
    and tags into an existing CATMAID project. The source for this data can
    either be a file or another project. Users can only be carried over if the
    source is another project in the target instance. Otherwise, the importing
    user gets ownership on all model objects.
    """
    form_list = [
        ("sourcetypeselection", SourceTypeForm),
        ("projectimport", ProjectBasedImportForm),
        ("fileimport", FileBasedImportForm),
        ("confirmation", ConfirmationForm),
    ]

    # Either file or project import form will be shown
    condition_dict = {
        'fileimport': lambda w: get_source_type(w) == 'file',
        'projectimport': lambda w: get_source_type(w) == 'project',
    }

    def get_context_data(self, form, **kwargs):
        """ On the confirmation step, this will read in the data to import and
        collect some statistics on it.
        """
        context = super(ImportingWizard, self).get_context_data(form=form, **kwargs)
        if self.steps.current == 'confirmation':
            stats = []
            # Load all wanted information from the selected projects
            scd = self.get_cleaned_data_for_step('sourcetypeselection')
            if scd["source_type"] == 'project':
                projects = self.get_cleaned_data_for_step('projectimport')['projects']
                for p in projects:
                    ps = {
                        'source': "%s (%s)" % (p.title, p.id),
                        'ntreenodes': 0,
                        'nconnectors': 0,
                        'nannotations': 0,
                        'nannotationlinks': 0,
                        'ntags': 0,
                    }
                    if scd['import_treenodes']:
                        ps['ntreenodes'] = Treenode.objects.filter(project=p).count();
                    if scd['import_connectors']:
                        ps['nconnectors'] = Connector.objects.filter(project=p).count();
                    if scd['import_annotations']:
                        annotation = Class.objects.filter(project=p,
                                class_name="annotation")
                        annotated_with = Relation.objects.filter(project=p,
                                relation_name="annotated_with")
                        ps['nannotations'] = ClassInstance.objects.filter(
                                project=p, class_column=annotation).count()
                        ps['nannotationlinks'] = ClassInstanceClassInstance.objects.filter(
                                project=p, relation=annotated_with).count()
                    if scd['import_tags']:
                        pass

                    stats.append(ps)

            # Update context
            context.update({
                'source_type': scd["source_type"],
                'stats': stats,
            })

        return context

    def get_template_names(self):
        return [IMPORT_TEMPLATES[self.steps.current]]

    def done(self, form_list, **kwargs):
        """ All previously configured sources will now be used to import data.
        """
        # Load all wanted information from the selected projects
        scd = self.get_cleaned_data_for_step('sourcetypeselection')
        target_project = scd['target_project']

        if scd["source_type"] == 'project':
            # Use raw SQL to duplicate the rows, because there is no
            # need to transfer the data to Django and back to Postgres
            # again.
            cursor = connection.cursor()
            projects = self.get_cleaned_data_for_step('projectimport')['projects']
            for p in projects:
                # For every project the
                if scd['import_treenodes']:
                    cursor.execute('''
                        INSERT INTO treenode (project_id, location_x,
                            location_y, location_z, editor_id, user_id,
                            creation_time, edition_time, skeleton_id,
                            radius, confidence, parent_id)
                        SELECT %s, location_x, location_y, location_z,
                            editor_id, user_id, creation_time, edition_time,
                            skeleton_id, radius, confidence, parent_id
                        FROM treenode tn
                        WHERE tn.project_id=%s
                        ''', (target_project.id, p.id))
                if scd['import_connectors']:
                    cursor.execute('''
                        INSERT INTO connector (project_id, location_x,
                            location_y, location_z, editor_id, user_id,
                            creation_time, edition_time,  confidence)
                        SELECT %s, location_x, location_y, location_z,
                            editor_id, user_id, creation_time, edition_time,
                            confidence
                        FROM connector cn
                        WHERE cn.project_id=%s
                        ''', (target_project.id, p.id))
                if scd['import_annotations']:
                    pass
                if scd['import_tags']:
                    pass

        return render_to_response(IMPORT_TEMPLATES['done'])


class ExportingWizard(SessionWizardView):
    """ The export wizard makes it possible to export neurons and their
    annotations as well as the linked skeletons and their treenodes into a JSON
    representation.
    """
    pass