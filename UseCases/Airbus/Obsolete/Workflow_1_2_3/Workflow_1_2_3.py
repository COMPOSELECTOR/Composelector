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
    import ApplicationsConfigs.LAMMPS_v3 as lammps
else:
    import LAMMPS_v4 as lammps
    


nshost = '172.30.0.1'
nsport = 9090
hkey = 'mupif-secret-key'
digimatJobManName='eX_DigimatMF_JobManager'
mul2JobManName='MUL2.JobManager@UseCase1'

class Workflow_1_2_3(Workflow.Workflow):

    def __init__(self, metaData={}):
        """
        Initializes the workflow.
        """

        MD = {
            'Name': 'Airbus Case',
            'ID': '1_2_2',
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

        super(Workflow_1_2_3, self).__init__(metaData=MD)
        self.updateMetadata(metaData)        

        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_SMILE_MOLECULAR_STRUCTURE,PropertyID.PID_MOLECULAR_WEIGHT, PropertyID.PID_CROSSLINKER_TYPE,PropertyID.PID_FILLER_DESIGNATION, PropertyID.PID_CROSSLINKONG_DENSITY,PropertyID.PID_FILLER_CONCENTRATION, PropertyID.PID_TEMPERATURE, PropertyID.PID_PRESSURE, PropertyID.PID_POLYDISPERSITY_INDEX,PropertyID.PID_SMILE_MODIFIER_MOLECULAR_STRUCTURE,PropertyID.PID_SMILE_FILLER_MOLECULAR_STRUCTURE,PropertyID.PID_DENSITY_OF_FUNCTIONALIZATION, PropertyID.PID_InclusionYoung, PropertyID.PID_InclusionPoisson, PropertyID.PID_InclusionVolumeFraction, PropertyID.PID_InclusionAspectRatio]
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_EModulus, PropertyID.PID_PoissonRatio, PropertyID.PID_DENSITY, PropertyID.PID_effective_conductivity, PropertyID.PID_TRANSITION_TEMPERATURE, PropertyID.PID_CriticalLoadLevel, PropertyID.PID_CompositeAxialYoung, PropertyID.PID_CompositeInPlaneYoung, PropertyID.PID_CompositeInPlaneShear, PropertyID.PID_CompositeTransverseShear, PropertyID.PID_CompositeInPlanePoisson, PropertyID.PID_CompositeTransversePoisson]

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        # solvers
        self.lammpsSolver = None 
        self.digimatSolver = None
        self.mul2Solver = None
    


    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(0., 's'), metaData={}, validateMetaData=True, **kwargs):

        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to digimat JobManager running on (remote) server
        self.digimatJobMan = PyroUtil.connectJobManager(ns, digimatJobManName,hkey)
        #connect to mult2 JobManager running on (remote) server
        self.mul2JobMan = PyroUtil.connectJobManager(ns, mul2JobManName,hkey)

        #allocate the Digimat remote instance
        try:
            log.info('Created LAMMPS job')
            self.lammpsSolver = lammps.LAMMPS_API()
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created digimat job')
            self.mul2Solver = PyroUtil.allocateApplicationWithJobManager( ns, self.mul2JobMan, None, hkey)
            log.info('Created mul2 job')            
        except Exception as e:
            log.exception(e)
        else:
            if ((self.lammpsSolver is not None) and (self.digimatSolver is not None) and (self.mul2Solver is not None)):
                lammpsSolverSignature=self.lammpsSolver.getApplicationSignature()
                log.info("Working lammps solver on server " + lammpsSolverSignature)
                digimatSolverSignature=self.digimatSolver.getApplicationSignature()
                log.info("Working digimat solver on server " + digimatSolverSignature)
                mul2SolverSignature=self.mul2Solver.getApplicationSignature()
                log.info("Working mul2 solver on server " + mul2SolverSignature)
            else:
                log.debug("Connection to server failed, exiting")


        super(Workflow_1_2_3, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)

        # To be sure update only required passed metadata in models
        passingMD = {
            'Execution': {
                'ID': self.getMetadata('Execution.ID'),
                'Use_case_ID': self.getMetadata('Execution.Use_case_ID'),
                'Task_ID': self.getMetadata('Execution.Task_ID')
            }
        }        
        self.lammpsSolver.initialize(metaData=passingMD)
        self.digimatSolver.initialize(metaData=passingMD)
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
            
        try:
            # lammps 
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_SMILE_MOLECULAR_STRUCTURE])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_MOLECULAR_WEIGHT])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_CROSSLINKER_TYPE])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_FILLER_DESIGNATION])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_CROSSLINKONG_DENSITY])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_FILLER_CONCENTRATION])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_TEMPERATURE])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_PRESSURE])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_POLYDISPERSITY_INDEX])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_SMILE_MODIFIER_MOLECULAR_STRUCTURE])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_SMILE_FILLER_MOLECULAR_STRUCTURE])
            self.lammpsSolver.setProperty(self.myInputProps[PropertyID.PID_DENSITY_OF_FUNCTIONALIZATION])
	    # solve (involves operator interaction)
            self.lammpsSolver.solveStep (TimeStep.TimeStep(0.0, 0.1, 1, 's'))
            # get result of the simulation
            matrixYoung = self.lammpsSolver.getProperty(PropertyID.PID_EModulus, 0.0)
            matrixPoisson = self.lammpsSolver.getProperty(PropertyID.PID_PoissonRatio, 0.0)
            matrixDensity = self.lammpsSolver.getProperty(PropertyID.PID_DENSITY, 0.0)
            matrixThermalConductivity = self.lammpsSolver.getProperty(PropertyID.PID_effective_conductivity, 0.0)
            matrixGlassTransitionTemperature = self.lammpsSolver.getProperty(PropertyID.PID_TRANSITION_TEMPERATURE,0.0)

            self.myOutProps[PropertyID.PID_EModulus] = matrixYoung
            self.myOutProps[PropertyID.PID_PoissonRatio] = matrixPoisson
            self.myOutProps[PropertyID.PID_DENSITY] = matrixDensity
            self.myOutProps[PropertyID.PID_effective_conductivity] = matrixThermalConductivity
            self.myOutProps[PropertyID.PID_TRANSITION_TEMPERATURE] = matrixGlassTransitionTemperature

        except Exception as err:
            print ("Error:" + repr(err))
            self.terminate()
        # digimat
        try:
            # map properties from lammps to properties of Digimat
            matrixYoung.propID = PropertyID.PID_MatrixYoung
            matrixPoisson.propID = PropertyID.PID_MatrixPoisson
            self.digimatSolver.setProperty(matrixYoung)
            self.digimatSolver.setProperty(matrixPoisson)
            # fixed properties - taken form the database
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
            print ("Digimat Error: " + repr(err))
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
        self.lammpsSolver.terminate()
        self.digimatSolver.terminate()
        self.mul2Solver.terminate()
        super(Workflow_1_2_3, self).terminate()

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
        
        #Define properties:units to export
        propsToExp = {"Monomer molecular structure (SMILE representation)":"",
                      "Polymer molecular weight":"",
                      "Polydispersity index":"",
                      "Crosslinker type (SMILE representation)":"",
                      "Filler designation":"",
                      "Filler modifier molecular structure (SMILE representation)":"",
                      "Polymer/Filler compatibilizer molecular structure (SMILE representation)":"",
                      "Crosslinking density":"%",
                      "Filler concentration":"%w/w",
                      "Density of functionalization":"n/nm^2",
                      "Temperature":"°C",
                      "Pressure":"atm",
                      "Inclusion Young's modulus": "MPa",
                      "Inclusion Poisson's ratio": "",
                      "Inclusion volume fraction": "%",
                      "Inclusion aspect ratio": ""
        }
        
        #Export data from database
        ExportedData = miu.ExportData("MI_Composelector","Inputs-Outputs",inputGUID,propsToExp,miu.unitSystems.METRIC)
        monomerMolStructure = ExportedData["Monomer molecular structure (SMILE representation)"]
        polymerMolWeight = ExportedData["Polymer molecular weight"]
        polyIndex = ExportedData["Polydispersity index"]
        crosslinkerType = ExportedData["Crosslinker type (SMILE representation)"]
        fillerDesignation = ExportedData["Filler designation"]
        fillerModMolStructure = ExportedData["Filler modifier molecular structure (SMILE representation)"]
        polFilCompatibilizerMolStructure = ExportedData["Polymer/Filler compatibilizer molecular structure (SMILE representation)"]
        crosslinkingDens = ExportedData["Crosslinking density"]
        fillerConc = ExportedData["Filler concentration"]
        functionalizationDens = ExportedData["Density of functionalization"]
        temperature = ExportedData["Temperature"]
        pressure = ExportedData["Pressure"]
        inclusionYoung = ExportedData["Inclusion Young's modulus"]
        inclusionPoisson = ExportedData["Inclusion Poisson's ratio"]
        inclusionVolumeFraction = ExportedData["Inclusion volume fraction"]
        inclusionAspectRatio = ExportedData["Inclusion aspect ratio"]
    else:
        monomerMolStructure = 1
        polymerMolWeight = 0.5
        crosslinkerType = 2
        fillerDesignation = 1
        crosslinkingDens = 1
        fillerConc = 1
        temperature = 10
        pressure = 20
        polyIndex = 1
        fillerModMolStructure = 3
        polFilCompatibilizerMolStructure = 2
        functionalizationDens = 0.3
        inclusionYoung = 1000
        inclusionPoisson = 0.2
        inclusionVolumeFraction = 0.5
        inclusionAspectRatio = 1        
                

    try:
        workflow = Workflow_1_2_3()
        workflowMD = {
            'Execution': {
                'ID': '1',
                'Use_case_ID': '1_1',
                'Task_ID': '1'
            }
        }
        workflow.initialize(targetTime=PQ.PhysicalQuantity(1., 's'), metaData=workflowMD)   
        # create and set lammps material properties
        workflow.setProperty(Property.ConstantProperty(monomerMolStructure, PropertyID.PID_SMILE_MOLECULAR_STRUCTURE, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(polymerMolWeight, PropertyID.PID_MOLECULAR_WEIGHT, ValueType.Scalar, 'mol', None, 0))
        workflow.setProperty(Property.ConstantProperty(crosslinkerType, PropertyID.PID_CROSSLINKER_TYPE, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(fillerDesignation, PropertyID.PID_FILLER_DESIGNATION, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(crosslinkingDens, PropertyID.PID_CROSSLINKONG_DENSITY, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(fillerConc, PropertyID.PID_FILLER_CONCENTRATION, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(temperature, PropertyID.PID_TEMPERATURE, ValueType.Scalar, 'degC', None, 0))
        workflow.setProperty(Property.ConstantProperty(pressure, PropertyID.PID_PRESSURE, ValueType.Scalar, 'atm', None, 0))
        workflow.setProperty(Property.ConstantProperty(polyIndex, PropertyID.PID_POLYDISPERSITY_INDEX, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(fillerModMolStructure, PropertyID.PID_SMILE_MODIFIER_MOLECULAR_STRUCTURE, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(polFilCompatibilizerMolStructure, PropertyID.PID_SMILE_FILLER_MOLECULAR_STRUCTURE, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(functionalizationDens, PropertyID.PID_DENSITY_OF_FUNCTIONALIZATION, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(inclusionYoung, PropertyID.PID_InclusionYoung,  ValueType.Scalar, 'MPa', None, 0))
        workflow.setProperty(Property.ConstantProperty(inclusionPoisson, PropertyID.PID_InclusionPoisson, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(inclusionVolumeFraction, PropertyID.PID_InclusionVolumeFraction, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))
        workflow.setProperty(Property.ConstantProperty(inclusionAspectRatio, PropertyID.PID_InclusionAspectRatio, ValueType.Scalar, PQ.getDimensionlessUnit(), None, 0))

        
        # solve workflow
        workflow.solve()
        time = PQ.PhysicalQuantity(1.0, 's')
        
        # get LAMMPS outputs
        matrixDensity = workflow.getProperty(PropertyID.PID_DENSITY, 0.0).getValue()
        matrixEmodulus = workflow.getProperty(PropertyID.PID_EModulus, 0.0).getValue()
        matrixThermalConductivity = workflow.getProperty(PropertyID.PID_effective_conductivity, 0.0).getValue()
        matrixGlassTransitionTemperature = workflow.getProperty(PropertyID.PID_TRANSITION_TEMPERATURE, 0.0).getValue()
        matrixPoissonRatio = workflow.getProperty(PropertyID.PID_PoissonRatio, 0.0).getValue()
        
        # get DigimatMF outputs
        compositeAxialYoung = workflow.getProperty(PropertyID.PID_CompositeAxialYoung, time).inUnitsOf('MPa').getValue()
        compositeInPlaneYoung = workflow.getProperty(PropertyID.PID_CompositeInPlaneYoung, time).inUnitsOf('MPa').getValue()
        compositeInPlaneShear = workflow.getProperty(PropertyID.PID_CompositeInPlaneShear, time).inUnitsOf('MPa').getValue()
        compositeTransverseShear = workflow.getProperty(PropertyID.PID_CompositeTransverseShear, time).inUnitsOf('MPa').getValue()
        compositeInPlanePoisson = workflow.getProperty(PropertyID.PID_CompositeInPlanePoisson, time).getValue()
        compositeTransversePoisson = workflow.getProperty(PropertyID.PID_CompositeTransversePoisson, time).getValue()
        
        # get MUL2 outputs
        bucklingLoad = workflow.getProperty(PropertyID.PID_CriticalLoadLevel, time).inUnitsOf('N').getValue()
        log.info("Requested KPI : Buckling Load: " + str(bucklingLoad) + ' N')
        workflow.terminate()
        log.info("Process complete")
        
        if not debug:
            # import data into database
            ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
            ImportHelper.CreateAttribute("Execution ID", execID, "")
            ImportHelper.CreateAttribute("Matrix density", matrixDensity, "g/cm^3")
            ImportHelper.CreateAttribute("Matrix Young's modulus", matrixEmodulus, "GPa")
            ImportHelper.CreateAttribute("Matrix thermal conductivity", matrixThermalConductivity, "W/m.°C")
            ImportHelper.CreateAttribute("Matrix glass transition temperature", matrixGlassTransitionTemperature, "K")
            ImportHelper.CreateAttribute("Matrix Poisson's ratio", matrixPoissonRatio, "")
            ImportHelper.CreateAttribute("Axial Young's modulus", compositeAxialYoung, "MPa")
            ImportHelper.CreateAttribute("In-plane Young's modulus", compositeInPlaneYoung, "MPa")
            ImportHelper.CreateAttribute("In-plane shear modulus", compositeInPlaneShear, "MPa")
            ImportHelper.CreateAttribute("Transverse shear modulus", compositeTransverseShear, "MPa")
            ImportHelper.CreateAttribute("In-plane Poisson's ratio", compositeInPlanePoisson, "")
            ImportHelper.CreateAttribute("Transverse Poisson's ratio", compositeTransversePoisson, "")
            ImportHelper.CreateAttribute("Buckling Load", bucklingLoad, "N")
            return ImportHelper
        
        
    except APIError.APIError as err:
        print ("Mupif API for Workflow_1_2_3 error: " + repr(err))
    except Exception as err:
        print ("Error: " + repr(err))
    except:
        print ("Unknown error.")
        
        


if __name__=='__main__':
    workflow(0,0)
