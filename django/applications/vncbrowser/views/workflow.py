from django.conf import settings
from django.http import HttpResponse

from vncbrowser.views import catmaid_login_required

import sopynet
from lazyflow import graph
from lazyflow import stype
from lazyflow import operators
import numpy as np
import Image

class OpGraphCut(graph.Operator):
    name = "OpGraphCut"

    InputImage = graph.InputSlot(stype.ArrayLike) # required slot
    PottsWeight = graph.InputSlot(value = 0.2) # required with default

    OutputImage = graph.OutputSlot(stype.ArrayLike)

    def __init__(self, parent):
        graph.Operator.__init__(self,parent)
        self._configured = False

    def setupOutputs(self):
        print 'Configure OpGraphCut ...'
        # output image need to have the same shape
        self.OutputImage.meta.shape = self.InputImage.meta.shape
        self.OutputImage.meta.dtype = self.InputImage.meta.dtype
        print "OpInternal shape=%r, dtype=%r" % (self.InputImage.meta.shape,
                                           self.InputImage.meta.dtype)
        self.graphcut = sopynet.GraphCut()
        self._configured = True
        print 'Configuration Done.'

    def execute(self, slot, roi, result):
        # slot is for instance OutputImage
        if slot == self.OutputImage:

            self.graphcut.setInputImage(self.InputImage.get(roi).wait() )
            self.graphcut.setPottsWeight( self.PottsWeight.value )

            out=np.empty( self.OutputImage.meta.shape , dtype=np.float32 )
            out=self.graphcut.getOutputImage( out )

            result[roi.toSlice()] = out

        return result

def tearDown(self):
    self.graph.stopGraph()

def test_graphcut_node(self):
    print 'Output of Sopynet test ...'
    res = self.opgraphcut.OutputImage[:].wait()
    print 'OpGraphCut output image', res.shape, res.dtype, res, res.max()


@catmaid_login_required
def flow(request, **kwargs):

    #print request.session
    #if not request.session.has_attr('workflow'):
    if not request.session.has_key('graph'):
        i=Image.open('/home/stephan/Desktop/Screenshot-5.png')
        testVol = np.asarray(i).astype( np.float32 ) / 255

        # create control graph
        request.session['graph'] = graph.Graph()

        #self.oparraypiper = operators.OpArrayPiper(self.graph)
        #self.oparraypiper.Input.setValue(self.testVol)

        # self.roiOp = OpRoiTest(self.graph)
        # self.roiOp.inputs["input"].setValue(self.testVol)

        # graph cut operator
        request.session['opgraphcut'] = OpGraphCut(request.session['graph'])
        request.session['opgraphcut'].InputImage.setValue( testVol )
        request.session['opgraphcut'].PottsWeight.setValue( 0.2 )
        print 'graphcut setup done.'
        
    else:
        print 'compute output...'
        # res = self.opgraphcut.OutputImage[:].wait()
        # request.session['test1'] += 1

    #request.session['workflow'] += 1

    return HttpResponse("Setup flow" )
