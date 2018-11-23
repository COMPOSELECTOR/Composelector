import os,sys
#Import example-wide configuration
from Config import config
#import INSA_API


class serverConfig(config):
    def __init__(self,mode):
        #inherit necessary variables: nshost, nsport, hkey, server, serverNathost  
        super(serverConfig, self).__init__(mode)
        #Let Daemon run on higher ports
        self.serverPort = self.serverPort+1
        if self.serverNatport != None:
            self.serverNatport+=1
        self.socketApps = self.socketApps+1
        self.portsForJobs=( 9380, 9500 )
        self.jobNatPorts = [None] if self.jobNatPorts[0]==None else list(range(6230, 6300)) 
        self.jobManName='Mupif.JobManager@INSA'#Name of job manager
        self.jobManWorkDir=os.path.abspath(os.path.join(os.getcwd(), 'INSAWorkDir'))
        self.sshHost = '172.30.0.2'
        self.serverPort = 44382
        self.serverNatport = None
        self.serverNathost = None
        self.serverUserName = os.getenv('USER')
