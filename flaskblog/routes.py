import os
import secrets
import networkx as nx
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort, jsonify
from flaskblog import app, db, bcrypt
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, MessageForm, SearchUserForm, AddFriendForm, InterestForm, BiographyForm, CommentForm
from flaskblog.models import User, Post, Message, Notification, Friendship, Interest, Conversation, Comment , Like
from flask_login import login_user, current_user, logout_user, login_required
from flask_wtf.csrf import generate_csrf

@app.context_processor
def inject_search_form():
    return {
        'search_form': SearchUserForm(),
        'csrf_token': generate_csrf()
    }

@app.route("/", methods=['GET', 'POST'])
@app.route("/home", methods=['GET', 'POST'])
def home():
    filter_friends = request.form.get('filter_friends')
    page = request.args.get('page', 1, type=int)
    comment_form = CommentForm()

    if filter_friends:
        friends_ids = [friend.id for friend in current_user.friends]
        posts = Post.query.filter(Post.user_id.in_(friends_ids)).order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    else:
        posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)

    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = []
    if current_user.is_authenticated:
        announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
        friends_with_conversations = [
            (friend, Conversation.query.filter(
                ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == friend.id)) |
                ((Conversation.user1_id == friend.id) & (Conversation.user2_id == current_user.id))
            ).first())
            for friend in current_user.friends
        ]
    else:
        friends_with_conversations = []

    return render_template('home.html', posts=posts, form=AddFriendForm(), comment_form=comment_form, latest_posts=latest_posts,
                           announcements=announcements, friends_with_conversations=friends_with_conversations)


@app.route("/about")
def about():
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = []
    if current_user.is_authenticated:
        announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('about.html', title='About', latest_posts=latest_posts, announcements=announcements)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = []
    if current_user.is_authenticated:
        announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('register.html', title='Register', form=form, latest_posts=latest_posts,
                           announcements=announcements)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = []
    if current_user.is_authenticated:
        announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('login.html', title='Login', form=form, latest_posts=latest_posts,
                           announcements=announcements)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    interest_form = InterestForm()
    biography_form = BiographyForm()
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.current_password.data and form.new_password.data:
            if bcrypt.check_password_hash(current_user.password, form.current_password.data):
                current_user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            else:
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('account'))
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        biography_form.biography.data = current_user.biography
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    interests = current_user.interests  # Fetch the interests of the current user
    return render_template('account.html', title='Account', image_file=image_file, form=form,
                           interest_form=interest_form, biography_form=biography_form, latest_posts=latest_posts,
                           announcements=announcements, interests=interests)

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post',
                           latest_posts=latest_posts, announcements=announcements)

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = []
    if current_user.is_authenticated:
        announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('post.html', title=post.title, post=post, latest_posts=latest_posts,
                           announcements=announcements)

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post',
                           latest_posts=latest_posts, announcements=announcements)

@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home', latest_posts=latest_posts, announcements=announcements))

@app.route("/messages")
@login_required
def messages():
    form = MessageForm()
    received_messages = Message.query.filter_by(receiver_id=current_user.id).all()
    sent_messages = Message.query.filter_by(sender_id=current_user.id).all()
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('messages.html', title='Messages', received_messages=received_messages,
                           sent_messages=sent_messages, form=form, latest_posts=latest_posts,
                           announcements=announcements)

@app.route("/messages/new", methods=['GET', 'POST'])
@login_required
def new_message():
    form = MessageForm()
    if form.validate_on_submit():
        receiver_username = request.form.get('receiver_username')
        receiver = User.query.filter_by(username=receiver_username).first()
        if receiver:
            conversation = Conversation.query.filter(
                ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == receiver.id)) |
                ((Conversation.user1_id == receiver.id) & (Conversation.user2_id == current_user.id))
            ).first()
            if not conversation:
                conversation = Conversation(user1_id=current_user.id, user2_id=receiver.id)
                db.session.add(conversation)
                db.session.commit()
            message = Message(content=form.content.data, sender_id=current_user.id, receiver_id=receiver.id, conversation_id=conversation.id)
            db.session.add(message)
            db.session.commit()
            # Create a notification for the receiver
            notification_content = f"New message from {current_user.username}: {form.content.data}"
            notification = Notification(content=notification_content, user_id=receiver.id)
            db.session.add(notification)
            db.session.commit()
            flash('Your message has been sent!', 'success')
            return redirect(url_for('conversation', conversation_id=conversation.id))
        else:
            flash('No user with that username.', 'danger')
    return render_template('create_message.html', title='New Message', form=form)

