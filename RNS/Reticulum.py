from .Interfaces import *
import configparser
from .vendor.configobj import ConfigObj
import RNS
import atexit
import struct
import array
import os.path
import os
import RNS

#import traceback

class Reticulum:
	MTU            = 500
	HEADER_MAXSIZE = 23
	MDU            = MTU - HEADER_MAXSIZE

	router         = None
	config         = None
	
	configdir    = os.path.expanduser("~")+"/.reticulum"
	configpath   = ""
	storagepath  = ""
	cachepath    = ""
	
	@staticmethod
	def exit_handler():
		RNS.Transport.exitHandler()
		RNS.Identity.exitHandler()

	def __init__(self,configdir=None):
		if configdir != None:
			Reticulum.configdir = configdir
		
		Reticulum.configpath   = Reticulum.configdir+"/config"
		Reticulum.storagepath = Reticulum.configdir+"/storage"
		Reticulum.cachepath = Reticulum.configdir+"/storage/cache"

		Reticulum.__allow_unencrypted = False
		Reticulum.__transport_enabled = False
		Reticulum.__use_implicit_proof = True

		if not os.path.isdir(Reticulum.storagepath):
			os.makedirs(Reticulum.storagepath)

		if not os.path.isdir(Reticulum.cachepath):
			os.makedirs(Reticulum.cachepath)

		if os.path.isfile(self.configpath):
			self.config = ConfigObj(self.configpath)
			RNS.log("Configuration loaded from "+self.configpath)
		else:
			RNS.log("Could not load config file, creating default configuration file...")
			self.createDefaultConfig()
			RNS.log("Default config file created. Make any necessary changes in "+Reticulum.configdir+"/config and start Reticulum again.")
			RNS.log("Exiting now!")
			exit(1)

		self.applyConfig()
		RNS.Identity.loadKnownDestinations()

		RNS.Transport.start()

		atexit.register(Reticulum.exit_handler)

	def applyConfig(self):
		if "logging" in self.config:
			for option in self.config["logging"]:
				value = self.config["logging"][option]
				if option == "loglevel":
					RNS.loglevel = int(value)
					if RNS.loglevel < 0:
						RNS.loglevel = 0
					if RNS.loglevel > 7:
						RNS.loglevel = 7

		if "reticulum" in self.config:
			for option in self.config["reticulum"]:
				value = self.config["reticulum"][option]
				if option == "enable_transport":
					v = self.config["reticulum"].as_bool(option)
					if v == True:
						Reticulum.__transport_enabled = True
				if option == "use_implicit_proof":
					v = self.config["reticulum"].as_bool(option)
					if v == True:
						Reticulum.__use_implicit_proof = True
					if v == False:
						Reticulum.__use_implicit_proof = False
				if option == "allow_unencrypted":
					v = self.config["reticulum"].as_bool(option)
					if v == True:
						RNS.log("", RNS.LOG_CRITICAL)
						RNS.log("! ! !     ! ! !     ! ! !", RNS.LOG_CRITICAL)
						RNS.log("", RNS.LOG_CRITICAL)
						RNS.log("Danger! Encryptionless links have been allowed in the config file!", RNS.LOG_CRITICAL)
						RNS.log("Beware of the consequences! Any data sent over a link can potentially be intercepted,", RNS.LOG_CRITICAL)
						RNS.log("read and modified! If you are not absolutely sure that you want this,", RNS.LOG_CRITICAL)
						RNS.log("you should exit Reticulum NOW and change your config file!", RNS.LOG_CRITICAL)
						RNS.log("", RNS.LOG_CRITICAL)
						RNS.log("! ! !     ! ! !     ! ! !", RNS.LOG_CRITICAL)
						RNS.log("", RNS.LOG_CRITICAL)
						Reticulum.__allow_unencrypted = True


		for name in self.config["interfaces"]:
			c = self.config["interfaces"][name]

			try:
				if ("interface_enabled" in c) and c.as_bool("interface_enabled") == True:
					if c["type"] == "UdpInterface":
						interface = UdpInterface.UdpInterface(
							RNS.Transport,
							name,
							c["listen_ip"],
							int(c["listen_port"]),
							c["forward_ip"],
							int(c["forward_port"])
						)

						if "outgoing" in c and c.as_bool("outgoing") == True:
							interface.OUT = True
						else:
							interface.OUT = False

						RNS.Transport.interfaces.append(interface)

					if c["type"] == "SerialInterface":
						port = c["port"] if "port" in c else None
						speed = int(c["speed"]) if "speed" in c else 9600
						databits = int(c["databits"]) if "databits" in c else 8
						parity = c["parity"] if "parity" in c else "N"
						stopbits = int(c["stopbits"]) if "stopbits" in c else 1

						if port == None:
							raise ValueError("No port specified for serial interface")

						interface = SerialInterface.SerialInterface(
							RNS.Transport,
							name,
							port,
							speed,
							databits,
							parity,
							stopbits
						)

						if "outgoing" in c and c["outgoing"].lower() == "true":
							interface.OUT = True
						else:
							interface.OUT = False

						RNS.Transport.interfaces.append(interface)

					if c["type"] == "KISSInterface":
						preamble = int(c["preamble"]) if "preamble" in c else None
						txtail = int(c["txtail"]) if "txtail" in c else None
						persistence = int(c["persistence"]) if "persistence" in c else None
						slottime = int(c["slottime"]) if "slottime" in c else None
						flow_control = (True if c["flow_control"] == "true" else False) if "flow_control" in c else False

						port = c["port"] if "port" in c else None
						speed = int(c["speed"]) if "speed" in c else 9600
						databits = int(c["databits"]) if "databits" in c else 8
						parity = c["parity"] if "parity" in c else "N"
						stopbits = int(c["stopbits"]) if "stopbits" in c else 1

						if port == None:
							raise ValueError("No port specified for serial interface")

						interface = KISSInterface.KISSInterface(
							RNS.Transport,
							name,
							port,
							speed,
							databits,
							parity,
							stopbits,
							preamble,
							txtail,
							persistence,
							slottime,
							flow_control
						)

						if "outgoing" in c and c["outgoing"].lower() == "true":
							interface.OUT = True
						else:
							interface.OUT = False

						RNS.Transport.interfaces.append(interface)

					if c["type"] == "AX25KISSInterface":
						preamble = int(c["preamble"]) if "preamble" in c else None
						txtail = int(c["txtail"]) if "txtail" in c else None
						persistence = int(c["persistence"]) if "persistence" in c else None
						slottime = int(c["slottime"]) if "slottime" in c else None
						flow_control = (True if c["flow_control"] == "true" else False) if "flow_control" in c else False

						port = c["port"] if "port" in c else None
						speed = int(c["speed"]) if "speed" in c else 9600
						databits = int(c["databits"]) if "databits" in c else 8
						parity = c["parity"] if "parity" in c else "N"
						stopbits = int(c["stopbits"]) if "stopbits" in c else 1

						callsign = c["callsign"] if "callsign" in c else ""
						ssid = int(c["ssid"]) if "ssid" in c else -1

						if port == None:
							raise ValueError("No port specified for serial interface")

						interface = AX25KISSInterface.AX25KISSInterface(
							RNS.Transport,
							name,
							callsign,
							ssid,
							port,
							speed,
							databits,
							parity,
							stopbits,
							preamble,
							txtail,
							persistence,
							slottime,
							flow_control
						)

						if "outgoing" in c and c["outgoing"].lower() == "true":
							interface.OUT = True
						else:
							interface.OUT = False

						RNS.Transport.interfaces.append(interface)

					if c["type"] == "RNodeInterface":
						frequency = int(c["frequency"]) if "frequency" in c else None
						bandwidth = int(c["bandwidth"]) if "bandwidth" in c else None
						txpower = int(c["txpower"]) if "txpower" in c else None
						spreadingfactor = int(c["spreadingfactor"]) if "spreadingfactor" in c else None
						codingrate = int(c["codingrate"]) if "codingrate" in c else None
						flow_control = (True if c["flow_control"] == "true" else False) if "flow_control" in c else False

						port = c["port"] if "port" in c else None
						
						if port == None:
							raise ValueError("No port specified for RNode interface")

						interface = RNodeInterface.RNodeInterface(
							RNS.Transport,
							name,
							port,
							frequency,
							bandwidth,
							txpower,
							spreadingfactor,
							flow_control
						)

						if "outgoing" in c and c["outgoing"].lower() == "true":
							interface.OUT = True
						else:
							interface.OUT = False

						RNS.Transport.interfaces.append(interface)
				else:
					RNS.log("Skipping disabled interface \""+name+"\"", RNS.LOG_VERBOSE)

			except Exception as e:
				RNS.log("The interface \""+name+"\" could not be created. Check your configuration file for errors!", RNS.LOG_ERROR)
				RNS.log("The contained exception was: "+str(e), RNS.LOG_ERROR)
				raise e
				

	def createDefaultConfig(self):
		self.config = ConfigObj(__default_rns_config__)
		self.config.filename = Reticulum.configpath
		
		if not os.path.isdir(Reticulum.configdir):
			os.makedirs(Reticulum.configdir)
		self.config.write()
		self.applyConfig()

	@staticmethod
	def should_allow_unencrypted():
		return Reticulum.__allow_unencrypted

	@staticmethod
	def should_use_implicit_proof():
		return Reticulum.__use_implicit_proof

	@staticmethod
	def transport_enabled():
		return Reticulum.__transport_enabled

