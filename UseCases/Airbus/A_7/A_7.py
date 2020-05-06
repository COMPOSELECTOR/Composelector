import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
from mupif import *
from mupif import dataID, PropertyID, Property, ValueType
import mupif
import argparse
import Pyro4
import os
import shutil
import glob
import logging
log = logging.getLogger()
import time as timeT
import mupif.Physics.PhysicalQuantities as PQ
debug = True



if not debug:
    import ComposelectorSimulationTools.MIUtilities as miu

log = logging.getLogger()

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
vpsJobManName = 'ESI_VPS_Jobmanager_MUPIF_v2.2'


class Airbus_Workflow_7(Workflow.Workflow):
   
    def __init__(self, metaData={}):
        """
        Initializes the workflow. As the workflow is non-stationary, we allocate individual 
        applications and store them within a class.
        """

        log.info('Setting Workflow basic metadata')
        MD = {
####  Model information #### 
            'Name': 'Airbus Case',
            'ID': '7',
            'Description': 'Simulation of buckling load',
            'Model_refs_ID': ['xy', 'xy'],
############################

####  Workflow input definition #### 
            'Inputs': [
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
            'Outputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ESI_VPS_BUCKL_LOAD', 'Name': 'F_crit',
                 'Description': 'Buckling load of the structure', 'Units': 'kN*mm'},
#                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_Volume',  'Name': 'volume',
#                 'Description': 'volume of the structure', 'Units': 'mm**3', 'Required': True},
#                Volume calculation not possible in pure buckling analysis !!!!
############################

            ]
        }
        super(Airbus_Workflow_7, self).__init__(metaData=MD)
        self.updateMetadata(metaData)        

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
        
       
        self.myMacroOutPropIDs = []
        for data in self.getMetadata("Outputs"):
            self.myMacroOutPropIDs.append(eval(data['Type_ID']))
        
        self.myMacroOutProps = {}       

        self.vpsSolver = None



    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(0., 's'), metaData={}, validateMetaData=True, **kwargs):

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)

# initialisze vps application 
        #connect to JobManager running on (remote) server
        self.vpsJobMan = PyroUtil.connectJobManager(ns, vpsJobManName,hkey)

        #allocate the Vps remote instance
        try:
            self.vpsSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.vpsJobMan, None, hkey, sshContext=None)       
            log.info('Created VPS job')
        except Exception as e:
            log.exception(e)
        else:
            if ((self.vpsSolver is not None)):
                vpsSolverSignature=self.vpsSolver.getApplicationSignature()
                log.info("Working VPS solver on server " + vpsSolverSignature)
            else:
                log.debug("Connection to server failed, exiting")
       


        super(Airbus_Workflow_7, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        # To be sure update only required passed metadata in models
        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }
        

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

        # set material properties for Vps 
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

        except Exception as err:
            print ("Setting Vps params failed: " + repr(err));
            self.terminate()

        try:
            # solve Vps part
            log.info("Running Vps")
            self.vpsSolver.solveStep(None)

            ## get KPIs from Vps
            # KPIs have to be extracted here because default self.solve terminates application instance
            self.myOutProps[PropertyID.PID_ESI_VPS_BUCKL_LOAD] = self.vpsSolver.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD,0)

        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()



    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        self.vpsSolver.terminate()
        super(Airbus_Workflow_7, self).terminate()

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
        E1 = 10
        E2 = 10
        E3 = 5
        G12 = 3
        G13 = 3
        G23 = 3
        nu12 = 0.2
        nu13 = 0.3
        nu23 = 0.1
        


        try:
            workflow = Airbus_Workflow_7()
            workflowID = {
                'Execution': {
                    'ID': '1',
                    'Use_case_ID': '1_1',
                    'Task_ID': '1'
                }
            }
            workflowMD = workflowID.copy()

            workflow.initialize(targetTime=PQ.PhysicalQuantity(1., 's'), metaData=workflowMD)
            print('WORKFLOW INITIALIZED')
            # set workflow input data
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
            
            # define metadata to be passed to VPS solver
            app2MD=workflowID.copy()
            app2MD['Inputs']=workflow.getMetadata('Inputs').copy()
            app2MD['Outputs']=workflow.getMetadata('Outputs').copy()
            ############################
            
            # initialize vps solver
            log.info('Setting Execution Metadata of Vps')       
            workdir=workflow.vpsJobMan.getJobWorkDir(workflow.vpsSolver.getJobID())
            workflow.vpsSolver.initialize(metaData=app2MD,workdir=workdir)
            workflow.vpsSolver.readInput()
            ############################

            # solve workflow
            workflow.solve()
            print('WORKFLOW SOLVED')
            
            # get workflow outputs
            time = PQ.PhysicalQuantity(1.0, 's')
            bucklingLoad = workflow.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD, time).inUnitsOf('kN*mm').getValue()
            log.info("Requested KPI : Buckling Load: " + str(bucklingLoad) + ' kN*mm')
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
