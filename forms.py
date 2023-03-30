from flask import Flask
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import StringField, SubmitField, PasswordField, FileField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


app = Flask(__name__)


class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    image = FileField("Blog Image", validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], "Image only!")])
    content = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField("Sign me up")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField("Let me in")


class CommentForm(FlaskForm):
    text = StringField("Comment", validators=[DataRequired()], render_kw=dict(style="height: 100px;"))
    submit = SubmitField("Submit comment")


class EditCommentForm(FlaskForm):
    text = StringField("Comment", validators=[DataRequired()], render_kw=dict(style="height: 100px;"))
    submit = SubmitField("Edit comment")


class EditProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    image = FileField("Profile Image", validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], "Image only!")])
    submit = SubmitField("Edit Profile")


class AddMovieForm(FlaskForm):
    movie_title = StringField('Movie title', validators=[DataRequired()])
    submit = SubmitField("Find Movie")
