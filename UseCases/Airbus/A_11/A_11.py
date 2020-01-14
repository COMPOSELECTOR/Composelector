import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
from mupif import *
import time as timeT
import logging
log = logging.getLogger()
log.setLevel(logging.INFO)
import mupif.Physics.PhysicalQuantities as PQ

debug = True

if not debug:
    import ComposelectorSimulationTools.MIUtilities as miu


nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
jobManName='eX_DigimatMF_JobManager'#Name of job manager


class A_11(Workflow.Workflow):
   
    def __init__ (self, metaData={}):
        MD = {
            'Name': 'ESI combined with',
            'ID': '1_1_4',
            'Description': 'Simulation of ',
            'Model_refs_ID': ['xy', 'xy'],
            'Inputs': [],
            'Outputs': [
                {'Type': 'mupif.Field', 'Type_ID': 'mupif.FieldID.FID_Displacement', 'Name': 'Displacement field',
                 'Description': 'Displacement field on 2D domain', 'Units': 'm'}]
        }

        super(A_11, self).__init__(metaData=MD)
        self.updateMetadata(metaData)        


        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_MatrixYoung, PropertyID.PID_MatrixPoisson,PropertyID.PID_InclusionYoung, PropertyID.PID_InclusionPoisson, PropertyID.PID_InclusionVolumeFraction, PropertyID.PID_InclusionAspectRatio]
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs
        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_CompositeAxialYoung, PropertyID.PID_CompositeInPlaneYoung,PropertyID.PID_CompositeInPlaneShear,PropertyID.PID_CompositeTransverseShear, PropertyID.PID_CompositeInPlanePoisson, PropertyID.PID_CompositeTransversePoisson]
       
        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        self.digimatSolver = None
        

    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(0., 's'), metaData={}, validateMetaData=True, **kwargs):

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to JobManager running on (remote) server and create a tunnel to it
        self.digimatJobMan = PyroUtil.connectJobManager(ns, jobManName, hkey)
    
        #allocate the Digimat remote instance
        try:
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created Digimiat job')
        except Exception as e:
            log.exception(e)
        else:
            if ((self.digimatSolver is not None)):
                appsig=self.digimatSolver.getApplicationSignature()
                log.info("Working application 1 on server " + appsig)
            else:
                log.debug("Connection to server failed, exiting")

        super(A_11, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        # To be sure update only required passed metadata in models
        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }        
        self.digimatSolver.initialize(metaData=passingMD)

                

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
        # Digimat
        try:
            for propid in self.myInputPropIDs:
                self.digimatSolver.setProperty(self.myInputProps[propid])
        except Exception as err:
            print ("Setting Digimat params failed: " + repr(err));
            self.terminate()
        try:
            # solve Digimat
            log.info("Running Digimat")
            self.digimatSolver.solveStep(None)
            ## set the desired properties
            for propid in self.myOutPropIDs:
                self.myOutProps[propid] = self.digimatSolver.getProperty(propid)
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()

    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

            
    def terminate(self):    
        self.digimatSolver.terminate()
        super(A_11, self).terminate()

    def getApplicationSignature(self):
        return "Digimat workflow"

    def getAPIVersion(self):
        return "1.0"

