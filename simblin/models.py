# -*- coding: utf-8 -*-
"""
    Simblin Models
    ~~~~~~~~~~~~~~

    Database abstractions.

    :copyright: (c) 2010 by Eugen Kiss.
    :license: BSD, see LICENSE for more details.
"""
from datetime import datetime
from werkzeug import check_password_hash, generate_password_hash

from simblin.helpers import normalize, convert_markup
from simblin.extensions import db
from simblin import signals

# TODO: Comments! Danjac, look at cached_property!

class Admin(db.Model):
    """There should ever only be one admin"""
    
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(), unique=True)
    pw_hash = db.Column(db.String(),)
    
    def __init__(self, username, password):
        self.username = username
        self.pw_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)


class Post(db.Model):
    
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    _slug = db.Column(db.String(255), unique=True, nullable=False)
    _title = db.Column(db.String(255), nullable=False)
    _markup = db.Column(db.Text)
    _html = db.Column(db.Text)
    published = db.Column(db.DateTime)
    
    # Many to many Post <-> Tag
    _tags = db.relationship('Tag', secondary='post_tags', 
        backref=db.backref('posts', lazy='dynamic'))
    
    def __init__(self, title, markup):
        self.title = title
        self.markup = markup
        self.published = datetime.now()
    
    def _set_title(self, title):
        """Constrain title with slug so slug is never set directly"""
        self._title = title
        slug = normalize(title)
        # Make the slug unique
        while True:
            entry = Post.query.filter_by(slug=slug).first()
            if not entry: break
            slug += "-2"
        self._slug = slug
        
    def _get_title(self):
        return self._title
    
    title = db.synonym("_title", descriptor=property(_get_title, _set_title))
    
    def _get_slug(self):
        return self._slug
    
    slug = db.synonym("_slug", descriptor=property(_get_slug))
    
    def _set_markup(self, markup):
        """Constrain markup with html so html is never set directly"""
        self._markup = markup
        self._html = convert_markup(markup)
        
    def _get_markup(self):
        return self._markup
    
    markup = db.synonym('_markup', 
                        descriptor=property(_get_markup, _set_markup))
        
    def _get_html(self):
        return self._html
    
    html = db.synonym('_html', descriptor=property(_get_html))
    
    def _set_tags(self, taglist):
        """Associate tags with this entry. The taglist is expected to be already
        normalized without duplicates."""
        # Remove all previous tags
        self._tags = []
        for tag_name in taglist:
            exists = Tag.query.filter(Tag.name==tag_name).first()
            # Only add tags to the database that don't exist yet
            # TODO: Put this in the init method of Tag (if possible)
            if not exists:
                self._tags.append(Tag(tag_name))
            else:
                self._tags.append(exists)
                
        
    def _get_tags(self):
        return self._tags
        
    tags = db.synonym("_tags", descriptor=property(_get_tags, _set_tags))
    
    def set_categories(self, categorylist):
        pass
    
    def __repr__(self):
        return '<Post: %s>' % self.slug
    
    
#: Association table
# TODO: Explain ondelete='Cascade'
post_tags = db.Table('post_tags', db.Model.metadata,
    db.Column('post_id', db.Integer, 
              db.ForeignKey('posts.id', ondelete='CASCADE')),
    db.Column('tag_id', db.Integer,
              db.ForeignKey('tags.id', ondelete='CASCADE')))


class Tag(db.Model):
    
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    
    def __init__(self, name):
        # TODO: only create new row if name does not exist yet (ask IRC how)
        #       __new__ to the rescue?
        self.name = name
    
    @property
    def num_associations(self):
        """Return the number of posts with this tag"""
        return len(self.posts)
    
    def __repr__(self):
        return '<Tag: %s>' % self.name
    
    
# ------------- SIGNALS ----------------#

def tidy_tags(post):
    """Remove tags with zero associations"""
    for tag in Tag.query.filter_by(posts=None):
        db.session.delete(tag)
    db.session.commit()

signals.post_created.connect(tidy_tags)
signals.post_updated.connect(tidy_tags)
signals.post_deleted.connect(tidy_tags)