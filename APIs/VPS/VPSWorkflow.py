# -*- coding: utf-8 -*-
"""
Created on Mon Jul  9 13:56:16 2018

@author: SLL
"""
#%% Load packages
import sys
from   mupif_esi_vps_api import VPS_API
from   mupif import *
import logging
import mupif.Physics.PhysicalQuantities as PQ

#%% Load VPS config
from Config import config

#%% Load log
log = logging.getLogger()

#%% Workflow definition
class VPSWorkflow(Workflow.Workflow):

    def __init__(self,workdir='', targetTime=PQ.PhysicalQuantity('0 s'),execMode=0,modelID=1):
        """
        Initializes the workflow. As the workflow is non-stationary, we allocate individual
        applications and store them within a class.
        """
        super(VPSWorkflow, self).__init__(file='', workdir='', targetTime=targetTime)

        if modelID==1: # Airbus fuselage failure analysis
           #list of recognized input porperty IDs
           self.myInputPropIDs = [PropertyID.PID_ESI_VPS_PLY1_E0t1,
                                  PropertyID.PID_ESI_VPS_PLY1_E0t2,
                                  PropertyID.PID_ESI_VPS_PLY1_E0t3,
                                  PropertyID.PID_ESI_VPS_PLY1_E0c1,
                                  PropertyID.PID_ESI_VPS_PLY1_G012,
                                  PropertyID.PID_ESI_VPS_PLY1_G023,
                                  PropertyID.PID_ESI_VPS_PLY1_G013,
                                  PropertyID.PID_ESI_VPS_PLY1_NU12,
                                  PropertyID.PID_ESI_VPS_PLY1_NU23,
                                  PropertyID.PID_ESI_VPS_PLY1_NU13]
           #list of recognized output property IDs
           self.myOutPropIDs =  [PropertyID.PID_ESI_VPS_MOMENT_CURVE,
                                 PropertyID.PID_ESI_VPS_MOMENT_CURVE,
                                 PropertyID.PID_ESI_VPS_ROTATION_CURVE,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_MOM,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_ROT,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_LOC,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_ELE,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_PLY,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_PART]
        elif modelID==2: # Airbus fuselage static analysis
           #list of recognized input porperty IDs
           self.myInputPropIDs = [PropertyID.PID_ESI_VPS_PLY1_E0t1,
                                  PropertyID.PID_ESI_VPS_PLY1_E0t2,
                                  PropertyID.PID_ESI_VPS_PLY1_E0t3,
                                  PropertyID.PID_ESI_VPS_PLY1_E0c1,
                                  PropertyID.PID_ESI_VPS_PLY1_G012,
                                  PropertyID.PID_ESI_VPS_PLY1_G023,
                                  PropertyID.PID_ESI_VPS_PLY1_G013,
                                  PropertyID.PID_ESI_VPS_PLY1_NU12,
                                  PropertyID.PID_ESI_VPS_PLY1_NU23,
                                  PropertyID.PID_ESI_VPS_PLY1_NU13]
           #list of recognized output property IDs
           self.myOutPropIDs =  [PropertyID.PID_ESI_VPS_MOMENT_CURVE,
                                 PropertyID.PID_ESI_VPS_MOMENT_CURVE,
                                 PropertyID.PID_ESI_VPS_ROTATION_CURVE,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_MOM,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_ROT,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_LOC,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_ELE,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_PLY,
                                 PropertyID.PID_ESI_VPS_FIRST_FAILURE_PART]
        elif modelID==3: # Airbus fuselage buckling analysis
           #list of recognized input porperty IDs
           self.myInputPropIDs = [PropertyID.PID_ESI_VPS_PLY1_E0t1,
                                  PropertyID.PID_ESI_VPS_PLY1_E0t2,
                                  PropertyID.PID_ESI_VPS_PLY1_E0t3,
                                  PropertyID.PID_ESI_VPS_PLY1_E0c1,
                                  PropertyID.PID_ESI_VPS_PLY1_G012,
                                  PropertyID.PID_ESI_VPS_PLY1_G023,
                                  PropertyID.PID_ESI_VPS_PLY1_G013,
                                  PropertyID.PID_ESI_VPS_PLY1_NU12,
                                  PropertyID.PID_ESI_VPS_PLY1_NU23,
                                  PropertyID.PID_ESI_VPS_PLY1_NU13]
           #list of recognized output property IDs
           self.myOutPropIDs =  [PropertyID.PID_ESI_VPS_BUCKL_LOAD]
        else:
           log.debug("Unknown model ID, exiting.")

        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        # Allocate VPS API
        self.VPS_API = None
        if execMode==0:
           try:
              # Allocate local VPS API instance
              self.VPS_API = VPS_API(workdir=workdir,modelID=modelID)
              log.info('Created ESI VPS local application interface')
           except Exception as err:
               log.exception("Allocating local VPS API failed: " + repr(err))
        elif execMode==1:
           # Get configuration
           cfg=config(mode=2)

           #locate nameserver
           ns = PyroUtil.connectNameServer(cfg.nshost, cfg.nsport, cfg.hkey)
           #connect to JobManager running on (remote) server
           self.vpsJobMan = PyroUtil.connectJobManager(ns, cfg.jobManName,cfg.hkey)

           # Allocate remote ESI VPS instance
           try:
               self.VPS_API = PyroUtil.allocateApplicationWithJobManager( ns, self.vpsJobMan, None, cfg.hkey, sshContext=None)
               log.info('Created ESI VPS remote application interface')
           except Exception as err:
               log.exception("Allocating VPS jobmanager failed: " + repr(err))
           else:
               if ((self.VPS_API is not None)):
                   VPS_APISignature=self.VPS_API.getApplicationSignature()
                   log.info("Working ESI VPS solver on server " + VPS_APISignature)
               else:
                   log.debug("Connection to server failed, exiting.")


    def setProperty(self, property, objectID=0):
        propID = property.getPropertyID()
        if (propID in self.myInputPropIDs):
            self.myInputProps[propID]=property
        else:
            raise APIError.APIError('Property ID is no valid input for current model', propID)

    def getProperty(self, propID, time, objectID=0):
        if (propID in self.myOutPropIDs):
            return self.myOutProps[propID]
        else:
            raise APIError.APIError('Property ID is no valid output for current model', propID)

    def solveStep(self, istep, stageID=0, runInBackground=False):

        for cID in self.myCompulsoryPropIDs:
            if cID not in self.myInputProps:
                raise APIError.APIError (self.getApplicationSignature(), ' Missing compulsory property ', cID)
            else:
               try:
                  self.VPS_API.setProperty(self.myInputProps[cID])
               except Exception as err:
                  log.exception("Setting VPS property failed: " + repr(err));
                  self.terminate()

        try:
            # Execute ESI VPS solver
            log.info("Running ESI VPS solver")
            self.VPS_API.solveStep(runInBackground=runInBackground)

        except Exception as err:
            log.exception("Launching VPS solver failed: " + repr(err))
            self.terminate()

        # set the desired properties
        for cID in self.myOutPropIDs:
            self.myOutProps[cID] = self.VPS_API.getProperty(cID, 0.0)
    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        #self.thermalAppRec.terminateAll()
        #self.VPS_API.terminate()
        super(VPSWorkflow, self).terminate()

    def getApplicationSignature(self):
        return "Composelector ESI VPS workflow"

    def getAPIVersion(self):
        return "1.0"


