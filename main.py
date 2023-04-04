from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
import datetime
from werkzeug.utils import secure_filename
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, EditCommentForm, EditProfileForm
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = "f64170de13c84937a4b476a110f1ed4e"
Bootstrap(app)
ckeditor = CKEditor(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CONFIGURE TABLE
class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250),  nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    comments = db.relationship("Comments", back_populates="parent_post")
    image = db.Column(db.String(250), nullable=False)
    saves = db.relationship("SavedPosts", back_populates="saved_post")
    views = db.Column(db.Integer)

    def __repr__(self):
        return f'<Post "{self.title}">'


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    comments = db.relationship("Comments", back_populates="comment_author")
    saved_posts = db.relationship("SavedPosts", back_populates='user')
    role = db.Column(db.String(100))
    profile_image = db.Column(db.String(100))

    def __repr__(self):
        return f"<User {self.name}>"


class Comments(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = db.relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)
    parent_post = db.relationship("BlogPost", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))

    def __repr__(self):
        return f"<Comment {self.id}>"


class SavedPosts(db.Model):
    __tablename__ = "saved_posts"

    id = db.Column(db.Integer, primary_key=True)
    saved_post = db.relationship('BlogPost', back_populates='saves')
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"), nullable=False)
    user = db.relationship("User", back_populates="saved_posts")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


# ===================================================================


def is_admin(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if current_user.is_authenticated and current_user.role == 'admin':
            return func(*args, **kwargs)
        else:
            return redirect(url_for('get_all_posts'))

    return decorator


@app.route("/about")
def about():
    return render_template("about.html")


# ===========Posts====================


@app.route('/', methods=["GET"])
def get_all_posts():
    per_page = 5
    page = request.args.get('page')

    if page:
        page_1 = (int(page) * per_page) - per_page
        posts = BlogPost.query.order_by(BlogPost.id.desc()).all()[page_1: page_1+per_page]
    else:
        posts = BlogPost.query.order_by(BlogPost.id.desc()).all()[0: 5]
        page = 1
    count = math.ceil(len(BlogPost.query.order_by(BlogPost.id.desc()).all()) / per_page)
    popular_post = BlogPost.query.order_by(BlogPost.views.desc()).all()[0:5]
    return render_template("index.html", all_posts=posts, popular_post=popular_post, count=count, page=int(page))


@app.route("/post/<int:index>", methods=['GET', 'POST'])
def show_post(index):
    form = CommentForm()
    edit_form = EditCommentForm()
    comment_to_edit_id = 0
    post = BlogPost.query.get(index)
    post.views = int(post.views) + 1
    saved = False
    edit_comment = False

    save = request.args.get('save')
    unsave = request.args.get('unsave')

    if request.method == "GET":
        if save:
            db.session.add(SavedPosts(post_id=index,
                                      user_id=current_user.id))
            db.session.commit()
            return redirect(url_for('show_post', index=index))
        elif unsave:
            db.session.delete(SavedPosts.query.filter_by(post_id=index,
                                                         user_id=current_user.id).first())
            db.session.commit()
            return redirect(url_for('show_post', index=index))

    if current_user.is_authenticated:
        if len(SavedPosts.query.filter_by(post_id=index, user_id=current_user.id).all()) > 0:
            saved = True

    if request.args.get("edit"):
        comment_to_edit_id = int(request.args.get("edit"))
        comment_to_edit = Comments.query.get(comment_to_edit_id)
        edit_form = EditCommentForm(text=comment_to_edit.text)
        edit_comment = True
        if edit_form.validate_on_submit() and edit_form.submit.data:
            comment_to_edit.text = edit_form.text.data
            db.session.commit()
            return redirect(url_for('show_post', index=index))

    if form.validate_on_submit() and form.submit.data:
        comment = form.text.data
        author_id = current_user.id
        new_comment = Comments(text=comment,
                               author_id=author_id,
                               post_id=index)
        db.session.add(new_comment)
        db.session.commit()
        form.text.data = ''
        return redirect(url_for('show_post', index=index))

    comments = Comments.query.filter_by(post_id=index).all()
    return render_template("post.html", post=post, form=form, comments=comments, edit_form=edit_form,
                           edit_comment=edit_comment, edit_comment_id=comment_to_edit_id, saved=saved)


@app.route('/admin/add_post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        title = form.title.data
        subtitle = form.subtitle.data
        content = form.content.data
        day = datetime.datetime.now().day
        month = datetime.datetime.now().strftime("%B")
        year = datetime.datetime.now().year
        date = f"{month} {day}, {year}"
        file = secure_filename(form.image.data.filename)
        form.image.data.save('static/img/' + file)
        post = BlogPost(title=title,
                        subtitle=subtitle,
                        body=content,
                        date=date,
                        image=file,
                        views=0)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    return render_template("admin/add_post.html", form=form)


@app.route('/admin/edit-post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    form = CreatePostForm(title=post.title,
                          subtitle=post.subtitle,
                          image=post.image,
                          content=post.body)

    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.body = form.content.data
        if form.image.data:
            file = secure_filename(form.image.data.filename)
            form.image.data.save('static/img/' + file)
            post.image = file

        db.session.commit()
        return redirect(url_for('show_post', index=post_id))

    return render_template("admin/add_post.html", form=form, post_id=post_id)


@app.route("/admin/delete/<post_id>")
@is_admin
@login_required
def delete(post_id):
    post = BlogPost.query.get(post_id)
    comments = Comments.query.filter_by(post_id=post_id).all()
    saves = SavedPosts.query.filter_by(post_id=post_id).all()

    for save in saves:
        db.session.delete(save)

    for comment in comments:
        db.session.delete(comment)

    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('admin_posts'))


@app.route("/delete/comment/<post_id>/<comment_id>")
@login_required
def delete_comment(comment_id, post_id):
    comment = Comments.query.get(comment_id)
    if current_user.id == comment.author_id:
        db.session.delete(comment)
        db.session.commit()
    return redirect(url_for('show_post', index=post_id))


# ===========Authentication====================


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password=form.password.data,
                                                 method="pbkdf2:sha256",
                                                 salt_length=8)
        new_user = User(name=form.name.data,
                        email=form.email.data,
                        password=hashed_password,
                        role="subscriber",
                        profile_image='user-icon.jpg')
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Password incorrect, please try again.")
        except AttributeError:
            flash("That email does not exist, please try again.")

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


