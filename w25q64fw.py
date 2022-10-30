#q25q64fw flash memory programming 
#Author: Davis Gong
#Date: 2022.09.17

from __future__ import division, with_statement, print_function
from aardvark_device import AARDVARK_MASTER
from aardvark_py import aa_sleep_ms as delay_ms
import color_print
import os
import argparse
import time

device_id =0x90
read_status = 0x05
write_en = 0x06
read_data = 0x03
write_dis = 0x04
page_program = 0x02
sector_erase =0x20
block32k_erase=0x52
block64k_erase=0xd8
chip_erase=0x60
reset_device=0x99

page_size=256
max_page_count=32768
max_read_byte=32768
erase_unit_size=65536

def printhexstring(data):
	if data:
		hexstringdata=['0x{:02X}'.format(i) for i in data]
		while True:
			size=len(hexstringdata)
			if size>=16:
				data=hexstringdata[:16]
				print(data)
				hexstringdata=hexstringdata[16:]
				if hexstringdata==[]:
					break
			else:
				data=hexstringdata
				print(data)
				break
		
class q25q64fw():
	def __init__(self,**kwargs):
		self.colorprinter=color_print.color_print()
		self.sn=kwargs.get('sn',None)
		self.binefiledata=[]
		self.port=AARDVARK_MASTER(sn=self.sn,porttype='SPI_GPIO',spibitrate=8000)
		self.port.target_power(True)
		delay_ms(500)
		if self.port.port!=-1:
			self.colorprinter.color_print('-----HW init succeed-----\n',color_print.FOREGROUND_DARKGREEN)
			if self.device_id():
				self.colorprinter.color_print('-----Find flash chip-----\n',color_print.FOREGROUND_DARKGREEN)
			else:
				self.colorprinter.color_print('-----No flash chip-----\n',color_print.FOREGROUND_DARKRED)
		else: 
			self.colorprinter.color_print('-----HW init fail-----\n',color_print.FOREGROUND_DARKRED)
	
	def readbinfile(self,filename):
		self.colorprinter.color_print('-----Read bin file-----\n',color_print.FOREGROUND_DARKGREEN)
		size=os.path.getsize(filename)
		with open(filename,"rb") as binfile:
			print(f'bin file size: {size} bytes')
			if size>page_size*max_page_count:
				print(f'bin file size over limit!!!')
				return None
			data=[]
			for i in range(size):
				data.append(binfile.read(1)[0])
		self.binefiledata=data
		return data	
	
	def device_id(self):
		while self.device_busy():
			delay_ms(1)
		if self.port.spireadreg([device_id],5)[5]==22:
			return True
		else:
			return False

	def write_en(self):
		while self.device_busy():
			delay_ms(1)
		self.port.spireadreg([write_en],0)
		
	def read_data(self,addr,length):
		while self.device_busy():
			delay_ms(1)
		data=self.port.spireadreg([read_data,addr>>16,(addr&0xff00)>>8,addr&0x00FF],length)
		return data[4:]	
		
	def chip_read(self,addr,length):
		data=[]
		while self.device_busy():
			delay_ms(1)
		if length<=max_read_byte:
			data=data.extend(self.read_data(addr,length))
		else:
			read_count=int(length/max_read_byte)
			remain_count=length%max_read_byte
			for i in range(read_count):
				data.extend(self.read_data(addr,max_read_byte))
				addr=addr+max_read_byte
			if remain_count>0:
				data.extend(self.read_data(addr,remain_count))
			return data

	def chip_readbin(self,length):
		self.colorprinter.color_print('-----Create bin file start-----\n',color_print.FOREGROUND_DARKGREEN)
		start_ticks = time.time()
		data=self.chip_read(0x00,length)
		filename=time.strftime("%Y%m%d_%H%M%S", time.localtime())+'.bin'
		with open(filename, 'wb+') as binfile:
			binfile.write(bytearray(data))
		end_ticks = time.time()
		print('Create bin file done: '+str(float('%.2f'%(end_ticks-start_ticks)))+'s')

	def chip_verify(self,addr):
		if self.binefiledata:
			self.colorprinter.color_print('-----Chip verification start-----\n',color_print.FOREGROUND_DARKGREEN)
			start_ticks = time.time()
			data=self.chip_read(addr,len(self.binefiledata))
			if data==self.binefiledata:
				self.colorprinter.color_print('-----Chip verification suceed-----\n',color_print.FOREGROUND_DARKGREEN)
			else:
				self.colorprinter.color_print('-----Chip verification fail-----\n',color_print.FOREGROUND_DARKRED)
			end_ticks = time.time()
			print('chip verification time: '+str(float('%.2f'%(end_ticks-start_ticks)))+'s')
		else:
			self.colorprinter.color_print('-----No reference bin file-----\n',color_print.FOREGROUND_DARKRED)

	def page_program(self,addr,data):
		while self.device_busy():
			delay_ms(1)
		self.write_en()	
		command_data=[page_program,addr>>16,(addr&0xff00)>>8,addr&0x00FF]
		command_data.extend(data)
		self.port.spireadreg(command_data,0)
		while self.device_busy():
			delay_ms(1)
				
	def chip_program(self,addr,data):
		self.colorprinter.color_print('-----Chip programming start-----\n',color_print.FOREGROUND_DARKGREEN)
		start_ticks = time.time()
		datasize=len(data)
		firstpagefree=page_size-addr%page_size
		if datasize<=firstpagefree:
			head=datasize
			page=0
			tail=0
		else:
			head=firstpagefree
			page=int((datasize-firstpagefree)/page_size)
			tail=(datasize-firstpagefree)%page_size
		
		#print(f'head:{head} page:{page} tail:{tail}')
		if head!=0:
			self.block64k_erase(addr)
			pagedata=data[:head]
			self.page_program(addr,pagedata)
			data=data[head:]
			addr=addr+head
		if page!=0:
			for i in range(page):
				if addr%erase_unit_size==0:
					self.block64k_erase(addr)
				pagedata=data[:page_size]
				self.page_program(addr,pagedata)
				data=data[page_size:]
				addr=addr+page_size
		if tail!=0:
			if addr%erase_unit_size==0:
				self.page_program(addr,pagedata)
			pagedata=data[:tail]
			self.page_program(addr,pagedata)
		end_ticks = time.time()
		print('chip program done: '+str(float('%.2f'%(end_ticks-start_ticks)))+'s')
				
	def chip_erase(self):
		self.colorprinter.color_print('-----Chip erase start-----\n',color_print.FOREGROUND_DARKGREEN)
		start_ticks = time.time()
		while self.device_busy():
			delay_ms(1)
		self.write_en()
		self.port.spireadreg([chip_erase],0)
		while self.device_busy():
			delay_ms(1)
		end_ticks = time.time()
		print('chip erase done: '+str(float('%.2f'%(end_ticks-start_ticks)))+'s')

	def block64k_erase(self,addr):
		while self.device_busy():
			delay_ms(1)
		self.write_en()
		return len(self.port.spireadreg([block64k_erase,addr>>16,(addr&0xff00)>>8,addr&0x00FF],0))
				
	def sector_erase(self,addr):
		while self.device_busy():
			delay_ms(1)
		self.write_en()
		return len(self.port.spireadreg([sector_erase,addr>>16,(addr&0xff00)>>8,addr&0x00FF],0))

	def device_busy(self):
		if self.port.spireadreg([read_status],1)[1] & 0x01==0x01:
			return True
		else:
			return False	
						
	def cleanup(self):
		self.colorprinter.color_print('-----HW tear down-----\n',color_print.FOREGROUND_DARKGREEN)
		if self.port:
			self.port.close()
			if self.sn:
				self.port=AARDVARK_MASTER(sn=self.sn,type='GPIO')
				self.port.target_power(False)
				self.port.close()
				
def main():
	parser = argparse.ArgumentParser(description='flash chip program')
	parser.add_argument('--file', type=str, default ='test.bin')
	parser.add_argument('--addr', type=int, default = 0x00)
	parser.add_argument('--erase', type=bool, default=False)
	parser.add_argument('--verify', type=bool, default=False)
	parser.add_argument('--program', type=bool, default=False)
	parser.add_argument('--readbinlen', type=int, default=max_page_count*page_size)
	parser.add_argument('--readbin', type=bool, default=False)
	parser.add_argument('--sn', type=int, default=None)
	args = parser.parse_args()
	
	dut=q25q64fw(sn=args.sn,spibitrate=8000)
	if dut.port.port!=-1:	
		if args.readbin:
			dut.chip_readbin(args.readbinlen)
		if args.erase:
			dut.chip_erase()
		if args.program or args.verify:
			binfile=args.file
			if os.path.exists(binfile):
				if args.verify or args.program:
					data=dut.readbinfile(binfile)
				if args.program:
					dut.chip_program(args.addr,data)
				if args.verify:
					dut.chip_verify(args.addr)
			else:
				print('Bin file not found!!!')
		dut.cleanup()	
		
if __name__ == "__main__":
	main()
