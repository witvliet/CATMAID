from django.core.management.base import NoArgsCommand, CommandError
from optparse import make_option

from catmaid.models import *

class Command(NoArgsCommand):
    help = 'Set up the required database entries for annotating neurons in a project'

    option_list = NoArgsCommand.option_list + (
        make_option('--project', dest='project_id', help='The ID of the project to setup annotation classes for'),
        make_option('--user', dest='user_id', help='The ID of the user who will own the relations and classes'),
        )

    def handle_noargs(self, **options):

        if not (options['project_id'] and options['user_id']):
            raise CommandError("You must specify both --project and --user")

        project = Project.objects.get(pk=options['project_id'])
        user = User.objects.get(pk=options['user_id'])

        annotation_ontology = {
            'GAL4 line': ['GMR_94F01_AE_01', 'GMR_20B01_AE_01'],
            'segment': [ 'T1', 'T2', 'T3', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'Protocerebrum', 'Deuterocerebrum', 'Tritocerebrum', 'Labial', 'Maxillar', 'Mandibular' ],
            'region': ['Brain', 'SOG', 'Thorax', 'Abdomen'],
            'compartment': ['Antennal lobe', 'Optic lobe'],
            'nerve': ['ISNa', 'ISNp', 'SN', 'Bolwigs nerve', 'Antennal nerve'],
            'neuron_name' : ['A09b'],
            'lineage': ['%02d' % i for i in xrange(33)],
            'neuron_type': ['sensory neuron', 'motor neuron', 'interneuron'],
            'status': ['TODO', 'draft', 'reviewed', 'finalized'],
        }

        # Create the classes first:
        class_dictionary = {}
        for required_class in annotation_ontology.keys():
            class_object, _ = Class.objects.get_or_create(
                class_name=required_class,
                project=project,
                defaults={'user': user})
            class_dictionary[required_class] = class_object

        # Create instances if they do not yet exist
        # Make sure that a root node exists:
        for k,v in annotation_ontology.items():
            for instance_element in v:
                ClassInstance.objects.get_or_create(
                    class_column=class_dictionary[k],
                    project=project,
                    user=user,
                    name=instance_element)

        # Now also create the annotation relation:
        for relation_required in ["annotated_with"]:
            Relation.objects.get_or_create(
                relation_name=relation_required,
                project=project,
                defaults={'user': user})

