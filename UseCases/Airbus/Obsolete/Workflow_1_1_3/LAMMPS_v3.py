#!/usr/bin/env python3
import sys
sys.path.extend(['..', '../../..'])
from mupif import *
from mupif.Physics import *
#import jsonpickle
import time #for sleep
import logging
log = logging.getLogger()
#import ComposelectorSimulationTools.MIUtilities as miu

#
# Expected response from operator: E-mail with (useCase + execID)
# in the subject line, message body: json encoded dictionary with 'Operator-results' key, e.g.
# {"Result": 3.14}
#

class emailAPI(Application.Application):

    class inputParam: # helper class to track input parameters
        def __init__(self, compulsory=False, defaultValue=None):
            self.compulsory = compulsory
            self.isSet = False
            self.value = defaultValue
        def isCompulsory(self):
            return self.compulsory
        def set(self, value):
            self.value = value  
            self.isSet = True


    """
    Simple application API that involves operator interaction
    """
    def __init__(self, file):
        super(emailAPI, self).__init__(file)
        # note: "From" should correspond to destination e-mail
        # where the response is received (Operator can reply to the message)
        self.operator = operatorUtil.OperatorEMailInteraction(From='mdcompouser@gmail.com', To='erik.laurini@dia.units.it',
                                                              smtpHost='smtp.units.it', imapHost='imap.gmail.com', imapUser='mdcompouser', imapPsswd='CompoSelector2017')
        #self.operator = operatorUtil.OperatorEMailInteraction(From='borpat@seznam.cz', To='borpat@seznam.cz',
        #                                                      smtpHost='smtp.fsv.cvut.cz', imapHost='imap.seznam.cz', imapUser='borpat' )

        # list of recognized input IDs
        self.inputProps = {PropertyID.PID_SMILE_MOLECULAR_STRUCTURE: self.inputParam(compulsory=True),
                           PropertyID.PID_MOLECULAR_WEIGHT: self.inputParam(compulsory=True),
                           PropertyID.PID_POLYDISPERSITY_INDEX: self.inputParam(compulsory=True),
                           PropertyID.PID_CROSSLINKER_TYPE: self.inputParam(compulsory=True),
                           PropertyID.PID_FILLER_DESIGNATION: self.inputParam(compulsory=True),
                           PropertyID.PID_SMILE_MODIFIER_MOLECULAR_STRUCTURE: self.inputParam(compulsory=False),
                           PropertyID.PID_SMILE_FILLER_MOLECULAR_STRUCTURE: self.inputParam(compulsory=False),
                           PropertyID.PID_CROSSLINKONG_DENSITY: self.inputParam(compulsory=True),
                           PropertyID.PID_FILLER_CONCENTRATION:self.inputParam(compulsory=True),
                           PropertyID.PID_DENSITY_OF_FUNCTIONALIZATION: self.inputParam(compulsory=False),
                           PropertyID.PID_TEMPERATURE: self.inputParam(compulsory=True),
                           PropertyID.PID_PRESSURE: self.inputParam(compulsory=True)}

        # list of collected inputs to be sent to operator
        self.inputs = {}
        self.outputs = {}
        #self.key = 'Operator-results'

    def setProperty(self, property, objectID=0):
        # remember the mapped value
        if property.propID in self.inputProps.keys():
            self.inputProps[property.propID].set(property)
            #self.inputs[str(property.propID)] = property
        else:
            log.error("Property %s not supported on input" % property.propID)
        


    def _extractProperty (self, key, unit):
        if str(key) in self.outputs:
            value = float(self.outputs[str(key)])
            log.info('Found key %s with value %f' %(str(key),value))
            return Property.ConstantProperty(value, key, ValueType.Scalar, unit, None, 0)
        else:
            log.error('Not found key %s in email' % str(key))
            return None

    def getProperty(self, propID, time, objectID=0):
        if (True):
            #unpack & process outputs (expected json encoded data)
            if (propID == PropertyID.PID_DENSITY):
                return Property.ConstantProperty(0.1, propID, ValueType.Scalar, 'g/cm/cm/cm', None, 0)
#                return self._extractProperty(propID, 'g/cm/cm/cm')
            elif (propID == PropertyID.PID_EModulus):
                return Property.ConstantProperty(210, propID, ValueType.Scalar, 'GPa', None, 0)
#                return self._extractProperty(propID, 'GPa')
            elif (propID == PropertyID.PID_effective_conductivity):
                return Property.ConstantProperty(50, propID, ValueType.Scalar, 'W/m/K', None, 0)
#                return self._extractProperty(propID, 'W/m/K')
            elif (propID == PropertyID.PID_PoissonRatio):
                return Property.ConstantProperty(0.2, propID, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0)
#                return self._extractProperty(propID, PhysicalQuantities.getDimensionlessUnit())
            elif (propID == PropertyID.PID_TRANSITION_TEMPERATURE):
                return Property.ConstantProperty(528, propID, ValueType.Scalar, 'K', None, 0)
