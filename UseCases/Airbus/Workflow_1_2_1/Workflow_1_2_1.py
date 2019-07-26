import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/actual'])
from mupif import *
import Pyro4
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
mul2JobManName='MUL2.JobManager@UseCase1'


class Mul2Workflow(Workflow.Workflow):
   
    def __init__(self, metaData={}):
        """
        Initializes the workflow. As the workflow is non-stationary, we allocate individual 
        applications and store them within a class.
        """

        log.info('Setting Workflow basic metadata')
        MD = {
            'Name': 'Airbus Case',
            'ID': '1_2_2',
            'Description': 'Simulation of ',
            'Model_refs_ID': ['xy', 'xy'],
            'Inputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_YoungModulus1', 'Name': 'E_1',
                 'Description': 'Young modulus 1', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_YoungModulus2', 'Name': 'E_2',
                 'Description': 'Young modulus 2', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_YoungModulus3', 'Name': 'E_3',
                 'Description': 'Young modulus 3', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio12', 'Name': 'nu_12',
                 'Description': 'Poisson\'s ration 12', 'Units': 'None', 'Required': True},                
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio13', 'Name': 'nu_13',
                 'Description': 'Poisson\'s ration 13', 'Units': 'None', 'Required': True},                
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio23', 'Name': 'nu_23',
                 'Description': 'Poisson\'s ration 23', 'Units': 'None', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ShearModulus12', 'Name': 'G_12',
                 'Description': 'Shear modulus 12', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ShearModulus13', 'Name': 'G_13',
                 'Description': 'Shear modulus 13', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_ShearModulus23', 'Name': 'G_23',
                 'Description': 'Shear modulus 23', 'Units': 'MPa', 'Required': True},                
            ],
            'Outputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CriticalLoadLevel', 'Name': 'F_crit',
                 'Description': 'Buckling load of the structure', 'Units': 'kN'},
            ]
        }
        super(Mul2Workflow, self).__init__(metaData=MD)
        self.updateMetadata(metaData)        

        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_YoungModulus1,PropertyID.PID_YoungModulus2, PropertyID.PID_YoungModulus3, PropertyID.PID_PoissonRatio12, PropertyID.PID_PoissonRatio13,PropertyID.PID_PoissonRatio23, PropertyID.PID_ShearModulus12, PropertyID.PID_ShearModulus13, PropertyID.PID_ShearModulus23]     
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs
        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_CriticalLoadLevel]

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}
        
       
       
        self.mul2Solver = None



    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(0., 's'), metaData={}, validateMetaData=True, **kwargs):

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to JobManager running on (remote) server
        self.mul2JobMan = PyroUtil.connectJobManager(ns, mul2JobManName,hkey)

        #allocate the Mul2 remote instance
        try:
            self.mul2Solver = PyroUtil.allocateApplicationWithJobManager( ns, self.mul2JobMan, None, hkey, sshContext=None)       
            log.info('Created mul2 job')
        except Exception as e:
            log.exception(e)
        else:
            if ((self.mul2Solver is not None)):
                mul2SolverSignature=self.mul2Solver.getApplicationSignature()
                log.info("Working mul2 solver on server " + mul2SolverSignature)
            else:
                log.debug("Connection to server failed, exiting")
       


        super(Mul2Workflow, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        # To be sure update only required passed metadata in models
        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }
        workDir = self.mul2Solver.getWorkDir() +'/'+self.mul2Solver.getJobID()
        self.mul2Solver.initialize(metaData=passingMD, workdir = workDir)
        

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
        # mul2
        try:
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_YoungModulus1])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_YoungModulus2])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_YoungModulus3])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_PoissonRatio12])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_PoissonRatio13])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_PoissonRatio23])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_ShearModulus12])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_ShearModulus13])
            self.mul2Solver.setProperty(self.myInputProps[PropertyID.PID_ShearModulus23])
        except Exception as err:
            print ("Setting Mul2 params failed: " + repr(err));
            self.terminate()

        try:
            # solve mul2 part
            log.info("Running mul2")
            self.mul2Solver.solveStep(None)
            ## set the desired properties
            self.myOutProps[PropertyID.PID_CriticalLoadLevel] = self.mul2Solver.getProperty(PropertyID.PID_CriticalLoadLevel, 0.0)
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()




    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        #self.thermalAppRec.terminateAll()
        self.mul2Solver.terminate()
        super(Mul2Workflow, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"

def workflow(inputGUID, execGUID):
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
            workflow = Mul2Workflow()
            workflowMD = {
                'Execution': {
                    'ID': '1',
                    'Use_case_ID': '1_1',
                    'Task_ID': '1'
                }
            }
            workflow.initialize(targetTime=PQ.PhysicalQuantity(1., 's'), metaData=workflowMD)
            # set workflow input data
            # Submitting new material properties
            pE1 = workflow.setProperty(Property.ConstantProperty(E1, PropertyID.PID_YoungModulus1, ValueType.Scalar, 'MPa'))
            pE2 = workflow.setProperty(Property.ConstantProperty(E2, PropertyID.PID_YoungModulus2, ValueType.Scalar, 'MPa'))
            pE3 = workflow.setProperty(Property.ConstantProperty(E3, PropertyID.PID_YoungModulus3, ValueType.Scalar, 'MPa'))
            pnu12 = workflow.setProperty(Property.ConstantProperty(nu12, PropertyID.PID_PoissonRatio12, ValueType.Scalar, PQ.getDimensionlessUnit()))
            pnu13 = workflow.setProperty(Property.ConstantProperty(nu13, PropertyID.PID_PoissonRatio13, ValueType.Scalar, PQ.getDimensionlessUnit()))
            pnu23 = workflow.setProperty(Property.ConstantProperty(nu23, PropertyID.PID_PoissonRatio23, ValueType.Scalar, PQ.getDimensionlessUnit()))
            pG12 = workflow.setProperty(Property.ConstantProperty(G12, PropertyID.PID_ShearModulus12, ValueType.Scalar, 'MPa'))
            pG13 = workflow.setProperty(Property.ConstantProperty(G13, PropertyID.PID_ShearModulus13, ValueType.Scalar, 'MPa'))
            pG23 = workflow.setProperty(Property.ConstantProperty(G23, PropertyID.PID_ShearModulus23, ValueType.Scalar, 'MPa'))
            
            # solve workflow
            workflow.solve()
            
            # get workflow outputs
            time = PQ.PhysicalQuantity(1.0, 's')
            
            
            # collect MUL2 outputs
            bucklingLoad = workflow.getProperty(PropertyID.PID_CriticalLoadLevel, time).inUnitsOf('N').getValue()
            log.info("Requested KPI : Buckling Load: " + str(bucklingLoad) + ' N')
            workflow.terminate()
            log.info("Process complete")
            
            if not debug:
                # Importing output to database
                ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
                ImportHelper.CreateAttribute("Execution ID", execID, "")
                ImportHelper.CreateAttribute("Buckling Load", buckLoad, "N")
                return ImportHelper
            
        except APIError.APIError as err:
            print ("Mupif API for DIGIMAT-MF error: " + repr(err))
        except Exception as err:
            print ("Error: " + repr(err))
        except:
            print ("Unknown error.")
            
if __name__=='__main__':
    workflow(0,0)
