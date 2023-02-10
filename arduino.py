import umsgpack
import machine
import uasyncio
import _thread
import time

REQUEST = 0
RESPONSE = 1
NOTIFY = 2
msgid = 0
response_obj = []
request_obj = []

async def async_receiver():
	receiver("Receiver");

from uasyncio import Event

evt_resp = Event()

def receiver(ThreadName):
	global response_obj
	global request_obj
	while True:
		res = machine.RPC().read()
		while res and len(res) > 0:
			try:
				obj, i = umsgpack.loads(res)
				if obj[0] is RESPONSE:
					response_obj = obj
				if obj[0] is REQUEST:
					request_obj = obj
				res = res[i:]
			except:
				pass

def _rpc_call(_class_name, _function_name, args):
	global msgid
	global response_obj
	# wait for response
	message = umsgpack.dumps([REQUEST, msgid, _class_name.lower() + "_" + _function_name, args])
	machine.RPC().write(message)
	#res = machine.RPC().readinto()
	#response_obj, i = umsgpack.loads(res)
	while len(response_obj) < 1 or response_obj[0] is not RESPONSE or msgid is not response_obj[1]:
		time.sleep(0.01)
	msgid += 1
	res = response_obj[3]
	if response_obj[2] is not None:
		print(response_obj[2])
	response_obj = []
	return res

def _rpc_send(_class_name, _function_name, args):
	global msgid
	global request_obj
	# don't wait for response
	message = umsgpack.dumps([REQUEST, msgid, _class_name.lower() + "_" + _function_name, args])
	machine.RPC().write(message)

def init():
	machine.RPC().init()
	_thread.start_new_thread(receiver, ("Receiver", ))

class ArduinoBaseType(type):
    arduino_class_name = ""

    def __getattr__(cls, func_name):
        # A static/class method was called (e.g. WiFi.begin)
        def wrapper(*args):
            print("Called static method: %s.%s (with %d args)"
                % (cls.arduino_class_name, func_name, len(args)))
            #return _arduino_call(self, self.arduino_class_name, func_name, args)
        return wrapper

class ArduinoObjectBase:
    __metaclass__ = ArduinoBaseType

    def __init__(self, *args):
        print("Object instantiated: %s (with %d args)"
            % (self.arduino_class_name, len(args)))
        args = list(args)
        args.insert(0, 0)
        self.id = _rpc_call(self.arduino_class_name, "new", args)
        pass

    def __getattr__(self, func_name):
        # self is a generic wrapper class like Arduino_Servo
        def wrapper(*args):
            print("Called object method: %s.%s (with %d args)"
                % (self.arduino_class_name, func_name, len(args)))
            args = list(args)
            args.insert(0, self.id)
            return _rpc_call(self.arduino_class_name, func_name, args)
        return wrapper

def __getattr__(name):
    return ArduinoBaseType("Arduino_" + name, (ArduinoObjectBase,), {"arduino_class_name": name})
