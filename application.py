from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r')
                       .read())['web']['client_id']
APPLICATION_NAME = "Item Catalog"

# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# User related methods
# Create new user if not already available in DB
def createUser(login_session):
    try:
        new_user = User(email=login_session['email'],
                        name=login_session['username'],
                        picture=login_session['picture'])
        session.add(new_user)
        print('user added')
        print(new_user.name)
        print(new_user.email)
        session.commit()
        currUser = session.query(User).filter_by(
                   email=login_session['email']).one()
        print(currUser.id)
        return currUser.id
    except:
        return None


# retrive's user id by email filtering
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        print(email)
        print(user.id)
        return user.id
    except:
        return None


# retrieve complete user information by user id filtering
def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        print (user)
        return user
    except:
        print (user)
        return None


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
        response = make_response(json.dumps(
                   'Current user is already connected.'), 200)
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

    # #verfy user existance, otherwise create new
    user_id = getUserID(login_session['email'])
    print(user_id)

    if not user_id or user_id == 'None':
        user_id = createUser(login_session)

    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/'
    url += 'revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
                    'Failed to revoke token for given user.',
                    400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Show all Categorires Items
@app.route('/')
@app.route('/category/')
def showCategories():
    category = session.query(Category).all()

    items = session.query(Item).all()
    return render_template('categories.html', category=category, items=items)


# Show all Items related to a specific Category
@app.route('/byCategory/<int:cat_id>/')
def showItemByCategory(cat_id):
    category = session.query(Category).all()

    items = session.query(Item).filter_by(cat_id=cat_id).all()
    return render_template('categories.html', category=category, items=items)


# Show a specific Item complete information
@app.route('/itemdetails/<int:item_id>/', methods=['GET'])
def showItemDetils(item_id):
    item = session.query(Item).filter_by(id=item_id).one()

    print 'username'
    if 'username' not in login_session:
        return render_template("login.html")

    return render_template('itemdetails.html', item=item)


# Add new Item
@app.route('/item/new/', methods=['GET', 'POST'])
def newItem():
    category = session.query(Category).all()

    if 'username' not in login_session:
        return render_template("login.html")

    if request.method == 'POST':
        newItem = Item(title=request.form['title'],
                       description=request.form['description'],
                       cat_id=request.form['category1'],
                       user_id=login_session['user_id'])
        session.add(newItem)
        flash('New Item %s Successfully Created' % newItem.title)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newItem.html', category=category)


# Edit an Item
@app.route('/item/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(item_id):
    editedItem = session.query(Item).filter_by(id=item_id).one()

    # Check the owner of item
    owner = editedItem.user_id
    # Autorize the owner only to perform this action

    curr = (login_session['user_id'])
    print("owner")
    print(owner)
    print("current")
    print(curr)

    # Check if the logged in user is theowner of the current Item
    if owner != curr:
        flash('Not allowed ,only logged in user can edit items they created!')
        return redirect(url_for('showCategories'))

    if request.method == 'POST':
        if request.form['title']:
            editedItem.title = request.form['title']
            editedItem.description = request.form['description']

            flash('Item Successfully Edited %s' % editedItem.title)
            session.add(editedItem)
            session.commit()
            return redirect(url_for('showCategories'))
    else:
        return render_template('edititem.html', item=editedItem)


# Delete item
@app.route('/item/<int:item_id>/delete/', methods=['GET', 'POST'])
def deleteItem(item_id):
    itemToDelete = session.query(Item).filter_by(id=item_id).one()

    # Check the owner of item
    owner = itemToDelete.user_id
    curr = (login_session['user_id'])
    print("owner")
    print(owner)
    print("current")
    print(curr)

    # Check if the logged in user is the owner of the current Item
    if owner != curr:
        flash('You can Delete only Items that belogns to you !')
        return redirect(url_for('showCategories'))

    if request.method == 'POST':
        session.delete(itemToDelete)
        flash('%s Successfully Deleted' % itemToDelete.title)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


# ==== JSON functions ====
# All Items
@app.route('/items/JSON')
def itemsJSON():
    items = session.query(Item).all()
    return jsonify(items=[i.serialize for i in items])


# All Categories
@app.route('/categories/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[c.serialize for c in categories])


# All Items by Category
@app.route('/catalog/<int:category_id>/JSON')
def categoryItemsJSON(category_id):
    items = [item.serialize for item in session.query(Item).
             ilter_by(cat_id=category_id).all()]

    return jsonify(items=items)

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=4000)
