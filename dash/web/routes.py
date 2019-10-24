from dash.web import dash_app


@dash_app.route('/')
@dash_app.route('/index')
def index():
    return "Hello, World!"
