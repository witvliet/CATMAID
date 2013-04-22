from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import numpy as np
import os, os.path
from contextlib import closing
import h5py
import random
import time

from catmaid.models import *
from catmaid.objects import *
from catmaid.control.authentication import *
from catmaid.control.common import *

try:
    from PIL import Image
except:
    pass

# change roles; prevent random vote requests (how?)
# @requires_user_role([UserRole.Annotate, UserRole.Browse])
def segment_vote(request):

    project_id = 11
    stack_id = 15

    project = get_object_or_404(Project, pk=project_id)
    stack = get_object_or_404(Stack, pk=stack_id)

    segmentkey = int(request.POST.get('segmentkey', -1))
    vote = int(request.POST.get('vote', -1))
    comment = request.POST.get('comment', None)

    if segmentkey == -1:
        return HttpResponse(json.dumps({'error':'Invalid segmentkey'}), mimetype='text/json')
    else:
        segment = Segments.objects.get(pk=segmentkey)

    if vote == -1 or not vote in [1,2,3]:
        return HttpResponse(json.dumps({'error':'Invalid vote'}), mimetype='text/json')
    
    # TODO: increase nr_votes for segment
    # segment.update(...)

    sv = SegmentVote()
    sv.user = request.user
    sv.project = project
    sv.stack = stack
    sv.vote = vote
    sv.segment = segment
    sv.save()

    if not comment is None and len(comment) > 0:
        sc = SegmentComment()
        sc.user = request.user
        sc.project = project
        sc.stack = stack
        sc.segmentvote = sv
        sc.comment = comment
        sc.save()

    return HttpResponse(json.dumps({'message':'Voted'}), mimetype='text/json')


def get_segment_sequence():
    """ Sampling from the data volume """

    segments = Segments.objects.filter(
            stack = stack,
            project = p,
            randomforest_cost__lt = 0.5).all()[:100]

    # TODO: intelligent sampling of the segments
    segment = random.choice( segments ) #segments[0]
    print 'segment selected', segment.segmentid, segment.id

    return segment

def get_random_segment():

    project_id = 11
    stack_id = 15

    stack = get_object_or_404(Stack, pk=stack_id)
    project = get_object_or_404(Project, pk=project_id)

    segments = Segments.objects.filter(
            stack = stack,
            project = project,
            randomforest_cost__lt = 5.0).all()[:70]

    # TODO: intelligent sampling of the segments
    segment = random.choice( segments ) # random.choice( segments ) #segments[0]
    # print 'segment selected', segment.origin_section, segment.target_section, segment.segmentid
    return segment

def get_segment( project, stack, origin_section, target_section, segment_id ):
    """ TODO: add segment node_id column to database """
    segments = Segments.objects.filter(
            stack = stack,
            project = project,
            origin_section = origin_section,
            target_section = target_section,
            segmentid = segment_id ).all()
    if len(segments) == 0:
        return None
    else:
        return segments[0] # what if more than one found?

def slice_path( node_id, sliceinfo ):
    sectionindex, slice_id = node_id.split('_')
    fnametuple = tuple(str(slice_id))
    fname = fnametuple[-1] + '.' + sliceinfo.file_extension
    fpathslice = fnametuple[:-1]
    slice_path_local = os.path.join( 
        str(sliceinfo.slice_base_path).rstrip('\n'), 
        str(sectionindex), 
        '/'.join(fpathslice),
        fname )
    return slice_path_local

def slice_path2( node_id, sliceinfo ):
    sectionindex, slice_id = node_id.split('_')
    fnametuple = tuple(str(slice_id))
    fname = fnametuple[-1] + '.' + sliceinfo.file_extension
    fpathslice = fnametuple[:-1]
    slice_path_url = os.path.join( 
        str(sliceinfo.slice_base_url).rstrip('\n'), 
        str(sectionindex), 
        '/'.join(fpathslice),
        fname )
    return slice_path_url

def get_segment_boundingbox(request):

    project_id = 11
    stack_id = 15

    stack = get_object_or_404(Stack, pk=stack_id)
    project = get_object_or_404(Project, pk=project_id)
    sliceinfo = StackSliceInfo.objects.get(stack=stack)

    segmentid = request.GET.get('segmentid', '0')
    originsection = int(request.GET.get('originsection', '0'))
    targetsection = int(request.GET.get('targetsection', '0'))
    edge = int(request.GET.get('edge', '0'))

    segment = get_segment( project, stack, originsection, targetsection, segmentid )

    slice_node_ids = [ str(segment.origin_section) + '_' + str(segment.origin_slice_id) ]
    sections = [ segment.origin_section ]
    if segment.segmenttype == 2:
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target1_slice_id) )
        sections.append( segment.target_section )
        slicelist = [0] if edge == 0 else [1]
    elif segment.segmenttype == 3:
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target1_slice_id) )
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target2_slice_id) )
        sections.append( segment.target_section )
        sections.append( segment.target_section )
        slicelist = [0] if edge == 0 else [1,2]

    slices = Slices.objects.filter(
        stack = stack,
        project = project,
        node_id__in = slice_node_ids )

    # find maximal bounding box across all slices
    min_x, min_y, max_x, max_y = slices[0].min_x, slices[0].min_y, slices[0].max_x, slices[0].max_y
    originsection = [{
            'min_x': slices[0].min_x, 'max_x': slices[0].max_x,
            'min_y': slices[0].min_y, 'max_y': slices[0].max_y,
            'slicepath': slice_path2( slices[0].node_id, sliceinfo ),
            'width': slices[0].max_x - slices[0].min_x,
            'height': slices[0].max_y - slices[0].min_y }]

    targetsection = []
    for slice in slices[1:]:
        min_x = min(min_x, slice.min_x)
        min_y = min(min_y, slice.min_y)
        max_x = max(max_x, slice.max_x)
        max_y = max(max_y, slice.max_y)
        targetsection.append({
            'min_x': slice.min_x, 'max_x': slice.max_x,
            'min_y': slice.min_y, 'max_y': slice.max_y,
            'slicepath': slice_path2( slice.node_id, sliceinfo ),
            'width': slice.max_x - slice.min_x,
            'height': slice.max_y - slice.min_y })

    totalbb = {
            'min_x': min_x, 'max_x': max_x,
            'min_y': min_y, 'max_y': max_y,
            'width': max_x - min_x,
            'height': max_y - min_y }

    return HttpResponse(json.dumps({
        'segmenttype': segment.segmenttype,
        'originsection': originsection,
        'targetsection': targetsection,
        'totalbb': totalbb,
        'tile_width': stack.tile_width,
        'tile_height': stack.tile_height 
    }), mimetype="text/json")


