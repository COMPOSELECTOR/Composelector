# -*- coding: utf-8 -*-
"""
Created on Fri Nov  9 14:00:05 2018

@author: Yao Koutsawa, Gast Rauchs
"""
import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
import logging
import argparse
import time as timeT
import os
import shutil
import glob

from mupif import PyroUtil, Util, Workflow, APIError
from mupif import dataID, PropertyID, Property, ValueType
import mupif.Physics.PhysicalQuantities as PQ
from mupif import TimeStep

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
cmbsfeJobManName='CmbsFE@Mupif.LIST'
abaqusJobManName='Abaqus@Mupif.LIST'



sys.path.append('../abaqusServer')
sys.path.append('../cmbsfeServer')
sys.path.append('../WFGeneric')

#from AbaqusWorkFlow import AbaqusWorkflow
#from CmbsfeWorkFlow import CmbsfeWorkflow

log = logging.getLogger()

start = timeT.time()
log.info('Timer started')


class DowWorkflow(Workflow.Workflow):
        
    def __init__(self, metaData={}):
        """
        Workflow for Dow use case. version 2. for mupif 2.2
        """
        MD = {
            'Name': 'Dow use case simple multiscale workflow',
            'ID': 'Dow-1',
            'Description': 'simple multiscale mechanical model',
            'Model_refs_ID': ['MicroMechanical','MacroMechanical'],
        }

        super(DowWorkflow, self).__init__(metaData=MD)
        self.updateMetadata(metaData)

        self.workflowMonitor = None  # No monitor by default
        self.targetTime = None

    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(0., 's'), metaData={}, validateMetaData=False, **kwargs):
        """
        Initializes workflow
        
        :param str file: Name of file
        :param str workdir: Optional parameter for working directory
        :param dict metaData: Optional dictionary used to set up metadata (can be also set by setMetadata() )
        :param bool validateMetaData: Defines if the metadata validation will be called
        :param named_arguments kwargs: Arbitrary further parameters
        """

        super(DowWorkflow, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }

        if PQ.isPhysicalQuantity(targetTime):
            self.targetTime = targetTime
        else:
            raise TypeError('targetTime is not PhysicalQuantity')

        self.updateMetadata(metaData)
        # define futher app metadata

        self.myInputPropIDs = []
        self.myCompulsoryPropIDs = []
        for data in self.getMetadata("Inputs"):
            self.myCompulsoryPropIDs.append(eval(data['Type_ID']))

        # list of recognized micro-scale outputs property IDs
        self.myMicroOutPropIDs =  self.myCompulsoryPropIDs[2:11].copy()

        # list of property domains
        fiberID = 1
        matrixID = 2
        self.myInputPropDomIDs = {PropertyID.PID_YoungModulus1: fiberID,
                               PropertyID.PID_YoungModulus2: fiberID,
                               PropertyID.PID_YoungModulus3: fiberID,
                               PropertyID.PID_PoissonRatio23: fiberID,
                               PropertyID.PID_PoissonRatio13: fiberID,
                               PropertyID.PID_PoissonRatio12: fiberID,
                               PropertyID.PID_ShearModulus23: fiberID,
                               PropertyID.PID_ShearModulus13: fiberID,
                               PropertyID.PID_ShearModulus12: fiberID,
                               PropertyID.PID_EModulus: matrixID,
                               PropertyID.PID_PoissonRatio: matrixID}
        
        # list of recognized macro-scale outputs (KPIs) property IDs
        self.myMacroOutPropIDs = []
        for data in self.getMetadata("Outputs"):
            self.myMacroOutPropIDs.append(eval(data['Type_ID']))
       
        # dictionary of input properties (values)
        self.myInputProps = {}
        
        # dictionary of micro-scale output properties (values)
        self.myMicroOutProps = {}
        
        # dictionary of Macro-scale output properties (values)
        self.myMacroOutProps = {}
        
        # Locate nameserver
        ns = PyroUtil.connectNameServer(nshost=nshost, nsport=nsport, hkey=hkey)
        log.info('Solver: Nameserver connected')
        # Connect to JobManagers running on (remote) servers
        log.info('Connecting to JobManagers running on servers')
        print('**** Abaqus jobmanager')
        self.JobMan2 = PyroUtil.connectJobManager(ns,abaqusJobManName, hkey,None)
        log.info('**** Abaqus jobmanager found')
        self.app2 = None

        print('**** CMBSFE jobmanager')
        self.JobMan1 = PyroUtil.connectJobManager(ns,cmbsfeJobManName, hkey,None)
        self.app1 = None
        log.info('**** CMBSFE jobmanager found')

        try:
            print('**** Creating job 1 : CMBSFE')
            self.app1 = PyroUtil.allocateApplicationWithJobManager(ns, self.JobMan1, None, hkey, None)
            log.info('Created job 1 : CMBSFE')

            print('**** Creating job 2 : ABAQUS')
            self.app2 = PyroUtil.allocateApplicationWithJobManager(ns, self.JobMan2, None, hkey, None)
            log.info('Created job 2 : ABAQUS')

        except Exception as e:
            log.exception(e)
        else:
            if (self.app1 != None):
                SolverSignature=self.app1.getApplicationSignature()
                log.info("*** Working CMBSFE solver on server " + SolverSignature)
            if (self.app2 != None):
                SolverSignature=self.app2.getApplicationSignature()
                log.info("*** Working ABAQUS solver on server " + SolverSignature)
            else:
                log.debug("Connection to server failed, exiting")
                           
            
    def setProperty(self, property, objectID=0):
        propID = property.getPropertyID()
        if (propID in self.myCompulsoryPropIDs):
            self.myInputPropIDs.append(propID)
            self.myInputProps[propID]=property
        else:
            raise APIError.APIError('Unknown property ID', propID)

    def getProperty(self, propID, time, objectID=0):
        MetaDataToData = { # define metadata
            'Execution' : {
                'ID' : self.getMetadata('Execution.ID'),
                'Use_case_ID' : self.getMetadata('Execution.Use_case_ID'),
                'Task_ID' : self.getMetadata('Execution.Task_ID')}
        }

        if (propID in self.myMacroOutPropIDs):
            return self.myMacroOutProps[propID]
        elif (propID in self.myMicroOutPropIDs):
            return self.myMicroOutProps[propID]
        else:
            raise APIError.APIError ('Unknown property ID', propID) 
               
    def solve(self, runInBackground=False):

        for cID in self.myCompulsoryPropIDs:
            if cID not in self.myInputProps:
                raise APIError.APIError (self.getApplicationSignature(), 
                                         ' Missing compulsory property ', cID)   
        try:
            for propid in self.myInputPropIDs:
                self.app1.setProperty(self.myInputProps[propid], 
                                        objectID=self.myInputPropDomIDs[propid])
        except Exception as err:
            print("Setting LIST CmbsFE params failed: " + repr(err));
            self.terminate()

        try:
            # solve using  LIST CmbsFE solver
            log.info("Running LIST CmbsFE solver")
            try :
                istep = TimeStep.TimeStep(1., 1., 1.,'s',1)
                print('CMBSFE solve',istep)
                self.app1.solveStep(istep, stageID=1, runInBackground=False)
                print('CMBSFE solved')
            except Exception as e:
                print("\n An exception was thrown! \n")
                log.error("Cmbsfe computation FAILED")
                print(str(e))

            ## get properties from CmbsFE and set the properties for Abaqus
            for propID in self.myMicroOutPropIDs:
                prop = self.app1.getProperty(propID)
                self.myMicroOutProps[propID] = prop
                self.app2.setProperty(prop)
                
            # solve using LIST Abaqus solver
            log.info("Running LIST Abaqus solver")
            
            try :
                istep = TimeStep.TimeStep(1., 1., 1.,'s',1)
                print('ABAQUS solve',istep)
                self.app2.solveStep(istep, stageID=1, runInBackground=False)
                print('ABAQUS solved')
            except Exception as e:
                print("\n An exception was thrown! \n")
                log.error("ABAQUS computation FAILED")
                print(str(e))

            print('*** use case workflow solve : solved')
                
            ## get KPIs from Abaqus
            print('*** Get KPIs:',self.myMacroOutPropIDs)
            for propID in self.myMacroOutPropIDs:
                prop = self.app2.getProperty(propID)
                self.myMacroOutProps[propID] = prop
                
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()
            
    def terminate(self):
        self.app1.terminate()
        self.app2.terminate()
        super(DowWorkflow, self).terminate()

    def getCriticalTimeStep(self):
        return min(self.app1.getCriticalTimeStep(), 
                   self.app2.getCriticalTimeStep())
        
    def getApplicationSignature(self):
        return "Dow Workflow for simple multiscale model"
    
    def getAPIVersion(self):
        return "2.0.0"
    
