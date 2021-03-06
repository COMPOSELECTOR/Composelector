# -*- coding: utf-8 -*-
"""
Created on Thu Sep 20 15:19:50 2018

@author: Yao Koutsawa
"""
# last modification 2019.11.22

import os
import subprocess
import logging
import sys
import numpy as np

import Pyro4

import mupif
from mupif import APIError, ValueType, Mesh, Vertex, Cell, CellGeometryType
from mupif import Property, Physics, Field, FieldID, PropertyID
from mupif import dataID 

# from customDataID import MyPropertyID #, MyFieldID

#sys.path.append('../API/Subs')
#import hyperinteg

orthotropicDef  = (PropertyID.PID_YoungModulus1,  PropertyID.PID_YoungModulus2,  PropertyID.PID_YoungModulus3,
                   PropertyID.PID_PoissonRatio23, PropertyID.PID_PoissonRatio13, PropertyID.PID_PoissonRatio12,
                   PropertyID.PID_ShearModulus23, PropertyID.PID_ShearModulus13, PropertyID.PID_ShearModulus12 )

isotropicDef    = (PropertyID.PID_EModulus, PropertyID.PID_PoissonRatio)

hyperelasticDef = (PropertyID.PID_Hyper1)

log = logging.getLogger()

@Pyro4.expose
class AbaqusApp(mupif.Model.Model):
    """
    A class representing Abaqus application and its interface (API).
    """
    def __init__ (self, metaData = {}):
        """
        Constructor. Initializes the application.
        """
        MD = {
                    'Name': 'ABAQUS finite element solver',
                    'ID': 'N/A',
                    'Description': 'multi-purpose finite element software',
                    'Physics': {
                        'Type': 'Other',
                        'Entity': 'Other'
                    },
                            
                    'Execution' : {'ID' : 'none', 'Use_case_ID': 'Dow', 'Task_ID': 'none'
                    },
                            
                    'Solver': {
                        'Software': 'ABAQUS Solver using ABAQUS',
                        'Language': 'FORTRAN, C/C++',
                        'License': 'proprietary code',
                        'Creator': 'Dassault systemes',
                        'Version_date': '03/2019',
                        'Type': 'Summator',
                        'Documentation': 'extensive',
                        'Estim_time_step_s': 1,
                        'Estim_comp_time_s': 0.01,
                        'Estim_execution_cost_EUR': 0.01,
                        'Estim_personnel_cost_EUR': 0.01,
                        'Required_expertise': 'User',
                        'Accuracy': 'High',
                        'Sensitivity': 'High',
                        'Complexity': 'Low',
                        'Robustness': 'High'
                    },
                            
                    'Inputs': [],  # May be defined in the workflow depending on the use case
                    'Outputs': [], # May be defined in the workflow depending on the use case
                    'refPoint': 'none', # May be defined in the workflow depending on the use case
                    'componentID': 'none', # May be defined in the workflow depending on the use case
                }
        super(AbaqusApp, self).__init__(metaData=MD)
        self.updateMetadata(metaData)
        
    def initialize (self, file, workdir = '.', metaData = {}, 
                    validateMetaData=False, **kwargs):
        """
        Initializes the ABAQUS solver, reads input file, prepares data structures.

        :param str file: Name of file
        :param str workdir: Optional parameter for working directory
        """
        super(AbaqusApp, self).initialize(file, workdir, metaData, 
             validateMetaData, **kwargs)
        self.updateMetadata(metaData)
        
        for (name, value) in kwargs.items():
            setattr(self, name, value)

        self.mesh = None

        log.info("Abaqus intialization")

        #self.inpFile = os.path.splitext(os.path.basename(self.file))[self]
        #0.jobName = self.inpFile
        #self.basename = self.workDir + os.sep + self.jobName
            
        self.inputPropIDs = {}
        self.inputProperties = {}
        log.info (str(self.getMetadata("Inputs")))
        
        for data in self.getMetadata("Inputs"):
            self.inputPropIDs[eval(data['Type_ID'])] = (data['Name'], data['Units'])
        #self.writtenProperties=False
        self.compositeProperties=[]
        #self.hyperelasticProperties=[]
        
    def solveStep(self, tstep=None, stageID=0, runInBackground=False):
        """
        """
        # write material file before running the analysis
        #if self.writtenProperties == False :
        #    self._writeMaterialsForAbaqus()
        #    self.writtenProperties = True
        #cmd = "abaqus job=%s  input=%s interactive"%(self.jobName, self.inpFile)
        print("\nSolving the macro-scale problem...\n")
        
        #process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
        #cwd=self.workDir)
        #output, error = process.communicate()
        #print(output.decode('utf-8') if output else "", error if error else "")
        
        #fid = open("%s.log"%self.jobName, "w")
        #if output: fid.write("%s\n"%output.decode('utf-8'))
        #if error: fid.write(error)
        #fid.close()
        
    def setProperty(self, property, objectID=0):
        """
        """
        propID = property.getPropertyID()
        if propID == PropertyID.PID_Hyper1:
