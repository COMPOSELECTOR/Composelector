import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/commit'])
from mupif import *
import Pyro4
import logging
log = logging.getLogger()
import time as timeT
import mupif.Physics.PhysicalQuantities as PQ
import ComposelectorSimulationTools.MIUtilities as miu

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
digimatJobManName='eX_DigimatMF_JobManager'
mul2JobManName='MUL2.JobManager@Demo1'

class Workflow_1_1_2(Workflow.Workflow):
   
    def __init__(self, targetTime=PQ.PhysicalQuantity('0 s')):
        """
        Initializes the workflow. 
        """
        super(Workflow_1_1_2, self).__init__(file='', workdir='', targetTime=targetTime)

        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_MatrixYoung, PropertyID.PID_MatrixPoisson, PropertyID.PID_InclusionYoung, PropertyID.PID_InclusionPoisson, PropertyID.PID_InclusionVolumeFraction, PropertyID.PID_InclusionAspectRatio]
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_CriticalLoadLevel, PropertyID.PID_CompositeAxialYoung, PropertyID.PID_CompositeInPlaneYoung, PropertyID.PID_CompositeInPlaneShear, PropertyID.PID_CompositeTransverseShear, PropertyID.PID_CompositeInPlanePoisson, PropertyID.PID_CompositeTransversePoisson]

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to digimat JobManager running on (remote) server
        self.digimatJobMan = PyroUtil.connectJobManager(ns, digimatJobManName,hkey)
        #connect to mult2 JobManager running on (remote) server
        self.mul2JobMan = PyroUtil.connectJobManager(ns, mul2JobManName,hkey)

        # solvers
        self.digimatSolver = None
        self.mul2Solver = None
        #allocate the Digimat remote instance
        try:
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created digimat job')
            self.mul2Solver = PyroUtil.allocateApplicationWithJobManager( ns, self.mul2JobMan, None, hkey)
            log.info('Created mul2 job')            
        except Exception as e:
            log.exception(e)
        else:
            if ((self.digimatSolver is not None) and (self.mul2Solver is not None)):
                digimatSolverSignature=self.digimatSolver.getApplicationSignature()
                log.info("Working digimat solver on server " + digimatSolverSignature)
                mul2SolverSignature=self.mul2Solver.getApplicationSignature()
                log.info("Working mul2 solver on server " + mul2SolverSignature)
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
            # map properties from Digimat to properties of MUL2
            # Young modulus
            compositeAxialYoung.propID = PropertyID.PID_YoungModulus1
            compositeInPlaneYoung1 = compositeInPlaneYoung
            compositeInPlaneYoung1.propID = PropertyID.PID_YoungModulus2
            compositeInPlaneYoung2 = compositeInPlaneYoung
            compositeInPlaneYoung2.propID = PropertyID.PID_YoungModulus3
            # Shear modulus
            compositeInPlaneShear.propID = PropertyID.PID_ShearModulus12
            compositeTransverseShear1 = compositeTransverseShear
            compositeTransverseShear1.propID = PropertyID.PID_ShearModulus13
            compositeTransverseShear2 = compositeTransverseShear
            compositeTransverseShear2.propID = PropertyID.PID_ShearModulus23
            # Poisson ratio
            compositeInPlanePoisson.propID =  PropertyID.PID_PoissonRatio12
            compositeTransversePoisson1 =  compositeTransversePoisson
            compositeTransversePoisson1.propID = PropertyID.PID_PoissonRatio13
            compositeTransversePoisson2 =  compositeTransversePoisson
            compositeTransversePoisson2.propID = PropertyID.PID_PoissonRatio23
            
            self.mul2Solver.setProperty(compositeAxialYoung)
            self.mul2Solver.setProperty(compositeInPlaneYoung1)
            self.mul2Solver.setProperty(compositeInPlaneYoung2)
            
            self.mul2Solver.setProperty(compositeInPlaneShear)          
            self.mul2Solver.setProperty(compositeTransverseShear1)
            self.mul2Solver.setProperty(compositeTransverseShear2)
            
            self.mul2Solver.setProperty(compositeInPlanePoisson)          
            self.mul2Solver.setProperty(compositeTransversePoisson1)
            self.mul2Solver.setProperty(compositeTransversePoisson2)
            
            
        except Exception as err:
            print ("Setting MUL2 params failed: " + repr(err));
            self.terminate()
            
        try:
            # solve digimat part
            log.info("Running mul2")
            self.mul2Solver.solveStep(None)
            ## get the desired properties
            self.myOutProps[PropertyID.PID_CriticalLoadLevel] = self.mul2Solver.getProperty(PropertyID.PID_CriticalLoadLevel,0)
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()



    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        #self.thermalAppRec.terminateAll()
        self.digimatSolver.terminate()
        self.mul2Solver.terminate()
        super(Workflow_1_1_2, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"


def workflow(inputGUID, execGUID):
    # Define execution details to export
    execPropsToExp = {"ID": "",
                      "Use case ID": ""}

    # Export execution information from database
    ExportedExecInfo = miu.ExportData("MI_Composelector", "Modelling tasks workflows executions", execGUID,
                                      execPropsToExp)
    execID = ExportedExecInfo["ID"]
    useCaseID = ExportedExecInfo["Use case ID"]

    # Define properties:units to export
    propsToExp = {"Matrix Young modulus": "MPa",
                  "Matrix Poisson ratio": "",
                  "Inclusion Young modulus": "MPa",
                  "Inclusion Poisson ratio": "",
                  "Inclusion volume fraction": "%",
                  "Inclusion aspect ratio": ""
                  }

    # Export data from database
    ExportedData = miu.ExportData("MI_Composelector", "Inputs-Outputs", inputGUID, propsToExp, miu.unitSystems.METRIC)

    matrixYoung = ExportedData["Matrix Young modulus"]
    matrixPoisson = ExportedData["Matrix Poisson ratio"]
    inclusionYoung = ExportedData["Inclusion Young modulus"]
    inclusionPoisson = ExportedData["Inclusion Poisson ratio"]
    inclusionVolumeFraction = ExportedData["Inclusion volume fraction"]
    inclusionAspectRatio = ExportedData["Inclusion aspect ratio"]

    try:
        workflow = Workflow_1_1_2(targetTime=PQ.PhysicalQuantity(1.,'s'))

        # set workflow input data
        workflow.setProperty(Property.ConstantProperty(matrixYoung, PropertyID.PID_MatrixYoung,               ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(inclusionYoung, PropertyID.PID_InclusionYoung,            ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(matrixPoisson, PropertyID.PID_MatrixPoisson,             ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionPoisson, PropertyID.PID_InclusionPoisson,          ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionVolumeFraction, PropertyID.PID_InclusionVolumeFraction,   ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionAspectRatio, PropertyID.PID_InclusionAspectRatio,      ValueType.Scalar, "none"))

        # set workflow input metadata
        workflow.setMetadata(MetadataKeys.UseCaseID, useCaseID)
        workflow.setMetadata(MetadataKeys.ExecID, execID)

        # solve workflow
        workflow.solve()

        # get workflow outputs
        time = PQ.PhysicalQuantity(1.0, 's')

        # collect Digimat outputs
        compositeAxialYoung = workflow.getProperty(PropertyID.PID_CompositeAxialYoung,time).inUnitsOf('MPa').getValue()
        compositeInPlaneYoung = workflow.getProperty(PropertyID.PID_CompositeInPlaneYoung,time).inUnitsOf('MPa').getValue()
        compositeInPlaneShear = workflow.getProperty(PropertyID.PID_CompositeInPlaneShear,time).inUnitsOf('MPa').getValue()
        compositeTransverseShear = workflow.getProperty(PropertyID.PID_CompositeTransverseShear,time).inUnitsOf('MPa').getValue()
        compositeInPlanePoisson = workflow.getProperty(PropertyID.PID_CompositeInPlanePoisson,time).getValue()
        compositeTransversePoisson = workflow.getProperty(PropertyID.PID_CompositeTransversePoisson,time).getValue()

        # collect MUP2 outputs
        bucklingLoad = workflow.getProperty(PropertyID.PID_CriticalLoadLevel, time).inUnitsOf('N').getValue()

        # Importing output to database
        ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
        ImportHelper.CreateAttribute("Axial Young modulus", compositeAxialYoung, "MPa")
        ImportHelper.CreateAttribute("In-plane Young modulus", compositeInPlaneYoung, "MPa")
        ImportHelper.CreateAttribute("In-plane shear modulus", compositeInPlaneShear, "MPa")
        ImportHelper.CreateAttribute("Tranverse shear modulus", compositeTransverseShear, "MPa")
        ImportHelper.CreateAttribute("In-plane Poisson ratio", compositeInPlanePoisson, "")
        ImportHelper.CreateAttribute("Transverse Poisson ratio", compositeTransversePoisson, "")
        ImportHelper.CreateAttribute("Buckling Load", bucklingLoad, "N")
        return ImportHelper

    except APIError.APIError as err:
        print ("Mupif API for DIGIMAT-MF error: " + repr(err))
    except Exception as err:
        print ("Error: " + repr(err))
    except:
        print ("Unkown error.")
