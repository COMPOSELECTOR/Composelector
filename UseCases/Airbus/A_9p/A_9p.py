import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
from mupif import *
import Pyro4
import logging
log = logging.getLogger()
import time as timeT
import mupif.Physics.PhysicalQuantities as PQ
import numpy as np

from copy import deepcopy
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
comsolJobManName = 'Mupif.JobManager@INSA'
vpsJobManName= 'ESI_VPS_Jobmanager_MUPIF_v2.2'

class Airbus_Workflow_9p(Workflow.Workflow):

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

        super(Airbus_Workflow_9p, self).__init__(metaData=MD)
        self.updateMetadata(metaData)

        #list of recognized input porperty IDs
        self.myInputPropIDs = [PropertyID.PID_MatrixYoung, PropertyID.PID_MatrixPoisson, PropertyID.PID_InclusionYoung, PropertyID.PID_InclusionPoisson, PropertyID.PID_InclusionVolumeFraction, PropertyID.PID_InclusionAspectRatio]
        # list of compulsory IDs
        self.myCompulsoryPropIDs = self.myInputPropIDs

        #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_ESI_VPS_BUCKL_LOAD, PropertyID.PID_ESI_VPS_TOTAL_MODEL_MASS, PropertyID.PID_CompositeAxialYoung, PropertyID.PID_CompositeInPlaneYoung, PropertyID.PID_CompositeInPlaneShear, PropertyID.PID_CompositeTransverseShear, PropertyID.PID_CompositeInPlanePoisson, PropertyID.PID_CompositeTransversePoisson]

        #dictionary of input properties (values)
        self.myInputProps = {}
        #dictionary of output properties (values)
        self.myOutProps = {}

        # solvers
        self.digimatSolver = None
        self.comsolSolver = None
        self.vpsSolver = None



    def initialize(self, file='', workdir='', targetTime=PQ.PhysicalQuantity(1., 's'), metaData={}, validateMetaData=True, **kwargs):
        log.info('Workflow initialization')
        #locate nameserver
        ns = PyroUtil.connectNameServer(nshost, nsport, hkey)
        #connect to digimat JobManager running on (remote) server
        self.digimatJobMan = PyroUtil.connectJobManager(ns, digimatJobManName,hkey)
        #connect to vps JobManager running on (remote) server
        self.vpsJobMan = PyroUtil.connectJobManager(ns, vpsJobManName,hkey)
        #connect to comsol JobManager running on (remote) server
        self.comsolJobMan = PyroUtil.connectJobManager(ns, comsolJobManName,hkey)



        #allocate the Digimat remote instance
        try:
            self.digimatSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.digimatJobMan, None, hkey)
            log.info('Created digimat job')
            self.comsolSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.comsolJobMan, None, hkey)
            log.info('Created comsol job')
            self.vpsSolver = PyroUtil.allocateApplicationWithJobManager( ns, self.vpsJobMan, None, hkey)
            log.info('Created Vps job')
        except Exception as e:
            log.exception(e)
        else:
            if ((self.comsolSolver is not None) and (self.digimatSolver is not None) and (self.vpsSolver is not None)):
                comsolSolverSignature=self.comsolSolver.getApplicationSignature()
                log.info("Working comsol solver on server " + comsolSolverSignature)
                digimatSolverSignature=self.digimatSolver.getApplicationSignature()
                log.info("Working digimat solver on server " + digimatSolverSignature)
                vpsSolverSignature=self.vpsSolver.getApplicationSignature()
                log.info("Working vps solver on server " + vpsSolverSignature)
            else:
                log.debug("Connection to server failed, exiting")

        super(Airbus_Workflow_9p, self).initialize(file=file, workdir=workdir, targetTime=targetTime, metaData=metaData, validateMetaData=validateMetaData, **kwargs)
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
        # initialize digimat solver
        self.digimatSolver.initialize(metaData=passingMD)
        # initialize comsol solver
        log.info('Setting Execution Metadata of comsol')
        self.comsolSolver.initialize(metaData=passingMD)
        # initialize vps solver
        log.info('Setting Execution Metadata of Vps')
        workdir=self.vpsJobMan.getJobWorkDir(self.vpsSolver.getJobID())
        self.vpsSolver.initialize(metaData=passingMD,workdir=workdir)
        self.vpsSolver.readInput()



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
            # solve comsol part
            log.info("Running comsol")
            self.comsolSolver.solveStep(None)
            ## get the desired properties
            # get domain number to filter tooling
            domainNumber = self.comsolSolver.getField(FieldID.FID_DomainNumber,0,0)
            ## get fibre orientation for four different layers, already on filtered domain (no toling)
            #self.fibreOrientation0 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,1), self.domainNumber, 1.0)
            #self.fibreOrientation90 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,2), self.domainNumber, 1.0)
            #self.fibreOrientation45 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,3), self.domainNumber, 1.0)
            # - 45
            #self.fibreOrientation_45 = filterField(self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,4), self.domainNumber, 1.0)

            INSA_fibre0  = self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,1)
            INSA_fibre90 = self.comsolSolver.getField(FieldID.FID_FibreOrientation,0,2)
            INSA_disp   = self.comsolSolver.getField(FieldID.FID_Displacement,0,1)

            print('Filter ori 0')
            self.fibreOrientation0  = INSAoriextract(INSA_fibre0,INSA_disp,domainNumber)
            print('Filter ori 90')
            self.fibreOrientation90 = INSAoriextract(INSA_fibre90,INSA_disp,domainNumber)

            #print(self.fibreOrientation0)
        except Exception as err:
            print ("Error COMSOL:" + repr(err))
            self.terminate()

        try:
            log.info("Map properties from Digimat to properties of Vps")
            # map properties from Digimat to properties of Vps
            # Young modulus
            ESI_VPS_PLY1_E0t1 = deepcopy(compositeAxialYoung)
            ESI_VPS_PLY1_E0t1.propID = PropertyID.PID_ESI_VPS_PLY1_E0t1

            ESI_VPS_PLY1_E0c1 = deepcopy(compositeAxialYoung)
            ESI_VPS_PLY1_E0c1.propID = PropertyID.PID_ESI_VPS_PLY1_E0c1

            ESI_VPS_PLY1_E0t2 = deepcopy(compositeInPlaneYoung)
            ESI_VPS_PLY1_E0t2.propID = PropertyID.PID_ESI_VPS_PLY1_E0t2

            ESI_VPS_PLY1_E0t3 = deepcopy(compositeInPlaneYoung)
            ESI_VPS_PLY1_E0t3.propID = PropertyID.PID_ESI_VPS_PLY1_E0t3

            # Shear modulus
            ESI_VPS_PLY1_G012 = deepcopy(compositeInPlaneShear)
            ESI_VPS_PLY1_G012.propID = PropertyID.PID_ESI_VPS_PLY1_G012

            ESI_VPS_PLY1_G013 = deepcopy(compositeInPlaneShear)
            ESI_VPS_PLY1_G013.propID = PropertyID.PID_ESI_VPS_PLY1_G013

            ESI_VPS_PLY1_G023 = deepcopy(compositeTransverseShear)
            ESI_VPS_PLY1_G023.propID = PropertyID.PID_ESI_VPS_PLY1_G023

            # Poisson ratio
            ESI_VPS_PLY1_NU12 = deepcopy(compositeInPlanePoisson)
            ESI_VPS_PLY1_NU12.propID = PropertyID.PID_ESI_VPS_PLY1_NU12

            ESI_VPS_PLY1_NU13 = deepcopy(compositeInPlanePoisson)
            ESI_VPS_PLY1_NU13.propID = PropertyID.PID_ESI_VPS_PLY1_NU13

            ESI_VPS_PLY1_NU23 = deepcopy(compositeTransversePoisson)
            ESI_VPS_PLY1_NU23.propID = PropertyID.PID_ESI_VPS_PLY1_NU23


            # Assign properties
            self.vpsSolver.setProperty(ESI_VPS_PLY1_E0t1)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_E0t2)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_E0t3)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_E0c1)

            self.vpsSolver.setProperty(ESI_VPS_PLY1_G012)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_G013)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_G023)

            self.vpsSolver.setProperty(ESI_VPS_PLY1_NU12)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_NU13)
            self.vpsSolver.setProperty(ESI_VPS_PLY1_NU23)


            # set the field orientation, the objectID corresponds to layer angle, i.e, 0,90,45,-45
            print('Set ori 0')
            self.vpsSolver.setField(self.fibreOrientation0,angle = 0.0)
            #self.fibreOrientation0.toVTK2('f0')
            #print('Set ori 90')
            #self.fibreOrientation90.toVTK2('f90')
            #self.vpsSolver.setField(self.fibreOrientation90,angle = 90.0)

            #self.vpsSolver.setField(self.fibreOrientation90,FieldID.FID_FibreOrientation,0,90)
            #self.vpsSolver.setField(self.fibreOrientation45,FieldID.FID_FibreOrientation,0,45)
            #self.vpsSolver.setField(self.fibreOrientation_45,FieldID.FID_FibreOrientation,0,-45)


        except Exception as err:
            print ("Setting Vps params failed: " + repr(err));
            self.terminate()

        try:
            # solve vps model
            log.info("Running Vps")
            self.vpsSolver.solveStep(None)
            ## get the desired properties
            self.myOutProps[PropertyID.PID_ESI_VPS_BUCKL_LOAD] = self.vpsSolver.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD,0)
            self.myOutProps[PropertyID.PID_ESI_VPS_TOTAL_MODEL_MASS] = self.vpsSolver.getProperty(PropertyID.PID_ESI_VPS_TOTAL_MODEL_MASS,0)

            
            log.info("Done")
        except Exception as err:
            print ("Error VPS:" + repr(err))
            self.terminate()


    def filterField(sourceField, filterField, tresholdValue):
        # filter composite part
        # sourceField: source field from which subFIELD IS CREATED
        # filterField: Field defining quantintity based on which the filtering is done
        # tresholdValue: Only parts of source field with filterField = tresholdValue will be returned
        # return: field defined on submesh of sourceField, where filterField==tresholdValue
        fmesh = sourceField.getMesh()
        targetMesh = Mesh.UnstructuredMesh()
        targetCells = []
        targetVertices = []
        nodeMap = [-1] * fmesh.getNumberOfVertices()

        fvalues = []
        for iv in fmesh.vertices():
            n = iv.getNumber()
            if (abs(filterField.getVertexValue(n).getValue()[0] - tresholdValue) < 1.e-3):
                nn = copy.deepcopy(iv)
                nn.number = len(targetVertices)
                nodeMap[n] = nn.number
                targetVertices.append(nn)
                fvalues.append(sourceField.getVertexValue(n).getValue())

        for icell in fmesh.cellsq():
            # determine if icell belongs to composite domain
            if (nodeMap[icell.getVertices()[0].getNumber()] >= 0):
                # cell belonging to composite
                c = icell.copy()
                # append all cell vertices
                cvertices = []
                for i in range(len(c.vertices)):
                    # inum = c.vertices[i].getNumber()
                    inum = c.vertices[i]
                    cvertices.append(nodeMap[inum])
                    c.vertices = cvertices
                    targetCells.append(c)

        targetMesh.setup(targetVertices, targetCells)
        targetField = Field.Field(targetMesh, FieldID.FID_FibreOrientation, sourceField.getValueType(),
                              sourceField.getUnits(), sourceField.getTime(), values=fvalues,
                              fieldType=sourceField.getFieldType(), objectID=sourceField.getObjectID())
        return targetField




    def getCriticalTimeStep(self):
        # determine critical time step
        return PQ.PhysicalQuantity(1.0, 's')

    def terminate(self):
        #self.thermalAppRec.terminateAll()
        self.digimatSolver.terminate()
        self.vpsSolver.terminate()
        super(Airbus_Workflow_9p, self).terminate()

    def getApplicationSignature(self):
        return "Composelector workflow 1.0"

    def getAPIVersion(self):
        return "1.0"


