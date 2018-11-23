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
digimatJobManName='eX_DigimatMF_JobManager'
vpsJobManName='ESI_VPS_Jobmanager'

class Workflow_1_1_5(Workflow.Workflow):
   
    def __init__(self, targetTime=PQ.PhysicalQuantity('0 s')):
        """
        Initializes the workflow.
        """
        super(Workflow_1_1_5, self).__init__(file='', workdir='', targetTime=targetTime)

        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_MatrixYoung, PropertyID.PID_MatrixPoisson, PropertyID.PID_InclusionYoung, PropertyID.PID_InclusionPoisson, PropertyID.PID_InclusionVolumeFraction, PropertyID.PID_InclusionAspectRatio]
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_ESI_VPS_BUCKL_LOAD, PropertyID.PID_CompositeAxialYoung, PropertyID.PID_CompositeInPlaneYoung, PropertyID.PID_CompositeInPlaneShear, PropertyID.PID_CompositeTransverseShear, PropertyID.PID_CompositeInPlanePoisson, PropertyID.PID_CompositeTransversePoisson]

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to digimat JobManager running on (remote) server
        self.digimatJobMan = PyroUtil.connectJobManager(ns, digimatJobManName,hkey)
        #connect to mult2 JobManager running on (remote) server
        self.vpsJobMan = PyroUtil.connectJobManager(ns, vpsJobManName,hkey)

        # solvers
        self.digimatSolver = None
        self.vpsSolver = None
        #allocate the Digimat remote instance
        try:
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created digimat job')
            self.vpsSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.vpsJobMan, None, hkey)
            log.info('Created vps job')            
        except Exception as e:
            log.exception(e)
        else:
            if ((self.digimatSolver is not None) and (self.vpsSolver is not None)):
                digimatSolverSignature=self.digimatSolver.getApplicationSignature()
                log.info("Working digimat solver on server " + digimatSolverSignature)
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

        # digimat
        try:
            # fixed properties - taken form the database
            self.digimatSolver.setProperty(self.myInputProps[PropertyID.PID_MatrixYoung])
            self.digimatSolver.setProperty(self.myInputProps[PropertyID.PID_MatrixPoisson])
            self.digimatSolver.setProperty(self.myInputProps[PropertyID.PID_InclusionYoung])
            self.digimatSolver.setProperty(self.myInputProps[PropertyID.PID_InclusionPoisson])
            self.digimatSolver.setProperty(self.myInputProps[PropertyID.PID_InclusionVolumeFraction])
            self.digimatSolver.setProperty(self.myInputProps[PropertyID.PID_InclusionAspectRatio])
        except Exception as err:
            print ("Setting Digimat params failed: " + repr(err));
            self.terminate()

        try:
            # solve digimat part
            log.info("Running digimat")
            self.digimatSolver.solveStep(None)
            ## get the desired properties
            self.myOutProps[PropertyID.PID_CompositeAxialYoung] = self.digimatSolver.getProperty(PropertyID.PID_CompositeAxialYoung)
            compositeAxialYoung = self.digimatSolver.getProperty(PropertyID.PID_CompositeAxialYoung)
            self.myOutProps[PropertyID.PID_CompositeInPlaneYoung] = self.digimatSolver.getProperty(PropertyID.PID_CompositeInPlaneYoung)
            compositeInPlaneYoung = self.digimatSolver.getProperty(PropertyID.PID_CompositeInPlaneYoung)
            self.myOutProps[PropertyID.PID_CompositeInPlaneShear] = self.digimatSolver.getProperty(PropertyID.PID_CompositeInPlaneShear)
            compositeInPlaneShear = self.digimatSolver.getProperty(PropertyID.PID_CompositeInPlaneShear)
            self.myOutProps[PropertyID.PID_CompositeTransverseShear] = self.digimatSolver.getProperty(PropertyID.PID_CompositeTransverseShear)
            compositeTransverseShear = self.digimatSolver.getProperty(PropertyID.PID_CompositeTransverseShear)
            self.myOutProps[PropertyID.PID_CompositeInPlanePoisson] = self.digimatSolver.getProperty(PropertyID.PID_CompositeInPlanePoisson)
            compositeInPlanePoisson = self.digimatSolver.getProperty(PropertyID.PID_CompositeInPlanePoisson)
            self.myOutProps[PropertyID.PID_CompositeTransversePoisson] = self.digimatSolver.getProperty(PropertyID.PID_CompositeTransversePoisson)
            compositeTransversePoisson = self.digimatSolver.getProperty(PropertyID.PID_CompositeTransversePoisson)
            
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()

            
        try:
            # map properties from Digimat to properties of VPS
            # Young modulus
            compositeAxialYoung.propID = PropertyID.PID_ESI_VPS_PLY1_E0c1
            compositeInPlaneYoung1 = compositeInPlaneYoung
            compositeInPlaneYoung1.propID = PropertyID.PID_ESI_VPS_PLY1_E0t2
            compositeInPlaneYoung2 = compositeInPlaneYoung
            compositeInPlaneYoung2.propID = PropertyID.PID_ESI_VPS_PLY1_E0t3
            # Shear modulus
            compositeInPlaneShear.propID = PropertyID.PID_ESI_VPS_PLY1_G012
            compositeTransverseShear1 = compositeTransverseShear
            compositeTransverseShear1.propID = PropertyID.PID_ESI_VPS_PLY1_G013
            compositeTransverseShear2 = compositeTransverseShear
            compositeTransverseShear2.propID = PropertyID.PID_ESI_VPS_PLY1_G023
            # Poisson ratio
            compositeInPlanePoisson.propID =  PropertyID.PID_ESI_VPS_PLY1_NU12
            compositeTransversePoisson1 =  compositeTransversePoisson
            compositeTransversePoisson1.propID = PropertyID.PID_ESI_VPS_PLY1_NU13
            compositeTransversePoisson2 =  compositeTransversePoisson
            compositeTransversePoisson2.propID = PropertyID.PID_ESI_VPS_PLY1_NU23
            
            self.vpsSolver.setProperty(compositeAxialYoung)
            self.vpsSolver.setProperty(compositeInPlaneYoung1)
            self.vpsSolver.setProperty(compositeInPlaneYoung2)
            
            self.vpsSolver.setProperty(compositeInPlaneShear)          
            self.vpsSolver.setProperty(compositeTransverseShear1)
            self.vpsSolver.setProperty(compositeTransverseShear2)
            
            self.vpsSolver.setProperty(compositeInPlanePoisson)          
            self.vpsSolver.setProperty(compositeTransversePoisson1)
            self.vpsSolver.setProperty(compositeTransversePoisson2)
            
            
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
        #self.thermalAppRec.terminateAll()
        self.digimatSolver.terminate()
        self.vpsSolver.terminate()
        super(Workflow_1_1_5, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"

    
if __name__=='__main__':

    useCaseID = 1
    execID = 1
    
    workflow = Workflow_1_1_5(targetTime=PQ.PhysicalQuantity(1.,'s'))
    # set Digimat material properties
    workflow.setProperty(Property.ConstantProperty(100, PropertyID.PID_MatrixYoung,  ValueType.Scalar, 'MPa', None, 0))
    workflow.setProperty(Property.ConstantProperty(0.2, PropertyID.PID_MatrixPoisson, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(100, PropertyID.PID_InclusionYoung,  ValueType.Scalar, 'MPa', None, 0))
    workflow.setProperty(Property.ConstantProperty(0.2, PropertyID.PID_InclusionPoisson, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(0.5, PropertyID.PID_InclusionVolumeFraction, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
    workflow.setProperty(Property.ConstantProperty(0.2, PropertyID.PID_InclusionAspectRatio, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))

    # set useCaseID and ExecID 
    workflow.setMetadata(MetadataKeys.UseCaseID, useCaseID)
    workflow.setMetadata(MetadataKeys.ExecID, execID)
    workflow.solve()
    time = PQ.PhysicalQuantity(1.0, 's')


    # collect Digimat outputs
    compositeAxialYoung = workflow.getProperty(PropertyID.PID_CompositeAxialYoung,time).inUnitsOf('MPa').getValue()
    compositeInPlaneYoung = workflow.getProperty(PropertyID.PID_CompositeInPlaneYoung,time).inUnitsOf('MPa').getValue()
    compositeInPlaneShear = workflow.getProperty(PropertyID.PID_CompositeInPlaneShear,time).inUnitsOf('MPa').getValue()
    compositeTransverseShear = workflow.getProperty(PropertyID.PID_CompositeTransverseShear,time).inUnitsOf('MPa').getValue()
    compositeInPlanePoisson = workflow.getProperty(PropertyID.PID_CompositeInPlanePoisson,time).getValue()
    compositeTransversePoisson = workflow.getProperty(PropertyID.PID_CompositeTransversePoisson,time).getValue()
    # collect vpn outputs
    bucklingLoad = workflow.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD, time).inUnitsOf('N').getValue()

    print ('OK')
