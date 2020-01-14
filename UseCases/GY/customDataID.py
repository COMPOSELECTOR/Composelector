# -*- coding: utf-8 -*-
"""
Created on Fri May 10 11:36:19 2019

@author: Yao Koutsawa
"""
from enum import IntEnum

class MyPropertyID(IntEnum):
    PID_Footprint = 1000000
    PID_Braking_Force = 1000001
    PID_Stiffness = 1000002
    PID_Hyper1 = 1000003
    PID_maxDisplacement = 1000004
    PID_maxMisesStress = 1000005
    PID_maxPrincipalStress = 1000006
    
class MyFieldID(IntEnum):   
    FID_Mises_Stress = 2000000
    FID_MaxPrincipal_Stress = 2000001
    FID_MidPrincipal_Stress = 2000002
    FID_MinPrincipal_Stress = 2000003
    
    FID_MaxPrincipal_Strain = 2000004
    FID_MidPrincipal_Strain = 2000005
    FID_MinPrincipal_Strain = 2000006
    