# ===========Profile====================


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    saved_posts = SavedPosts.query.filter_by(user_id=current_user.id).all()
    is_edit = request.args.get('is_edit')
    form = EditProfileForm(name=current_user.name)
    if request.method == 'POST':
        if form.image.data:
            file = secure_filename(form.image.data.filename)
            form.image.data.save('static/img/' + file)
            current_user.profile_image = file
        current_user.name = form.name.data
        db.session.commit()

    return render_template('profile.html', edit=is_edit, form=form, saved_posts=saved_posts)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    return render_template('profile.html', edit=True)


@app.route('/delete-image')
@login_required
def delete_image():
    current_user.profile_image = 'user-icon.jpg'
    db.session.commit()

    return redirect(url_for('edit_profile'))


# ================Search===================


@app.route('/search/', methods=['GET'])
def search():
    key_word = request.args.get("search")

    per_page = 5
    page = request.args.get('page')
    posts = BlogPost.query.filter(BlogPost.title.like("%" + key_word + "%")).order_by(BlogPost.id.desc()).all()

    if page:
        page_1 = (int(page) * per_page) - per_page
        search_results = posts[page_1: page_1 + per_page]
    else:
        search_results = posts[0: 5]
        page = 1
    count = math.ceil(len(posts) / per_page)
    popular_post = BlogPost.query.order_by(BlogPost.views.desc()).all()[0:5]

    return render_template('index.html', key_word=key_word, search_results=search_results, search=True, page=int(page),
                           count=count, popular_post=popular_post)


# ===========Admin===========

@app.route('/admin')
@is_admin
def admin_dashboard():
    all_posts = BlogPost.query.all()
    all_comments = Comments.query.all()
    all_user = User.query.all()
    return render_template('admin/index.html', users=all_user, posts=all_posts, comments=all_comments)


@app.route('/admin/posts')
@is_admin
def admin_posts():
    all_posts = BlogPost.query.all()
    return render_template('admin/posts.html', posts=all_posts)


@app.route('/admin/users')
@is_admin
@login_required
def admin_users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)


@app.route('/admin/comments')
@is_admin
@login_required
def admin_comments():
    all_comments = Comments.query.all()
    return render_template('admin/comments.html', comments=all_comments)


# ==============================


if __name__ == "__main__":
    app.run()
