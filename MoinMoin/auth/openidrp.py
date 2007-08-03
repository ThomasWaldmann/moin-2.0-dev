# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - OpenID authorization

    @copyright: 2007 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.util.moinoid import MoinOpenIDStore
from MoinMoin import user
from MoinMoin.auth import BaseAuth
from openid.consumer import consumer
from openid.yadis.discover import DiscoveryFailure
from openid.fetchers import HTTPFetchingError
from MoinMoin import wikiutil
from MoinMoin.widget import html
from MoinMoin.auth import CancelLogin, ContinueLogin
from MoinMoin.auth import MultistageFormLogin, MultistageRedirectLogin
from MoinMoin.auth import get_multistage_continuation_url

class OpenIDAuth(BaseAuth):
    login_inputs = ['openid_identifier']
    name = 'openid'
    logout_possible = True

    def _get_account_name(self, request, form, msg=None):
        # now we need to ask the user for a new username
        # that they want to use on this wiki
        # XXX: request nickname from OP and suggest using it
        # (if it isn't in use yet)
        _ = request.getText
        form.append(html.INPUT(type='hidden', name='oidstage', value='2'))
        table = html.TABLE(border='0')
        form.append(table)
        td = html.TD(colspan=2)
        td.append(html.Raw(_("""Please choose an account name now.
If you choose an existing account name you will be asked for the
password and be able to associate the account with your OpenID.""")))
        table.append(html.TR().append(td))
        if msg:
            td = html.TD(colspan='2')
            td.append(html.P().append(html.STRONG().append(html.Raw(msg))))
            table.append(html.TR().append(td))
        td1 = html.TD()
        td1.append(html.STRONG().append(html.Raw(_('Name'))))
        td2 = html.TD()
        td2.append(html.INPUT(type='text', name='username'))
        table.append(html.TR().append(td1).append(td2))
        td1 = html.TD()
        td2 = html.TD()
        td2.append(html.INPUT(type='submit', name='submit',
                              value=_('Choose this name')))
        table.append(html.TR().append(td1).append(td2))

    def _associate_account(self, request, form, accountname, msg=None):
        _ = request.getText

        form.append(html.INPUT(type='hidden', name='oidstage', value='3'))
        table = html.TABLE(border='0')
        form.append(table)
        td = html.TD(colspan=2)
        td.append(html.Raw(_("""The username you have chosen is already
taken. If it is your username, enter your password below to associate
the username with your OpenID. Otherwise, please choose a different
username and leave the password field blank.""")))
        table.append(html.TR().append(td))
        if msg:
            td.append(html.P().append(html.STRONG().append(html.Raw(msg))))
        td1 = html.TD()
        td1.append(html.STRONG().append(html.Raw(_('Name'))))
        td2 = html.TD()
        td2.append(html.INPUT(type='text', name='username', value=accountname))
        table.append(html.TR().append(td1).append(td2))
        td1 = html.TD()
        td1.append(html.STRONG().append(html.Raw(_('Password'))))
        td2 = html.TD()
        td2.append(html.INPUT(type='password', name='password'))
        table.append(html.TR().append(td1).append(td2))
        td1 = html.TD()
        td2 = html.TD()
        td2.append(html.INPUT(type='submit', name='submit',
                              value=_('Associate this name')))
        table.append(html.TR().append(td1).append(td2))

    def _handle_verify_continuation(self, request):
        _ = request.getText
        oidconsumer = consumer.Consumer(request.session,
                                        MoinOpenIDStore(request))
        query = {}
        for key in request.form:
            query[key] = request.form[key][0]
        return_to = get_multistage_continuation_url(request, self.name,
                                                    {'oidstage': '1'})
        info = oidconsumer.complete(query, return_to=return_to)
        if info.status == consumer.FAILURE:
            return CancelLogin(_('OpenID error: %s.') % info.message)
        elif info.status == consumer.CANCEL:
            return CancelLogin(_('Verification canceled.'))
        elif info.status == consumer.SUCCESS:
            # try to find user object
            uid = user.getUserIdByOpenId(request, info.identity_url)
            if uid:
                u = user.User(request, id=uid, auth_method=self.name,
                              auth_username=info.identity_url)
                return ContinueLogin(u)
            # if no user found, then we need to ask for a username,
            # possibly associating an existing account.
            request.session['openid.id'] = info.identity_url
            return MultistageFormLogin(self._get_account_name)
        else:
            return CancelLogin(_('OpenID failure.'))

    def _handle_name_continuation(self, request):
        if not 'openid.id' in request.session:
            return CancelLogin(None)

        _ = request.getText
        newname = request.form.get('username', [''])[0]
        if not newname:
            return MultistageFormLogin(self._get_account_name)
        if not user.isValidName(request, newname):
            return MultistageFormLogin(self._get_account_name,
                    _('This is not a valid username, choose a different one.'))
        uid = None
        if newname:
            uid = user.getUserId(request, newname)
        if not uid:
            # we can create a new user with this name :)
            u = user.User(request, id=uid, auth_method=self.name,
                          auth_username=request.session['openid.id'])
            u.name = newname
            u.openids = [request.session['openid.id']]
            u.aliasname = request.session['openid.id']
            del request.session['openid.id']
            u.save()
            return ContinueLogin(u)
        # requested username already exists. if they know the password,
        # they can associate that account with the openid.
        assoc = lambda req, form: self._associate_account(req, form, newname)
        return MultistageFormLogin(assoc)

    def _handle_associate_continuation(self, request):
        if not 'openid.id' in request.session:
            return CancelLogin()

        _ = request.getText
        username = request.form.get('username', [''])[0]
        password = request.form.get('password', [''])[0]
        if not password:
            return self._handle_name_continuation(request)
        u = user.User(request, name=username, password=password,
                      auth_method=self.name,
                      auth_username=request.session['openid.id'])
        if u.valid:
            if not hasattr(u, 'openids'):
                u.openids = []
            u.openids.append(request.session['openid.id'])
            if not u.aliasname:
                u.aliasname = request.session['openid.id']
            u.save()
            del request.session['openid.id']
            return ContinueLogin(u, _('Your account is now associated to your OpenID.'))
        else:
            msg = _('The password you entered is not valid.')
            assoc = lambda req, form: self._associate_account(req, form, username, msg=msg)
            return MultistageFormLogin(assoc)

    def _handle_continuation(self, request):
        oidstage = request.form.get('oidstage', [0])[0]
        if oidstage == '1':
            return self._handle_verify_continuation(request)
        elif oidstage == '2':
            return self._handle_name_continuation(request)
        elif oidstage == '3':
            return self._handle_associate_continuation(request)
        return CancelLogin()

    def _openid_form(self, request, form, oidhtml):
        _ = request.getText
        txt = _('OpenID verification requires that you click this button:')
        # create JS to automatically submit the form if possible
        submitjs = """<script type="text/javascript">
<!--//
document.getElementById("openid_message").submit();
//-->
</script>
"""
        return ''.join([txt, oidhtml, submitjs])

    def login(self, request, user_obj, **kw):
        continuation = kw.get('multistage')

        if continuation:
            return self._handle_continuation(request)

        # openid is designed to work together with other auths
        if user_obj and user_obj.valid:
            return ContinueLogin(user_obj)

        openid_id = kw.get('openid_identifier')
        # nothing entered? continue...
        if not openid_id:
            return ContinueLogin(user_obj)

        _ = request.getText

        # user entered something but the session can't be stored
        if not request.session.is_stored:
            return ContinueLogin(user_obj,
                                 _('Anonymous sessions need to be enabled for OpenID login.'))

        oidconsumer = consumer.Consumer(request.session,
                                        MoinOpenIDStore(request))

        try:
            oidreq = oidconsumer.begin(openid_id)
        except HTTPFetchingError:
            return ContinueLogin(None, _('Failed to resolve OpenID.'))
        except DiscoveryFailure:
            return ContinueLogin(None, _('OpenID discovery failure, not a valid OpenID.'))
        else:
            if oidreq is None:
                return ContinueLogin(None, _('No OpenID.'))

            return_to = get_multistage_continuation_url(request, self.name,
                                                        {'oidstage': '1'})
            trust_root = request.getBaseURL()
            if oidreq.shouldSendRedirect():
                redirect_url = oidreq.redirectURL(trust_root, return_to)
                return MultistageRedirectLogin(redirect_url)
            else:
                form_html = oidreq.formMarkup(trust_root, return_to,
                    form_tag_attrs={'id': 'openid_message'})
                mcall = lambda request, form:\
                    self._openid_form(request, form, form_html)
                ret = MultistageFormLogin(mcall)
                return ret

    def login_hint(self, request):
        _ = request.getText
        return _("If you do not have an account yet, you can still log in "
                 "with your OpenID and create one during login.")