if __name__=='__main__':

    # Define execution mode (0: local, 1: remote)
    execMode = 1

    # Specify model ID
    # modelID = 1 # AIRBUS fuselage explicit failure analysis
    # modelID = 2 # AIRBUS fuselage implicit stiffness analysis
    # modelID = 3 # AIRBUS fuselage implicit buckling analysis
    modelID = 3

    #Specify workdir for the local execution mode (remote its defined by the job manager)
    hostname = socket.gethostname()
    if hostname == 'NEULAP021':
        workdir = 'D:/workspace/Composite_VP_CoE/Python/COMPOSELECTOR/Output/01_AIRBUS_Fuselage_model/03_buckl/'
    elif hostname == 'STUVWO003':
        workdir = '/home/CSuser/COMPOSELECTOR/Output/01_AIRBUS_Fuselage_model/03_buckl/'

    # Initialze VPS workflow
    workflow = VPSWorkflow(workdir=workdir, targetTime=PQ.PhysicalQuantity(1.,'s'),execMode=execMode,modelID=modelID)

    # Set composite stiffness properties
    workflow.setProperty(Property.ConstantProperty(160.  , PropertyID.PID_ESI_VPS_PLY1_E0t1, ValueType.Scalar, 'MPa'))
    workflow.setProperty(Property.ConstantProperty( 11.  , PropertyID.PID_ESI_VPS_PLY1_E0t2, ValueType.Scalar, 'MPa'))
    workflow.setProperty(Property.ConstantProperty( 11.  , PropertyID.PID_ESI_VPS_PLY1_E0t3, ValueType.Scalar, 'MPa'))
    workflow.setProperty(Property.ConstantProperty(130.  , PropertyID.PID_ESI_VPS_PLY1_E0c1, ValueType.Scalar, 'MPa'))
    workflow.setProperty(Property.ConstantProperty(  0.35, PropertyID.PID_ESI_VPS_PLY1_NU12, ValueType.Scalar, PQ.getDimensionlessUnit()))
    workflow.setProperty(Property.ConstantProperty(  0.35, PropertyID.PID_ESI_VPS_PLY1_NU23, ValueType.Scalar, PQ.getDimensionlessUnit()))
    workflow.setProperty(Property.ConstantProperty(  0.35, PropertyID.PID_ESI_VPS_PLY1_NU13, ValueType.Scalar, PQ.getDimensionlessUnit()))
    workflow.setProperty(Property.ConstantProperty(  5.3 , PropertyID.PID_ESI_VPS_PLY1_G012, ValueType.Scalar, 'MPa'))
    workflow.setProperty(Property.ConstantProperty(  5.3 , PropertyID.PID_ESI_VPS_PLY1_G023, ValueType.Scalar, 'MPa'))
    workflow.setProperty(Property.ConstantProperty(  5.3 , PropertyID.PID_ESI_VPS_PLY1_G013, ValueType.Scalar, 'MPa'))

    # Execute the solver
    workflow.solve()

    print (workflow.myOutProps)

