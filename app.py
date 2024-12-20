from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['ITEMS_PER_PAGE'] = 10

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Authentication routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if Member.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 400
        
    hashed_password = generate_password_hash(data['password'])
    new_member = Member(
        name=data['name'],
        email=data['email'],
        password=hashed_password
    )
    
    db.session.add(new_member)
    db.session.commit()
    
    return jsonify({'message': 'Member registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    member = Member.query.filter_by(email=data['email']).first()
    
    if member and check_password_hash(member.password, data['password']):
        access_token = create_access_token(identity=member.id)
        return jsonify({'access_token': access_token}), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401

# Book routes
@app.route('/books', methods=['POST'])
@jwt_required()
def create_book():
    data = request.get_json()
    
    new_book = Book(
        title=data['title'],
        author=data['author'],
        isbn=data['isbn'],
        quantity=data.get('quantity', 1)
    )
    
    db.session.add(new_book)
    db.session.commit()
    
    return jsonify({
        'message': 'Book added successfully',
        'book': {
            'id': new_book.id,
            'title': new_book.title,
            'author': new_book.author,
            'isbn': new_book.isbn,
            'quantity': new_book.quantity
        }
    }), 201

@app.route('/books', methods=['GET'])
@jwt_required()
def get_books():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    
    query = Book.query
    
    if search_term:
        query = query.filter(
            (Book.title.ilike(f'%{search_term}%')) |
            (Book.author.ilike(f'%{search_term}%'))
        )
    
    pagination = query.paginate(
        page=page,
        per_page=app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    books = [{
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'isbn': book.isbn,
        'quantity': book.quantity
    } for book in pagination.items]
    
    return jsonify({
        'books': books,
        'total_pages': pagination.pages,
        'current_page': page,
        'total_items': pagination.total
    })

@app.route('/books/<int:id>', methods=['GET'])
@jwt_required()
def get_book(id):
    book = Book.query.get_or_404(id)
    
    return jsonify({
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'isbn': book.isbn,
        'quantity': book.quantity
    })

@app.route('/books/<int:id>', methods=['PUT'])
@jwt_required()
def update_book(id):
    book = Book.query.get_or_404(id)
    data = request.get_json()
    
    book.title = data.get('title', book.title)
    book.author = data.get('author', book.author)
    book.isbn = data.get('isbn', book.isbn)
    book.quantity = data.get('quantity', book.quantity)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Book updated successfully',
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'quantity': book.quantity
        }
    })

@app.route('/books/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_book(id):
    book = Book.query.get_or_404(id)
    
    db.session.delete(book)
    db.session.commit()
    
    return jsonify({'message': 'Book deleted successfully'})

# Member routes
@app.route('/members', methods=['GET'])
@jwt_required()
def get_members():
    page = request.args.get('page', 1, type=int)
    
    pagination = Member.query.paginate(
        page=page,
        per_page=app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    members = [{
        'id': member.id,
        'name': member.name,
        'email': member.email
    } for member in pagination.items]
    
    return jsonify({
        'members': members,
        'total_pages': pagination.pages,
        'current_page': page,
        'total_items': pagination.total
    })

@app.route('/members/<int:id>', methods=['GET'])
@jwt_required()
def get_member(id):
    member = Member.query.get_or_404(id)
    
    return jsonify({
        'id': member.id,
        'name': member.name,
        'email': member.email
    })

@app.route('/members/<int:id>', methods=['PUT'])
@jwt_required()
def update_member(id):
    member = Member.query.get_or_404(id)
    data = request.get_json()
    
    member.name = data.get('name', member.name)
    member.email = data.get('email', member.email)
    
    if 'password' in data:
        member.password = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Member updated successfully',
        'member': {
            'id': member.id,
            'name': member.name,
            'email': member.email
        }
    })

@app.route('/members/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_member(id):
    member = Member.query.get_or_404(id)
    
    db.session.delete(member)
    db.session.commit()
    
    return jsonify({'message': 'Member deleted successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)