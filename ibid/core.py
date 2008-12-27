from traceback import print_exc
import inspect

from twisted.internet import reactor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import ibid
import ibid.plugins
import ibid.auth_

class Dispatcher(object):

    def _process(self, event):
        for processor in ibid.processors:
            try:
                event = processor.process(event) or event
            except Exception:
                print_exc()

        print event

        for response in event['responses']:
            if response['source'] in ibid.sources:
                reactor.callFromThread(ibid.sources[response['source']].respond, response)
            else:
                print u'Invalid source %s' % response['source']

    def dispatch(self, event):
        reactor.callInThread(self._process, event)

class Reloader(object):

    def run(self):
        self.reload_dispatcher()
        self.load_sources()
        self.load_processors()
        reactor.run()

    def reload_dispatcher(self):
        try:
            reload(ibid.core)
            dispatcher = ibid.core.Dispatcher()
            ibid.dispatcher = dispatcher
            return True
        except Exception:
            print_exc()
            return False
        
    def load_source(self, name, service=None):
        type = ibid.config['sources'][name]['type']

        module = 'ibid.source.%s' % type
        factory = 'ibid.source.%s.SourceFactory' % type
        try:
            __import__(module)
            moduleclass = eval(factory)
        except:
            print_exc()
            return

        ibid.sources[name] = moduleclass(name)
        ibid.sources[name].setServiceParent(service)
        return True

    def load_sources(self, service=None):
        for source in ibid.config['sources'].keys():
            if 'disabled' not in ibid.config.sources[source]:
                self.load_source(source, service)

    def unload_source(self, name):
        if name not in ibid.sources:
            return False

        ibid.sources[name].protocol.loseConnection()
        del ibid.sources[name]

    def reload_source(self, name):
        if name not in ibid.config['sources']:
            return False

        self.unload_source(name)

        source = ibid.config['sources'][name]
        m=eval('ibid.source.%s' % source['type'])
        reload(m)

        self.load_source(source)

    def load_processors(self):
        for processor in ibid.config['load']:
            if not self.load_processor(processor):
                print "Couldn't load processor %s" % processor

    def load_processor(self, name):
        object = name
        if name in ibid.config.plugins and 'type' in ibid.config.plugins[name]:
            object = ibid.config['plugins'][name]['type']

        module = 'ibid.plugins.' + object.split('.')[0]
        classname = 'ibid.plugins.' + object
        try:
            __import__(module)
            m = eval(module)
            reload(m)
        except Exception:
            print_exc()
            return False

        try:
            if module == classname:
                for classname, klass in inspect.getmembers(m, inspect.isclass):
                    if issubclass(klass, ibid.plugins.Processor) and klass != ibid.plugins.Processor:
                        ibid.processors.append(klass(name))
            else:
                moduleclass = eval(classname)
                ibid.processors.append(moduleclass(name))
                
        except Exception:
            print_exc()
            return False

        ibid.processors.sort(key=lambda x: x.priority)

        return True

    def unload_processor(self, name):
        found = False
        for processor in ibid.processors:
            if processor.name == name:
                ibid.processors.remove(processor)
                found = True

        return found

    def reload_databases(self):
        reload(ibid.core)
        ibid.databases = DatabaseManager()
        return True

    def reload_auth(self):
        reload(ibid.auth_)
        ibid.auth = ibid.auth_.Auth()
        return True

class DatabaseManager(dict):

    def __init__(self):
        for database in ibid.config.databases.keys():
            self.load(database)

    def load(self, name):
        uri = ibid.config.databases[name]['uri']
        engine = create_engine(uri, echo=False)
        self[name] = scoped_session(sessionmaker(bind=engine))

    def __getattr__(self, name):
        return self[name]

# vi: set et sta sw=4 ts=4:
