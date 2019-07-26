import sys
sys.path.extend(['..', '../../..'])
from mupif import *
from mupif.Physics import *
#import jsonpickle
import time #for sleep1
import logging
log = logging.getLogger()

debug = True

if not debug:
    import ComposelectorSimulationTools.MIUtilities as miu


#
# Expected response from operator: E-mail with (useCase + execID)
# in the subject line, message body: json encoded dictionary with 'Operator-results' key, e.g.
# {"Result": 3.14}
#

class LAMMPS_API(Application.Application):

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
    def __init__(self,metaData={}):
        super(LAMMPS_API, self).__init__()
        # note: "From" should correspond to destination e-mail
        # where the response is received (Operator can reply to the message)
        MD = {
            'Name': 'LAMMPS',
            'ID': 'LAMMPS',
            'Description': 'Moluecular dynamics simulation for the Airbus case',
            'Physics': {
                'Type': 'Molecular'
            },
            'Solver': {
                'Software': 'LAMMPS',
                'Language': 'C++',
                'License': 'Open-source',
                'Creator': 'Borek Patzak',
                'Version_date': 'lammps-12dec18',
                'Type': 'Atomistic/Mesoscopic',
                'Documentation': 'https://lammps.sandia.gov/doc/Manual.html',
                'Estim_time_step_s': 1,
                'Estim_comp_time_s': 0.01,
                'Estim_execution_cost_EUR': 0.01,
                'Estim_personnel_cost_EUR': 0.01,
                'Required_expertise': 'None',
                'Accuracy': 'High',
                'Sensitivity': 'High',
                'Complexity': 'Low',
                'Robustness': 'High'
            },
            'Inputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_SMILE_MOLECULAR_STRUCTURE', 'Name': 'Monomer Molecular Structure', 'Description': 'Monomer Molecular Structure', 'Units': 'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_MOLECULAR_WEIGHT', 'Name': 'Polymer Molecular Weight', 'Description': 'Polymer Molecular Weight',  'Units': 'mol', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CROSSLINKER_TYPE', 'Name': 'CROSSLINKER TYPE', 'Description': 'CROSSLINKER TYPE',  'Units': 'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_FILLER_DESIGNATION', 'Name': 'FILLER DESIGNATION', 'Description': 'FILLER DESIGNATION', 'Units':  'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_CROSSLINKONG_DENSITY', 'Name': 'CROSSLINKONG DENSITY', 'Description': 'CROSSLINKONG DENSITY',  'Units':  'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_FILLER_CONCENTRATION', 'Name': 'FILLER CONCENTRATION', 'Description': 'FILLER CONCENTRATION',  'Units':  'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_TEMPERATURE', 'Name': 'TEMPERATURE', 'Description': 'TEMPERATURE',  'Units':  'degC', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PRESSURE', 'Name': 'PRESSURE', 'Description': 'TEMPERATURE',  'Units':  'atm', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_POLYDISPERSITY_INDEX', 'Name': 'POLYDISPERSITY INDEX', 'Description': 'POLYDISPERSITY INDEX',  'Units':  'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_SMILE_MODIFIER_MOLECULAR_STRUCTURE', 'Name': 'SMILE MODIFIER MOLECULAR STRUCTURE', 'Description': 'SMILE MODIFIER MOLECULAR STRUCTURE',  'Units':  'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_SMILE_FILLER_MOLECULAR_STRUCTURE', 'Name': 'SMILE FILLER MOLECULAR STRUCTURE', 'Description': 'SMILE FILLER MOLECULAR STRUCTURE', 'Units':  'None', 'Origin': 'Simulated', 'Required': True},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_DENSITY_OF_FUNCTIONALIZATION', 'Name': 'DENSITY OF FUNCTIONALIZATION', 'Description': 'DENSITY OF FUNCTIONALIZATION', 'Units':  'None', 'Origin': 'Simulated', 'Required': True}
            ],
            'Outputs': [
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_DENSITY', 'Name': 'density', 'Description': 'density', 'Units': 'g/cm^3', 'Origin': 'Simulated'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_EModulus', 'Name': 'Young modulus', 'Description': 'Young modulus', 'Units': 'GPa', 'Origin': 'Simulated'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_effective_conductivity', 'Name': 'Thermal Conductivity', 'Description': 'Thermal Conductivity', 'Units': 'W/m.??C', 'Origin': 'Simulated'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_TRANSITION_TEMPERATURE', 'Name': 'Glass Transition Temperature', 'Description': 'Glass Transition Temperature', 'Units': 'K', 'Origin': 'Simulated'},
                {'Type': 'mupif.Property', 'Type_ID': 'mupif.PropertyID.PID_PoissonRatio', 'Name': 'Poisson Ratio', 'Description': 'Poisson Ratio', 'Units': 'None', 'Origin': 'Simulated'}
            ]
        }

        super(LAMMPS_API, self).__init__(MD)
        self.updateMetadata(metaData)

    def initialize(self, file='', workdir='', metaData={}, **kwargs):
        self.operator = operatorUtil.OperatorEMailInteraction(From='mdcompouser@gmail.com', To='erik.laurini@dia.units.it',smtpHost='smtp.units.it', imapHost='imap.gmail.com', imapUser='mdcompouser', imapPsswd='CompoSelector2017')

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

             #list of recognized output property IDs
        self.myOutPropIDs =  [PropertyID.PID_DENSITY, PropertyID.PID_EModulus, PropertyID.PID_effective_conductivity, PropertyID.PID_TRANSITION_TEMPERATURE, PropertyID.PID_PoissonRatio]
   
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
            elif (propID == PropertyID.PID_EModulus):
                return Property.ConstantProperty(210, propID, ValueType.Scalar, 'GPa', None, 0)
            elif (propID == PropertyID.PID_effective_conductivity):
                return Property.ConstantProperty(50, propID, ValueType.Scalar, 'W/m/K', None, 0)
            elif (propID == PropertyID.PID_PoissonRatio):
                return Property.ConstantProperty(0.2, propID, ValueType.Scalar, PhysicalQuantities.getDimensionlessUnit(), None, 0)
            elif (propID == PropertyID.PID_TRANSITION_TEMPERATURE):
                return Property.ConstantProperty(528, propID, ValueType.Scalar, 'K', None, 0)
            else:
                log.error('Not found key %s in email' % self.key)
                return None
        else:
            log.error("Property %s not recognized as output property"%propID)
            
    def solveStep(self, tstep, stageID=0, runInBackground=False):
        #check inputs (if all compulsory set, generate collected inputs for operator)

        proceed = True
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
        #    responseReceived, operatorOutput = self.operator.checkOperatorResponse(useCaseID, execID)
        #    if responseReceived:
        #        try:
                    #self.outputs = jsonpickle.decode(operatorOutput.splitlines()) #pick up only dictionary to new line
                    #self.outputs = jsonpickle.decode(''.join(operatorOutput.replace('=', '').split()).split('}')[0] + '}') #pick up only dictionary to new line
        #        except Exception as e:
        #            log.error(e)
        #        log.info("Received response from operator %s" % self.outputs)
        #    else:
        time.sleep(10) #wait
            
    def getCriticalTimeStep(self):
        return 1.0
