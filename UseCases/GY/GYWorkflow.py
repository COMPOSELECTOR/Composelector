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
from mupif import TimeStep

import mupif.Physics.PhysicalQuantities as PQ

nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
digimatJobManName='eX_DigimatMF_GYR_JobManager'
abaqusJobManName='Abaqus@Mupif.LIST'

###########################################################################################
### START ::: THIS PART CAN BE REMOVED ONCE USER-DEFINED PROP IDs ARE INTEGRATED INTO MUPIF
# this directory definition is required for import user-defined property IDs
# data ID definitions not yet incorporated into Mupif
### END ::: THIS PART CAN BE REMOVED ONCE USER-DEFINED PROP IDs ARE INTEGRATED INTO MUPIF
#########################################################################################

log = logging.getLogger()

start = timeT.time()
log.info('Timer started')

class LISTWorkflow(Workflow.Workflow):
        
    def __init__(self, metaData={}):
        """
        Workflow for Dow use case. version 2. for mupif 2.2
        """
        MD = {
            'Name': 'Goodyear use case simple workflow',
            'ID': 'Goodyear-1',
            'Description': 'simple twoscale mechanical model',
            'Model_refs_ID': ['MicroMechanical','MacroMechanical'],
        }

        super(LISTWorkflow, self).__init__(metaData=MD)
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

        super(LISTWorkflow, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        if PQ.isPhysicalQuantity(targetTime):
            self.targetTime = targetTime
        else:
            raise TypeError('targetTime is not PhysicalQuantity')

        self.updateMetadata(metaData)
        # define futher app metadata

        # list of recognized input property IDs
        self.inputPropIDs = []
        
        # dictionary of input properties (values)
        self.inputProps = {}
        
        # dictionary of output properties (values)
        self.outputProps = {}
        
        sshContext = None
#       locate nameserver
        ns = PyroUtil.connectNameServer(nshost=nshost, nsport=nsport, hkey=hkey)
        log.info('**** nameserver connected')
#       connect to JobManager running on (remote) server
        print('**** Abaqus jobmanager',sshContext)
        self.abaqusJobMan = PyroUtil.connectJobManager(ns,abaqusJobManName, hkey,sshContext)
        log.info('**** Abaqus jobmanager found')
        self.abaqusApp = None
        print('**** Digimat jobmanager')
        self.digimatJobMan = PyroUtil.connectJobManager(ns,digimatJobManName, hkey,sshContext)
        self.digimatApp = None
        log.info('**** Digimat jobmanager found')
#       allocate the application instances
#print('**** creating job on', jobManName)
        try:
            print('**** Creating job 2 : DIGIMAT-MF')
            self.digimatApp = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created job 2 : DIGIMAT-MF')

            print('**** Creating job 3 : ABAQUS')
            self.abaqusApp = PyroUtil.allocateApplicationWithJobManager( ns, self.abaqusJobMan, None, hkey)
            log.info('Created job 3 : ABAQUS')

        except Exception as e:
            log.exception(e)
        else:
            if (self.abaqusApp != None):
                SolverSignature=self.abaqusApp.getApplicationSignature()
                log.info("*** Working ABAQUS solver on server " + SolverSignature)
            else:
                log.debug("Connection to server failed, exiting")
                           
#        # create list of compulsory input IDs from metadata
#        self.CompulsoryPropIDs = {}
#        print('create list of compulsory input IDs from metadata')
#        for data in self.getMetadata("Inputs"):
#            self.CompulsoryPropIDs[eval(data['Type_ID'])] = (data['Name'], data['Units'])
#        print('required PropIDs',self.CompulsoryPropIDs)
        
        # create list of recognized outputs property IDs from metadata
        self.outputPropIDs={}
        print('create list of recognized outputs property IDs from metadata')
        for data in self.getMetadata("Outputs"):
            self.outputPropIDs[eval(data['Type_ID'])] = (data['Name'], data['Units'])
        print('outputPropsIDs',self.outputPropIDs)
        
        print('USE CASE WORKFLOW INITIALIZATION DONE')
            
    def setProperty(self, property, objectID=0):
        propID = property.getPropertyID()
        if (propID in self.CompulsoryPropIDs):
            self.inputPropIDs.append(propID)
            self.inputProps[propID]=property
        else:
            raise APIError.APIError('Unknown property ID', propID)

    def getProperty(self, propID, time, objectID=0):
        MetaDataToData = { # define metadata
            'Execution' : {
                'ID' : self.getMetadata('Execution.ID'),
                'Use_case_ID' : self.getMetadata('Execution.Use_case_ID'),
                'Task_ID' : self.getMetadata('Execution.Task_ID')}
        }

        if (propID in self.outputPropIDs):
            return self.outputProps[propID]
        else:
            raise APIError.APIError ('Unknown property ID', propID) 
               
    def solve(self, runInBackground=False):

        print('*** entering use case workflow solve method')
        for cID in self.CompulsoryPropIDs:
            if cID not in self.inputProps:
                raise APIError.APIError (self.getApplicationSignature(), 
                                         ' Missing compulsory property ', cID)   
        try:
            for propID in self.inputPropIDs:
                property = self.inputProps[propID]
                self.abaqusApp.setProperty(property)
                
            try :
                istep = TimeStep.TimeStep(1., 1., 1.,'s',1)
                print('ABAQUS solve',istep)
                self.abaqusApp.solveStep(istep, stageID=1, runInBackground=False)
                print('ABAQUS solved')
            except Exception as e:
                print("\n An exception was thrown! \n")
                log.error("ABAQUS computation FAILED")
                print(str(e))

            print('*** use case workflow solve : solved')
                
        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()
            
    def terminate(self):
        self.digimatApp.terminate()
        self.abaqusApp.terminate()
        print("\nterminate \n=======")
        self.digimatJobMan.terminate()
        self.abaqusJobMan.terminate()

        super(LISTWorkflow, self).terminate()

    def getCriticalTimeStep(self):
        return min(self.abaqusApp.getCriticalTimeStep(),self.digimatApp.getCriticalTimeStep())
        
    def getApplicationSignature(self):
        return "LIST Workflow"
    
    def getAPIVersion(self):
        return "2.0.0"
    
def workflow_execution(inputGUID, execGUID):

    workflow = LISTWorkflow()
    workflowID = { 'Execution': { 'ID': '1', 'Use_case_ID': '1_1', 'Task_ID': '1'}}

#    # Define properties: units to export
#    propsToExp = {"Matrix Young modulus": "MPa",
#                  "Inclusion Shear modulus 23": "MPa"
#                  }

    # Andrea
    # Export data from database
    #ExportedData = miu.ExportData("MI_Composelector", "Inputs-Outputs", inputGUID, propsToExp, miu.unitSystems.METRIC)
    #matrixYoung = ExportedData["Matrix Young modulus"]

    # set input properties for DigimatMF microscale model
    MatrixOgdenModulus_values = [8.740000000000001e-02, 1.180000000000000e-07, 4.700000000000000e-01]
    MatrixOgdenExponent_values= [3.250000000000000e+00, 1.128000000000000e+01, 7.400000000000000e-01]
    InclusionModulus = 72000.
    InclusionPoisson = 0.22
    Volumefraction = 0.40

    try:
        
        workflowMD = workflowID.copy()
        workflowMD['Inputs'] = [
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_MatrixOgdenModulus',  'Name': 'Ogden Moduli', 'Units': 'MPa', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_MatrixOgdenExponent',  'Name': 'Ogden Exponent', 'Units': 'none', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_InclusionYoung',  'Name': 'Inclusion Young', 'Units': 'MPa', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_InclusionPoisson',  'Name': 'Inclusion Poisson', 'Units': 'none', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_InclusionVolumeFraction',  'Name': 'Volume Fraction', 'Units': 'none', 'Required': True},
        ]
        workflowMD['Outputs'] = [
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_Footprint',  'Name': 'Footprint', 'Units': 'mm**2', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_Braking_Force',  'Name': 'Braking Force', 'Units': 'N', 'Required': True},
        ]
        abaqusAppMD=workflowID.copy()
        abaqusAppMD['Inputs'] = [
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_Hyper1',  'Name': 'E1', 'Units': 'MPa', 'Required': True},
                       ]
        abaqusAppMD['Outputs'] = [
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_Footprint',  'Name': 'Footprint', 'Units': 'mm**2', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'PropertyID.PID_Braking_Force',  'Name': 'Braking Force', 'Units': 'N', 'Required': True},
                       ]
        abaqusAppMD['refPoint'] = 'RF-1'
        abaqusAppMD['componentID'] = 1
 
        workflow.initialize(metaData=workflowMD )
        print('**** usecase metadata')
        workflow.printMetadata()
        print()

        # initialize DigimatMF
        print('Initializing Digimat')
        digimatAppMD=workflowID.copy()
        digimatAppMD['Inputs'] = [
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_MatrixOgdenModulus',  'Name': 'Ogden Moduli', 'Units': 'MPa', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_MatrixOgdenExponent',  'Name': 'Ogden Exponent', 'Units': 'none', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionYoung',  'Name': 'Inclusion Young', 'Units': 'MPa', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionPoisson',  'Name': 'Inclusion Poisson', 'Units': 'none', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_InclusionVolumeFraction',  'Name': 'Volume Fraction', 'Units': 'none', 'Required': True},
        ]
        digimatAppMD['Outputs'] = [
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeStress11Tensor',  'Name': 'axial stress vector', 'Units': 'MPa', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeStrain11Tensor',  'Name': 'axial strain vector', 'Units': 'none', 'Required': True},
            {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CompositeStrain22Tensor',  'Name': 'transverse stress vector', 'Units': 'none', 'Required': True},
        ]
        workflow.digimatApp.initialize(metaData=digimatAppMD, validateMetaData = False)
		
        # set hyperelastic properties for DigimatMF
        workflow.digimatApp.setProperty(Property.ConstantProperty(tuple(MatrixOgdenModulus_values), PropertyID.PID_MatrixOgdenModulus, ValueType.Scalar, "MPa"))
        workflow.digimatApp.setProperty(Property.ConstantProperty(tuple(MatrixOgdenExponent_values), PropertyID.PID_MatrixOgdenExponent, ValueType.Scalar, "none"))

        # set inclusion properties for DigimatMF
        workflow.digimatApp.setProperty(Property.ConstantProperty(InclusionModulus, PropertyID.PID_InclusionYoung, ValueType.Scalar, "MPa"))
        workflow.digimatApp.setProperty(Property.ConstantProperty(InclusionPoisson, PropertyID.PID_InclusionPoisson, ValueType.Scalar, "none"))
        workflow.digimatApp.setProperty(Property.ConstantProperty(Volumefraction, PropertyID.PID_InclusionVolumeFraction, ValueType.Scalar, "none"))

        # solve DigimatMF
        print('Solve Digimat')
        workflow.digimatApp.solveStep(None)

        # get stress strain data from Digimat
        stress = workflow.digimatApp.getProperty(PropertyID.PID_CompositeStress11Tensor).getValue()
        axistrain =  workflow.digimatApp.getProperty(PropertyID.PID_CompositeStrain11Tensor).getValue()
        transtrain  = workflow.digimatApp.getProperty(PropertyID.PID_CompositeStrain22Tensor).getValue()
		
        ###########################################################################################
        ### START ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        # select input file location: True = application server, False: control script computer
        filesend = False

        print('Initializing Abaqus')
        # Define server path of Abaqus input files
        if filesend:
            basepath=os.path.abspath('..')
            inpDir2 = os.path.join(basepath,'abaqusserver','inputFiles')
        else:
            inpDir2 = os.path.abspath('./inputFiles')

