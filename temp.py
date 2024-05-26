import random
from flaskblog import app, db, bcrypt
from flaskblog.models import User, Post, Interest, Friendship

def populate_db():
    # Drop all tables and recreate them
    db.drop_all()
    db.create_all()

    # Define the interests
    interests_choices = ['Technology', 'Sports', 'Music', 'Movies']

    # Create 300 users
    users = []
    for i in range(1, 301):
        username = f'alex{i}'
        email = f'alex{i}@gmail.com'
        password = bcrypt.generate_password_hash('password').decode('utf-8')
        user = User(username=username, email=email, password=password)
        users.append(user)
        db.session.add(user)
    
    # Commit to get user ids
    db.session.commit()
    
    # Assign random interests and create a post for each user
    for user in users:
        # Assign a random interest
        interest_name = random.choice(interests_choices)
        interest = Interest(name=interest_name, user_id=user.id)
        db.session.add(interest)
        
        # Create a post for the user
        post = Post(title='First Post', content=f'Hi, my name is {user.username} and this is my first post.', user_id=user.id)
        db.session.add(post)
    
    # Commit all the changes
    db.session.commit()

    # Create random friendships
    user_ids = [user.id for user in users]
    for user in users:
        # Select a random number of friends for each user
        friend_ids = random.sample(user_ids, k=random.randint(5, 15))  # Each user will have between 5 to 15 friends
        for friend_id in friend_ids:
            if friend_id != user.id:
                friendship = Friendship(user_id=user.id, friend_id=friend_id, status='accepted')
                db.session.add(friendship)
    
    # Commit all friendships
    db.session.commit()

    print("Database tables created and populated with sample data, including users, interests, and friendships.")

if __name__ == "__main__":
    with app.app_context():
        populate_db()
