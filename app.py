import os
import json
import logging
from flask import Flask, current_app, render_template, redirect, url_for, request
from flask_session import Session
from pathlib import Path
import app_config
from ms_identity_web import IdentityWebPython
from ms_identity_web.adapters import FlaskContextAdapter
from ms_identity_web.errors import NotAuthenticatedError
from ms_identity_web.configuration import AADConfig
from types import SimpleNamespace

"""
Instructions for running the sample app. These are dev environment instructions ONLY.
Do not run using this configuration in production.

IN OSX with system-trusted dev https certs:
=======================================================
    # start from the folder in which the sample code is cloned into
    cd ./ssl
    source generate-local-cert.sh
    source trust-local-cert-on-macos.sh
    cd ../ # back to folder in which the sample code is cloned into
    source run.flask.dev.certs.sh

LINUX/OSX - in a terminal window, type the following:
=======================================================
    # start from the folder in which the sample is cloned into
    source run.flask.dev.sh

WINDOWS - in a powershell window, type the following:
====================================================
    # start from the folder in which the sample is cloned into
    . .\run.flask.dev.ps1

You can also use "python -m flask run" instead of "flask run"
"""
# get workload identity token if it exists
def workload_identity_client_credential_injection():
    config_file = open('aad.config.json', 'r')
    config = json.loads(config_file.read())#, object_hook=lambda d: SimpleNamespace(**d))
    if os.environ.get('AZURE_FEDERATED_TOKEN_FILE') and not 'client_secret' in config['client']:
        token_file_path = os.environ.get('AZURE_FEDERATED_TOKEN_FILE')
        token_file = open(token_file_path, 'r')
        secure_client_credential = dict([('client_assertion', token_file.read())])
        return secure_client_credential

def create_app(secure_client_credential=None):
    app = Flask(__name__, root_path=Path(__file__).parent) #initialize Flask app
    app.config.from_object(app_config) # load Flask configuration file (e.g., session configs)
    Session(app) # init the serverside session for the app: this is required due to large cookie size
    # tell flask to render the 401 template on not-authenticated error. it is not strictly required:
    app.register_error_handler(NotAuthenticatedError, lambda err: (render_template('auth/401.html'), err.code))
    # comment out the previous line and uncomment the following line in order to use (experimental) <redirect to page after login>
    # app.register_error_handler(NotAuthenticatedError, lambda err: (redirect(url_for('auth.sign_in', post_sign_in_url=request.url_rule))))
    # other exceptions - uncomment to get details printed to screen:
    # app.register_error_handler(Exception, lambda err: (f"Error {err.code}: {err.description}"))
    aad_configuration = AADConfig.parse_json('aad.config.json') # parse the aad configs
    app.logger.level=logging.DEBUG # can set to DEBUG for verbose logs
    if app.config.get('ENV') == 'production':
        # The following is required to run on Azure App Service or any other host with reverse proxy:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    # retrieve environment variable if it exists and value isn't set in config file
    if aad_configuration.client.client_id == '<replace_me>' and os.environ.get('AZURE_CLIENT_ID'):
        aad_configuration.client.client_id = os.environ.get('AZURE_CLIENT_ID')    
    if aad_configuration.client.authority == '<replace_me>' and os.environ.get('AZURE_TENANT_ID'):
        aad_configuration.client.authority = f"https://login.microsoftonline.com/{os.environ.get('AZURE_TENANT_ID')}"  
    # Use client credential from outside the config file, if available.
    if secure_client_credential: 
        aad_configuration.client.client_credential = secure_client_credential
    AADConfig.sanity_check_configs(aad_configuration)
    adapter = FlaskContextAdapter(app) # ms identity web for python: instantiate the flask adapter
    ms_identity_web = IdentityWebPython(aad_configuration, adapter) # then instantiate ms identity web for python

    @app.route('/')
    @app.route('/sign_in_status')
    def index():
        return render_template('auth/status.html')

    @app.route('/token_details')
    @ms_identity_web.login_required # <-- developer only needs to hook up login-required endpoint like this
    def token_details():
        current_app.logger.info("token_details: user is authenticated, will display token details")
        return render_template('auth/token.html')

    return app

if __name__ == '__main__':
    app=create_app(secure_client_credential=workload_identity_client_credential_injection()) # this is for running flask's dev server for local testing purposes ONLY
    app.run(ssl_context='adhoc', host='0.0.0.0', port=8080) # create an adhoc ssl cert for HTTPS on 127.0.0.1

app=create_app(secure_client_credential=workload_identity_client_credential_injection())
