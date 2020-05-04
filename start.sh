# start.sh
export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export STATIC_FOLDER=./application/static
export TEMPLATES_FOLDER=./application/templates
export APP_CONFIG_FILE=config.py
flask run