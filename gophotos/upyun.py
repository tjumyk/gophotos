import base64
import hashlib
import hmac
import json
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time

import requests


class UPYunError(Exception):
    def __init__(self, msg=None):
        super(UPYunError, self).__init__(msg)


class UPYun:
    API_ENTRY = 'https://v0.api.upyun.com'

    def __init__(self, bucket_id, operator, password):
        self.bucket_id = bucket_id
        self.operator = operator
        self._password_md5 = hashlib.new('md5', password.encode()).hexdigest()

    def _build_authorization_code(self, method, uri, date, md5=None):
        if md5 is None:
            msg = "%s&%s&%s" % (method, uri, date)
        else:
            msg = "%s&%s&%s&%s" % (method, uri, date, md5)
        signature = base64.b64encode(
            hmac.new(self._password_md5.encode(), msg.encode(), hashlib.sha1).digest()).decode()
        return "UPYUN %s:%s" % (self.operator, signature)

    def _get_time_rfc1123(self):
        return format_date_time(mktime(datetime.now().timetuple()))

    def upload_file_content(self, path, content, content_type):
        uri = '/%s/%s' % (self.bucket_id, path)
        date = self._get_time_rfc1123()
        md5 = hashlib.new('md5', content).hexdigest()
        auth = self._build_authorization_code('PUT', uri, date, md5)
        headers = {
            'Authorization': auth,
            'Date': date,
            'Content-Length': str(len(content)),
            'Content-MD5': md5,
            'Content-Type': content_type
        }
        r = requests.put(UPYun.API_ENTRY + uri, data=content, headers=headers)
        if r.status_code != 200:
            raise UPYunError("[Upload File Failed (%s)]: %s" % (path, r.text))

    def list_files(self, folder_path):
        uri = '/%s/%s' % (self.bucket_id, folder_path)
        date = self._get_time_rfc1123()
        auth = self._build_authorization_code('GET', uri, date)
        headers = {
            'Date': date,
            'Authorization': auth
        }
        r = requests.get(UPYun.API_ENTRY + uri, headers=headers)
        if r.status_code != 200:
            raise UPYunError("[List Files Failed]: %s" % r.text)
        results = []
        if len(r.text) > 0:
            for line in r.text.split('\n'):
                name, f_type, size, mtime = line.split('\t')
                results.append({
                    'name': name,
                    'type': f_type,
                    'size': int(size),
                    'mtime': int(mtime)
                })
        return results

    def remove_file(self, path, async_mode=True):
        uri = '/%s/%s' % (self.bucket_id, path)
        date = self._get_time_rfc1123()
        auth = self._build_authorization_code('DELETE', uri, date)
        headers = {
            'Authorization': auth,
            'Date': date
        }
        if async_mode:
            headers['x-upyun-async'] = 'true'
        r = requests.delete(UPYun.API_ENTRY + uri, headers=headers)
        if r.status_code != 200:
            raise UPYunError("[Delete File/Folder Failed (%s)]: %s" % (path, r.text))

    def remove_folder(self, folder_path):
        self.remove_file(folder_path, False)

    def get_url(self, path):
        return 'http://%s.b0.upaiyun.com/%s' % (self.bucket_id, path)


if __name__ == '__main__':
    with open('../config.json') as f:
        config = json.load(f)
    uc = UPYun(**config['upyun'])
    dir_path = '6282281410266429761'
    files = uc.list_files(dir_path)
    print('Total files: %d' % len(files))
    for f in files:
        path = '%s/%s' % (dir_path, f['name'])
        uc.remove_file(path)