def INSAoriextract(srcfield, dispfield, domainfield):

    mesh = srcfield.getMesh()

    boundingbox = np.zeros([3,2])
    boundingbox[:,0] =  1e12
    boundingbox[:,1] = -1e12

    vertexsrclist = {}
    vertexlist    = []
    celllist      = []


    trgmesh = Mesh.UnstructuredMesh()

    node_num = 0

    for ii, vertex in enumerate(mesh.vertexList, 0):
        vertid = vertex.number

        domainid = domainfield.getVertexValue(vertid).value[0]
        if domainid==1.0:
            coord = mesh.getVertex(vertid).coords + dispfield.getVertexValue(vertid).value
            coord *= 1000.0  # m to mm
            ori   = srcfield.getVertexValue(vertid).value
            vertexsrclist[vertid] = dict(MUPIF_ID = node_num, ori = deepcopy(ori))
            vertexlist.append(Vertex.Vertex(node_num, node_num, coord))
            node_num += 1

    for ii, element in enumerate(mesh.cellList, 0):
        vertices = element.getVertices()
        connect = []
        isindomain = True
        for vert in vertices:
            if not (vert.number) in vertexsrclist:
                isindomain = False
                break
            vertexsrclist
            connect.append(vertexsrclist[vert.number]['MUPIF_ID'])

        if isindomain:
            celllist.append(Cell.Tetrahedron_3d_lin(trgmesh, ii, ii, connect))

    trgmesh.setup(vertexlist, celllist)

    orifield = Field.Field(trgmesh,FieldID.FID_FibreOrientation,ValueType.Vector,srcfield.getUnits(), srcfield.getTime(),None,1)

    for ii, vertid in enumerate(vertexsrclist, 0):
        orifield.setValue(vertexsrclist[vertid]['MUPIF_ID'], vertexsrclist[vertid]['ori'])

    orifield.updateMetadata(srcfield.getAllMetadata())

    return orifield

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
            workflow = Airbus_Workflow_9p()
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
            #compositeAxialYoung = workflow.getProperty(PropertyID.PID_CompositeAxialYoung,time).inUnitsOf('MPa').getValue()
            #compositeInPlaneYoung = workflow.getProperty(PropertyID.PID_CompositeInPlaneYoung,time).inUnitsOf('MPa').getValue()
            #compositeInPlaneShear = workflow.getProperty(PropertyID.PID_CompositeInPlaneShear,time).inUnitsOf('MPa').getValue()
            #compositeTransverseShear = workflow.getProperty(PropertyID.PID_CompositeTransverseShear,time).inUnitsOf('MPa').getValue()
            #compositeInPlanePoisson = workflow.getProperty(PropertyID.PID_CompositeInPlanePoisson,time).getValue()
            #compositeTransversePoisson = workflow.getProperty(PropertyID.PID_CompositeTransversePoisson,time).getValue()

            # collect Vps outputs
            #KPI 1-1 weight
            #weight = workflow.getProperty(PropertyID.PID_Weight, time).inUnitsOf('kg').getValue()
            #log.info("Requested KPI : Weight: " + str(weight) + ' kg')
            #KPI 1-2 buckling load
            bucklingLoad = workflow.getProperty(PropertyID.PID_ESI_VPS_BUCKL_LOAD, time).inUnitsOf('N*mm').getValue()
            log.info("Requested KPI : Buckling Load: " + str(bucklingLoad) + ' N*mm')
            mass = workflow.getProperty(PropertyID.PID_ESI_VPS_TOTAL_MODEL_MASS, time).inUnitsOf('kg').getValue()
            log.info("Requested KPI : Mass: " + str(mass) + ' kg')
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
                ImportHelper.CreateAttribute("Buckling Load", bucklingLoad, "N*mm")
                return ImportHelper

        except APIError.APIError as err:
            print ("Mupif API for Airubu_Workflow_9p: " + repr(err))
        except Exception as err:
            print ("Error: " + repr(err))
        except:
            print ("Unknown error.")

    return workflow

if __name__=='__main__':
    model = workflow(0,0)

    srcfield    = model.fibreOrientation0
    #dispfield   = model.INSA_disp
    #domainfield = model.domainNumber

    mesh = srcfield.getMesh()

    nverts = mesh.getNumberOfVertices()

    src_coord = np.zeros([nverts,3])
    src_res   = np.zeros([nverts,3])

    boundingbox = np.zeros([3,2])
    boundingbox[:,0] =  1e12
    boundingbox[:,1] = -1e12

    model_pc    = {}
    nodes    = {}
    elements = {}

    for ii, vertex in enumerate(mesh.vertexList, 0):
        vertid = vertex.number
        coord = mesh.getVertex(vertid).coords
        ori   = srcfield.getVertexValue(vertid).value
        nodes[vertid+1] = dict(coord=deepcopy(coord),ori = deepcopy(ori))

    for ii, element in enumerate(mesh.cellList, 0):
        vertices = element.getVertices()
        connect = []
        isindomain = True
        for vert in vertices:
            connect.append(vert.number + 1)

        if isindomain:
            elements[ii+1] = dict(idprt=1,elementtype = 'TETR4',
                                   connectivity = connect)

    model_pc['nodes']    = nodes
    model_pc['elements'] = elements
