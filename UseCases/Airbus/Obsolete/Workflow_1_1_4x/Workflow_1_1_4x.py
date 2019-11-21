import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/commit'])
from mupif import *
import Pyro4
import logging
log = logging.getLogger()
import time as timeT
import mupif.Physics.PhysicalQuantities as PQ

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
comsolJobManName = 'Mupif.JobManager@INSA'
vpsJobManName='ESI_VPS_Jobmanager'

class Workflow_1_1_4x(Workflow.Workflow):
   
    def __init__(self, targetTime=PQ.PhysicalQuantity('0 s')):
        """
        Initializes the workflow. As the workflow is non-stationary, we allocate individual 
        applications and store them within a class.
        """
        super(Workflow_1_1_4x, self).__init__(file='', workdir='', targetTime=targetTime)
        
        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_ESI_VPS_PLY1_E0c1, PropertyID.PID_ESI_VPS_PLY1_E0t2, PropertyID.PID_ESI_VPS_PLY1_E0t3,PropertyID.PID_ESI_VPS_PLY1_G012,PropertyID.PID_ESI_VPS_PLY1_G013,PropertyID.PID_ESI_VPS_PLY1_G023,PropertyID.PID_ESI_VPS_PLY1_NU12,PropertyID.PID_ESI_VPS_PLY1_NU13,PropertyID.PID_ESI_VPS_PLY1_NU23]
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_ESI_VPS_BUCKL_LOAD]

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
      
        #connect to comsol JobManager running on (remote) server
        self.comsolJobMan = PyroUtil.connectJobManager(ns, comsolJobManName,hkey)
        
        #connect to vps JobManager running on (remote) server
        self.vpsJobMan = PyroUtil.connectJobManager(ns, vpsJobManName,hkey)

        # solvers
        self.comsolSolver = None
        self.vpsSolver = None
        try:
            self.comsolSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.comsolJobMan, None, hkey)
            log.info('Created comsol job')
            self.vpsSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.vpsJobMan, None, hkey)
            log.info('Created vps job')            
        except Exception as e:
            log.exception(e)
        else:
            if ((self.comsolSolver is not None) and (self.vpsSolver is not None)):
                comsolSolverSignature=self.comsolSolver.getApplicationSignature()
                log.info("Working comsol solver on server " + comsolSolverSignature)
                vpsSolverSignature=self.vpsSolver.getApplicationSignature()
                log.info("Working vps solver on server " + vpsSolverSignature)
            else:
                log.debug("Connection to server failed, exiting")


    def setProperty(self, property, objectID=0):
        propID = property.getPropertyID()
        if (propID in self.myInputPropIDs):
            self.myInputProps[propID]=property
        else:
            raise APIError.APIError('Unknown property ID')

    def getProperty(self, propID, time, objectID=0):
        if (propID in self.myOutPropIDs):
            return self.myOutProps[propID]
        else:
            raise APIError.APIError ('Unknown property ID', propID)   

    def solveStep(self, istep, stageID=0, runInBackground=False):

        for cID in self.myCompulsoryPropIDs:
            if cID not in self.myInputProps:
                raise APIError.APIError (self.getApplicationSignature(), ' Missing compulsory property ', cID)   

       
        try:
            # solve comsol part
            log.info("Running comsol")
            self.comsolSolver.solveStep(None)
            ## get the desired properties
            # get domain number to filter tooling
            self.domainNumber = self.comsolSolver.getField(FieldID.FID_DomainNumber,0,0)
            ## get fibre orientation for four different layers, already on filtered domain (no toling)
            self.fibreOrientation0 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,1), self.domainNumber, 1.0)
	    self.fibreOrientation90 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,2), self.domainNumber, 1.0)
	    self.fibreOrientation45 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,3), self.domainNumber, 1.0)
	    self.fibreOrientation_45 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,4), self.domainNumber, 1.0)
	    
            
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()    

            
            
        try:
            # Young modulus
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_E0c1])
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_E0t2])
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_E0t3])
            # Shear modulus
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_G012])
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_G013])
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_G023]) 
            # Poisson ratio
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_NU12])
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_NU13])
            self.vpsSolver.setProperty(self.myInputProps[PropertyID.PID_ESI_VPS_PLY1_NU23])
            # set the field orientation, the objectID corresponds to layer angle, i.e, 0,90,45,-45
            self.vpsSolver.setField(self.fibreOrientation0,FieldID.FID_FibreOrientation,0,0)
            self.vpsSolver.setField(self.fibreOrientation90,FieldID.FID_FibreOrientation,0,90)
            self.vpsSolver.setField(self.fibreOrientation45,FieldID.FID_FibreOrientation,0,45)
            self.vpsSolver.setField(self.fibreOrientation_45,FieldID.FID_FibreOrientation,0,-45)
            
        except Exception as err:
            print ("Setting VPS params failed: " + repr(err));
            self.terminate()
            
        try:
            # solve vps part
            log.info("Running vps")
            self.vpsSolver.solveStep(None)
            ## get the desired properties
            self.myOutProps[PropertyID.PID_ESI_VPS_BUCKL_LOAD] = self.vpsSolver.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD,0)
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()



    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        self.comsolSolver.terminate()
        self.vpsSolver.terminate()
        super(Workflow_1_1_4x, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"

    
if __name__=='__main__':

    useCaseID = 1
    execID = 1
    
    workflow = Workflow_1_1_4x(targetTime=PQ.PhysicalQuantity(1.,'s'))
    # set VPS material properties
    ## Young modulus
    workflow.setProperty(Property.ConstantProperty(100, PropertyID.PID_ESI_VPS_PLY1_E0c1,  ValueType.Scalar, 'MPa', None, 0))
    workflow.setProperty(Property.ConstantProperty(100, PropertyID.PID_ESI_VPS_PLY1_E0t2, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(100, PropertyID.PID_ESI_VPS_PLY1_E0t3,  ValueType.Scalar, 'MPa', None, 0))
    # shear modulus
    workflow.setProperty(Property.ConstantProperty(50, PropertyID.PID_ESI_VPS_PLY1_G012, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(50, PropertyID.PID_ESI_VPS_PLY1_G013, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(50, PropertyID.PID_ESI_VPS_PLY1_G023, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    # Poisson ratio
    workflow.setProperty(Property.ConstantProperty(0.2,     PropertyID.PID_ESI_VPS_PLY1_NU12, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(0.2,     PropertyID.PID_ESI_VPS_PLY1_NU13, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(0.2,     PropertyID.PID_ESI_VPS_PLY1_NU23, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))

    
    # set useCaseID and ExecID 
    workflow.setMetadata(MetadataKeys.UseCaseID, useCaseID)
    workflow.setMetadata(MetadataKeys.ExecID, execID)
    workflow.solve()
    time = PQ.PhysicalQuantity(1.0, 's')


    # collect vpn outputs
    bucklingLoad = workflow.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD, time).inUnitsOf('N').getValue()

    print ('OK')
