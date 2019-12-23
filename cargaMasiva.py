#!/usr/bin/env python
# -*- coding: utf-8 -*-

import django
django.setup()
import sys, os, csv
from products.models import *

with open('productsFull.csv', newline='') as csvfile:
    myfile = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in myfile:
    	print(row[0])
    	p = Product()
    	p.description = row[0]
    	p.price = 0
    	p.cost = 0
    	p.itbis = 0
    	p.category = ProductCategory.objects.get(description='GENERICA')
    	p.company = Company.objects.get(id=14)
    	p.save()