def get_segment_image(request):

    project_id = 11
    stack_id = 15
    scale = 0
    xboundary = 20
    yboundary = 20
    spacing = 40
    border = 0
    edge = 0
    only_raw = False
    segment_node_id = '5_10'

    stack = get_object_or_404(Stack, pk=stack_id)
    project = get_object_or_404(Project, pk=project_id)
    fpath = os.path.join( settings.HDF5_STORAGE_PATH, '{0}_{1}_raw.hdf'.format( project_id, stack_id) )
    sliceinfo = StackSliceInfo.objects.get(stack=stack)

    segmentid = request.GET.get('segmentid', '0')
    originsection = int(request.GET.get('originsection', '0'))
    targetsection = int(request.GET.get('targetsection', '0'))
    edge = int(request.GET.get('edge', '0'))

    # retrieve segment
    segment = get_segment( project, stack, originsection, targetsection, segmentid )

    if segment is None:
        result_img = Image.fromarray(np.random.random_integers(0, 255, (512,512)).astype(np.uint8) )
        response = HttpResponse(mimetype="image/png")
        result_img.save(response, "PNG")
        return response

    # retrieve associated slices
    ts = time.time()
    slice_node_ids = [ str(segment.origin_section) + '_' + str(segment.origin_slice_id) ]
    sections = [ segment.origin_section ]
    if segment.segmenttype == 2:
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target1_slice_id) )
        sections.append( segment.target_section )
        slicelist = [0] if edge == 0 else [1]
    elif segment.segmenttype == 3:
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target1_slice_id) ,
            str(segment.target_section) + '_' + str(segment.target2_slice_id) )
        sections.append( segment.target_section )
        sections.append( segment.target_section )
        slicelist = [0] if edge == 0 else [1,2]

    slices = Slices.objects.filter(
        stack = stack,
        project = project,
        node_id__in = slice_node_ids )

    print 'retrieve slices', time.time() - ts
    ts = time.time()

    # find maximal bounding box across all slices
    min_x, min_y, max_x, max_y = slices[0].min_x, slices[0].min_y, slices[0].max_x, slices[0].max_y
    for slice in slices[1:]:
        min_x = min(min_x, slice.min_x)
        min_y = min(min_y, slice.min_y)
        max_x = max(max_x, slice.max_x)
        max_y = max(max_y, slice.max_y)

    # compute offsets
    offsets = []
    for slice in slices:
        offsets.append( (abs(slice.min_x - min_x), abs(slice.min_y - min_y) ) )

    width, height = max_x - min_x, max_y - min_y

    merged_image = np.zeros( (height+2*border, width+2*border, 4), dtype = np.uint8 )

    def load_raw( min_x, min_y, max_x, max_y, z ):
        with closing(h5py.File(fpath, 'r')) as hfile:
            hdfpath = '/' + str(int(scale)) + '/' + str(z) + '/data'
            image_data = hfile[hdfpath]
            print 'miny', min_y,(max_y-min_y)
            print 'minx', min_x,(max_x-min_x)
            data = image_data[min_y:min_y+(max_y-min_y),min_x:min_x+(max_x-min_x)]
        return data

    if edge == 0:
        data = load_raw( min_x-border, min_y-border, max_x+border, max_y+border, sections[0] )
    else:
        data = load_raw( min_x-border, min_y-border, max_x+border, max_y+border, sections[1] )

    print 'load raw', time.time() - ts
    ts = time.time()

    merged_image[:,:,0] = data
    merged_image[:,:,1] = data
    merged_image[:,:,2] = data
    merged_image[:,:,3] = 255

    print 'store in merged image', time.time() - ts
    ts = time.time()

    if not only_raw:
        for sliceindex in slicelist:
            if os.path.exists( slice_path( slice_node_ids[sliceindex], sliceinfo ) ):
                pic = Image.open( slice_path( slice_node_ids[sliceindex], sliceinfo ) )
                pix = np.array(pic.getdata()).reshape(pic.size[1], pic.size[0], 2)
                pix = pix[:,:,0].astype(np.uint8)
                from_y = offsets[sliceindex][1]+border
                from_x = offsets[sliceindex][0]+border
                merged_image[from_y:from_y+pix.shape[0], from_x:from_x+pix.shape[1],3] -= pix*0.7

    print 'load slicie overlay', time.time() - ts

    result_img =  Image.fromarray( merged_image ) # Image.new('RGBA', (height, width) )
    response = HttpResponse(mimetype="image/png")
    result_img.save(response, "PNG")
    return response