#        # identify Abaqus input files
        try:
            inpFiles2 = []
            for ext in ('*.inp', '*.env'):
                if ext == '*.inp':
                    ifile = glob.glob(os.path.join(inpDir2, ext))[0]
                    ifile = os.path.basename(ifile)
                    inpFiles2.extend(glob.glob(os.path.join(inpDir2, ext)))
        except Exception as err:
            print("Error:" + repr(err))
        
        # identify Abaqus input files
        try:
            for ext in ('*.inp', '*.env'):
                if ext == '*.inp':
                    ifile = glob.glob(os.path.join(inpDir2, ext))[0]
                    ifile = os.path.basename(ifile)
        except Exception as err:
            print("Error:" + repr(err))
        

        # copy Abaqus input files to server work directories
        print("Transferring input files to the work directory.")
        if filesend:
            print("$$$ Uploading input files from application server to workdir",ifile)
            try:
                shutil.copy(os.path.join(inpDir2,"abaqus_v6.env"), workflow.abaqusJobMan.getJobWorkDir(workflow.abaqusApp.getJobID()))
                for inpFile in inpFiles2:
                    shutil.copy(inpFile, workflow.abaqusJobMan.getJobWorkDir(workflow.abaqusApp.getJobID()))
            except Exception as err:
                print("Error:" + repr(err))
        else:
            print("$$$ Uploading input files from control computer to workdir",ifile)
            log.info("Uploading input files to server")
            try:
                pf = workflow.abaqusJobMan.getPyroFile(workflow.abaqusApp.getJobID(), "abaqus_v6.env", 'wb')
                PyroUtil.uploadPyroFile(os.path.join(inpDir2,"abaqus_v6.env"), pf, hkey)
                mf = workflow.abaqusJobMan.getPyroFile(workflow.abaqusApp.getJobID(), ifile, 'wb')
                PyroUtil.uploadPyroFile(os.path.join(inpDir2,ifile), mf, hkey)
                print("$$$ input files uploaded on server")
            except Exception as err:
                print("Error:" + repr(err))

        ### END ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        #########################################################################################
      
        ###########################################################################################
        ### START ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        # Define path to Abaqus input files
