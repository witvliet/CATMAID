import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import connection

from catmaid.control.authentication import *
from catmaid.control.common import *

import operator
from collections import defaultdict

@requires_user_role([UserRole.Annotate, UserRole.Browse])
def get_all_annotations_of_neuron(request, project_id=None, neuron_id=None):
    p = get_object_or_404(Project, pk=project_id)
    neuron = get_object_or_404(ClassInstance,
        pk=neuron_id,
        class_column__class_name='neuron',
        project=p)
    qs = ClassInstance.objects.filter(
        project=p,
        cici_via_a__relation__relation_name='annotated_with',
        cici_via_a__class_instance_b=neuron)
    return HttpResponse(json.dumps([x.id for x in qs]), mimetype="text/json")


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def create_neuron_annotation(request, project_id=None):
    p = get_object_or_404(Project, pk=project_id)

    neuron_id = int(request.POST.get('neuron_id', 0))
    class_instance_id = int(request.POST.get('class_instance_id', 0))

    neuron = get_object_or_404(ClassInstance,
        pk=neuron_id, project=p)

    annotation = get_object_or_404(ClassInstance,
        pk=class_instance_id, project=p)

    annotation_relation = Relation.objects.filter(relation_name='annotated_with', project=p)[0]

    cici = ClassInstanceClassInstance()
    cici.user = request.user
    cici.project = p
    cici.relation = annotation_relation
    cici.class_instance_a = annotation
    cici.class_instance_b = neuron
    cici.save()

    return HttpResponse(json.dumps({'message': 'Created new annotation for neuron.'}), mimetype="text/json")


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def get_all_annotations(request, project_id=None):
    p = get_object_or_404(Project, pk=project_id)

    annotation_classes = Class.objects.filter(project=p).exclude(class_name__in=['root', 'neuron', 'skeleton', 'group',
     'assembly', 'label', 'classification_root', 'classification_project']).values('class_name', 'id')

    annotation_class_ids = [s['id'] for s in annotation_classes]

    annotation_instances = ClassInstance.objects.filter(
        project=p,
        class_column__in=annotation_class_ids).values('class_column', 'name', 'id')

    print 'annotation_instances', annotation_instances

    annotation_instances_map = {}
    for annotation_instance in annotation_instances:
        if not annotation_instance['class_column'] in annotation_instances_map:
            annotation_instances_map[ annotation_instance['class_column'] ] = {
                'instance_names': [],
                'instance_ids': []
            }
        annotation_instances_map[ annotation_instance['class_column'] ]['instance_names'].append(
            annotation_instance['name'])
        annotation_instances_map[ annotation_instance['class_column'] ]['instance_ids'].append(
            annotation_instance['id'])

    result = {'annotations':[]}
    for annotation_class in annotation_classes:
        result['annotations'].append(
            {
                'classname': annotation_class['class_name'],
                'class_id': annotation_class['id'],
                'instance_names': annotation_instances_map[ annotation_class['id'] ]['instance_names'],
                'instance_ids': annotation_instances_map[ annotation_class['id'] ]['instance_ids']
            })

    return HttpResponse(json.dumps(result), mimetype="text/json")
