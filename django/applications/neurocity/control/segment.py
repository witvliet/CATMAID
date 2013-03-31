from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import numpy as np
import os, os.path
from contextlib import closing
import h5py
import random

from catmaid.models import *
from catmaid.objects import *
from catmaid.control.authentication import *
from catmaid.control.common import *

try:
    from PIL import Image
except:
    pass

def get_segment_image(request):

    project_id = 11
    stack_id = 15
    scale = 0
    xboundary = 20
    yboundary = 20
    spacing = 40

    segmentid = request.GET.get('segmentid', '0')
    sectionindex = int(request.GET.get('sectionindex', '0'))
    sliceid = int(request.GET.get('sliceid', '0'))

    stack = get_object_or_404(Stack, pk=stack_id)
    p = get_object_or_404(Project, pk=project_id)

    fpath=os.path.join( settings.HDF5_STORAGE_PATH, '{0}_{1}_raw.hdf'.format( project_id, stack_id) )

    segments = Segments.objects.filter(
            stack = stack,
            project = p,
            randomforest_cost__lt = 0.5).all()[:100]

    # TODO: intelligent sampling of the segments
    segment = random.choice( segments ) #segments[0]
    print 'segment selected', segment.segmentid, segment.id

    if segment.segmenttype == 2:
        origin_slice = Slices.objects.get(
            stack = stack,
            project = p,
            node_id = str(segment.origin_section) + '_' + str(segment.origin_slice_id) )

        target_slice = Slices.objects.get(
            stack = stack,
            project = p,
            node_id = str(segment.target_section) + '_' + str(segment.target1_slice_id) )
        print 'target slice', target_slice
    else:
        return

    sliceinfo = StackSliceInfo.objects.get(stack=stack)

    def slice_parameters( slice ):
        width = slice.max_x - slice.min_x 
        height = slice.max_y - slice.min_y
        x = slice.min_x
        y = slice.min_y
        z = slice.sectionindex
        x -= xboundary        
        width += 2*xboundary
        y -= yboundary
        height += 2*yboundary
    
        fnametuple = tuple(str(slice.slice_id))
        fname = fnametuple[-1] + '.' + sliceinfo.file_extension
        fpathslice = fnametuple[:-1]
        slice_path = os.path.join( 
            str(sliceinfo.slice_base_path).rstrip('\n'), 
            str(slice.sectionindex), 
            '/'.join(fpathslice),
            fname )

        if os.path.exists( slice_path ):
            pic = Image.open( slice_path )
            pix = np.array(pic.getdata()).reshape(pic.size[1], pic.size[0], 2)
            pix = pix[:,:,0]
            pixarr = np.zeros( (height,width), dtype = np.uint8 )
            pixarr[yboundary:yboundary+pix.shape[0],xboundary:xboundary+pix.shape[1]] = pix

        with closing(h5py.File(fpath, 'r')) as hfile:
            hdfpath = '/' + str(int(scale)) + '/' + str(z) + '/data'
            image_data=hfile[hdfpath]
            yends = y+height
            xends = x+width
            if yends > image_data.shape[0]:
                yends = image_data.shape[0]
            if xends > image_data.shape[1]:
                xends = image_data.shape[1]
            if x < 0: x = 0
            if y < 0: y = 0
            data=image_data[y:yends,x:xends]
            mask = pixarr[:,:] == 255
            data[mask] = 100
            pilImage = Image.frombuffer('RGBA',(width,height),data,'raw','L',0,1)

        return pilImage
        # return x,y,slice.sectionindex,width,height,pixarr
    
    # x,y,z,width,height,pixarr = slice_parameters( origin_slice )
    # x,y,z,width,height,pixarr = slice_parameters( target_slice )

    origin_img = slice_parameters( origin_slice )
    target_img = slice_parameters( target_slice )

    bigwidth = origin_img.size[0] + spacing + target_img.size[0]
    bigheight = max( origin_img.size[1], target_img.size[1] )
    print 'bigheight', bigheight, 'bigwidth', bigwidth

    result_img = Image.new('RGBA', (bigheight, bigwidth) )
    result_img.paste( origin_img, (0, 0))
    result_img.paste( target_img, (0, origin_img.size[0] + spacing))
    #origin_img = origin_img.resize( (400, 400) )

    


    response = HttpResponse(mimetype="image/png")
    result_img.save(response, "PNG")
    return response
