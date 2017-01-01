# -*- coding: utf-8 -*-

import sys
import logging.handlers
import os
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
    @staticmethod
    def get():
        args = request.args
        if args['id'].isspace():
            abort(400, message="The package name undefined. Example: "
                               "com.android.sample")
        package_name = args['id']

        app.logger.info('Try loading version from cache')
        formatted_version = cache.get(package_name)
        if formatted_version is not None:
            app.logger.info('Done from cache')
            return {'last_version': formatted_version}

        app.logger.info("Cache for {0} is empty or expired. Try to get version"
                        " from Google. Loading key file".format(package_name))
        credentials = None
        # noinspection PyBroadException
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                os.path.dirname(os.path.abspath(__file__)) + '/key.json',
                scopes='https://www.googleapis.com/auth/androidpublisher')
        except:
            abort(501, message="Can`t load credentials. The key file is "
                               "empty or corrupted. Contact your server "
                               "administrator.")

        # noinspection PyBroadException
        try:
            app.logger.info("Request for {0} started".format(package_name))
            http = httplib2.Http()
            http = credentials.authorize(http)
            service = apiclient.discovery.build(
                'androidpublisher', 'v2', http=http)
            edit_request = service.edits().insert(body={},
                                                  packageName=package_name)
            result = edit_request.execute()
            edit_id = result['id']

            apks_result = service.edits().apks().list(
                editId=edit_id, packageName=package_name).execute()
            app.logger.info("Request for {0} completed".format(package_name))
            last_version = str(apks_result['apks'][-1]['versionCode'])

            formatted_version = '{0}.{1}.{2}'.format(last_version[0],
                                                     last_version[3],
                                                     last_version[4])
            app.logger.info('Save to cache')
            # Usually releasing new app version take 4 hours. That's why we
            # save version to cache for 4 hours
            cache.set(package_name, formatted_version, timeout=4 * 60 * 60)
            return {'last_version': formatted_version}
        except IndexError:
            app.logger.error(sys.exc_info()[0])
            abort(422, message="No one valid version for {0} was found.".
                  format(package_name))
        except apiclient.errors.HttpError:
            app.logger.error(sys.exc_info()[0])
            abort(422, message="Can`t find package " + package_name)
        except:
            app.logger.error(sys.exc_info()[0])
            abort(400, message="Can`t get android version for some reason")


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
