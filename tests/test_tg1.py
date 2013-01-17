import wsme.tg11
from wsme import WSRoot
from wsme.tg11 import wsexpose, wsvalidate
import wsme.tg1

from turbogears.controllers import RootController

import unittest

import simplejson


from wsmeext.soap.tests import test_soap


class WSController(WSRoot):
    pass


class Subcontroller(object):
    @wsexpose(int, int, int)
    def add(self, a, b):
        return a + b


class Root(RootController):
    class UselessSubClass:
        # This class is here only to make sure wsme.tg1.scan_api
        # does its job properly
        pass

    ws = WSController(webpath='/ws')
    ws.addprotocol(
        'soap',
        tns=test_soap.tns,
        typenamespace=test_soap.typenamespace,
        baseURL='/ws/'
    )
    ws = wsme.tg11.adapt(ws)

    @wsexpose(int)
    @wsvalidate(int, int)
    def multiply(self, a, b):
        return a * b

    sub = Subcontroller()

import cherrypy

from turbogears import testutil, config, startup


class TestController(unittest.TestCase):
    root = Root

    def setUp(self):
        "Tests the output of the index method"
        self.app = testutil.make_app(self.root)
        testutil.start_server()

    def tearDown(self):
        # implementation copied from turbogears.testutil.stop_server.
        # The only change is that cherrypy.root is set to None
        # AFTER stopTurbogears has been called so that wsme.tg11
        # can correctly uninstall its filter.
        if config.get("cp_started"):
            cherrypy.server.stop()
            config.update({"cp_started": False})

        if config.get("server_started"):
            startup.stopTurboGears()
            config.update({"server_started": False})

    def test_restcall(self):
        response = self.app.post("/multiply",
            simplejson.dumps({'a': 5, 'b': 10}),
            {'Content-Type': 'application/json'}
        )
        print response
        assert simplejson.loads(response.body) == 50

        response = self.app.post("/sub/add",
            simplejson.dumps({'a': 5, 'b': 10}),
            {'Content-Type': 'application/json'}
        )
        print response
        assert simplejson.loads(response.body) == 15

        response = self.app.post("/multiply",
            simplejson.dumps({'a': 5, 'b': 10}),
            {'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        print response
        assert simplejson.loads(response.body) == 50

        response = self.app.post("/multiply",
            simplejson.dumps({'a': 5, 'b': 10}),
            {'Content-Type': 'application/json', 'Accept': 'text/javascript'}
        )
        print response
        assert simplejson.loads(response.body) == 50

        response = self.app.post("/multiply",
            simplejson.dumps({'a': 5, 'b': 10}),
            {'Content-Type': 'application/json',
             'Accept': 'text/xml'}
        )
        print response
        assert response.body == "<result>50</result>"

    def test_soap_wsdl(self):
        ts = test_soap.TestSOAP('test_wsdl')
        ts.app = self.app
        ts.ws_path = '/ws/'
        ts.run()
        #wsdl = self.app.get('/ws/api.wsdl').body
        #print wsdl
        #assert 'multiply' in wsdl

    def test_soap_call(self):
        ts = test_soap.TestSOAP('test_wsdl')
        ts.app = self.app
        ts.ws_path = '/ws/'

        print ts.ws_path
        assert ts.call('multiply', a=5, b=10, _rt=int) == 50

    def test_scan_api_loops(self):
        class MyRoot(object):
            pass

        MyRoot.loop = MyRoot()

        root = MyRoot()

        api = list(wsme.tg1._scan_api(root))
        print(api)

        self.assertEquals(len(api), 0)

    def test_scan_api_maxlen(self):
        class ARoot(object):
            pass

        def make_subcontrollers(n):
            c = type('Controller%s' % n, (object,), {})
            return c

        c = ARoot
        for n in xrange(55):
            subc = make_subcontrollers(n)
            c.sub = subc()
            c = subc
        root = ARoot()
        self.assertRaises(ValueError, list, wsme.tg1._scan_api(root))

    def test_templates_content_type(self):
        self.assertEquals(
            "application/json",
            wsme.tg1.AutoJSONTemplate().get_content_type('dummy')
        )
        self.assertEquals(
            "text/xml",
            wsme.tg1.AutoXMLTemplate().get_content_type('dummy')
        )