#            print('HYPERELASTIC PROPERTY',property)
            #dd=hyperinteg.transferHyper(property)
            #dd.executehypertranfer()
            self.hyperelasticProperties.append({"C10":dd.a, "C20":dd.b, "D1":dd.c, "D2":0.})
            print('HYPERELASTIC REDUCED POLYNOMIAL CONSTITUTIVE LAW',self.hyperelasticProperties)
        else:
            if (propID in self.inputPropIDs.keys()):
                (name, unit) = self.inputPropIDs[propID]
                self.inputProperties[name] = property.inUnitsOf(unit).getValue()
                if propID in orthotropicDef:
                    self._storeCompositeProperties(property.inUnitsOf(unit).getValue(),propID, objectID)
                    
            else:
                print(self.inputPropIDs.keys())
                print("Property ID is", propID)
                raise APIError.APIError('HUHU Unknown input property ID', propID)

            
    def getProperty(self, propID=None, time=None, objectID=0):
        """
        """
        metaData = { 
            'Execution' : {
                'ID' : self.getMetadata('Execution.ID'),
                'Use_case_ID' : self.getMetadata('Execution.Use_case_ID'),
                'Task_ID' : self.getMetadata('Execution.Task_ID')}
        }
            
        if (propID==PropertyID.PID_Footprint):
            name = 'footprint'
            #self._runOdbProcess(name)
            footprint = 0.0
            
            #try:
                #filename =  "%s.%s.dat"%(self.basename, name)
                #footprint += np.loadtxt(filename, delimiter=",")
            #except Exception:
                #msg = "Failed to load %s file"%(name)
                #raise APIError.APIError(msg)

            return Property.ConstantProperty(footprint, propID, ValueType.Scalar, 
                                             "mm**2", time, objectID, 
                                             metaData=metaData)
            
        elif (propID==PropertyID.PID_Braking_Force):
            name = 'braking_force'
            componentID = self.getMetadata('componentID')
            refPoint = self.getMetadata('refPoint')
            #self._runOdbProcess(componentID, refPoint, name)
            braking_force = 0.0
            
            #try:
                #filename =  "%s.%s.dat"%(self.basename, name)
                #braking_force += np.loadtxt(filename, delimiter=",")
            #except Exception:
                #msg = "Failed to load %s file"%(name)
                #raise APIError.APIError(msg)

            return Property.ConstantProperty(braking_force, propID, 
                                             ValueType.Scalar, 
                                             "N", time, objectID, 
                                             metaData=metaData)
            
        elif (propID==PropertyID.PID_Stiffness):
            name = 'stiffness'
            componentID = self.getMetadata('componentID')
            refPoint = self.getMetadata('refPoint')
                
            #self._runOdbProcess(componentID, refPoint, name)
            stiffness = 0.0
            
            #try:
                #filename =  "%s.%s.dat"%(self.basename, name)
                #stiffness += np.loadtxt(filename, delimiter=",")
            #except Exception:
                #msg = "Failed to load %s file"%(name)
                #raise APIError.APIError(msg)
		
            return Property.ConstantProperty(stiffness, propID, 
                                             ValueType.Scalar, 
                                             "N/mm", time, objectID, 
                                             metaData=metaData)

        elif (propID==PropertyID.PID_maxDisplacement):
            name = 'maximum displacement'
            componentID = self.getMetadata('componentID')
                
            #try:
                #disp=self.getField(FieldID.FID_Displacement, time, objectID)
                #mesh=disp.getMesh()
                #maxDisp = 'none'
                #for node in mesh.vertices():
                    #val=disp.getVertexValue(node.getNumber()).getValue()[componentID-1]
                    #if maxDisp == 'none':
                        #maxDisp = val
                    #else:
                        #if val > maxDisp:
                            #maxDisp = val
            #except Exception:
                #msg = "Failed to get %s "%(name)
                #raise APIError.APIError(msg)
            maxDisp = 0
            return Property.ConstantProperty(maxDisp, propID, 
                                             ValueType.Scalar, 
                                             "mm", time, objectID, 
                                             metaData=metaData)

        elif (propID==PropertyID.PID_maxMisesStress):
            name = 'maximum von Mises Stress'
            vMStress = 0
            #try:
                #vMStress=self.getField(FieldID.FID_Mises_Stress, time, objectID)
                #mesh=vMStress.getMesh()
                #maxvMStress = 'none'
                #for node in mesh.vertices():
                    #val=vMStress.getVertexValue(node.getNumber()-1).getValue()
                    #if maxvMStress == 'none':
                        #maxvMStress = val
                    #else:
                        #if val > maxvMStress:
                            #maxvMStress = val
            #except Exception:
                #msg = "Failed to get %s "%(name)
                #raise APIError.APIError(msg)
            
            return Property.ConstantProperty(maxvMStress, propID, 
                                             ValueType.Scalar, 
                                             "MPa", time, objectID, 
                                             metaData=metaData)

        elif (propID==PropertyID.PID_maxPrincipalStress):
            name = 'maximum principal Stress'
            pStress = 0
            #try:
                #pStress=self.getField(FieldID.FID_MaxPrincipal_Stress, time, objectID)
                #mesh=pStress.getMesh()
                #maxpStress = 'none'
                #for node in mesh.vertices():
                    #val=pStress.getVertexValue(node.getNumber()-1).getValue()
                    #if maxpStress == 'none':
                        #maxpStress = val
                    #else:
                        #if val > maxpStress:
                            #maxpStress = val
            #except Exception:
                #msg = "Failed to get %s "%(name)
                #raise APIError.APIError(msg)
            
            return Property.ConstantProperty(maxpStress, propID, 
                                             ValueType.Scalar, 
                                             "MPa", time, objectID, 
                                             metaData=metaData)
        elif (propID==PropertyID.PID_CriticalLoadLevel):
            name = 'buckle_load'
            #self._runOdbProcess(name)
            buckle_load = 0.0
            #data = self._loadOdbData(name=name, objectID=None, delimiter=",")
            #buckle_load += data

            return Property.ConstantProperty(buckle_load, propID, ValueType.Scalar, 
                                             "N", time, objectID, 
                                             metaData=metaData)
        elif (propID==PropertyID.PID_Volume):
            name = 'volume'
            #self._runOdbProcess(name)
            volume = 0.0
            #data = self._loadOdbData(name=name, objectID=None, delimiter=",")
            #volume += data

            return Property.ConstantProperty(volume, propID, ValueType.Scalar, 
                                             "mm**3", time, objectID, 
                                             metaData=metaData)
        else:
            print('Property ID is', propID)
            raise APIError.APIError("Unknown property ID", propID)
            
    def getMesh(self, tstep=0):
        """
        """
        if (self.mesh == None):
            self.mesh = Mesh.UnstructuredMesh()
            
            vertexlist = []
            celllist   = []
            
            self._runOdbProcess('mesh')
            
            try:
                nodes = np.loadtxt(self.basename + ".nodes.dat", delimiter=",")
                nd = nodes.shape[0] 
                
                for i in range(1, nd + 1):
                    label = int(nodes[i-1, 0])
                    coords = tuple(nodes[i-1, 1:])
                    vertexlist.append(Vertex.Vertex(i-1, label, coords))  
                
            except Exception:
                raise APIError.APIError("Failed to load nodes file.")
                
            try:
                elements = np.loadtxt(self.basename+ ".elements.dat", 
                                      delimiter=",", dtype=int)
                ne = elements.shape[0] 
                
                for i in range(1, ne + 1):
                    label = elements[i-1, 0]
                    etype = elements[i-1, 0]
                    connec = tuple(elements[i-1, 2:])
                    
                    if etype == CellGeometryType.CGT_HEXAHEDRON:
                        celllist.append(Cell.Brick_3d_lin(self.mesh, i-1, 
                                                          label, connec))    
            except Exception:
                raise APIError.APIError("Failed to load elements file.")
                
            self.mesh.setup(vertexlist, celllist)
            
        return self.mesh
    
    def getField(self, fieldID, time=0, objectID=0):
        """
        """            
        metaData = { 
            'Execution' : {
                'ID' : self.getMetadata('Execution.ID'),
                'Use_case_ID' : self.getMetadata('Execution.Use_case_ID'),
                'Task_ID' : self.getMetadata('Execution.Task_ID')}
        }
        
        if fieldID==FieldID.FID_Displacement:
            name = 'displacements'
            self._runOdbProcess('displacements')
            
            try:
                filename =  "%s.%s.dat"%(self.basename, name)
                displ = np.loadtxt(filename, delimiter=",")
                nd = displ.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(displ[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Vector, 'mm', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        elif fieldID==FieldID.FID_Stress:
            name = 'stress'
            self._runOdbProcess(objectID, name)
            
            try:
                fileName = self.basename + ".%s_ID_%g.dat"%(name, objectID)
                stress = np.loadtxt(fileName, delimiter=",")
                nd = stress.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(stress[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Tensor, 'MPa', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        elif fieldID==FieldID.FID_Strain:
            name = 'strain'
            self._runOdbProcess(objectID, name)
            
            try:
                fileName = self.basename + ".%s_ID_%g.dat"%(name, objectID)
                strain = np.loadtxt(fileName, delimiter=",")
                nd = strain.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(strain[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Tensor, 'none', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        elif fieldID==FieldID.FID_Mises_Stress:
            name = 'mises_stress'
            self._runOdbProcess(objectID, name)
            
            try:
                fileName = self.basename + ".%s_ID_%g.dat"%(name, objectID)
                stress = np.loadtxt(fileName, delimiter=",")
                nd = stress.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(stress[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Scalar, 'MPa', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        elif fieldID==FieldID.FID_MaxPrincipal_Stress:
            name = 'maxprincipal_stress'
            self._runOdbProcess(objectID, name)
            
            try:
                fileName = self.basename + ".%s_ID_%g.dat"%(name, objectID)
                stress = np.loadtxt(fileName, delimiter=",")
                nd = stress.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(stress[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Scalar, 'MPa', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        elif fieldID==FieldID.FID_MinPrincipal_Stress:
            name = 'minprincipal_stress'
            self._runOdbProcess(objectID, name)
            
            try:
                fileName = self.basename + ".%s_ID_%g.dat"%(name, objectID)
                stress = np.loadtxt(fileName, delimiter=",")
                nd = stress.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(stress[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Scalar, 'MPa', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        elif fieldID==FieldID.FID_MidPrincipal_Stress:
            name = 'midprincipal_stress'
            self._runOdbProcess(objectID, name)
            
            try:
                fileName = self.basename + ".%s_ID_%g.dat"%(name, objectID)
                stress = np.loadtxt(fileName, delimiter=",")
                nd = stress.shape[0] 
                values = []
                
                for i in range(1, nd + 1):
                    values.append(tuple(stress[i-1, 1:]))
                    
                return Field.Field(self.getMesh(time), fieldID, ValueType.Scalar, 'MPa', 
                                   time, values, Field.FieldType.FT_vertexBased, 
                                   metaData=metaData)     
            except Exception:
                raise APIError.APIError("Failed to load %s file." % name)
                
        else:
            raise APIError.APIError("Not Yet implemented")
                     
    def setField(self, obj, objectID=0):
        """
        set fields for ABAQUS analysis
        only fibre orientation
        """            
        metaData = { 
            'Execution' : {
                'ID' : self.getMetadata('Execution.ID'),
                'Use_case_ID' : self.getMetadata('Execution.Use_case_ID'),
                'Task_ID' : self.getMetadata('Execution.Task_ID')}
        }
        
#        print('OBJ ID',obj.getFieldID())
#        if obj.getFieldID()==FieldID.FID_FibreOrientation
#            print('setting fibre orientation field')




    def getCriticalTimeStep(self):
        return Physics.PhysicalQuantities.PhysicalQuantity(1.0, "s")
    
    def getAssemblyTime(self, tstep):
        return tstep.getTime()
    
    def getApplicationSignature(self):
        return "LIST_Abaqus_API"
    
    def getAPIVersion(self):
        return "1.0.0"
    
    def _writeMaterialsForAbaqus(self):
        """
        print material property data into include files for use with Abaqus FEM software
        """
        if len(self.compositeProperties) > 0:
            self._writeCompositeProperties()
        if len(self.hyperelasticProperties) > 0:
            self._writeHyperelasticProperties()
    
    def _getAttribute(self, name):
        """
        """
        if hasattr(self, name):
            value = getattr(self, name)
        elif self.hasMetadata(name):
            value = self.getMetadata(name) 
        else:
            msg = "Attribute '%s' is not defined. "%(name)
            msg += "It can be defined in the *kwagrs"
            msg += "when initializing the API or in the API's metadata."
            raise APIError.APIError(msg) 
        return value
       
    def _loadOdbData(self, name, objectID=None, **kwargs):
        """
        Load field/property extracted from Odb file.
        """
        try:
            if objectID != None:
                filename = "%s.%s_ID_%g.dat"%(self.basename, name, objectID)
            else:
                filename = "%s.%s.dat"%(self.basename, name)
            data = np.loadtxt(filename, **kwargs)  
        except Exception:
            raise APIError.APIError("Failed to load %s file." % name)
            
        return data
       
    def _runOdbProcess(self, *cmdlines):
        """
        """
        path = os.path.dirname(os.path.abspath(__file__))
        odbname = self.workDir + os.sep + self.jobName + ".odb"
        cmd = "abaqus python %s%sodbProcess.py --  " % (path, os.sep)
        
        cmdlines = list(cmdlines)
        cmdlines.append(odbname)
        for cmdline in cmdlines:
            cmd = "%s  %s " % (cmd, str(cmdline))
        
        print("Getting %s from Abaqus solver...\n" % cmdlines[-2])
        
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   cwd=self.workDir)
        output, error = process.communicate()
        print(output.decode('utf-8') if output else "", error if error else "")
        
        print("Done.")

    def _storeCompositeProperties(self,value,propID,objectID):

        if len(self.compositeProperties) < objectID+1:
            self.compositeProperties.append({"E1":None,"E2":None,"E3":None,
                                                "G12":None,"G13":None,"G23":None,
                                                "nu12":None,"nu13":None,"nu23":None}  )

        if propID == PropertyID.PID_YoungModulus1:
            self.compositeProperties[objectID]["E1"] = value 
        elif propID == PropertyID.PID_YoungModulus2:
            self.compositeProperties[objectID]["E2"] = value
        elif propID == PropertyID.PID_YoungModulus3:
            self.compositeProperties[objectID]["E3"] = value
        elif propID == PropertyID.PID_PoissonRatio12:
            self.compositeProperties[objectID]["nu12"] = value
        elif propID == PropertyID.PID_PoissonRatio13:
            self.compositeProperties[objectID]["nu13"] = value
        elif propID == PropertyID.PID_PoissonRatio23:
            self.compositeProperties[objectID]["nu23"] = value
        elif propID == PropertyID.PID_ShearModulus12:
            self.compositeProperties[objectID]["G12"] = value
        elif propID == PropertyID.PID_ShearModulus13:
            self.compositeProperties[objectID]["G13"] = value
        elif propID == PropertyID.PID_ShearModulus23:
            self.compositeProperties[objectID]["G23"] = value

    def _writeCompositeProperties(self):
        for i in range(0,len(self.compositeProperties)):
            if None in self.compositeProperties[i].values():
                raise APIError.APIError("Please, set all the composite properties.")
            
            filename = 'composite_material_'+str(i+1)+'.inp'
        
            prop = self.compositeProperties[i]
            values = (prop["E1"], prop["E2"], prop["E3"], 
                  prop["nu12"], prop["nu13"], prop["nu23"],
                  prop["G12"], prop["G13"], prop["G23"],)

            fid = open(self.workDir + os.sep + filename, "w")
            fid.write("*Elastic, type=ENGINEERING CONSTANTS\n")
            fid.write("  %1.6E,%1.6E,%1.6E, %1.6E,%1.6E,%1.6E, %1.6E,%1.6E,\n  %1.6E,\n"%values)
            fid.close()
        
    def _writeHyperelasticProperties(self):
        for i in range(0,len(self.hyperelasticProperties)):
            if None in self.hyperelasticProperties[i].values():
                raise APIError.APIError("Please, set all the composite properties.")
            filename = 'hyper_material_'+str(i+1)+'.inp'
            
            prop = self.hyperelasticProperties[i]
            values = (prop["C10"], prop["C20"], prop["D1"], prop["D2"],)

            fid = open(self.workDir + os.sep + filename, "w")
            _writeHyperelasticAbaqusDefinition(fid,values)
            fid.close()
            print('FILE WRITTEN :',i+1)

def _writeHyperelasticAbaqusDefinition(file,vals):
    """ write definition of second order reduced polynomial hyperelastic constitutive law material parameters
        into open file
    """
    if len(vals)!=4:
        raise APIError.APIError("Please, set all the composite properties.")
            
    print('=== hyperelastic values (write)',vals)

    file.write("**Material definition for the REDUCED POLYNOMIAL, N=2 material model\n")
    file.write("**\n")
    file.write("*HYPERELASTIC, REDUCED POLYNOMIAL, N=2\n")
    file.write("  %1.6E,%1.6E,%1.6E, %1.6E "%vals)
    print('WRITTEN to FILE')

        
        
