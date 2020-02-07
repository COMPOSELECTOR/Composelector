import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
import mupif
from mupif import *
from mupif import PyroUtil, Util, Workflow, APIError
from mupif import dataID, PropertyID, Property, ValueType
import mupif.Physics.PhysicalQuantities as PQ

import sys
import argparse
import Pyro4
import os
import shutil
import glob
import logging
log = logging.getLogger()
import time as timeT

debug = True

if not debug:
    import ComposelectorSimulationTools.MIUtilities as miu

log = logging.getLogger()

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
digimatJobManName = 'eX_DigimatMF_JobManager'
abaqusJobManName='Abaqus@Mupif.LIST'

class A_13(Workflow.Workflow):
   
    def __init__(self, metaData={}):
        """
        Initializes the workflow. As the workflow is non-stationary, we allocate individual 
        applications and store them within a class.
        """

        log.info('Setting Workflow basic metadata')
        MD = {
####  Model information #### 
            'Name': 'Airbus Case',
            'ID': '1_2_2',
            'Description': 'Simulation of volume, stiffness and maximum principal stress',
            'Model_refs_ID': ['quasistatic Macromodel'],
############################

####  Workflow input definition ####
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
            ],

            'AbaqusInputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_YoungModulus1', 'Name': 'E_1',
                 'Description': 'Young modulus 1', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_YoungModulus2', 'Name': 'E_2',
                 'Description': 'Young modulus 2', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_YoungModulus3', 'Name': 'E_3',
                 'Description': 'Young modulus 3', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio12', 'Name': 'nu_12',
                 'Description': 'Poisson\'s ration 12', 'Units': 'none', 'Required': True},                
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio13', 'Name': 'nu_13',
                 'Description': 'Poisson\'s ration 13', 'Units': 'none', 'Required': True},                
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio23', 'Name': 'nu_23',
                 'Description': 'Poisson\'s ration 23', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ShearModulus12', 'Name': 'G_12',
                 'Description': 'Shear modulus 12', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ShearModulus13', 'Name': 'G_13',
                 'Description': 'Shear modulus 13', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ShearModulus23', 'Name': 'G_23',
                 'Description': 'Shear modulus 23', 'Units': 'MPa', 'Required': True},                
            ],
############################

#### Workflow output definition #### 
            'AbaqusOutputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_Volume',  'Name': 'volume',
                 'Description': 'volume of the structure', 'Units': 'mm**3', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_Stiffness',  'Name': 'stiffness',
                 'Description': 'rotational stiffness of the structure', 'Units': 'Nmm', 'Required': True},
