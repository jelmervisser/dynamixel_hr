#!/usr/bin/env python

# Dynamixel library for MX28 and MX64

# WINDOWS WARNING: For best performance, parameters of the COM Port should be set to maximum baud rate, and 1ms delay (Device Manager, COM Ports, properties, advanced)

import sys
import serial
import time
import logging
from threading import Lock
import json
import array
from collections import OrderedDict

logging.basicConfig(level=logging.DEBUG)


class DxlConfigurationException(Exception):    pass
class DxlCommunicationException(Exception):    pass


class DxlRegister():
    def __init__(self,address,size,mode='r',eeprom=False,fromdxl= lambda x: x,todxl= lambda x: x):
        self.address=address
        self.size=size
        self.mode=mode
        self.eeprom=eeprom
        self.fromdxl=fromdxl
        self.todxl=todxl

class DxlRegisterByte(DxlRegister):
    def __init__(self,address,mode='r',eeprom=False):
        DxlRegister.__init__(self,address,1,mode,eeprom,fromdxl=lambda x:x[0],todxl=lambda x:[x])

class DxlRegisterWord(DxlRegister):
    def __init__(self,address,mode='r',eeprom=False):
        DxlRegister.__init__(self,address,2,mode,eeprom,fromdxl=lambda x:x[0]+(x[1]<<8),todxl=lambda x:[x&0xFF,(x>>8)&0xFF] )

class DynamixelMotor:
    def __init__(self):
        self.registers=OrderedDict()
        
    def getRegisterCmd(self,name):
        if not name in self.registers.keys():
            raise DxlConfigurationException,"Model %s has no register called %s"%(name,self.model_name)
        r=self.registers[name]
        if not 'r' in r.mode:
            raise DxlConfigurationException,"Register %s is not readable"%(name)
        return (r.size,[DynamixelChain.CMD_READ_DATA,r.address,r.size])

    def setRegisterCmd(self,name,value):
        if not name in self.registers.keys():
            raise DxlConfigurationException,"Model %s has no register called %s"%(self.model_name,name)
        r=self.registers[name]
        if not 'w' in r.mode:
            raise DxlConfigurationException,"Register %s is not writable"%(name)
        if r.size!=len(value):
            raise DxlConfigurationException,"Model %s register %s has size %d: passed size %d"%(self.model_name,name,r.size,len(value))
            
        return (0,[DynamixelChain.CMD_WRITE_DATA,r.address]+value )

    def sort(self):
        self.registers = OrderedDict( sorted(self.registers.iteritems(), key=lambda x: x[1].address) )
    
class DynamixelMotorAXMX(DynamixelMotor):
    def __init__(self):
        DynamixelMotor.__init__(self)

        self.registers["model_number"]=         DxlRegisterWord(0x00,'r',eeprom=True)
        self.registers["firmware"]=             DxlRegisterByte(0x02,'r',eeprom=True)
        self.registers["id"]=                   DxlRegisterByte(0x03,'rw',eeprom=True)
        self.registers["baud_rate"]=            DxlRegisterByte(0x04,'rw',eeprom=True)
        self.registers["return_delay"]=         DxlRegisterByte(0x05,'rw',eeprom=True)
        self.registers["cw_angle_limit"]=       DxlRegisterWord(0x06,'rw',eeprom=True)
        self.registers["ccw_angle_limit"]=      DxlRegisterWord(0x08,'rw',eeprom=True)
        self.registers["high_temp_limit"]=      DxlRegisterByte(0x0b,'rw',eeprom=True)
        self.registers["low_voltage_limit"]=    DxlRegisterByte(0x0c,'rw',eeprom=True)
        self.registers["high_voltage_limit"]=   DxlRegisterByte(0x0d,'rw',eeprom=True)
        self.registers["max_torque"]=           DxlRegisterWord(0x0e,'rw',eeprom=True)
        self.registers["status_return_level"]=  DxlRegisterByte(0x10,'rw',eeprom=True)
        self.registers["alarm_led"]=            DxlRegisterByte(0x11,'rw',eeprom=True)
        self.registers["alarm_shutdown"]=       DxlRegisterByte(0x12,'rw',eeprom=True)

        self.registers["torque_enable"]=        DxlRegisterByte(0x18,'rw')
        self.registers["led"]=                  DxlRegisterByte(0x19,'rw')
        
        # Here goes compliance or PID or DIP
        
        self.registers["goal_pos"]=             DxlRegisterWord(0x1E,'rw')
        self.registers["moving_speed"]=         DxlRegisterWord(0x20,'rw')
        self.registers["torque_limit"]=         DxlRegisterWord(0x22,'rw')
        self.registers["present_position"]=     DxlRegisterWord(0x24,'r')
        self.registers["present_speed"]=        DxlRegisterWord(0x26,'r')
        self.registers["present_load"]=         DxlRegisterWord(0x28,'r')

        self.registers["present_voltage"]=      DxlRegisterByte(0x2A,'r')
        self.registers["present_temp"]=         DxlRegisterByte(0x2B,'r')
        self.registers["registered"]=           DxlRegisterByte(0x2C,'r')
        self.registers["moving"]=               DxlRegisterByte(0x2E,'r')
        self.registers["lock"]=                 DxlRegisterByte(0x2F,'rw')
        self.registers["punch"]=                DxlRegisterWord(0x30,'rw')
        
        self.sort()