# Default configuration file:
__default_rns_config__ = '''# This is the default Reticulum config file.
# You should probably edit it to include any additional,
# interfaces and settings you might need.

[reticulum]

# Don't allow unencrypted links by default.
# If you REALLY need to allow unencrypted links, for example
# for debug or regulatory purposes, this can be set to true.
allow_unencrypted = False

# If you enable Transport, your system will route traffic
# for other peers, pass announces and serve path requests.
# Unless you really know what you're doing, this should be
# done only for systems that are suited to act as transport
# nodes, ie. if they are stationary and always-on.
enable_transport = False


[logging]
# Valid log levels are 0 through 7:
#   0: Log only critical information
#   1: Log errors and lower log levels
#   2: Log warnings and lower log levels
#   3: Log notices and lower log levels
#   4: Log info and lower (this is the default)
#   5: Verbose logging
#   6: Debug logging
#   7: Extreme logging

loglevel = 4


# The interfaces section defines the physical and virtual
# interfaces Reticulum will use to communicate on. This
# section will contain examples for a variety of interface
# types. You can modify these or use them as a basis for
# your own config, or simply remove the unused ones.

[interfaces]

  # This interface enables communication with other
  # Reticulum nodes on your local ethernet networks.
  [[Default UDP Interface]]
  	type = UdpInterface
    interface_enabled = True
    outgoing = True
    listen_ip = 0.0.0.0
    listen_port = 7777
    forward_ip = 255.255.255.255
    forward_port = 7777


  # Here's an example of how to add a LoRa interface
  # using the RNode LoRa transceiver.

  [[RNode LoRa Interface]]
    type = RNodeInterface

    # Enable interface if you want use it!
    interface_enabled = False

    # Allow transmit on interface. Setting
    # this to false will create a listen-
    # only interface.
    outgoing = true

    # Serial port for the device
    port = /dev/ttyUSB0

    # Set frequency to 867.2 MHz
    frequency = 867200000

    # Set LoRa bandwidth to 125 KHz
    bandwidth = 125000

    # Set TX power to 7 dBm (5 mW)
    txpower = 7

    # Select spreading factor 8. Valid 
    # range is 7 through 12, with 7
    # being the fastest and 12 having
    # the longest range.
    spreadingfactor = 8

    # Select coding rate 5. Valid range
    # is 5 throough 8, with 5 being the
    # fastest, and 8 the longest range.
    codingrate = 5

  # An example KISS modem interface. Useful for running
  # Reticulum over packet radio hardware.

  [[Packet Radio KISS Interface]]
    type = KISSInterface

    # Enable interface if you want use it!
    interface_enabled = False

    # Allow transmit on interface.
    outgoing = true

	# Serial port for the device
    port = /dev/ttyUSB1

    # Set the serial baud-rate and other
    # configuration parameters.
    speed = 115200    
    databits = 8
    parity = none
    stopbits = 1

    # Whether to use KISS flow-control.
    # This is useful for modems with a
    # small internal packet buffer.
    flow_control = false

    # Set the modem preamble. A 150ms
    # preamble should be a reasonable
    # default, but may need to be
    # increased for radios with slow-
    # opening squelch and long TX/RX
    # turnaround
    preamble = 150

    # Set the modem TX tail. In most
    # cases this should be kept as low
    # as possible to not waste airtime.
    txtail = 10

    # Configure CDMA parameters. These
    # settings are reasonable defaults.
    persistence = 200
    slottime = 20

  # If you're using Reticulum on amateur radio spectrum,
  # you might want to use the AX.25 KISS interface. This
  # way, Reticulum will automatically encapsulate it's
  # traffic in AX.25 and also identify your stations
  # transmissions with your callsign and SSID.
  # 
  # Only do this if you really need to! Reticulum doesn't
  # need the AX.25 layer for anything, and it incurs extra
  # overhead on every packet to encapsulate in AX.25.

  [[Packet Radio AX.25 KISS Interface]]
    type = AX25KISSInterface

    # Set the station callsign and SSID
    callsign = NO1CLL
    ssid = 0

    # Enable interface if you want use it!
    interface_enabled = False

    # Allow transmit on interface.
    outgoing = true

	# Serial port for the device
    port = /dev/ttyUSB2

    # Set the serial baud-rate and other
    # configuration parameters.
    speed = 115200    
    databits = 8
    parity = none
    stopbits = 1

    # Whether to use KISS flow-control.
    # This is useful for modems with a
    # small internal packet buffer.
    flow_control = false

    # Set the modem preamble. A 150ms
    # preamble should be a reasonable
    # default, but may need to be
    # increased for radios with slow-
    # opening squelch and long TX/RX
    # turnaround
    preamble = 150

    # Set the modem TX tail. In most
    # cases this should be kept as low
    # as possible to not waste airtime.
    txtail = 10

    # Configure CDMA parameters. These
    # settings are reasonable defaults.
    persistence = 200
    slottime = 20

'''.splitlines()