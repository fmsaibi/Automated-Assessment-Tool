# from blog import app as application
from blog import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
