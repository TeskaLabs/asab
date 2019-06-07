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

		# Read last object from a file
		p = self.LogFile.seek(0, os.SEEK_END)
		self.Term, self.Index, self.PrevEntry = self._read_prev_log_entry()

		self.print()


	def append(self, term, command):
		'''
		The serialized format of the log entry is follows:

		2 bytes (unsigned short) .. length of the command
		4 bytes (unsigned integer) .. term
		4 bytes (unsigned integer) .. index
		variable (bytes) .. command, encoded as UTF-8 JSON string
		2 bytes (unsigned short) .. length of the command (again, for reverse scrolling)
		'''
		cmd_ser = json.dumps(command)
		cmd_ser_len = len(cmd_ser)
		output = struct.pack('=HII', cmd_ser_len, term, self.Index+1) +\
			cmd_ser.encode('utf-8') +\
			struct.pack('=H', cmd_ser_len)

		self.LogFile.seek(0, os.SEEK_END)
		self.LogFile.write(output)
		self.LogFile.flush()

		self.Index += 1
		self.Term = term
		self.PrevEntry = command

		return self.Index


	def replicate(self, term, entries):
		for command in entries:
			self.append(term, command)


	def get_last(self):
		return self.Term, self.Index, self.PrevEntry


	def slice(self, index, count):
		assert(index >= 0)
		assert(count > 0)

		# Find first
		p = self.LogFile.seek(0, os.SEEK_END)
		while True:
			e_term, e_index, e_cmd = self._read_prev_log_entry()
			if index == e_index:
				if e_cmd is None:
					yield e_term, e_index, None
				else:
					yield e_term, e_index, json.loads(e_cmd)
					e_term, e_index, e_cmd = self._read_log_entry()
					assert(e_index == index)
				break

		for i in range(count-1):
			e_term, e_index, e_cmd = self._read_log_entry()
			yield e_term, e_index, json.loads(e_cmd) if e_cmd is not None else None


	def get(self, index):
		if index == 0:
			return 0, 0, None

		self.LogFile.seek(0, os.SEEK_END)
		while True:
			e_term, e_index, e_cmd = self._read_prev_log_entry()
			if e_index == 0:
				raise RuntimeError("Log entry {} not found".format(index))
			if e_index == index:
				return e_term, e_index, json.loads(e_cmd)

	def _read_log_entry(self):
		b = self.LogFile.read(10)
		if len(b) == 0: return 0, 0, None
		cmd_len, term, index = struct.unpack("=HII", b)
		cmd = self.LogFile.read(cmd_len)
		b = self.LogFile.read(2)
		assert(len(b) == 2)
		return term, index, cmd


	def _read_prev_log_entry(self):
		'''
		A read file pointer is just behind the log entry we want to read
		'''
		try:
			self.LogFile.seek(-2, os.SEEK_CUR)
		except:
			return 0, 0, None

		cmd_len, = struct.unpack("=H", self.LogFile.read(2))
		pos = self.LogFile.seek(-2-cmd_len-10, os.SEEK_CUR)
		term, index, cmd = self._read_log_entry()
		self.LogFile.seek(pos, os.SEEK_SET)
		return term, index, cmd


	def print(self):
		print("=========\nLog:")
		self.LogFile.seek(0, os.SEEK_SET)
		while True:
			term, index, cmd = self._read_log_entry()
			if index is 0: break
			print("  >>> i:{:02d} t:{:02d} c:{}".format(index, term, cmd))
