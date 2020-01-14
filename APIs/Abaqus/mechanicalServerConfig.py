import os
import sys
# Import example-wide configuration
sys.path.extend(['/home/nitram/Documents/work/MUPIF/mupif'])
from Config import config
import AbaqusAPI22
mode = 2

class serverConfig(config):
    def __init__(self, mode):
        # inherit necessary variables: nshost, nsport, hkey, server, serverNathost
        super(serverConfig, self).__init__(mode)
        # Let Daemon run on higher ports
        self.serverPort = self.serverPort+1
        if self.serverNatport is not None:
            self.serverNatport += 1
        self.socketApps = self.socketApps+1
        self.portsForJobs = (9550, 9800)
        self.jobNatPorts = [None] if self.jobNatPorts[0] is None else list(range(6230, 6300))
        
        self.applicationClass = AbaqusAPI22.AbaqusApp
        self.applicationInitialFile = 'input.in'  # dummy file
        self.jobManName = 'Mupif.Abaqus@Demo'  # Name of job manager
        self.jobManWorkDir = os.path.abspath(os.path.join(os.getcwd(), 'mechanicalWorkDir'))
        # self.sshHost = '147.32.130.71'
        self.sshHost = '127.0.0.1'  # ip adress of the server running mechanical server
        
        self.serverPort = 44530
        self.serverNatport = None
        self.serverNathost = None
        self.serverUserName = os.getenv('USER')