@app.route("/notifications")
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('notifications.html', title='Notifications', notifications=notifications,
                           latest_posts=latest_posts, announcements=announcements)

@app.route("/friends", methods=['GET', 'POST'])
@login_required
def friends():
    form = AddFriendForm()
    friends = current_user.friends  # SQLAlchemy query to get friends
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    return render_template('friends.html', title='Friends', friends=friends, form=form, latest_posts=latest_posts,
                           announcements=announcements)

@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    form = SearchUserForm()
    users = []
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = []
    if current_user.is_authenticated:
        announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    if form.validate_on_submit():
        search_query = form.username.data
        users = User.query.filter(User.username.contains(search_query)).all()
    return render_template('search.html', title='Search', form=form, users=users, latest_posts=latest_posts,
                           announcements=announcements)

@app.route("/update_biography", methods=['POST'])
@login_required
def update_biography():
    form = BiographyForm()
    if form.validate_on_submit():
        current_user.biography = form.biography.data
        db.session.commit()
        flash('Your biography has been updated!', 'success')
    return redirect(url_for('account'))

@app.route('/update_interests', methods=['POST'])
@login_required
def update_interests():
    form = InterestForm()
    if form.validate_on_submit():
        user = current_user
        # Clear existing interests
        Interest.query.filter_by(user_id=user.id).delete()
        # Add new interests
        for interest_name in form.interests.data:
            interest = Interest(name=interest_name.strip(), user_id=user.id)
            db.session.add(interest)
        db.session.commit()
        flash('Your interests have been updated!', 'success')
        return redirect(url_for('account'))
    return render_template('account.html', title='Account', form=form)

@app.route("/user/<username>", methods=['GET', 'POST'])
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).all()
    mutual_friends = current_user.friends.filter(User.friends.any(id=user.id)).all()
    form = AddFriendForm()
    latest_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
    announcements = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_sent.desc()).limit(5).all()
    interests = user.interests  # Fetch the interests of the user
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            if user in current_user.friends:
                flash('You are already friends with this user.', 'info')
            else:
                friendship = Friendship(user_id=current_user.id, friend_id=user.id, status='accepted')
                db.session.add(friendship)
                db.session.commit()
                flash('Friend added successfully!', 'success')
        elif action == 'remove':
            friendship = Friendship.query.filter(
                ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user.id)) |
                ((Friendship.user_id == user.id) & (Friendship.friend_id == current_user.id))
            ).first()
            if friendship:
                db.session.delete(friendship)
                db.session.commit()
                flash('Friend removed successfully!', 'success')
            else:
                flash('You are not friends with this user.', 'info')
        return redirect(url_for('user_profile', username=user.username))
    
    return render_template('user_profile.html', user=user, posts=posts, mutual_friends=mutual_friends, form=form,
                           latest_posts=latest_posts, announcements=announcements, interests=interests)

@app.route("/manage_friend/<int:user_id>", methods=['POST'])
@login_required
def manage_friend(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')

    if action == 'add':
        if user in current_user.friends:
            flash('You are already friends with this user.', 'info')
        else:
            friendship = Friendship(user_id=current_user.id, friend_id=user.id, status='accepted')
            db.session.add(friendship)
            db.session.commit()
            flash('Friend added successfully!', 'success')
    elif action == 'remove':
        friendship = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user.id)) |
            ((Friendship.user_id == user.id) & (Friendship.friend_id == current_user.id))
        ).first()
        if friendship:
            db.session.delete(friendship)
            db.session.commit()
            flash('Friend removed successfully!', 'success')
        else:
            flash('You are not friends with this user.', 'info')

    return redirect(url_for('friends'))