class DynamixelMotorAX12(DynamixelMotorAXMX):
    model_name="AX12"
    model_number=12
    def __init__(self):
        DynamixelMotorAXMX.__init__(self)

        self.registers["cw_compliance_margin"]= DxlRegisterByte(0x1A,'rw')
        self.registers["ccw_compliance_margin"]=DxlRegisterByte(0x1B,'rw')
        self.registers["cw_compliance_slope"]=  DxlRegisterByte(0x1C,'rw')
        self.registers["ccw_compliance_slope"]= DxlRegisterByte(0x1D,'rw')

        self.sort()
        

class DynamixelMotorMX28(DynamixelMotorAXMX):
    model_name="MX28"
    model_number=29
    def __init__(self):
        DynamixelMotorAXMX.__init__(self)

        self.registers["d_gain"]=               DxlRegisterByte(0x1A,'rw')
        self.registers["i_gain"]=               DxlRegisterByte(0x1B,'rw')
        self.registers["p_gain"]=               DxlRegisterByte(0x1C,'rw')
        
        self.sort()

class DynamixelMotorMX64(DynamixelMotorAXMX):
    model_name="MX64"
    model_number=310
    def __init__(self):
        DynamixelMotorAXMX.__init__(self)
        
        self.registers["d_gain"]=               DxlRegisterByte(0x1A,'rw')
        self.registers["i_gain"]=               DxlRegisterByte(0x1B,'rw')
        self.registers["p_gain"]=               DxlRegisterByte(0x1C,'rw')
        
        self.sort()
        




def buildMotorFromModel(modelnumber):
    if modelnumber not in DynamixelChain.MODELS.keys():
        raise DxlConfigurationException,"Could not create Dynamixel motor for non-existing model number %d"%modelnumber
    if modelnumber==12:
        return DynamixelMotorAX12()
    elif modelnumber==29:
        return DynamixelMotorMX28()
    elif modelnumber==310:
        return DynamixelMotorMX64()
    else:
        raise DxlConfigurationException,"Could not create Dynamixel motor for non-implemented model number %d"%modelnumber
        
        
        
        
        
