from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Catagory, Base, MenuItem, User

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()


cat1 = Catagory(cat_id=1, name="Toys", description = "A variety of toys", user_id = 1)
session.add(cat1)
session.commit()

cat2 = Catagory(cat_id=2, name="Equipment", description = "Equipment for the garden", user_id = 1)
session.add(cat2)
session.commit()

cat3 = Catagory(cat_id=3, name="Party", description = "All your party needs", user_id = 1)
session.add(cat3)
session.commit()

cat4= Catagory(cat_id=4, name="Other", description = "All the miscellaneous", user_id = 1)
session.add(cat4)
session.commit()

item1 = MenuItem(id=1, name="Gorilla Mask", description = "It is a Gorilla Mask", price_retail = "50", price_wholesale = "40", user_id = 1, catagory_id = 1)
session.add(item1)
session.commit()

item2 = MenuItem(id=2, name="Broom", description = "A very nice broom", price_retail = "30", price_wholesale = "20", user_id = 1, catagory_id = 2)
session.add(item2)
session.commit()

item3 = MenuItem(id=3, name="Balloon", description = "A pretty descent ballon", price_retail = "15", price_wholesale = "10", user_id = 1, catagory_id = 3)
session.add(item3)
session.commit()



print "added menu items!"