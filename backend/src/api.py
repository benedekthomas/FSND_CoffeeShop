import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink
from .auth.auth import AuthError, requires_auth

app = Flask(__name__)
setup_db(app)
CORS(app)

db_drop_and_create_all()

# ROUTES
"""
GET /drinks
    it should be a public endpoint
    it should contain only the drink.short() data representation
returns status code 200 and json {"success": True, "drinks": drinks} where
    drinks is the list of drinks
    or appropriate status code indicating reason for failure
"""


@app.route("/drinks", methods=["GET"])
def retrieve_drinks():
    try:
        drinks = [drink.short() for drink in Drink.query.all()]
    except exc.SQLAlchemyError:
        # return internal server error if couldn't add record
        abort(500)

    return jsonify({
                    "success": True,
                    "drinks": drinks
                    })


"""
GET /drinks-detail
    it should require the 'get:drinks-detail' permission
    it should contain the drink.long() data representation
returns status code 200 and json {"success": True, "drinks": drinks}
    where drinks is the list of drinks
    or appropriate status code indicating reason for failure
"""


@app.route("/drinks-detail", methods=["GET"])
@requires_auth("get:drinks-detail")
def retrieve_drinks_detail(jwt):
    drinks = [drink.long() for drink in Drink.query.all()]
    return jsonify({
                    "success": True,
                    "drinks": drinks
                    })


"""
POST /drinks
    it should create a new row in the drinks table
    it should require the 'post:drinks' permission
    it should contain the drink.long() data representation
returns status code 200 and json {"success": True, "drinks": drink} where
    drink an array containing only the newly created drink
    or appropriate status code indicating reason for failure
"""


@app.route("/drinks", methods=["POST"])
@requires_auth("post:drinks")
def create_new_drink(jwt):
    newDrink = Drink(
        title=request.json.get("title", ""),
        recipe=json.dumps(request.json.get("recipe", "")),
    )

    try:
        Drink.insert(newDrink)
    except exc.SQLAlchemyError:
        # return internal server error if couldn't add record
        abort(500)

    return jsonify({
                    "success": True,
                    "drinks": [newDrink.long()]
                    })


"""
PATCH /drinks/<int:drink_id>
    where <drink_id> is the existing model id
    it should respond with a 404 error if <id> is not found
    it should update the corresponding row for <id>
    it should require the 'patch:drinks' permission
    it should contain the drink.long() data representation
returns status code 200 and json {"success": True, "drinks": drink} where
    drink an array containing only the updated drink
    or appropriate status code indicating reason for failure
"""


@app.route("/drinks/<int:drink_id>", methods=["PATCH"])
@requires_auth("patch:drinks")
def patch_drink(jwt, drink_id):
    drink = Drink.query.filter_by(id=drink_id).one_or_none()
    if drink is None:
        # Drink with ID is not found
        return jsonify({
                        "success": False,
                        "error": 404,
                        "message": ("Drink #{} not found.".format(drink_id))
                        }), 404

    if request.json.get("title", "") != "":
        drink.title = request.json.get("title", "")

    if request.json.get("recipe", "") != "":
        drink.recipe = json.dumps(request.json.get("recipe", ""))

    return jsonify({
                    "success": True,
                    "drinks": [drink.long()]
                    })


"""
DELETE /drinks/<int:drink_id> endpoint
    where <drink_id> is the existing model id
    it should respond with a 404 error if <drink_id> is not found
    it should delete the corresponding row for <id>
    it should require the 'delete:drinks' permission
returns status code 200 and json {"success": True, "delete": id} where id is
    the id of the deleted record
    or appropriate status code indicating reason for failure
"""


@app.route("/drinks/<int:drink_id>", methods=["DELETE"])
@requires_auth("delete:drinks")
def delete_drink(jwt, drink_id):
    drink = Drink.query.filter_by(id=drink_id).one_or_none()

    if drink is None:
        # Drink with ID is not found
        return jsonify({
                        "success": False,
                        "error": 404,
                        "message": ("Drink #{} not found.".format(drink_id))
        }), 404

    try:
        drink.delete()
    except exc.SQLAlchemyError:
        # return internal server error if couldn't delete record
        abort(500)

    return jsonify({"success": True, "delete": drink_id})


# Error Handling
"""
HTTP error handlers> 400, 404, 422, 500
"""


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
                    "success": False,
                    "error": 400,
                    "message": "bad request"
                    }), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({
                "success": False,
                "error": 404,
                "message": "resource not found"
                }), 404


@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
                    "success": False,
                    "error": 422,
                    "message": "unprocessable"
                    }), 422


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
                    "success": False,
                    "error": 500,
                    "message": "Internal server error"
                    }), 500


"""
Authentication error handlers
"""


@app.errorhandler(AuthError)
def auth_error(error):
    return jsonify({
                    "success": False,
                    "error": error.status_code,
                    "message": error.error.get("description", "unknown error"),
                    }), error.status_code
                   