def workflow(inputGUID, execGUID):

    if not debug:
        # Define execution details to export
        execPropsToExp = {"ID": "",
                          "Use case ID": ""}

        # Export execution information from database
        ExportedExecInfo = miu.ExportData("MI_Composelector", "Modelling tasks workflows executions", execGUID,
                                          execPropsToExp)
        execID = ExportedExecInfo["ID"]
        useCaseID = ExportedExecInfo["Use case ID"]

        # Define properties:units to export
        propsToExp = {"Matrix Young's modulus": "MPa",
                      "Matrix Poisson's ratio": "",
                      "Inclusion Young's modulus": "MPa",
                      "Inclusion Poisson's ratio": "",
                      "Inclusion volume fraction": "%",
                      "Inclusion aspect ratio": ""
        }

        # Export data from database
        ExportedData = miu.ExportData("MI_Composelector", "Inputs-Outputs", inputGUID, propsToExp, miu.unitSystems.METRIC)
        
        matrixYoung = ExportedData["Matrix Young's modulus"]
        matrixPoisson = ExportedData["Matrix Poisson's ratio"]
        inclusionYoung = ExportedData["Inclusion Young's modulus"]
        inclusionPoisson = ExportedData["Inclusion Poisson's ratio"]
        inclusionVolumeFraction = ExportedData["Inclusion volume fraction"]
        inclusionAspectRatio = ExportedData["Inclusion aspect ratio"]

    else:
        matrixYoung = 10
        matrixPoisson = 0.2
        inclusionYoung = 5
        inclusionPoisson = 0.3
        inclusionVolumeFraction = 0.3
        inclusionAspectRatio = 0.5
        
    try:
        workflow = A_11()
        workflowMD = {
            'Execution': {
                'ID': '1',
                'Use_case_ID': '1_1',
                'Task_ID': '1'
            }
        }
        workflow.initialize(targetTime=PQ.PhysicalQuantity(1., 's'), metaData=workflowMD)   


        workflow.setProperty(Property.ConstantProperty(matrixYoung, PropertyID.PID_MatrixYoung,               ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(inclusionYoung, PropertyID.PID_InclusionYoung,            ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(matrixPoisson, PropertyID.PID_MatrixPoisson,             ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionPoisson, PropertyID.PID_InclusionPoisson,          ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionVolumeFraction, PropertyID.PID_InclusionVolumeFraction,   ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionAspectRatio, PropertyID.PID_InclusionAspectRatio,      ValueType.Scalar, "none"))

        workflow.solve()

        time = PQ.PhysicalQuantity(1.0, 's')
        # get result of the simulations
        compositeAxialYoung = workflow.getProperty(PropertyID.PID_CompositeAxialYoung,time).inUnitsOf('MPa').getValue()
        compositeInPlaneYoung = workflow.getProperty(PropertyID.PID_CompositeInPlaneYoung,time).inUnitsOf('MPa').getValue()
        compositeInPlaneShear = workflow.getProperty(PropertyID.PID_CompositeInPlaneShear,time).inUnitsOf('MPa').getValue()
        compositeTransverseShear = workflow.getProperty(PropertyID.PID_CompositeTransverseShear,time).inUnitsOf('MPa').getValue()
        compositeInPlanePoisson = workflow.getProperty(PropertyID.PID_CompositeInPlanePoisson,time).getValue()
        compositeTransversePoisson = workflow.getProperty(PropertyID.PID_CompositeTransversePoisson,time).getValue()

        workflow.terminate()
        log.info("Process complete")
        
        
        if not debug:
       
            ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
            ImportHelper.CreateAttribute("Execution ID", execID, "")
            ImportHelper.CreateAttribute("Axial Young's modulus", compositeAxialYoung, "MPa")
            ImportHelper.CreateAttribute("In-plane Young's modulus", compositeInPlaneYoung, "MPa")
            ImportHelper.CreateAttribute("In-plane shear modulus", compositeInPlaneShear, "MPa")
            ImportHelper.CreateAttribute("Transverse shear modulus", compositeTransverseShear, "MPa")
            ImportHelper.CreateAttribute("In-plane Poisson's ratio", compositeInPlanePoisson, "")
            ImportHelper.CreateAttribute("Transverse Poisson's ratio", compositeTransversePoisson, "")
            return ImportHelper

    except APIError.APIError as err:
        print ("Mupif API for DIGIMAT-MF error: "+ repr(err))
    except Exception as err:
        print ("Error: " + repr(err))
    except:
        print ("Unknown error.")



if __name__=='__main__':
    workflow(0,0)
