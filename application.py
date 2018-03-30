from flask import Flask, render_template, request, redirect, jsonify
from flask import make_response, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from models import Base, Catagory, MenuItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Evermore"

# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    print (login_session['username'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ style = "width: 300px; height: 300px;
                border-radius: 150px;-webkit-border-radius: 150px;
                -moz-border-radius: 150px;"""
    flash("You are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showMain'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showMain'))


# JSON APIs to view Catalog Information
# Show all items in a catagory
@app.route('/catalog/<catagory_name>/JSON')
def restaurantMenuJSON(catagory_name):
    catagory = session.query(Catagory).filter_by(name=catagory_name).first()
    items = session.query(MenuItem).filter_by(
        catagory_id=catagory.cat_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


# Show a specific item
@app.route('/catalog/<catagory_name>/<item_name>/JSON')
def menuItemJSON(catagory_name, item_name):
    items = session.query(MenuItem).filter_by(name=item_name).one()
    return jsonify(Menu_Item=items.serialize)

# Show a catagory
@app.route('/catalog/JSON')
def restaurantsJSON():
    catagory = session.query(Catagory).order_by(Catagory.name).all()
    return jsonify(Catagories=[c.serialize for c in catagory])

# Show all main screen
@app.route('/')
@app.route('/catalog/')
def showMain():
    catagory = session.query(Catagory).order_by(Catagory.name).all()
    items = session.query(MenuItem).order_by(MenuItem.date_added.desc()).all()
    user = session.query(User).all()
    return render_template('catalog.html', catagory=catagory, items=items)


# Show all items in a catagory
@app.route('/catalog/<catagory_name>/')
def showCatagory(catagory_name):
    catagory = session.query(Catagory).filter_by(name=catagory_name).first()
    creator = getUserInfo(catagory.user_id)
    items = session.query(MenuItem).filter_by(
        catagory_id=catagory.cat_id).all()
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return (render_template(
            'publiccatagory.html', items=items, catagory=catagory))
    else:
        return (render_template(
            'catagory.html', items=items, catagory=catagory))


# Show an item
@app.route('/catalog/<catagory_name>/<item_name>')
def showItem(catagory_name, item_name):
    items = session.query(MenuItem).filter_by(name=item_name).one()
    creator = getUserInfo(items.user_id)
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return render_template(
            'publicitem.html', items=items, catagory_name=catagory_name)
    else:
        return render_template(
            'item.html', items=items, catagory_name=catagory_name)


# Create a catagory
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newCatagory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCatagory = Catagory(
            name=request.form['name'],
            description=request.form['description'],
            user_id=login_session['user_id'])
        session.add(newCatagory)
        print (login_session['user_id'])
        flash('New catagory %s successfully created' % newCatagory.name)
        session.commit()
        return redirect(url_for('showMain'))
    else:
        catagory = session.query(Catagory).order_by(Catagory.name).all()
        return render_template('newcatagory.html', catagory=catagory)


# Edit an exitsting catagory
@app.route('/catalog/<catagory_name>/edit/', methods=['GET', 'POST'])
def editCatagory(catagory_name):
    editedCatagory = session.query(
        Catagory).filter_by(name=catagory_name).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedCatagory.user_id != login_session['user_id']:
        return """<script>function myFunction()
        {alert('You are not authorized to edit this catagory.');}
        window.setTimeout(function() { window.location.href = '/';}, 1000);
        </script><body onload='myFunction()' >"""
    if request.method == 'POST':
        if request.form['name']:
            editedCatagory.name = request.form['name']
        if request.form['description']:
            editedCatagory.description = request.form['description']
        flash('Catagory edited: %s' % editedCatagory.name)
        session.add(editedCatagory)
        session.commit()
        return redirect(url_for('showMain'))
    else:
        return render_template('editcatagory.html', catagory=editedCatagory)


# Delete a catagory
@app.route('/catalog/<catagory_name>/delete/', methods=['GET', 'POST'])
def deleteCatagory(catagory_name):
    deletedCatagory = session.query(
        Catagory).filter_by(name=catagory_name).first()
    if 'username' not in login_session:
        return redirect('/login')
    if deletedCatagory.user_id != login_session['user_id']:
        return """<script>function myFunction()
        {alert('You are not authorized to delete this catagory.');}
        window.setTimeout(function() { window.location.href = '/';}, 1000);
        </script><body onload='myFunction()' >"""
    if request.method == 'POST':
        flash('Successfully deleted: %s' % deletedCatagory.name)
        session.delete(deletedCatagory)
        session.commit()
        return redirect(url_for('showMain'))
    else:
        return render_template('deletecatagory.html', catagory=deletedCatagory)


# Add new item
@app.route('/catalog/newitem/', methods=['GET', 'POST'])
def newItem():
    catagory = session.query(Catagory).order_by(Catagory.name)
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = MenuItem(
            name=request.form['name'],
            description=request.form['description'],
            price_retail=request.form['price_retail'],
            price_wholesale=request.form['price_wholesale'],
            picture=request.form['picture'],
            catagory_id=request.form.get("catagory_id", None),
            quantity=request.form['quantity'],
            user_id=login_session['user_id'])
        flash('New item, %s, successfully created' % newItem.name)
        session.add(newItem)
        session.commit()
        return redirect(url_for('showMain'))
    else:
        return render_template('newItem.html', catagory=catagory)


# Edit an item
@app.route(
    '/catalog/<catagory_name>/<item_name>/edit', methods=['GET', 'POST'])
def editItem(catagory_name, item_name):
    if 'username' not in login_session:
        return redirect('/login')
    editItem = session.query(
        MenuItem).filter_by(name=item_name).first()
    catagory = session.query(Catagory).order_by(Catagory.name)
    if editItem.user_id != login_session['user_id']:
        return """<script>function myFunction()
        {alert('You are not authorized to edit this item.');}
        window.setTimeout(function() { window.location.href = '/';}, 1000);
        </script><body onload='myFunction()' >"""
    if request.method == 'POST':
        if request.form['name']:
            editItem.name = request.form['name']
        if request.form['description']:
            editItem.description = request.form['description']
        if request.form['price_retail']:
            editItem.price_retail = request.form['price_retail']
        if request.form['price_wholesale']:
            editItem.price_wholesale = request.form['price_wholesale']
        if request.form['picture']:
            editItem.picture = request.form['picture']
        if request.form.get("catagory_id", None):
            editItem.catagory_id = request.form.get("catagory_id", None)
        if request.form['quantity']:
            editItem.quantity = request.form['quantity']
        session.add(editItem)
        session.commit()
        flash('Item successfully edited: %s' % editItem.name)

        return redirect(url_for('showMain'))
    else:
        return render_template(
            'editItem.html', catagory=catagory, items=editItem)


# Delete item
@app.route(
    '/catalog/<catagory_name>/<item_name>/delete', methods=['GET', 'POST'])
def deleteItem(catagory_name, item_name):
    if 'username' not in login_session:
        return redirect('/login')
    deleteItem = session.query(
        MenuItem).filter_by(name=item_name).one()
    catagory = session.query(
        Catagory).filter_by(name=catagory_name).one()
    if deleteItem.user_id != login_session['user_id']:
        return """<script>function myFunction()
        {alert('You are not authorized to delete this item.');}
        window.setTimeout(function() { window.location.href = '/';}, 1000);
        </script><body onload='myFunction()'>"""
    if request.method == 'POST':
        session.delete(deleteItem)
        flash('Successfully deleted: %s ' % deleteItem.name)
        session.commit()
        return redirect(url_for('showMain'))
    else:
        return render_template(
            'deleteItem.html', catagory=catagory, items=deleteItem)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
