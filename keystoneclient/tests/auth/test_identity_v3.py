# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy

import httpretty
from six.moves import urllib

from keystoneclient import access
from keystoneclient.auth.identity import v3
from keystoneclient import exceptions
from keystoneclient.openstack.common import jsonutils
from keystoneclient import session
from keystoneclient.tests import utils


class V3IdentityPlugin(utils.TestCase):

    TEST_ROOT_URL = 'http://127.0.0.1:5000/'
    TEST_URL = '%s%s' % (TEST_ROOT_URL, 'v3')
    TEST_ROOT_ADMIN_URL = 'http://127.0.0.1:35357/'
    TEST_ADMIN_URL = '%s%s' % (TEST_ROOT_ADMIN_URL, 'v3')

    TEST_PASS = 'password'

    TEST_SERVICE_CATALOG = [{
        "endpoints": [{
            "url": "http://cdn.admin-nets.local:8774/v1.0/",
            "region": "RegionOne",
            "interface": "public"
        }, {
            "url": "http://127.0.0.1:8774/v1.0",
            "region": "RegionOne",
            "interface": "internal"
        }, {
            "url": "http://cdn.admin-nets.local:8774/v1.0",
            "region": "RegionOne",
            "interface": "admin"
        }],
        "type": "nova_compat"
    }, {
        "endpoints": [{
            "url": "http://nova/novapi/public",
            "region": "RegionOne",
            "interface": "public"
        }, {
            "url": "http://nova/novapi/internal",
            "region": "RegionOne",
            "interface": "internal"
        }, {
            "url": "http://nova/novapi/admin",
            "region": "RegionOne",
            "interface": "admin"
        }],
        "type": "compute"
    }, {
        "endpoints": [{
            "url": "http://glance/glanceapi/public",
            "region": "RegionOne",
            "interface": "public"
        }, {
            "url": "http://glance/glanceapi/internal",
            "region": "RegionOne",
            "interface": "internal"
        }, {
            "url": "http://glance/glanceapi/admin",
            "region": "RegionOne",
            "interface": "admin"
        }],
        "type": "image",
        "name": "glance"
    }, {
        "endpoints": [{
            "url": "http://127.0.0.1:5000/v3",
            "region": "RegionOne",
            "interface": "public"
        }, {
            "url": "http://127.0.0.1:5000/v3",
            "region": "RegionOne",
            "interface": "internal"
        }, {
            "url": TEST_ADMIN_URL,
            "region": "RegionOne",
            "interface": "admin"
        }],
        "type": "identity"
    }, {
        "endpoints": [{
            "url": "http://swift/swiftapi/public",
            "region": "RegionOne",
            "interface": "public"
        }, {
            "url": "http://swift/swiftapi/internal",
            "region": "RegionOne",
            "interface": "internal"
        }, {
            "url": "http://swift/swiftapi/admin",
            "region": "RegionOne",
            "interface": "admin"
        }],
        "type": "object-store"
    }]

    def setUp(self):
        super(V3IdentityPlugin, self).setUp()
        self.TEST_RESPONSE_DICT = {
            "token": {
                "methods": [
                    "token",
                    "password"
                ],

                "expires_at": "2020-01-01T00:00:10.000123Z",
                "project": {
                    "domain": {
                        "id": self.TEST_DOMAIN_ID,
                        "name": self.TEST_DOMAIN_NAME
                    },
                    "id": self.TEST_TENANT_ID,
                    "name": self.TEST_TENANT_NAME
                },
                "user": {
                    "domain": {
                        "id": self.TEST_DOMAIN_ID,
                        "name": self.TEST_DOMAIN_NAME
                    },
                    "id": self.TEST_USER,
                    "name": self.TEST_USER
                },
                "issued_at": "2013-05-29T16:55:21.468960Z",
                "catalog": self.TEST_SERVICE_CATALOG
            },
        }

    def stub_auth(self, subject_token=None, **kwargs):
        if not subject_token:
            subject_token = self.TEST_TOKEN

        self.stub_url(httpretty.POST, ['auth', 'tokens'],
                      X_Subject_Token=subject_token, **kwargs)

    @httpretty.activate
    def test_authenticate_with_username_password(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        a = v3.Password(self.TEST_URL,
                        username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['password'],
                'password': {'user': {'name': self.TEST_USER,
                                      'password': self.TEST_PASS}}}}}

        self.assertRequestBodyIs(json=req)
        self.assertRequestHeaderEqual('Content-Type', 'application/json')
        self.assertRequestHeaderEqual('Accept', 'application/json')
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)

    @httpretty.activate
    def test_authenticate_with_username_password_domain_scoped(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS, domain_id=self.TEST_DOMAIN_ID)
        s = session.Session(a)
        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['password'],
                'password': {'user': {'name': self.TEST_USER,
                                      'password': self.TEST_PASS}}},
               'scope': {'domain': {'id': self.TEST_DOMAIN_ID}}}}
        self.assertRequestBodyIs(json=req)
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)

    @httpretty.activate
    def test_authenticate_with_username_password_project_scoped(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS,
                        project_id=self.TEST_DOMAIN_ID)
        s = session.Session(a)
        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['password'],
                'password': {'user': {'name': self.TEST_USER,
                                      'password': self.TEST_PASS}}},
               'scope': {'project': {'id': self.TEST_DOMAIN_ID}}}}
        self.assertRequestBodyIs(json=req)
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)
        self.assertEqual(s.auth.auth_ref.project_id, self.TEST_DOMAIN_ID)

    @httpretty.activate
    def test_authenticate_with_token(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        a = v3.Token(self.TEST_URL, self.TEST_TOKEN)
        s = session.Session(auth=a)
        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['token'],
                'token': {'id': self.TEST_TOKEN}}}}

        self.assertRequestBodyIs(json=req)

        self.assertRequestHeaderEqual('Content-Type', 'application/json')
        self.assertRequestHeaderEqual('Accept', 'application/json')
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)

    def test_missing_auth_params(self):
        self.assertRaises(exceptions.AuthorizationFailure, v3.Auth._factory,
                          self.TEST_URL)

    @httpretty.activate
    def test_with_expired(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)

        d = copy.deepcopy(self.TEST_RESPONSE_DICT)
        d['token']['expires_at'] = '2000-01-01T00:00:10.000123Z'

        a = v3.Password(self.TEST_URL, username='username',
                        password='password')
        a.auth_ref = access.AccessInfo.factory(body=d)
        s = session.Session(auth=a)

        s.get_token()

        self.assertEqual(a.auth_ref['expires_at'],
                         self.TEST_RESPONSE_DICT['token']['expires_at'])

    def test_with_domain_and_project_scoping(self):
        a = v3.Password(self.TEST_URL, username='username',
                        password='password', project_id='project',
                        domain_id='domain')
        self.assertRaises(exceptions.AuthorizationFailure,
                          a.get_token, None)

    @httpretty.activate
    def test_with_trust_id(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS, trust_id='trust')
        s = session.Session(a)
        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['password'],
                'password': {'user': {'name': self.TEST_USER,
                                      'password': self.TEST_PASS}}},
               'scope': {'OS-TRUST:trust': {'id': 'trust'}}}}
        self.assertRequestBodyIs(json=req)
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)

    @httpretty.activate
    def test_with_multiple_mechanisms_factory(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        p = v3.PasswordMethod(username=self.TEST_USER, password=self.TEST_PASS)
        t = v3.TokenMethod(token='foo')
        a = v3.Auth(self.TEST_URL, [p, t], trust_id='trust')
        s = session.Session(a)
        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['password', 'token'],
                'password': {'user': {'name': self.TEST_USER,
                                      'password': self.TEST_PASS}},
                'token': {'id': 'foo'}},
               'scope': {'OS-TRUST:trust': {'id': 'trust'}}}}
        self.assertRequestBodyIs(json=req)
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)

    @httpretty.activate
    def test_with_multiple_mechanisms(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        p = v3.PasswordMethod(username=self.TEST_USER,
                              password=self.TEST_PASS)
        t = v3.TokenMethod(token='foo')
        a = v3.Auth(self.TEST_URL, [p, t], trust_id='trust')
        s = session.Session(auth=a)

        s.get_token()

        req = {'auth': {'identity':
               {'methods': ['password', 'token'],
                'password': {'user': {'name': self.TEST_USER,
                                      'password': self.TEST_PASS}},
                'token': {'id': 'foo'}},
               'scope': {'OS-TRUST:trust': {'id': 'trust'}}}}
        self.assertRequestBodyIs(json=req)
        self.assertEqual(s.auth.auth_ref.auth_token, self.TEST_TOKEN)

    def test_with_multiple_scopes(self):
        s = session.Session()

        a = v3.Password(self.TEST_URL,
                        username=self.TEST_USER, password=self.TEST_PASS,
                        domain_id='x', project_id='x')
        self.assertRaises(exceptions.AuthorizationFailure, a.get_auth_ref, s)

        a = v3.Password(self.TEST_URL,
                        username=self.TEST_USER, password=self.TEST_PASS,
                        domain_id='x', trust_id='x')
        self.assertRaises(exceptions.AuthorizationFailure, a.get_auth_ref, s)

    @httpretty.activate
    def _do_service_url_test(self, base_url, endpoint_filter):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        self.stub_url(httpretty.GET, ['path'],
                      base_url=base_url,
                      body='SUCCESS', status=200)

        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        resp = s.get('/path', endpoint_filter=endpoint_filter)

        self.assertEqual(resp.status_code, 200)
        path = "%s/%s" % (urllib.parse.urlparse(base_url).path, 'path')
        self.assertEqual(httpretty.last_request().path, path)

    def test_service_url(self):
        endpoint_filter = {'service_type': 'compute', 'interface': 'admin'}
        self._do_service_url_test('http://nova/novapi/admin', endpoint_filter)

    def test_service_url_defaults_to_public(self):
        endpoint_filter = {'service_type': 'compute'}
        self._do_service_url_test('http://nova/novapi/public', endpoint_filter)

    @httpretty.activate
    def test_endpoint_filter_without_service_type_fails(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)

        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        self.assertRaises(exceptions.EndpointNotFound, s.get, '/path',
                          endpoint_filter={'interface': 'admin'})

    @httpretty.activate
    def test_full_url_overrides_endpoint_filter(self):
        self.stub_auth(json=self.TEST_RESPONSE_DICT)
        self.stub_url(httpretty.GET, [],
                      base_url='http://testurl/',
                      body='SUCCESS', status=200)

        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        resp = s.get('http://testurl/',
                     endpoint_filter={'service_type': 'compute'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, 'SUCCESS')

    @httpretty.activate
    def test_invalid_auth_response_dict(self):
        self.stub_auth(json={'hello': 'world'})

        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        self.assertRaises(exceptions.InvalidResponse, s.get, 'http://any',
                          authenticated=True)

    @httpretty.activate
    def test_invalid_auth_response_type(self):
        self.stub_url(httpretty.POST, ['auth', 'tokens'], body='testdata')

        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        self.assertRaises(exceptions.InvalidResponse, s.get, 'http://any',
                          authenticated=True)

    @httpretty.activate
    def test_invalidate_response(self):
        body = jsonutils.dumps(self.TEST_RESPONSE_DICT)
        auth_responses = [httpretty.Response(body=body,
                                             X_Subject_Token='token1',
                                             status=200),
                          httpretty.Response(body=body,
                                             X_Subject_Token='token2',
                                             status=200)]

        httpretty.register_uri(httpretty.POST,
                               '%s/auth/tokens' % self.TEST_URL,
                               responses=auth_responses)

        a = v3.Password(self.TEST_URL, username=self.TEST_USER,
                        password=self.TEST_PASS)
        s = session.Session(auth=a)

        self.assertEqual('token1', s.get_token())
        a.invalidate()
        self.assertEqual('token2', s.get_token())