#                return self._extractProperty(propID, 'K')
            else:
                log.error('Not found key %s in email' % self.key)
                return None
        else:
            log.error("Property %s not recognized as output property"%propID)
            
    def solveStep(self, tstep, stageID=0, runInBackground=False):
        useCaseID = self.getMetadata(MetadataKeys.UseCaseID)
        execID = self.getMetadata(MetadataKeys.ExecID)
        huhu = 1
        #check inputs (if all compulsory set, generate collected inputs for operator)
        #proceed = True
        #for i,ip in self.inputProps.items():
        #    if ((ip.isCompulsory()==True) and (ip.isSet==False)):
        #        log.error("Compulsory parameter %s not set" % str(i))
        #        proceed = False
        #if not proceed:
        #    log.error("Error: some parameters heve not been set, Exiting")
        #    return
        # create input set for operator
        #for i,ip in self.inputProps.items():
        #    try:
        #        self.inputs[str(i)] = (ip.value.getValue(), str(ip.value.getUnits()))
        #    except:
        #        self.inputs[str(i)] = ip.value


        #send email to operator, pack json encoded inputs in the message
        #note workflow and job IDs will be available in upcoming MuPIF version
        #self.operator.contactOperator(useCaseID, execID, jsonpickle.encode(self.inputs))
        #responseReceived = False
        # check for response and repeat until received
        #while not responseReceived:
            #check response and receive the data
         #   responseReceived, operatorOutput = self.operator.checkOperatorResponse(useCaseID, execID)
          #  if responseReceived:
           #     try:
                    #self.outputs = jsonpickle.decode(operatorOutput.splitlines()) #pick up only dictionary to new line
            #        self.outputs = jsonpickle.decode(''.join(operatorOutput.replace('=', '').split()).split('}')[0] + '}') #pick up only dictionary to new line
             #   except Exception as e:
              #      log.error(e)
               # log.info("Received response from operator %s" % self.outputs)
            #else:
             #   time.sleep(60) #wait
            
    def getCriticalTimeStep(self):
        return 1.0


#################################################
#demo code
#################################################

def workflow(inputGUID, execGUID):
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
                "Pressure":"atm"}

    #Define execution details to export
    exexPropsToExp = {"ID":"",
                    "Use case ID":"",
                    "Modelling task ID": "",
                    "Modelling task workflow ID": "",
                    "Requested by": "",
                    "Technical review by": "",
                    "Description": "",
                    "Description of inputs": ""}

    #Export execution information from database
    ExportedExecInfo = miu.ExportData("MI_Composelector", "Modelling tasks workflows executions", execGUID, exexPropsToExp)
    execID = ExportedExecInfo["ID"]
    useCaseID = ExportedExecInfo["Use case ID"]
    modellingTaskID = ExportedExecInfo["Modelling task ID"]
    modellingTaksWfID = ExportedExecInfo["Modelling task workflow ID"]
    requestedBy = ExportedExecInfo["Requested by"]
    techRevBy = ExportedExecInfo["Technical review by"]
    desc = ExportedExecInfo["Description"]
    descInputs = ExportedExecInfo["Description of inputs"]

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

    # create instance of application API
    app = emailAPI(None)

    app.setProperty(Property.ConstantProperty(monomerMolStructure, PropertyID.PID_SMILE_MOLECULAR_STRUCTURE, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(polymerMolWeight, PropertyID.PID_MOLECULAR_WEIGHT, ValueType.Scalar, 'mol', None, 0))
    app.setProperty(Property.ConstantProperty(crosslinkerType, PropertyID.PID_CROSSLINKER_TYPE, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(fillerDesignation, PropertyID.PID_FILLER_DESIGNATION, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(crosslinkingDens, PropertyID.PID_CROSSLINKONG_DENSITY, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(fillerConc, PropertyID.PID_FILLER_CONCENTRATION, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(temperature, PropertyID.PID_TEMPERATURE, ValueType.Scalar, 'degC', None, 0))
    app.setProperty(Property.ConstantProperty(pressure, PropertyID.PID_PRESSURE, ValueType.Scalar, 'atm', None, 0))
    app.setProperty(Property.ConstantProperty(polyIndex, PropertyID.PID_POLYDISPERSITY_INDEX, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(fillerModMolStructure, PropertyID.PID_SMILE_MODIFIER_MOLECULAR_STRUCTURE, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(polFilCompatibilizerMolStructure, PropertyID.PID_SMILE_FILLER_MOLECULAR_STRUCTURE, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))
    app.setProperty(Property.ConstantProperty(functionalizationDens, PropertyID.PID_DENSITY_OF_FUNCTIONALIZATION, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0))

    # solve (involves operator interaction)
    app.solveStep (useCaseID, execID, TimeStep.TimeStep(0.0, 0.1, 1, 's'))

    # get result of the simulation
    density = app.getProperty(PropertyID.PID_DENSITY, 0.0).getValue()
    youngModulus = app.getProperty(PropertyID.PID_EModulus, 0.0).getValue()
    thermalConductivity = app.getProperty(PropertyID.PID_effective_conductivity, 0.0).getValue()
    glassTransitionTemperature = app.getProperty(PropertyID.PID_TRANSITION_TEMPERATURE, 0.0).getValue()
    poissonsRatio = app.getProperty(PropertyID.PID_PoissonRatio, 0.0).getValue()

    ImportHelper = miu.Importer("MI_Composelector", "Inputs-Outputs", ["Inputs/Outputs"])
    ImportHelper.CreateAttribute("Execution ID", execID, "")
    ImportHelper.CreateAttribute("Dataset generated by", 'LAMMPS', "")
    ImportHelper.CreateAttribute("Density", density, "g/cm^3")
    ImportHelper.CreateAttribute("Young modulus", youngModulus, "GPa")
    ImportHelper.CreateAttribute("Thermal conductivity", thermalConductivity, "W/m.°C")
    ImportHelper.CreateAttribute("Glass transition temperature", glassTransitionTemperature, "K")
    ImportHelper.CreateAttribute("Poisson's ratio", poissonsRatio, "")
    return ImportHelper

# terminate app

#except Exception as e:
#    log.error(e)
#finally:
#    app.terminate();
