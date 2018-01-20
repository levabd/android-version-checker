# -*- coding: utf-8 -*-

import sys
import logging.handlers
import os
import re
# noinspection PyUnresolvedReferences
import apiclient
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
from flask_restful import Resource, Api, abort
from flask_cache import Cache

app = Flask(__name__)
api = Api(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


class GetAppVersion(Resource):

    credentials = None
    package_name = ''
    package_name_undefined = ("The package name undefined. Example:" 
                              "com.android.sample")
    cache_empty = ("Cache for {0} is empty or expired. Try to get version"
                   " from Google. Loading key file")
    cant_load_credentials = ("Can`t load credentials. The key file is empty "
                             "or corrupted. Contact your server "
                             "administrator.")
    version_notfound = "No one valid version for {0} was found."
    cant_find = "Can`t find package {0}"
    error_400 = "Can`t get android version for some reason"

    # noinspection PyBroadException
    @property
    def get(self):
        args = request.args
        if args['id'].isspace():
            abort(400, message=self.package_name_undefined)
        self.package_name = args['id']
        app.logger.info('Try loading version from cache')
        formatted_version = cache.get
        if formatted_version is not None:
            app.logger.info('Done from cache')
            return {'last_version': formatted_version}
        app.logger.info(self.cache_empty.format(self.package_name))
        try:
            self.load_credentials()
        except:
            abort(501, message=self.cant_load_credentials)
        try:
            return{'last_version': self.proceed_query(self.extract_mask(args))}
        except IndexError:
            app.logger.error(sys.exc_info()[0])
            abort(422, message=self.version_notfound.format(self.package_name))
        except apiclient.errors.HttpError:
            app.logger.error(sys.exc_info()[0])
            abort(422, message=self.cant_find.format(self.package_name))
        except:
            app.logger.error(sys.exc_info()[0])
            abort(400, message=self.error_400)

    @staticmethod
    def extract_mask(args):
        # mask of your version code. H - Major, L- Minor, P-Patch, I-ignore
        mask = 'HILPIII' if 'mask' not in args else args['mask']
        # get list of index ignored symbols
        ignore = [m.start() for m in re.finditer('I', mask)]
        major = mask.count('H')  # calc Major symbols
        minor = mask.count('L')  # calc Minor symbols
        patch = mask.count('P')  # calc Patch symbols
        return ignore, major, minor, patch

    def load_credentials(self):
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.dirname(os.path.abspath(__file__)) + '/key.json',
            scopes='https://www.googleapis.com/auth/androidpublisher')

    def proceed_query(self, ignore, major, minor, patch):
        app.logger.info("Request for {0} started".format(self.package_name))
        http = httplib2.Http()
        http = self.credentials.authorize(http)
        service = apiclient.discovery.build('androidpublisher', 'v2',
                                            http=http)
        edit_request = service.edits().insert(body={},
                                              packageName=self.package_name)
        result = edit_request.execute()
        edit_id = result['id']
        apks_result = service.edits().apks().list(
            editId=edit_id, packageName=self.package_name).execute()
        app.logger.info("Request for {0} completed".format(self.package_name))
        last_version = str(apks_result['apks'][-1]['versionCode'])
        # remove ignored symbols
        for i in range(len(ignore)):
            last_version = last_version[:ignore[i] - i] + \
                           last_version[ignore[i] + 1 - i:]
        formatted_version = '{0}.{1}.{2}'.format(
            last_version[0:major],
            last_version[major:major + minor],
            last_version[major + minor:major + minor + patch])
        app.logger.info('Save to cache')
        # Usually releasing new app version take 4 hours. That's why we
        # save version to cache for 4 hours
        cache.set(self.package_name, formatted_version, timeout=4 * 60 * 60)
        return formatted_version


api.add_resource(GetAppVersion, '/')

if __name__ == '__main__':
    handler = logging.handlers.RotatingFileHandler(
        os.path.dirname(os.path.abspath(__file__)) +
        '/logs/android_version_checker.log',
        maxBytes=10000,
        backupCount=1)
    formatter = logging.Formatter(
        "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.info('Android app version checker started on port 5005')
    app.run(
        host="0.0.0.0",
        port=5005,
        debug=True
    )
