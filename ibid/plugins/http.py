"""Performs HTTP requests"""

from httplib2 import Http
import re

import ibid
from ibid.plugins import Processor, match

title = re.compile(r'<title>(.*)<\/title>', re.I+re.S)

class HTTP(Processor):
	"""Usage: (get|head) <url>"""

	@match('^\s*(get|head)\s+(.+)\s*$')
	def handler(self, event, action, url):
		http = Http()
		headers={}
		if action.lower() == 'get':
			headers['Range'] = 'bytes=0-500'
		response, content = http.request(url, action.upper(), headers=headers)
		reply = u'%s %s' % (response.status, response.reason)

		if action.lower() == 'get':
			match = title.search(content)
			if match:
				reply = u'%s "%s"' % (reply, match.groups()[0].strip())

		event.addresponse(reply)
		return event