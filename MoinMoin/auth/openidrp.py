from openid.store.memstore import MemoryStore
from openid.consumer import consumer

from flask import session, request, url_for
from MoinMoin.auth import BaseAuth, get_multistage_continuation_url
from MoinMoin.auth import ContinueLogin, CancelLogin, MultistageFormLogin, MultistageRedirectLogin
from MoinMoin import _, N_

# TODO
# add logging
# add docstrings

class OpenIDAuth(BaseAuth):
    def __init__(self):
        # the name
        self.name = 'openid'
        # we only need openid
        self.login_inputs = ['openid']
        # logout is possible
        self.logout_possible = True
        BaseAuth.__init__(self)

    def _handleContinuationVerify(self):
        # the consumer object with the storage in the memory
        oid_consumer = consumer.Consumer(session, MemoryStore())

        # a dict containing the parsed query string
        query = {}
        for key in request.values.keys():
            query[key] = request.values.get(key)
        # the current url(w/o query string)
        url = request.base_url

        # we get the info about the authentification
        oid_info = oid_consumer.complete(querry, url)
        # the identity we've retrieved from the response

        if oid_info.status == consumer.FAILURE:
            # verification has failed
            # return an error message with description of error
            error_message = _('OpenIDErorr: %(error)s') % {'error': oid_info.message}
            return CancelLogin(error_message)
        elif oid_info.status == consumer.CANCEL:
            # verification was canceled
            # return error
            return CancelLogin(_('OpenID verification canceled.'))
        elif oid_info.status == consumer.SUCCESS:
            # we have successfully authenticated our openid
            # we get the uid of the user with this openid associated to him
            user_id = user.get_by_openid(oid_info.identity_url)

            # if the user actually exists
            if user_id:
                # we get the authenticated user object
                new_user = user.User(uid=user_id, auth_method=self.name)
                # success!
                return ContinueLogin(new_user)
            # there is no user with this openid
            else:
                # show an appropriate message
                return ContinueLogin(None, _('There is no user with this OpenID.'))
        else:
            # the auth failed miserably
            return CancelLogin(_('OpenID failure.'))

    def _handleContinuation(self):
        # the current stage
        oidstage = request.values.get('oidstage')
        if oidstage == '1':
            return self._handleContinuationVerify()
        # more can be added for extended functionality

    def login(self, userobj, **kw):
        import pdb
        pdb.set_trace()
        continuation = kw.get('multistage')
        # process another subsequent step
        if continuation:
            return self._handleContinuation()

        openid = kw.get('openid')
        # no openid entered
        if not openid:
            return ContinueLogin(userobj)

        # we make a consumer object with a store
        # the store uses the memory
        oid_consumer = consumer.Consumer(session, MemoryStore())

        # we catch any possible openid-related exceptions
        try:
            oid_response = oid_consumer.begin(openid)
        except HTTPFetchingError:
            return ContinueLogin(None, _('Failed to resolve OpenID.'))
        except DiscoveryFailure:
            return ContinueLogin(None, _('OpenID discovery failure, not a valid OpenID.'))
        # raise unhandled exceptions
        except:
            raise
        else:
            # we got no response from the service
            if oid_response is None:
                return ContinueLogin(None, _('No OpenID service at this URL.'))

            # site root and where to return after the redirect
            site_root = url_for('frontend.show_root', _external=True)
            return_to = get_multistage_continuation_url(self.name, {'oidstage': '1'})

            # should we redirect the user?
            if oid_response.shouldSendRedirect():
                redirect_url = oid_response.redirectURL(site_root, return_to)
                return MultistageRedirectLogin(redirect_url)
            # send a form
            else:
                form_html = oid_response.formMarkup(site_root, return_to, form_tag_attrs={'id': 'openid_message'})
                # create a callable multistage object
                # XXX
                form_function = lambda form: form_html
                # returns a MultistageFormLogin
                return MultistageFormLogin(form_function)