def workflow_execution(inputGUID, execGUID):

    workflow = DowWorkflow()
    workflowID = { 'Execution': { 'ID': '1', 'Use_case_ID': '1_1', 'Task_ID': '1'}}

    # Define properties: units to export
    propsToExp = {"Matrix Young modulus": "MPa",
                  "Matrix Poisson ratio": "",
                  "Inclusion Young modulus 1": "MPa",
                  "Inclusion Young modulus 3": "MPa",
                  "Inclusion Young modulus 3": "MPa",
                  "Inclusion Poisson ratio 12": "",
                  "Inclusion Poisson ratio 13": "",
                  "Inclusion Poisson ratio 23": "",
                  "Inclusion Shear modulus 12": "MPa",
                  "Inclusion Shear modulus 13": "MPa",
                  "Inclusion Shear modulus 23": "MPa"
                  }

    # Andrea
    # Export data from database
    #ExportedData = miu.ExportData("MI_Composelector", "Inputs-Outputs", inputGUID, propsToExp, miu.unitSystems.METRIC)
    #matrixYoung = ExportedData["Matrix Young modulus"]
    #matrixPoisson = ExportedData["Matrix Poisson ratio"]
    #inclusionYoung1 = ExportedData["Inclusion Young modulus 1"]
    #inclusionYoung2 = ExportedData["Inclusion Young modulus 2"]
    #inclusionYoung3 = ExportedData["Inclusion Young modulus 3"]
    #inclusionPoisson12 = ExportedData["Inclusion Poisson ratio 12"]
    #inclusionPoisson13 = ExportedData["Inclusion Poisson ratio 13"]
    #inclusionPoisson23 = ExportedData["Inclusion Poisson ratio 23"]
    #inclusionShear13 = ExportedData["Inclusion Shear modulus 13"]
    #inclusionShear23 = ExportedData["Inclusion Shear modulus 23"]
    #inclusionShear12 = ExportedData["Inclusion Shear modulus 12"]

    # Matrix properties
    matrixYoung = 4.0E+3
    matrixPoisson = 0.32
    
    # Inclusion properties
    inclusionYoung1 = 15.00E+3
    inclusionYoung2 = 15.00E+3
    inclusionYoung3 = 230.0E+3
    
    inclusionPoisson12 = 0.07
    inclusionPoisson13 = 0.20
    inclusionPoisson23 = 0.20
    
    inclusionShear12 = 7.00E+3
    inclusionShear13 = 15.0E+3
    inclusionShear23 = 15.0E+3
        
    # define input file names
    afile1='compositeUD.msh'
    afile2='compositeUD.inp'
    cfile1='abaqus_v6.env'
    cfile2='leafSpring-v2.inp'

    try:
        
        workflowMD = workflowID.copy()

        workflowMD['Inputs'] = [
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_EModulus',  'Name': 'matrixYoung', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio',  'Name': 'matrixPoisson', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_YoungModulus1',  'Name': 'inclusionYoung1', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_YoungModulus2',  'Name': 'inclusionYoung2', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_YoungModulus3',  'Name': 'inclusionYoung3', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio12',  'Name': 'inclusionPoisson12', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio13',  'Name': 'inclusionPoisson13', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio23',  'Name': 'inclusionPoisson23', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_ShearModulus12',  'Name': 'inclusionShear12', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_ShearModulus13',  'Name': 'inclusionShear13', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_ShearModulus23',  'Name': 'inclusionShear23', 'Units': 'MPa', 'Required': True},
                       ]
        workflowMD['Outputs'] = [
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_Stiffness',  'Name': 'Footprint', 'Units': 'mm**2', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_maxDisplacement',  'Name': 'max. displacement', 'Units': 'mm', 'Required': True},
                       ]
