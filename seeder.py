from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Category, Base, Item, User

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()
 
user1=User(name="Waleed Al-Safwani", email ="waleed@udacity.com")
session.add(user1)
session.commit()

user2=User(name="Ali", email ="ali@udacity.com")
session.add(user2)
session.commit()

category1 = Category(name="Mobile phones", description="Mobile phones and handheld device's comes under this category")
session.add(category1)
session.commit()

item1=Item(description="IPhone 7 mobile phone", title ="iPhone 7",category=category1, user=user1)
session.add(item1)
session.commit()

item2=Item(description="IPhone 8 mobile phone", title ="iPhone 8",category=category1, user=user1)
session.add(item2)
session.commit()

item3=Item(description="Samsung 9s mobile phone", title ="Samsung 9s",category=category1, user=user1)
session.add(item3)
session.commit()

category2 = Category(name="Computers", description="Computer devices comes under this category")
session.add(category2)
session.commit()

item4=Item(description="HP", title ="HP Computer",category=category2, user=user1)
session.add(item4)
session.commit()

item5=Item(description="Acer", title ="Acer Computer",category=category2, user=user1)
session.add(item5)
session.commit()

item6=Item(description="Dell", title ="Dell Computer",category=category2, user=user1)
session.add(item6)
session.commit()

category3 = Category(name="Accessories", description="Accessories comes under this category")
session.add(category3)
session.commit()

item2=Item(description="Computer Headphone", title ="Headphone",category=category3, user=user2)
session.add(item2)
session.commit()

item2=Item(description="Computer Mouse", title ="mouse",category=category3, user=user2)
session.add(item2)
session.commit()

print "added items!"