class DynamixelChain:
    """
    Manages a list of Dynamixel motors on the same serial link
    Provides thread-safe access to the chain
    """
    BROADCAST      = 0xFE
    
    CMD_PING       = 0x01
    CMD_READ_DATA  = 0x02
    CMD_WRITE_DATA = 0x03
    CMD_REG_WRITE  = 0x04
    CMD_ACTION     = 0x05
    CMD_RESET      = 0x06
    CMD_SYNC_WRITE = 0x83
    
    MODELS={12:"AX12",29:"MX28",310:"MX64"}

    def __init__(self, portname,rate=57142,timeout=0.04):
        """
        DO NOT CHANGE THE DEFAULT BAUDRATE HERE: 57142 is the factory setting of Dynamixel motors
        """
        self.portname=portname
        self.rate=rate
        self.timeout=timeout
        self.lock=Lock()
        self.open()
        self.configuration=None
        self.motors={}
    


    # Low-level communication (Thread unsafe functions with _)
    
    def open(self):
        with self.lock:
            self._open()

    def _open(self):
        logging.info("Opening serial port %s at rate %d bps, timeout %f s"%(self.portname,self.rate,self.timeout))    
        self.port=serial.Serial(self.portname,self.rate,timeout=self.timeout)    

    def close(self):
        with self.lock:
            self._close()

    def _close(self):
        try:
            logging.info("Closing serial port %s"%(self.portname))
            self.port.close()
        except:
            logging.warning("Could not close port %s"%self.portname)
    
    def reopen(self):
        with self.lock:
            self._close()
            self._open()

    def send(self,id,packet):
        with self.lock:
            self._send(id,packet)
            
    def _send(self, id, packet):
        """ Takes a payload, packages it as [header,id,length,payload,checksum], sends it on serial and flush"""
        checksumed_data = [id, len(packet)+1] + packet
        
        data="".join(map(chr, [0xFF, 0xFF] + checksumed_data + [self.checksum(checksumed_data)]))
        self.port.write(data)
        self.port.flushOutput()

    def recv(self):
        with self.lock:
            return self._recv()

    def _recv(self):
        """ Wait for a response on the serial, validate it, raise errors if any, return id and data if any """
        # Read the first 4 bytes 0xFF,0xFF,id,length
        header = array.array('B',self.port.read(4))
        if(len(header)!=4):
            raise DxlCommunicationException('Could not read first 4 bytes of expected response, got %d bytes'%len(header))
        else :
            id,expectedsize=header[2:4]
            # Read number of expected bytes
            data=array.array('B',self.port.read(expectedsize))
            if len(data)!=expectedsize:
                raise DxlCommunicationException('Could not read %d data bytes of expected response, got %d bytes'%(len(expectedsize),len(data)))
                
            error=data[0]
            if error!=0:
                # TODO Distinguish communication/Hardware errors
                raise DxlCommunicationException('Received error code from motor %d: %d'%(id,error))
            
            checksum=self.checksum(header[2:]+data[:-1])
            if checksum!=data[-1]:
                raise DxlCommunicationException('Invalid checksum')
            data=data[1:-1]
            #~ print data
            return (id,data)

    def comm(self,id,packet):
        with self.lock:
            return self._comm(id,packet)

    def _comm(self,id,packet):
        self._send(id,packet)
        return self._recv()

    def checksum(self,values):
        """ Compute packet checksum """
        return (~sum(values))&0xFF



    # Basic commands
    
    def _ping(self,id):
        self._send(id,[self.CMD_PING])
        self._recv()
        
    def _ping_broadcast(self):
        """ Perform a ping on all servos. Returns list of responding IDs """
        self._send(self.BROADCAST,[self.CMD_PING])
        l=[]
        while True:
            try:
                (id,data)=self._recv()
                l.append(id)
            except DxlCommunicationException:
                break            
        return l


    def _read(self,id,address,size):
        data=self._comm(id,[self.CMD_READ_DATA,address,size])[1]
        if len(data)!=size:
            raise DxlCommunicationException('Read command did not obtain the %d bytes expected: got %d bytes'%(size,len(data)))
        return data

    def _write(self,id,address,values):        
        self._comm(id,[self.CMD_WRITE_DATA,register,values])


    def _get_model(self,id):
        data=self._read(id,0,2)
        return (data[1]<<8)+data[0]


    def modelFromString(self,s):
        for k,v in self.MODELS.items():
            if v==s: return k
        return None


        
    # Register Access

    def get_reg(self,id,name):
        m=self.motors[id]
        reg=m.registers[name]
        (esize,cmd)=m.getRegisterCmd(name)
        (nid,data)=self.comm(id,cmd)
        if len(data)!=esize:
            raise DxlCommunicationException,'Motor ID %d did not retrieve expected register %s size %d: got %d bytes'%(id,name,esize,len(data)) 
        return reg.fromdxl(data)

    def set_reg(self,id,name,v):
        m=self.motors[id]
        reg=m.registers[name]
        (esize,cmd)=m.setRegisterCmd(name,reg.todxl(v))
        (nid,data)=self.comm(id,cmd)
        if len(data)!=esize:
            raise DxlCommunicationException,'Motor ID %d did not retrieve expected register %s size %d: got %d bytes'%(id,name,esize,len(data)) 

    
        
    # Configuration get/set functionalities
    
    def get_motor_list(self):
        self.motors={}
        ids=self._ping_broadcast()
        for id in ids:
            model=self._get_model(id)
            smodel="unknown"
            if model in self.MODELS.keys():
                smodel=self.MODELS[model]
            logging.info("Found motor ID %d model %s (%d)"%(id,smodel,model))
            self.motors[id]=buildMotorFromModel(model)


    def get_configuration(self):
        self.get_motor_list()
        d=OrderedDict()
        for (id,m) in self.motors.items():
            dd=OrderedDict()
            d[id]=dd
            for (name,r) in m.registers.items():
                dd[name]=self.get_reg(id,name)
        return dd
        
    def set_configuration(self,conf):
        d={}
        self.get_motor_list()
        for id in conf.keys():
            sid=id
            iid=int(sid)
            if iid not in self.motors.keys(): raise DxlConfigurationException,"Cannot find motor ID %d to be configured"%iid
            motor=self.motors[iid]
            for (name,val) in conf[sid].items():
                if name not in motor.registers.keys(): raise DxlConfigurationException,"Cannot configure missing register %s on motor ID %d"%(name,iid)                    
                reg=motor.registers[name]
                current=self.get_reg(iid,name)
                if current==val: continue
                # Value has to be changed
                if not 'w' in reg.mode: # read only: generate error if setting is EEPROM
                    if reg.eeprom: raise DxlConfigurationException,"Cannot change EEPROM register %s from %d to %d on motor ID %d"%(name,current,val,iid)
                    else: pass
                else:
                    if reg.eeprom:
                        logging.info( "Changed (EEPROM register %s from %d to %d on motor ID %d"%(name,current,val,iid) )
                    self.set_reg(iid,name,val) # if writable set it

    def dump(self):
        conf=self.get_configuration()
        print json.dumps(conf,indent=4,sort_keys=False)