############################
            ]
        }
        super(A_13, self).__init__(metaData=MD)
        self.updateMetadata(metaData)        

        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_MatrixYoung, PropertyID.PID_MatrixPoisson, PropertyID.PID_InclusionYoung, PropertyID.PID_InclusionPoisson, PropertyID.PID_InclusionVolumeFraction, PropertyID.PID_InclusionAspectRatio]

        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_Volume,PropertyID.PID_Stiffness, PropertyID.PID_CompositeAxialYoung, PropertyID.PID_CompositeInPlaneYoung, PropertyID.PID_CompositeInPlaneShear, PropertyID.PID_CompositeTransverseShear, PropertyID.PID_CompositeInPlanePoisson, PropertyID.PID_CompositeTransversePoisson]


        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}
        
       
        self.myMacroOutPropIDs = []
        for data in self.getMetadata("AbaqusOutputs"):
            self.myMacroOutPropIDs.append(eval(data['Type_ID']))
        
        self.myMacroOutProps = {}       

        self.digimatSolver = None
        self.abaqusSolver = None



    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(0., 's'), metaData={}, validateMetaData=True, **kwargs):

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)

        #connect to digimat JobManager running on (remote) server
        self.digimatJobMan = PyroUtil.connectJobManager(ns, digimatJobManName,hkey)
        
        #connect to JobManager running on (remote) server
        self.abaqusJobMan = PyroUtil.connectJobManager(ns, abaqusJobManName,hkey)

        #allocate the Abaqus remote instance
        try:
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created digimat job')

            self.abaqusSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.abaqusJobMan, None, hkey, sshContext=None)       
            log.info('Created Abaqus job')
        except Exception as e:
            log.exception(e)
        else:
            if ((self.digimatSolver is not None) and (self.abaqusSolver is not None)):
                digimatSolverSignature=self.digimatSolver.getApplicationSignature()
                log.info("Working digimat solver on server " + digimatSolverSignature)

                abaqusSolverSignature=self.abaqusSolver.getApplicationSignature()
                log.info("Working Abaqus solver on server " + abaqusSolverSignature)
            else:
                log.debug("Connection to server failed, exiting")
       


        super(A_13, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        # To be sure update only required passed metadata in models
        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }


        log.info('Setting Execution Metadata of Digimat')
        # Digimat initialization
        self.digimatSolver.initialize(metaData=passingMD)

        log.info('Setting Execution Metadata of Abaqus')
        # Abaqus initialization
        cfile1='abaqus_v6.env'
        cfile2=self.file

        ###########################################################################################
        ### START ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        # select input file location: True = application server, False: control script computer
        filesend = False

        # Define server path of input files
        print('**** copy files to working directories')
        if filesend:
            basepath=os.path.abspath('..')
            inpDir2 = os.path.join(basepath,'abaqusserver','inputFiles')
        else:
            inpDir2 = os.path.abspath('./inputFiles')

        # identify input files
        print("Identifying input files.")
        self.file2 = glob.glob(os.path.join(inpDir2, cfile2))[0]
        self.file2 = os.path.basename(self.file2)

        try:
            inpFiles2 = []
            if filesend:
                inpFiles2.extend(glob.glob(os.path.join(inpDir2, cfile1)))
                inpFiles2.extend(glob.glob(os.path.join(inpDir2, cfile2)))
            else:
                inpFiles2.append(cfile1)
                inpFiles2.append(cfile2)
        except Exception as err:
            print("Error:" + repr(err))
        
        # copy Abaqus input files to server work directories
        print("Transferring input files to the work directory.")
        if filesend:
            print("$$$ Uploading input files from application server to workdir")
            try:
                for inpFile in inpFiles2:
                    shutil.copy(inpFile, self.abaqusJobMan.getJobWorkDir(self.abaqusSolver.getJobID()))
            except Exception as err:
                print("Error:" + repr(err))
        else:
            print("$$$ Uploading input files from control computer to workdir")
            log.info("Uploading input files to server")
            try:
                for inpFile in inpFiles2:
                    pf = self.abaqusJobMan.getPyroFile(self.abaqusSolver.getJobID(), inpFile, 'wb')
                    PyroUtil.uploadPyroFile(os.path.join(inpDir2,inpFile), pf, hkey)
            except Exception as err:
                print("Error:" + repr(err))

        ### END ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        #########################################################################################
        print('FILES COPIED')

        # define metadata to be passed to ABAQUS solver
        app2MD=passingMD.copy()
        app2MD['Inputs']=self.getMetadata('AbaqusInputs').copy()
        app2MD['Outputs']=self.getMetadata('AbaqusOutputs').copy()
        app2MD['refPoint'] = 'M_SET-1'
        app2MD['componentID'] = 6
        ############################
        
        # initialize abaqus solver
        self.abaqusSolver.initialize(metaData=app2MD, file = self.file2, workdir = self.abaqusJobMan.getJobWorkDir(self.abaqusSolver.getJobID()))
        print('SOLVER INITIALIZED')
        ############################


        
        

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

        # check if compulsory input properties exist
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

        # set material properties for Abaqus 
        try:
            # map properties from Digimat to properties of Abaqus
            # Young modulus
            compositeAxialYoung.propID = PropertyID.PID_YoungModulus1
            self.abaqusSolver.setProperty(compositeAxialYoung)
            compositeInPlaneYoung1 = compositeInPlaneYoung
            compositeInPlaneYoung1.propID = PropertyID.PID_YoungModulus2
            self.abaqusSolver.setProperty(compositeInPlaneYoung1)
            compositeInPlaneYoung2 = compositeInPlaneYoung
            compositeInPlaneYoung2.propID = PropertyID.PID_YoungModulus3
            self.abaqusSolver.setProperty(compositeInPlaneYoung2)
            # Shear modulus
            compositeInPlaneShear.propID = PropertyID.PID_ShearModulus12
            self.abaqusSolver.setProperty(compositeInPlaneShear)          
            compositeTransverseShear1 = compositeTransverseShear
            compositeTransverseShear1.propID = PropertyID.PID_ShearModulus13
            self.abaqusSolver.setProperty(compositeTransverseShear1)
            compositeTransverseShear2 = compositeTransverseShear
            compositeTransverseShear2.propID = PropertyID.PID_ShearModulus23
            self.abaqusSolver.setProperty(compositeTransverseShear2)
            # Poisson ratio
            compositeInPlanePoisson.propID =  PropertyID.PID_PoissonRatio12
            self.abaqusSolver.setProperty(compositeInPlanePoisson)          
            compositeTransversePoisson1 =  compositeTransversePoisson
            compositeTransversePoisson1.propID = PropertyID.PID_PoissonRatio13
            self.abaqusSolver.setProperty(compositeTransversePoisson1)
            compositeTransversePoisson2 =  compositeTransversePoisson
            compositeTransversePoisson2.propID = PropertyID.PID_PoissonRatio23
            self.abaqusSolver.setProperty(compositeTransversePoisson2)           
        except Exception as err:
            print ("Setting Abaqus params failed: " + repr(err));
            self.terminate()

        try:
            # solve Abaqus part
            log.info("Running Abaqus")
            self.abaqusSolver.solveStep(None)

            ## get KPIs from Abaqus
            # KPIs have to be extracted here because default self.solve terminates application instance
            print('*** Get KPIs:',self.myMacroOutPropIDs)
            for propID in self.myMacroOutPropIDs:
                try :
                    prop = self.abaqusSolver.getProperty(propID)
                    self.myMacroOutProps[propID] = prop
                    print('KPI',prop)
                except Exception as e:
                    log.error("ABAQUS KPI retrieval failed", propID)
                    print(str(e))
               
            print('*** KPIs:',self.myMacroOutProps)
            print('WORKFLOW: GOT ALL KPIs')

        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()



    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        self.abaqusSolver.terminate()
        super(A_13, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"

def workflow(inputGUID, execGUID):
    """
    Workflow for Airbus use case.
    Calculation of KPI buckling load from data base material properties
    """
    # Define execution details to export
    if not debug:
        execPropsToExp = {"ID": "",
                          "Use case ID": ""}
        
        # Export execution information from database
        ExportedExecInfo = miu.ExportData("MI_Composelector", "Modelling tasks workflows executions", execGUID,
                                          execPropsToExp)
        execID = ExportedExecInfo["ID"]
        useCaseID = ExportedExecInfo["Use case ID"]
        
        # Define properties:units to export
        propsToExp = {"Axial Young's modulus": "MPa",
                      "In-plane Young's modulus": "MPa",
                      "E3": "MPa",
                      "In-plane shear modulus": "MPa",
                      "Transverse shear modulus": "MPa",
                      "G23": "MPa",
                      "In-plane Poisson's ratio": "",
                      "Transverse Poisson's ratio": "",
                      "NU23": ""
        }
        
        # Export data from database
        ExportedData = miu.ExportData("MI_Composelector", "Inputs-Outputs", inputGUID, propsToExp, miu.unitSystems.METRIC)
        
        # Assign exported properties to variables
        E1 = ExportedData["Axial Young's modulus"]
        E2 = ExportedData["In-plane Young's modulus"]
        E3 = ExportedData["E3"]
        G12 = ExportedData["In-plane shear modulus"]
        G13 = ExportedData["Transverse shear modulus"]
        G23 = ExportedData["G23"]
        nu12 = ExportedData["In-plane Poisson's ratio"]
        nu13 = ExportedData["Transverse Poisson's ratio"]
        nu23 = ExportedData["NU23"]
    else:
        matrixYoung = 10
        matrixPoisson = 0.2
        inclusionYoung = 20
        inclusionPoisson = 0.1
        inclusionVolumeFraction = 0.5
        inclusionAspectRatio = 1

        
####    define ABAQUS input file names ####
        cfile2='composelector_Panel-quasi-v3.inp'

        try:
            workflow = A_13()
            workflowID = {
                'Execution': {
                    'ID': '1',
                    'Use_case_ID': '1_1',
                    'Task_ID': '1'
                }
            }
            workflowMD = workflowID.copy()
            workflow.initialize(file = cfile2,targetTime=PQ.PhysicalQuantity(1., 's'), metaData=workflowMD)
            print('WORKFLOW INITIALIZED')
            # set workflow input data
            # Submitting new material properties
            # set workflow input data
            workflow.setProperty(Property.ConstantProperty(matrixYoung, PropertyID.PID_MatrixYoung,               ValueType.Scalar, "MPa"))
            workflow.setProperty(Property.ConstantProperty(inclusionYoung, PropertyID.PID_InclusionYoung,            ValueType.Scalar, "MPa"))
            workflow.setProperty(Property.ConstantProperty(matrixPoisson, PropertyID.PID_MatrixPoisson,             ValueType.Scalar, "none"))
            workflow.setProperty(Property.ConstantProperty(inclusionPoisson, PropertyID.PID_InclusionPoisson,          ValueType.Scalar, "none"))
            workflow.setProperty(Property.ConstantProperty(inclusionVolumeFraction, PropertyID.PID_InclusionVolumeFraction,   ValueType.Scalar, "none"))
            workflow.setProperty(Property.ConstantProperty(inclusionAspectRatio, PropertyID.PID_InclusionAspectRatio,      ValueType.Scalar, "none"))
 
            

            
                      
            # solve workflow
            workflow.solve()
            log.info('WORKFLOW SOLVED')
            
            # get workflow outputs
            time = PQ.PhysicalQuantity(1.0, 's')
            
            # collect Digimat outputs
            compositeAxialYoung = workflow.getProperty(PropertyID.PID_CompositeAxialYoung,time).inUnitsOf('MPa').getValue()
            compositeInPlaneYoung = workflow.getProperty(PropertyID.PID_CompositeInPlaneYoung,time).inUnitsOf('MPa').getValue()
            compositeInPlaneShear = workflow.getProperty(PropertyID.PID_CompositeInPlaneShear,time).inUnitsOf('MPa').getValue()
            compositeTransverseShear = workflow.getProperty(PropertyID.PID_CompositeTransverseShear,time).inUnitsOf('MPa').getValue()
            compositeInPlanePoisson = workflow.getProperty(PropertyID.PID_CompositeInPlanePoisson,time).getValue()
            compositeTransversePoisson = workflow.getProperty(PropertyID.PID_CompositeTransversePoisson,time).getValue()

                       
            workflow.terminate()
            log.info("Process complete")
            
            if not debug:
                # Importing output to database
                ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
                ImportHelper.CreateAttribute("Execution ID", execID, "")
                ImportHelper.CreateAttribute("Buckling Load", buckLoad, "N")
                return ImportHelper
            
        except APIError.APIError as err:
            print ("Mupif API for Scenario error: " + repr(err))
            workflow.terminate()
        except Exception as err:
            print ("Error: " + repr(err))
            workflow.terminate()
        except:
            print ("Unknown error.")
            workflow.terminate()
            
if __name__=='__main__':
    workflow(0,0)