#        (maxMisesStress, maxDeflection, maxPrincipalStress, stiffness) = KPIs

        app1MD=workflowID.copy()
        app2MD=workflowID.copy()

        app1MD['Outputs'] = [
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_YoungModulus1',  'Name': 'compositeYoungModulus1', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_YoungModulus2',  'Name': 'compositeYoungModulus2', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_YoungModulus3',  'Name': 'compositeYoungModulus3', 'Units': 'MPa', 'Required': True},

                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_ShearModulus12',  'Name': 'compositeShearModulus12', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_ShearModulus13',  'Name': 'compositeShearModulus13', 'Units': 'MPa', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_ShearModulus23',  'Name': 'compositeShearModulus23', 'Units': 'MPa', 'Required': True},

                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio12',  'Name': 'compositePoissonRatio12', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio13',  'Name': 'compositePoissonRatio13', 'Units': 'none', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_PoissonRatio23',  'Name': 'compositePoissonRatio23', 'Units': 'none', 'Required': True},
                       ]
        app2MD['refPoint'] = 'RP'
        app2MD['componentID'] = 2
 
        workflow.initialize(metaData=workflowMD )
        print('**** usecase metadata')
        workflow.printMetadata()
        print()

        app1MD['Inputs']=workflow.getMetadata('Inputs').copy()
        app2MD['Outputs']=workflow.getMetadata('Outputs').copy()

        ###########################################################################################
        ### START ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        # select input file location: True = application server, False: control script computer
        filesend = False

        # Define server path of input files
        print('**** copy files to working directories')
        if filesend:
            basepath=os.path.abspath('..')
            inpDir1 = os.path.join(basepath,'cmbsfeserver','inputFiles')
            inpDir2 = os.path.join(basepath,'abaqusserver','inputFiles')
        else:
            inpDir1 = os.path.abspath('./inputFiles')
            inpDir2=inpDir1

        # identify input files
        print("Identifying input files.")
        workflow.file1 = glob.glob(os.path.join(inpDir1, afile2))[0]
        workflow.file1 = os.path.basename(workflow.file1)
        workflow.file2 = glob.glob(os.path.join(inpDir2, cfile2))[0]
        workflow.file2 = os.path.basename(workflow.file2)

        try:
            inpFiles1 = []
            inpFiles2 = []
            if filesend:
                inpFiles1.extend(glob.glob(os.path.join(inpDir1, afile1)))
                inpFiles1.extend(glob.glob(os.path.join(inpDir1, afile2)))
                inpFiles2.extend(glob.glob(os.path.join(inpDir2, cfile1)))
                inpFiles2.extend(glob.glob(os.path.join(inpDir2, cfile2)))
            else:
                inpFiles1.append(afile1)
                inpFiles1.append(afile2)
                inpFiles2.append(cfile1)
                inpFiles2.append(cfile2)
        except Exception as err:
            print("Error:" + repr(err))
        
        # copy Abaqus input files to server work directories
        print("Transferring input files to the work directory.")
        if filesend:
            print("$$$ Uploading input files from application server to workdir")
            try:
                for inpFile in inpFiles1:
                    shutil.copy(inpFile, workflow.JobMan1.getJobWorkDir(workflow.app1.getJobID()))
                for inpFile in inpFiles2:
                    shutil.copy(inpFile, workflow.JobMan2.getJobWorkDir(workflow.app2.getJobID()))
            except Exception as err:
                print("Error:" + repr(err))
        else:
            print("$$$ Uploading input files from control computer to workdir")
            log.info("Uploading input files to server")
            try:
                for inpFile in inpFiles1:
                    pf = workflow.JobMan1.getPyroFile(workflow.app1.getJobID(), inpFile, 'wb')
                    PyroUtil.uploadPyroFile(os.path.join(inpDir1,inpFile), pf, hkey)
                for inpFile in inpFiles2:
                    pf = workflow.JobMan2.getPyroFile(workflow.app2.getJobID(), inpFile, 'wb')
                    PyroUtil.uploadPyroFile(os.path.join(inpDir2,inpFile), pf, hkey)
            except Exception as err:
                print("Error:" + repr(err))

        ### END ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        #########################################################################################
      
        workflow.app1.initialize(metaData=app1MD, file=workflow.file1, workdir=workflow.JobMan1.getJobWorkDir(workflow.app1.getJobID()))
        workflow.app1.printMetadata()
        print()
        app2MD['Inputs']=workflow.app1.getMetadata('Outputs')
        workflow.app2.initialize(metaData=app2MD, file=workflow.file2, workdir=workflow.JobMan2.getJobWorkDir(workflow.app2.getJobID()))
        workflow.app2.printMetadata()
        print()

        # Set-up input properties to workflow
        print("Setting LIST CmbsFE properties")
        workflow.setProperty(Property.ConstantProperty(matrixYoung, PropertyID.PID_EModulus, ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(matrixPoisson, PropertyID.PID_PoissonRatio, ValueType.Scalar, "none"))
        
        workflow.setProperty(Property.ConstantProperty(inclusionYoung1, PropertyID.PID_YoungModulus1, ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(inclusionYoung2, PropertyID.PID_YoungModulus2, ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(inclusionYoung3, PropertyID.PID_YoungModulus3, ValueType.Scalar, "MPa"))
        
        workflow.setProperty(Property.ConstantProperty(inclusionPoisson12, PropertyID.PID_PoissonRatio12, ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionPoisson13, PropertyID.PID_PoissonRatio13, ValueType.Scalar, "none"))
        workflow.setProperty(Property.ConstantProperty(inclusionPoisson23, PropertyID.PID_PoissonRatio23, ValueType.Scalar, "none"))
        
        workflow.setProperty(Property.ConstantProperty(inclusionShear12, PropertyID.PID_ShearModulus12, ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(inclusionShear13, PropertyID.PID_ShearModulus13, ValueType.Scalar, "MPa"))
        workflow.setProperty(Property.ConstantProperty(inclusionShear23, PropertyID.PID_ShearModulus23, ValueType.Scalar, "MPa"))
        
        # solving the problem
        print("Solve workflow")
        workflow.solve()

        time = PQ.PhysicalQuantity(1.0, 's')
        
        # get desired properties from workflow
        # Micro-scale properties
        print("get properties from CMBSFE simulation")
        compositeYoungModulus1 = workflow.getProperty(PropertyID.PID_YoungModulus1,time).inUnitsOf('MPa').getValue()
        compositeYoungModulus2 = workflow.getProperty(PropertyID.PID_YoungModulus2,time).inUnitsOf('MPa').getValue()
        compositeYoungModulus3 = workflow.getProperty(PropertyID.PID_YoungModulus3,time).inUnitsOf('MPa').getValue()
       
        compositeShearModulus12 = workflow.getProperty(PropertyID.PID_ShearModulus12,time).inUnitsOf('MPa').getValue()
        compositeShearModulus13 = workflow.getProperty(PropertyID.PID_ShearModulus13,time).inUnitsOf('MPa').getValue()
        compositeShearModulus23 = workflow.getProperty(PropertyID.PID_ShearModulus23,time).inUnitsOf('MPa').getValue()
        
        compositePoissonRatio12 = workflow.getProperty(PropertyID.PID_PoissonRatio12,time).getValue()
        compositePoissonRatio13 = workflow.getProperty(PropertyID.PID_PoissonRatio13,time).getValue()
        compositePoissonRatio23 = workflow.getProperty(PropertyID.PID_PoissonRatio23,time).getValue()
        
        # Macro-scale properties (KPIs)
        print("get KPIs from ABAQUS simulation")
#        (maxMisesStress, maxDeflection, maxPrincipalStress, stiffness) = KPIs
        
#        #maxMisesStress /= 1.0e+6      # In MPa
#        #maxDeflection *= 1.0e+3       # In mm
#        #maxPrincipalStress /= 1.0e+6  # In MPa
#        #stiffness /= 1.0e+6           # In kN/mm
        
#        print("KPIs: ",(maxMisesStress, maxDeflection, maxPrincipalStress, stiffness))
        
#        print('ok')
#        workflow.terminate()
        
#        for propID in  workflow.outputPropIDs:
#            prop =  workflow.app3.getProperty(propID)
#            workflow.outputProps[propID] = prop
        print('KPIs',workflow.myMacroOutProps)
        print('KPIs done : OK')
        
        # Define properties: units to import 
        propsToImp = {
                  "Composite Young modulus 1": "MPa",
                  "Composite Young modulus 3": "MPa",
                  "Composite Young modulus 3": "MPa",
                  "Composite Poisson ratio 12": "",
                  "Composite Poisson ratio 13": "",
                  "Composite Poisson ratio 23": "",
                  "Composite Shear modulus 12": "MPa",
                  "Composite Shear modulus 13": "MPa",
                  "Composite Shear modulus 23": "MPa",
                  "Maximum Mises Stress": "MPa",
                  "Maximum Deflection": "mm",
                  "Maximum Principal Stress": "MPa",
                  "Stiffness": "kN/mm",
                  }
        
        # Andrea
        #ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
        #ImportHelper.CreateAttribute("Composite Young modulus 1", compositeYoungModulus1, "MPa")
        #ImportHelper.CreateAttribute("Composite Young modulus 2", compositeYoungModulus2, "MPa")
        #ImportHelper.CreateAttribute("Composite Young modulus 3", compositeYoungModulus3, "MPa")
        #ImportHelper.CreateAttribute("Composite Shear modulus 12", compositeShearModulus12, "MPa")
        #ImportHelper.CreateAttribute("Composite Shear modulus 13", compositeShearModulus13, "MPa")
        #ImportHelper.CreateAttribute("Composite Shear modulus 23", compositeShearModulus23, "MPa")
        #ImportHelper.CreateAttribute("Composite Poisson ratio 12", compositePoissonRatio12, "")
        #ImportHelper.CreateAttribute("Composite Poisson ratio 13", compositePoissonRatio13, "")
        #ImportHelper.CreateAttribute("Composite Poisson ratio 23", compositePoissonRatio23, "")
        #ImportHelper.CreateAttribute("Maximum Mises Stress", maxMisesStress, "MPa")
        #ImportHelper.CreateAttribute("Maximum Principal Stresss", maxPrincipalStress, "MPa")
        #ImportHelper.CreateAttribute("Maximum Deflection", maxDeflection, "mm")
        #ImportHelper.CreateAttribute("Stiffness", stiffness, "N/mm")
        #return ImportHelper

    except APIError.APIError as err:
        print ("Mupif API for LIST error: "+ repr(err))
    except Exception as err:
        print ("Error: " + repr(err))
    except:
        print ("Unkown error.")

if __name__=='__main__':
    workflow_execution(0,0)
            
            