if __name__ == "__main__":    
    chain=DynamixelChain("COM21", rate=1000000)
    #~ chain.reopen()
    chain.dump()

    conf="""
{
    "2": {
        "alarm_shutdown": 36, 
        "lock": 0, 
        "max_torque": 1023, 
        "goal_pos": 200, 
        "present_load": 104, 
        "id": 2, 
        "ccw_compliance_margin": 1, 
        "firmware": 24, 
        "alarm_led": 36, 
        "model_number": 12, 
        "baud_rate": 1, 
        "present_temp": 39, 
        "torque_enable": 1, 
        "moving_speed": 50, 
        "led": 0, 
        "torque_limit": 1023, 
        "status_return_level": 2, 
        "ccw_compliance_slope": 32, 
        "registered": 0, 
        "punch": 32, 
        "cw_compliance_margin": 1, 
        "high_temp_limit": 70, 
        "moving": 0, 
        "ccw_angle_limit": 1023, 
        "low_voltage_limit": 60, 
        "return_delay": 250, 
        "high_voltage_limit": 140, 
        "cw_compliance_slope": 32, 
        "present_speed": 52, 
        "present_voltage": 123, 
        "present_position": 773, 
        "cw_angle_limit": 0
    }
}
"""    
    #~ chain.loadConfiguration(conf)
    chain.set_configuration(json.loads(conf))
    #~ chain.set_reg(1,"torque_enable",1)
    #~ chain.set_reg(1,"moving_speed",50)
    #~ chain.set_reg(1,"goal_pos",100)
    #~ time.sleep(1)
    #~ chain.set_reg(1,"goal_pos",800)
    #~ time.sleep(1)
    #~ chain.set_reg(1,"torque_enable",0)
    
    chain.dump()
    chain.close()
