import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
from mupif import *
import Pyro4
import logging
log = logging.getLogger()
import time as timeT
import mupif.Physics.PhysicalQuantities as PQ

debug = True


if not debug:
    import ComposelectorSimulationTools.MIUtilities as miu
    import ApplicationsConfigs.LAMMPS_v3 as lammps
else:
    import LAMMPS_v4 as lammps

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
digimatJobManName = 'eX_DigimatMF_JobManager'
vpsJobManName='ESI_VPS_Jobmanager'

class Airbus_Workflow_14(Workflow.Workflow):

    def __init__(self, metaData={}):
        """
        Initializes the workflow. As the workflow is non-stationary, we allocate individual 
        applications and store them within a class.
        """
        log.info('Setting Workflow basic metadata')
        MD = {
            'Name': 'Airbus Case',
            'ID': 'A_14',
            'Description': 'Simulation of ',
            'Model_refs_ID': ['xy', 'xy'],
            'Inputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_MatrixYoung', 'Name': 'E_m',
                 'Description': 'Young modulus of the matrix', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_MatrixPoisson', 'Name': 'nu_m',
                 'Description': 'Poisson\'s ration of the matrix', 'Units': 'None', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionYoung', 'Name': 'E_i',
                 'Description': 'Young modulus of the inclusion', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionPoisson', 'Name': 'nu_i',
                 'Description': 'Poisson\'s ration of the inclusion', 'Units': 'None', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionVolumeFraction', 'Name': 'vof',
                 'Description': 'Volume fraction of the inclusion', 'Units': 'None', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionAspectRatio', 'Name': 'aspectratio',
                 'Description': 'Aspect ratio of the inclusion', 'Units': 'None', 'Required': True},
            ],
            'Outputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CriticalLoadLevel', 'Name': 'F_crit',
                 'Description': 'Buckling load of the structure', 'Units': 'kN'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeAxialYoung', 'Name': 'E_axial',
                 'Description': 'Axial Young modulus of the composite', 'Units': 'MPa'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeInPlaneYoung', 'Name': 'E_plane',
                 'Description': 'Young modulus in the plane of the composite', 'Units': 'MPa'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeInPlaneShear', 'Name': 'G_plane',
                 'Description': 'Shear modulus in the plane of the composite', 'Units': 'MPa'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeTransverseShear', 'Name': 'G_transverse',
                 'Description': 'Transverse shear modulus of the composite', 'Units': 'MPa'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeInPlanePoisson', 'Name': 'nu_plane',
                 'Description': 'Poisson\'s ration in the plane of the composite', 'Units': 'None'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeTransversePoisson', 'Name': 'nu_transverse',
                 'Description': 'Transverse Poisson\'s ration of the composite', 'Units': 'None'},
            ]
        }

        super(Airbus_Workflow_14, self).__init__(metaData=MD)
        self.updateMetadata(metaData)        

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

        # solvers
        self.digimatSolver = None
        self.vpsSolver = None
        


    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(1., 's'), metaData={}, validateMetaData=True, **kwargs):
        log.info('Workflow initialization')
        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to digimat JobManager running on (remote) server
        self.digimatJobMan = PyroUtil.connectJobManager(ns, digimatJobManName,hkey)
        #connect to vps JobManager running on (remote) server
        self.vpsJobMan = PyroUtil.connectJobManager(ns, vpsJobManName,hkey)
        

        #allocate the Digimat remote instance
        try:
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created digimat job')
            self.vpsSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.vpsJobMan, None, hkey)
            log.info('Created Vps job')            
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

        super(Airbus_Workflow_14, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)
        log.info('Metadata were successfully validate')

        # To be sure update only required passed metadata in models
        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }

        log.info('Setting Execution Metadata of Digimat')
        log.info('Setting Execution Metadata of Vps')

        
        self.digimatSolver.initialize(metaData=passingMD)
        # initialize vps solver
        self.vpsSolver.initialize(metaData=passingMD)

                

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
            log.info("Running Digimat")
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
            # map properties from Digimat to properties of Vps
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
            print ("Setting Vps params failed: " + repr(err));
            self.terminate()
            
        try:
            # solve digimat part
            log.info("Running Vps")
            self.vpsSolver.solveStep(None)
            ## get the desired properties
            self.myOutProps[PropertyID.PID_CriticalLoadLevel] = self.vpsSolver.getProperty(PropertyID.PID_CriticalLoadLevel,0)
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
        super(Airbus_Workflow_14, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"


def workflow(inputGUID, execGUID):
    # Define execution details to export
    if not debug:
        execPropsToExp = {"ID": "", "Use case ID": ""}
        # Export execution information from database
        ExportedExecInfo = miu.ExportData("MI_Composelector", "Modelling tasks workflows executions", execGUID, execPropsToExp)
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
        inclusionYoung = 20
        inclusionPoisson = 0.1
        inclusionVolumeFraction = 0.5
        inclusionAspectRatio = 1
        
        try:
            workflow = Airbus_Workflow_14()
            workflowMD = {
                'Execution': {
                    'ID': '1',
                    'Use_case_ID': '1_1',
                    'Task_ID': '1'
                }
            }
            workflow.initialize(targetTime=PQ.PhysicalQuantity(1., 's'), metaData=workflowMD)
            # set workflow input data
            workflow.setProperty(Property.ConstantProperty(matrixYoung, PropertyID.PID_MatrixYoung,               ValueType.Scalar, "MPa"))
            workflow.setProperty(Property.ConstantProperty(inclusionYoung, PropertyID.PID_InclusionYoung,            ValueType.Scalar, "MPa"))
            workflow.setProperty(Property.ConstantProperty(matrixPoisson, PropertyID.PID_MatrixPoisson,             ValueType.Scalar, "none"))
            workflow.setProperty(Property.ConstantProperty(inclusionPoisson, PropertyID.PID_InclusionPoisson,          ValueType.Scalar, "none"))
            workflow.setProperty(Property.ConstantProperty(inclusionVolumeFraction, PropertyID.PID_InclusionVolumeFraction,   ValueType.Scalar, "none"))
            workflow.setProperty(Property.ConstantProperty(inclusionAspectRatio, PropertyID.PID_InclusionAspectRatio,      ValueType.Scalar, "none"))

                      
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
            
            # collect Vps outputs
            #KPI 1-1 weight
            #weight = workflow.getProperty(PropertyID.PID_Weight, time).inUnitsOf('kg').getValue()
            #log.info("Requested KPI : Weight: " + str(weight) + ' kg')
            #KPI 1-2 buckling load
            bucklingLoad = workflow.getProperty(PropertyID.PID_CriticalLoadLevel, time).inUnitsOf('N').getValue()
            log.info("Requested KPI : Buckling Load: " + str(bucklingLoad) + ' N')
            workflow.terminate()
            log.info("Process complete")
            
            if not debug:
                # Importing output to database
                ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
                ImportHelper.CreateAttribute("Execution ID", execID, "")
                ImportHelper.CreateAttribute("Axial Young's modulus", compositeAxialYoung, "MPa")
                ImportHelper.CreateAttribute("In-plane Young's modulus", compositeInPlaneYoung, "MPa")
                ImportHelper.CreateAttribute("In-plane shear modulus", compositeInPlaneShear, "MPa")
                ImportHelper.CreateAttribute("Transverse shear modulus", compositeTransverseShear, "MPa")
                ImportHelper.CreateAttribute("In-plane Poisson's ratio", compositeInPlanePoisson, "")
                ImportHelper.CreateAttribute("Transverse Poisson's ratio", compositeTransversePoisson, "")
                ImportHelper.CreateAttribute("Buckling Load", bucklingLoad, "N")
                return ImportHelper
            
        except APIError.APIError as err:
            print ("Mupif API for Airubu_Workflow_3: " + repr(err))
        except Exception as err:
            print ("Error: " + repr(err))
        except:
            print ("Unknown error.")
            
if __name__=='__main__':
    workflow(0,0)
