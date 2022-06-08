from datetime import datetime
from email.policy import default
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)
app.debug = True
app.config['UPLOAD_FOLDER'] = 'images'
app.config['SECRET_KEY'] = 'GG'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///postplace.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_file = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return 'Post ' + str(self.id)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return 'User ' + str(self.id)


class UserLikedPosts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return 'UserLikedPosts ' + str(self.id)

    

db.create_all()
# login screen
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user'] = user.id
            return redirect('/')
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')


# logout api
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# register screen
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        error_username = User.query.filter_by(username=username).first()
        error_email = User.query.filter_by(email=email).first()
        if error_username:
            return flash('Username already exists', 'danger')
        elif error_email :
            return flash('Email already exists', 'danger')
        else:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            session['user'] = User.query.filter_by(username=username).first().id
            return redirect('/')
    return render_template('register.html')



# like post api endpoint which will take id of post and if user has liked it or not
# it will Check user in UserLikedPosts table if user has liked it or not
# if user has liked it, it will remove like from user's list of liked posts
# if user has not liked it, it will add like to user's list of liked posts
@app.route('/like/<int:id>', methods=['GET', 'POST'])
def like(id):
    post = Post.query.filter_by(id=id).first()
    current_user_liked_posts = UserLikedPosts.query.filter_by(user_id=session['user']).all()
    if len(list(filter(lambda user: user.post_id == id, current_user_liked_posts))) > 0:
        post.likes -= 1
        UserLikedPosts.query.filter_by(user_id=session['user'], post_id=id).delete()
        db.session.commit()
    else:
        post.likes += 1
        new_user_liked_post = UserLikedPosts(user_id=session['user'], post_id=id)
        db.session.add(new_user_liked_post)
        db.session.commit()
    
    return redirect('/')


@app.route("/", methods=["GET", "POST"])
def hello_world():
    if not session.get('user'):
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['body']
        image_file = request.files['image_file']
        if image_file:
            image_file.save(f'static/img/{image_file.filename}')
        new_post = Post(title=title, content=content, image_file=image_file.filename, author=session['user'],)
        db.session.add(new_post)
        db.session.commit()
        return redirect('/')

    weather_raw = requests.get('https://api.openweathermap.org/data/2.5/weather?lat=41.6934591&lon=44.801&units=metric&apikey=8f90e14760827409fd8f2461e43c4ca0&')
    current_weather = weather_raw.json()

    user = User.query.filter_by(id=session['user']).first()
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    for post in posts:
        post.author_data = User.query.get(post.author)
        # query all user that has liked this post
        userLikes = UserLikedPosts.query.filter_by(user_id=session['user']).all()
        post.isLiked = liked(userLikes, post.id)

    return render_template('timeline.html', items=posts, user=user, weather=current_weather)


# route for user profiles
@app.route('/user/<int:id>')
def user(id):
    user = User.query.filter_by(id=id).first()
    posts = Post.query.filter_by(author=id).order_by(Post.date_posted.desc()).all()
    for post in posts:
        post.author_data = User.query.get(post.author)
        # query all user that has liked this post
        userLikes = UserLikedPosts.query.filter_by(user_id=session['user']).all()
        post.isLiked = liked(userLikes, post.id)
    return render_template('user.html', user=user, posts=posts)

def liked(user_liked_posts, post_id):
    return len(list(filter(lambda user_liked_post: user_liked_post.post_id == post_id, user_liked_posts))) > 0



if __name__ == "__main__":
    app.run()
