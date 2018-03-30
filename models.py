from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

import os, sys
 
Base = declarative_base()

class User(Base):
		__tablename__ = 'user'


		name =Column(String(80), nullable = False)
		id = Column(Integer, primary_key = True)
		email = Column(String(250))
		picture = Column(String(30))
		


		@property
		def serialize(self):
			 """Return object data in easily serializeable format"""
			 return {
					 'name'         : self.name,
					 'email'         : self.email,
					 'id'         : self.id,
					 'picture'         : self.picture,					 
			 }


class Catagory(Base):
		__tablename__ = 'item_catagory'

		cat_id = Column(Integer, primary_key = True)
		name = Column(String(80), nullable = False)
		description = Column(String(250))
		user_id = Column(Integer, ForeignKey('user.id'))
		user = relationship(User)
		
		@property
		def serialize(self):
			 """Return object data in easily serializeable format"""
			 return {
					 'name'         : self.name,
					 'description'         : self.description,
					 'cat_id'		:self.cat_id,
					 
					 				 
			 }


class MenuItem(Base):
		__tablename__ = 'menu_item'


		name =Column(String(80), nullable = False)
		id = Column(Integer, primary_key = True)
		description = Column(String(250))
		price_retail = Column(String(8))
		price_wholesale = Column(String(8))
		date_added = Column(DateTime, default=func.now())
		quantity =  Column(Integer, default=0)
		picture = Column(String(30))
		user_id = Column(Integer, ForeignKey('user.id'))
		user = relationship(User)
		catagory_id = Column(Integer, ForeignKey('item_catagory.cat_id'), default=4) 
		cat = relationship(Catagory)



		@property
		def serialize(self):
			 """Return object data in easily serializeable format"""
			 return {
					 'name'         : self.name,
					 'description'         : self.description,
					 'id'         : self.id,
					 'price_retail'         : self.price_retail,
					 'price_wholesale'         : self.price_wholesale,
					 'catagory_id'			: self.catagory_id,
					 'date_added'		: self.date_added,
					 'quantity'			: self.quantity,
					 'picture'		: self.picture,

			 }




engine = create_engine('sqlite:///catalog.db')
 

Base.metadata.create_all(engine)