#        inpDir2 = os.path.abspath('./inputFiles')
        ### END ::: TRANSFER ABAQUS INPUT FILES AND IDENTIFY MODEL INPUT FILE: TO BE REPLACED ???
        #########################################################################################

        # Set-up input properties to workflow
        print("Define stress strain curve data.")
        # digimat provides stress strain curves by giving stress, axial strain and transverse strain in 3 different vectors
        # here, these three vectors are assembled into one tuple for compatibility
        print('data vector length',len(stress))
        # copy stress strain curve to vector and add 1. to strain values -> stretch
        stressstrain=[]
        for i in range (0,len(stress)):
            stressstrain.append(stress[i])
        for i in range (0,len(axistrain)):
            stressstrain.append(axistrain[i])
        for i in range (0,len(transtrain)):
            stressstrain.append(transtrain[i])
        curve=tuple(stressstrain)
        # end of stress strain curve generation

        workflow.abaqusApp.initialize(file = ifile, workdir=workflow.abaqusJobMan.getJobWorkDir(workflow.abaqusApp.getJobID()), metaData = abaqusAppMD)

        # create list of compulsory input IDs from metadata
        workflow.CompulsoryPropIDs = {}
        print('create list of compulsory input IDs from metadata')
        for data in workflow.abaqusApp.getMetadata("Inputs"):
            workflow.CompulsoryPropIDs[eval(data['Type_ID'])] = (data['Name'], data['Units'])
        print('required PropIDs',workflow.CompulsoryPropIDs)
        
        print("Setting Hyper Data")
        hyperdata=Property.ConstantProperty(curve,PropertyID.PID_Hyper1, ValueType.Vector, 'none')
        workflow.setProperty(hyperdata)
        print("Hyper Data set")
        
        workflow.abaqusApp.printMetadata() 

        # solving the problem
        print("Solve workflow")
        workflow.solve()

        time = PQ.PhysicalQuantity(1.0, 's')
        
        # get desired properties from workflow
        # Macro-scale properties (KPIs)
        print("get KPIs from ABAQUS simulation")
        for propID in  workflow.outputPropIDs:
            prop =  workflow.abaqusApp.getProperty(propID)
            workflow.outputProps[propID] = prop
        print('KPIs',workflow.outputProps)
        print('KPIs done : OK')
        
#        # Define properties: units to import 
#        propsToImp = {
#                  "Composite Young modulus 1": "MPa",
#                  }
        
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

        # tentative version by Gast from the commented script above
        #ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
        #ImportHelper.CreateAttribute("Composite Young modulus 1", compositeYoungModulus1, "MPa") ## something to be done for transfer of stress-strain curves ?
        #ImportHelper.CreateAttribute("Footprint", workflow.outputProps[MyPropertyID.PID_Footprint].getValue(), workflow.outputProps[MyPropertyID.PID_Footprint].getUnits())
        #ImportHelper.CreateAttribute("Braking Force", workflow.outputProps[MyPropertyID.PID_Braking_Force].getValue(), workflow.outputProps[MyPropertyID.PID_Breaking_Force].getUnits())
        #return ImportHelper

        workflow.terminate()
        
    except APIError.APIError as err:
        print ("Mupif API for LIST error: "+ repr(err))
    except Exception as err:
        print ("Error: " + repr(err))
    except:
        print ("Unkown error.")

if __name__=='__main__':
    workflow_execution(0,0)
            
            