@app.route("/conversations", methods=['GET', 'POST'])
@login_required
def conversations():
    friends = current_user.friends.all()  # Get mutual friends

    conversations = Conversation.query.filter(
        (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
    ).all()
    
    form = MessageForm()
    form.receiver_id.choices = [(friend.id, friend.username) for friend in friends]

    if form.validate_on_submit():
        receiver_id = form.receiver_id.data
        receiver = User.query.get(receiver_id)
        
        if receiver and receiver in friends:
            conversation = Conversation.query.filter(
                ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == receiver.id)) |
                ((Conversation.user1_id == receiver.id) & (Conversation.user2_id == current_user.id))
            ).first()
            
            if not conversation:
                conversation = Conversation(user1_id=current_user.id, user2_id=receiver.id)
                db.session.add(conversation)
                db.session.commit()
            
            message = Message(content=form.content.data, sender_id=current_user.id, receiver_id=receiver.id, conversation_id=conversation.id)
            db.session.add(message)
            db.session.commit()
            
            # Create a notification for the receiver
            notification_content = f"New message from {current_user.username}: {form.content.data}"
            notification = Notification(content=notification_content, user_id=receiver.id)
            db.session.add(notification)
            db.session.commit()
            
            flash('Your message has been sent!', 'success')
            return redirect(url_for('conversation', conversation_id=conversation.id))
        else:
            flash('User not found or not a mutual friend.', 'danger')
    
    return render_template('conversations.html', conversations=conversations, friends=friends, form=form)

@app.route("/conversation/<int:conversation_id>", methods=['GET', 'POST'])
@login_required
def conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.date_sent.asc()).all()
    
    form = MessageForm()
    form.receiver_id.choices = [(conversation.user1.id, conversation.user1.username), (conversation.user2.id, conversation.user2.username)]
    
    if form.validate_on_submit():
        receiver = conversation.user1 if conversation.user2 == current_user else conversation.user2
        message = Message(content=form.content.data, sender_id=current_user.id, receiver_id=receiver.id, conversation_id=conversation.id)
        db.session.add(message)
        db.session.commit()
        
        # Create a notification for the receiver
        notification_content = f"New message from {current_user.username}: {form.content.data}"
        notification = Notification(content=notification_content, user_id=receiver.id)
        db.session.add(notification)
        db.session.commit()
        flash('Your message has been sent!', 'success')
        return redirect(url_for('conversation', conversation_id=conversation.id))
    
    return render_template('conversation.html', conversation=conversation, messages=messages, form=form)

def get_recommendations(user_id):
    user = User.query.get(user_id)
    
    # Get the current user's friends
    friends = {friendship.friend_id for friendship in Friendship.query.filter_by(user_id=user.id).all()}
    friend_dict = {friend.id: friend.username for friend in User.query.filter(User.id.in_(friends)).all()}
    print(f"Friends of user {user.id}: {friends}")
    
    # Find mutual friends (users who share friends with the current user)
    mutual_friend_candidates = {}
    for friend_id in friends:
        friend_friends = {friendship.friend_id for friendship in Friendship.query.filter_by(user_id=friend_id).all()}
        mutual_friends = friend_friends.intersection(friends)
        for ff_id in friend_friends:
            if ff_id != user.id and ff_id not in friends:
                if ff_id not in mutual_friend_candidates:
                    mutual_friend_candidates[ff_id] = {'reason': 'Mutual Friends', 'details': set()}
                mutual_friend_candidates[ff_id]['details'].update(mutual_friends)
    
    # Remove candidates with empty mutual friends details
    mutual_friend_candidates = {k: v for k, v in mutual_friend_candidates.items() if v['details']}
    
    print(f"Mutual friend candidates for user {user.id}: {mutual_friend_candidates}")
    
    # Find users with common interests and limit to 2 per interest
    user_interests = {interest.name for interest in user.interests}
    interest_candidates = {}
    for interest in user_interests:
        interested_users = {interest.user_id for interest in Interest.query.filter_by(name=interest).limit(2).all()}
        for iu in interested_users:
            if iu != user.id and iu not in friends:
                if iu in interest_candidates:
                    interest_candidates[iu]['details'].append(interest)
                else:
                    interest_candidates[iu] = {'reason': 'Common Interests', 'details': [interest]}
    
    print(f"Interest candidates for user {user.id}: {interest_candidates}")
    
    # Combine both sets of candidates
    recommendation_candidates = set(mutual_friend_candidates.keys()) | set(interest_candidates.keys())
    recommendations = []
    for candidate_id in recommendation_candidates:
        reasons = []
        if candidate_id in mutual_friend_candidates:
            mutual_friends_usernames = [friend_dict[mf] for mf in mutual_friend_candidates[candidate_id]['details']]
            reasons.append({'reason': 'Mutual Friends', 'details': mutual_friends_usernames})
        if candidate_id in interest_candidates:
            reasons.append(interest_candidates[candidate_id])
        recommendations.append({'user': User.query.get(candidate_id), 'reasons': reasons})
    
    print(f"Recommendation candidates for user {user.id}: {recommendations}")
    return recommendations



