import sys
sys.path.extend(['/home/nitram/Documents/work/MUPIF/commit'])
from mupif import *
import time as timeT
import logging
log = logging.getLogger()
log.setLevel(logging.INFO)
import mupif.Physics.PhysicalQuantities as PQ


if __name__=='__main__':
    property = Property.ConstantProperty(100, PropertyID.PID_MatrixYoung,ValueType.Scalar, "MPa")
    units = property.getUnitName()
    value = property.getValue()
    print(type(units))
    print(type(value))
    vu = str(value) +' '+ '['+units + ']'
    print(type(vu))
    print(vu)
    

