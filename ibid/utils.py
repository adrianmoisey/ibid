from htmlentitydefs import name2codepoint
import os
import os.path
import re
import time
import urllib2

import ibid

def ago(delta, units=None):
	parts = []

	for unit, value in (('year', delta.days/365), ('month', delta.days/30 % 12), ('day', delta.days % 30), ('hour', delta.seconds/3600), ('minute', delta.seconds/60 % 60), ('second', delta.seconds % 60), ('millisecond', delta.microseconds/1000)):
		if value > 0 and (unit != 'millisecond' or len(parts) == 0):
			parts.append('%s %s%s' % (value, unit, value != 1 and 's' or ''))
			if units and len(parts) >= units:
				break

	formatted =  ' and '.join(parts)
	return formatted.replace(' and ', ', ', len(parts)-2)

def substitute_entity(match):
    ent = match.group(2)
    if match.group(1) == "#":
        return unichr(int(ent))
    else:
        cp = name2codepoint.get(ent)

        if cp:
            return unichr(cp)
        else:
            return match.group()

def decode_htmlentities(string):
    entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")
    return entity_re.subn(substitute_entity, string)[0]

def cacheable_download(url, cachefile):
	"""Download url to cachefile if it's modified since cachefile.
	Specify cachefile in the form pluginname/cachefile.
	Returns complete path to downloaded file."""

	# We do allow absolute paths, for people who know what they are doing,
	# but the common use case should be pluginname/cachefile.
	if cachefile[0] not in (os.sep, os.altsep):
		cachedir = ibid.config.plugins['cachedir']
		if not cachedir:
			raise ibid.ConfigException("No cache directory specified")

		cachedir = os.path.join(cachedir, os.path.dirname(cachefile))
		if not os.path.isdir(cachedir):
			os.makedirs(cachedir)
	
		cachefile = os.path.join(cachedir, os.path.basename(cachefile))

	exists = os.path.isfile(cachefile)

	req = urllib2.Request(url)

	if exists:
		modified = os.path.getmtime(cachefile)
		modified = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(modified))
		req.add_header("If-Modified-Since", modified)

	try:
		connection = urllib2.urlopen(req)
	except urllib2.HTTPError, e:
		if e.code == 304 and exists:
			return cachefile
		else:
			raise
	
	# Download into a temporary file, in case something goes wrong
	downloadfile = os.path.join(os.path.dirname(cachefile), ".download." + os.path.basename(cachefile))
	outfile = file(downloadfile, "wb")
	buf = "x"
	while len(buf) > 0:
		buf = connection.read(1024)
		outfile.write(buf)
	
	outfile.close()

	try:
		os.path.rename(downloadfile, cachefile)
	except OSError:
		# Are we on a system that doesn't support atomic renames?
		os.path.remove(cachefile)
		os.path.rename(downloadfile, cachefile)
	
	return cachefile

def file_in_path(program):
	path = os.environ.get("PATH", os.defpath).split(os.pathsep)
	path = [os.path.join(dir, program) for dir in path]
	path = [True for file in path if os.path.isfile(file)]
	return bool(path)

def unicode_output(output, errors="strict"):
	try:
		encoding = os.getenv("LANG").split(".")[1]
	except:
		encoding = "ascii"
	return unicode(output, encoding, errors)