@app.route("/recommendations", methods=['GET'])
@login_required
def recommendations():
    user_id = current_user.id
    recommendations = get_recommendations(user_id)
    print(f"Recommendations for user {user_id}: {[user.username for user in recommendations]}")
    return jsonify([{"id": user.id, "username": user.username} for user in recommendations])

@app.route("/recommendations_page", methods=['GET', 'POST'])
@login_required
def recommendations_page():
    user_id = current_user.id
    recommendations = get_recommendations(user_id)
    return render_template('recommendation.html', recommendations=recommendations)

@app.route("/add_friend_from_recommendations/<int:user_id>", methods=['POST'])
@login_required
def add_friend_from_recommendations(user_id):
    new_friend = User.query.get_or_404(user_id)
    if new_friend in current_user.friends:
        flash('You are already friends with this user.', 'info')
    else:
        friendship = Friendship(user_id=current_user.id, friend_id=new_friend.id, status='accepted')
        db.session.add(friendship)
        db.session.commit()
        flash(f'{new_friend.username} has been added to your friends!', 'success')
    return redirect(url_for('recommendations_page'))


@app.route("/foaf_graph_data")
@login_required  # Ensure you are logged in when accessing this route
def get_foaf_graph_data():
    nodes = []
    links = []
    user_id = current_user.id
    users = User.query.all()

    user_map = {user.id: user for user in users}

    for user in users:
        nodes.append({
            'id': user.id,
            'label': user.username
        })

    for user in users:
        friends = {friendship.friend_id for friendship in Friendship.query.filter_by(user_id=user.id).all()}
        interests = {interest.name for interest in Interest.query.filter_by(user_id=user.id).all()}

        for friend_id in friends:
            if friend_id > user.id:  # Avoid duplicate links
                friend_interests = {interest.name for interest in Interest.query.filter_by(user_id=friend_id).all()}
                shared_interests = interests.intersection(friend_interests)
                if shared_interests:
                    relationship_type = 'both' if shared_interests else 'mutual'
                else:
                    relationship_type = 'mutual'
                links.append({
                    'source': user.id,
                    'target': friend_id,
                    'relationship': relationship_type
                })

        for interest in interests:
            interested_users = {interest.user_id for interest in Interest.query.filter_by(name=interest).all()}
            for interested_user_id in interested_users:
                if interested_user_id > user.id and interested_user_id not in friends:
                    links.append({
                        'source': user.id,
                        'target': interested_user_id,
                        'relationship': 'interest'
                    })

    return jsonify({'nodes': nodes, 'links': links})


@app.route("/graph")
@login_required
def graph_page():
    return render_template('graph.html')

@app.route("/like_post/<int:post_id>", methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if like:
        # User already liked the post, so remove the like
        db.session.delete(like)
    else:
        # Add a new like
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)
    db.session.commit()

    # Return the new like count
    like_count = Like.query.filter_by(post_id=post.id).count()
    return jsonify({'like_count': like_count})

@app.route("/add_comment/<int:post_id>", methods=['POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        content = form.content.data
        post = Post.query.get_or_404(post_id)
        comment = Comment(content=content, user_id=current_user.id, post_id=post.id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
    return redirect(url_for('home'))