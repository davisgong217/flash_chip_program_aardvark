#!/usr/bin/env python3
#==========================================================================
#aardvark HW 
#Author: Davis Gong
#Date: 2022.01.12
#==========================================================================

#==========================================================================
# IMPORTS
#==========================================================================
from __future__ import division, with_statement, print_function
from aardvark_py import *

#==========================================================================
# FUNCTIONS
#==========================================================================
class AARDVARK_MASTER:
	def __init__(self,**kwargs):
		#if SN is assigned
		self.porttype=kwargs.get('type','SPI_I2C')
		self.sn=kwargs.get('sn',None)
		self.port=kwargs.get('port',0)
		self.handle=-1
		self.i2cbitrate=kwargs.get('i2cbitrate',400)
		self.i2cpullup=kwargs.get('i2cpullup',AA_I2C_PULLUP_BOTH)              #AA_I2C_PULLUP_BOTH/AA_I2C_PULLUP_NONE
		self.i2cbustimeout=kwargs.get('i2cbustimeout',3)  
		self.spibitrate=kwargs.get('spibitrate',8000) 
		self.spimode=kwargs.get('spimode',0)   
		self.spibitorder=kwargs.get('spibitorder',AA_SPI_BITORDER_MSB)         #AA_SPI_BITORDER_MSB/AA_SPI_BITORDER_LSB
		self.spissactive=kwargs.get('spissactive',AA_SPI_SS_ACTIVE_LOW)        #AA_SPI_SS_ACTIVE_LOW/AA_SPI_SS_ACTIVE_HIGH
		
		if self.porttype=='SPI_I2C':
			self.aaconfig=AA_CONFIG_SPI_I2C
		elif self.porttype=='SPI_GPIO':
			self.aaconfig=AA_CONFIG_SPI_GPIO
		elif self.porttype=='I2C_GPIO':
			self.aaconfig=AA_CONFIG_GPIO_I2C
		elif self.porttype=='GPIO':
			self.aaconfig=AA_CONFIG_GPIO_ONLY 		
		
		self.portvalidate()
		if self.port>=0:
			self.handle = aa_open(self.port)
			if (self.handle > 0):
				aa_configure(self.handle,self.aaconfig)
				if self.aaconfig==AA_CONFIG_SPI_GPIO:
					self.iodirmask=AA_GPIO_SCL+AA_GPIO_SDA
				elif self.aaconfig==AA_CONFIG_GPIO_I2C:
					self.iodirmask=AA_GPIO_MISO+AA_GPIO_SCK+AA_GPIO_MOSI+AA_GPIO_SS
				elif self.aaconfig==AA_CONFIG_SPI_I2C:
					self.iodirmask=0x00
				elif self.aaconfig==AA_CONFIG_GPIO_ONLY :
					self.iodirmask=AA_GPIO_SCL+AA_GPIO_SDA+AA_GPIO_MISO+AA_GPIO_SCK+AA_GPIO_MOSI+AA_GPIO_SS
				aa_gpio_direction(self.handle,self.iodirmask)
				aa_gpio_pullup(self.handle,0x00)
									
				#i2C configuration
				if self.aaconfig==AA_CONFIG_GPIO_I2C or self.aaconfig==AA_CONFIG_SPI_I2C:
					aa_i2c_bitrate(self.handle,self.i2cbitrate)
					aa_i2c_bus_timeout(self.handle,self.i2cbustimeout)
					aa_i2c_pullup(self.handle,self.i2cpullup)

				#spi configuration
				if self.aaconfig==AA_CONFIG_SPI_GPIO or self.aaconfig==AA_CONFIG_SPI_I2C:
					aa_spi_bitrate(self.handle,self.spibitrate)
					spipolarity=AA_SPI_POL_RISING_FALLING
					spiphase=AA_SPI_PHASE_SAMPLE_SETUP
					if self.spimode==0 or self.spimode==1:
						spipolarity=AA_SPI_POL_RISING_FALLING
					elif self.spimode==2 or self.spimode==3:
						spipolarity=AA_SPI_POL_FALLING_RISING
					if self.spimode==0 or self.spimode==2:
						spiphase=AA_SPI_PHASE_SAMPLE_SETUP
					elif self.spimode==1 or self.spimode==3:
						spiphase=AA_SPI_PHASE_SETUP_SAMPLE
												
					aa_spi_configure(self.handle,spipolarity,spiphase,self.spibitorder)
					aa_spi_master_ss_polarity(self.handle,self.spissactive)
	
	#self.port validation,return -1 if invalid	
	def portvalidate(self):
		devices=self.checkavailable()
		#if assigned sn
		if self.sn:
			self.port=-1
			for device in devices:
				if self.sn in device:
					self.port=device[0]
					break
		#if assigned port
		elif self.port>=0:
			port=self.port
			self.port=-1
			for device in devices:
				if port==device[0]:
					self.port=port
					break
					
	def setgpio(self,data):
		aa_gpio_set(self.handle,data)
		return
					
	def checkavailable(self):
		(num, ports, unique_ids) = aa_find_devices_ext(16, 16)
		device_list=[]
		for i in range(num):
			if not (ports[i] & AA_PORT_NOT_FREE):
				device_list.append([ports[i],unique_ids[i]])
		return device_list
	
	# |start|addrss+W|reg_addr|data(nLength)		
	def i2cwritereg(self,slave_addr,reg_addr,data,delay=0):
		if self.handle>0:
			data_out=[reg_addr]
			data_out.extend(data)
			length=aa_i2c_write(self.handle, slave_addr, AA_I2C_NO_FLAGS, array('B', data_out))
			aa_sleep_ms(delay)
			if length==len(data_out):
				return data
		else:
			return 0
	
	# |start|addrss+W|reg_addr|re_start|addrss+R|data(nLength)			
	def i2creadreg(self, slave_addr,reg_addr,length):
		if self.handle>0:
			regaddress=[]
			for reg in reg_addr:
				regaddress.append(reg & 0xFF)
			aa_i2c_write(self.handle, slave_addr, AA_I2C_NO_STOP, array('B', regaddress))
			(count, data_in) = aa_i2c_read(self.handle, slave_addr, AA_I2C_NO_FLAGS, length)
			if (count<= 0 or count!=length):
				return []
			else:
				return data_in.tolist()
					

	def i2c_write_read(self,slave_addr,data,length):
		if self.handle>0:
			(return_data,w_count,data_in,r_count) =aa_i2c_write_read (self.handle,slave_addr,AA_I2C_NO_FLAGS,array('B', data),length)
			if (r_count<= 0 or r_count!=length):
				return []
			else:
				return data_in.tolist()
				
				
	def spiwritereg(self,data,delay=1):
		if self.handle>0:
			data_out=array('B', data)
			data_in = array('B', [ 0xff for i in range(65535)])
			count, data_in = aa_spi_write(self.handle,data_out, 0)
			aa_sleep_ms(delay)
			if count < 0:
				print('error: %s\n' % aa_status_string(count))
				return 0
			elif count!= len(data_out):
				print('error: read %d bytes (expected %d)' %(count, len(data_out)))
				return 0
			else:
				return len(data)
		else:
			return 0

	def spireadreg(self,data,length):
		if self.handle>0:
			data_out = array_u08(len(data)+length)
			data_in = array_u08(len(data)+length)
			for i in range(len(data)):
				data_out[i]=data[i]
			(count, data_in) = aa_spi_write(self.handle, data_out, data_in)
			if (count < 0):
				print("error: %s\n" % aa_status_string(count))
				return []
			elif (count != length+len(data)):
				print("error: read %d bytes (expected %d)" % (count-len(data), length))
				return []
			else:
				return data_in.tolist()
		else:
			return []
	
	def target_power(self,on=False):
		if on:
			aa_target_power (self.handle,AA_TARGET_POWER_BOTH)
		else:
			aa_target_power (self.handle,AA_TARGET_POWER_NONE)
		
									
	def close(self,**kwargs):
		if self.handle>0:
			aa_close(self.handle)


