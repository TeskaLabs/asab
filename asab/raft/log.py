import os
import itertools
import struct
import json
import logging

#

L = logging.getLogger(__name__)

#

class Log(object):


	def __init__(self, fname):

		# Create a log file if doesn't exists
		if not os.path.isfile(fname):
			f = open(fname, 'wb')
			f.close()
		self.LogFile = open(fname, 'r+b')

		# Read last index from a file
		self.Index = 0
		self.LogFile.seek(0, os.SEEK_END)
		index, _, _ = self._read_prev_log_entry()
		if index is not None:
			self.Index = index


	def add(self, term, command):
		'''
		The serialized format of the log entry is follows:

		2 bytes (unsigned short) .. length of the command
		4 bytes (unsigned integer) .. index
		4 bytes (unsigned integer) .. term
		variable (bytes) .. command, encoded as UTF-8 JSON string
		2 bytes (unsigned short) .. length of the command (again, for reverse scrolling)
		'''
		self.Index += 1
		cmd_ser = json.dumps(command)
		cmd_ser_len = len(cmd_ser)
		output = struct.pack('=HII', cmd_ser_len, self.Index, term) +\
			cmd_ser.encode('utf-8') +\
			struct.pack('=H', cmd_ser_len)

		self.LogFile.seek(0, os.SEEK_END)
		self.LogFile.write(output)

		return self.Index


	def replicate(self, term, prevLogTerm, prevLogIndex, entries):
		if self.Index != prevLogIndex:
			print("XXXXX {} != {}".format(self.Index, prevLogIndex))
		for command in entries:
			self.add(term, command)


	def get(self, index):
		self.LogFile.seek(0, os.SEEK_END)
		while True:
			e_index, _, e = self._read_prev_log_entry()
			if e_index is None:
				raise RuntimeError("Log entry {} not found".format(index))
			if e_index == index: break

		prevLogIndex, prevLogTerm, _ = self._read_prev_log_entry()
		if prevLogIndex is None: prevLogIndex = 0
		if prevLogTerm is None: prevLogTerm = 0

		assert(e is not None)

		e = json.loads(e)

		return prevLogTerm, prevLogIndex, e


	def _read_log_entry(self):
		b = self.LogFile.read(10)
		if len(b) == 0: return None, None, None
		cmd_len, index, term = struct.unpack("=HII", b)
		cmd = self.LogFile.read(cmd_len)
		self.LogFile.read(2)
		return index, term, cmd


	def _read_prev_log_entry(self):
		'''
		A read file pointer is just behind the log entry we want to read
		'''
		try:
			self.LogFile.seek(-2, os.SEEK_CUR)
		except:
			return None, None, None

		b = self.LogFile.read(2)
		cmd_len, = struct.unpack("=H", b)
		pos = self.LogFile.seek(-2-cmd_len-10, os.SEEK_CUR)
		index, term, cmd = self._read_log_entry()
		self.LogFile.seek(pos, os.SEEK_SET)
		return index, term, cmd



	def print(self):
		print("=========\nLog:")
		self.LogFile.seek(0, os.SEEK_SET)
		while True:
			index, term, cmd = self._read_log_entry()
			if index is None: break
			print("  >>> i:{:02d} t:{:02d} c:{}".format(index, term, cmd))
