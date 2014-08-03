# coding: utf-8
import requests
import xml.etree.ElementTree as ET


class CleanwebError(Exception):
    pass


class Cleanweb(object):
    """ Python wrapper for Clean Web project by Yandex

        http://api.yandex.ru/cleanweb
    """

    def __init__(self, key=None, fake_captcha=None):
        if not key:
            raise CleanwebError('Cleanweb needs API key to operate. Get it here: http://api.yandex.ru/cleanweb/form.xml')
        self.session = requests.Session()
        self.session.params['key'] = key
        self.fake_captcha = fake_captcha

    def request(self, *args, **kwargs):
        """ Error handling in requests
            http://api.yandex.ru/cleanweb/doc/dg/concepts/error-codes.xml
        """
        r = self.session.request(*args, **kwargs)
        if r.status_code != requests.codes.ok:
            try:
                error = ET.fromstring(r.content)
                message = error.findtext('message')
                code = error.attrib['key']
            except ET.ParseError:
                message = "Invalid response from server"
                code = r.status_code

            raise CleanwebError('%s (%s)' % (message, code))
        return r

    def check_spam(self, ip=None, email=None, name=None, login=None, realname=None,
                   subject=None, body=None, subject_type='plain', body_type='plain'):
        """ http://api.yandex.ru/cleanweb/doc/dg/concepts/check-spam.xml
            subject_type = plain|html|bbcode
            body_type = plain|html|bbcode
        """
        data = {'ip': ip, 'email': email, 'name': name, 'login': login, 'realname': realname,
                'body-%s' % body_type: body, 'subject-%s' % subject_type: subject}

        try:
            r = self.request('post', 'http://cleanweb-api.yandex.ru/1.0/check-spam', data=data)
        except (CleanwebError, requests.ConnectionError):
            # Try to return fake result to hide cleanweb errors
            return {
                'id': -1,
                'spam_flag': False,
                'links': []
            }

        root = ET.fromstring(r.content)

        return {
            'id': root.findtext('id'),
            'spam_flag': yesnobool(root.find('text').attrib['spam-flag']),
            'links': [(link.attrib['href'], yesnobool(link.attrib['spam-flag']))
                      for link in root.findall('./links/link')]
        }

    def get_captcha(self, id=None):
        """ http://api.yandex.ru/cleanweb/doc/dg/concepts/get-captcha.xml"""
        payload = {'id': id}

        try:
            r = self.request('get', 'http://cleanweb-api.yandex.ru/1.0/get-captcha', params=payload)
        except (CleanwebError, requests.ConnectionError):
            if not self.fake_captcha:
                raise KeyError("CleanWeb responed with error and we can't build fake query. "
                               "You should set fake captcha")

            return {
                'captcha': '308JR213_g_JSaE76RvWQ3R63cK4mc8N',
                'url': self.fake_captcha
            }

        return dict((item.tag, item.text) for item in ET.fromstring(r.content))

    def check_captcha(self, captcha, value, id=None):
        """ http://api.yandex.ru/cleanweb/doc/dg/concepts/check-captcha.xml"""
        payload = {'captcha': captcha,
                   'value': value,
                   'id': id}
        try:
            r = self.request('get', 'http://cleanweb-api.yandex.ru/1.0/check-captcha', params=payload)
        except (CleanwebError, requests.ConnectionError):
            return True

        root = ET.fromstring(r.content)
        if root.findall('ok'):
            return True
        if root.findall('failed'):
            return False

    def complain(self, id, is_spam):
        """ http://api.yandex.ru/cleanweb/doc/dg/concepts/complain.xml"""
        try:
            r = self.request('post', 'http://cleanweb-api.yandex.ru/1.0/complain',
                             data={'id': id, 'spamtype': 'spam' if is_spam else 'ham'})
        except (CleanwebError, requests.ConnectionError):
            pass

        return True


def yesnobool(string):
    if string == 'yes':
        return True
    if string == 'no':
        return False