#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, csv
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django
django.setup()

from products.models import Product, ProductCategory
from administration.models import Company

def add_new_product(description, price, cost):
    description = description.strip()

    try:
        product = Product()
        product.description = description
        product.price = price if len(price) > 0 else 0
        product.cost = cost if len(cost) > 0 else 0
        product.itbis = 0
        product.category = ProductCategory.objects.filter(description='GENERICA')
        product.company = Company.objects.get(pk=14)
        product.save()
        print("*** product: ", description, ' -> added!')
    except:
        print('There was an error trying to add this product: ', description)
        
# Main Process        
with open('productsFull.csv', newline='') as csvfile:
    musical_works = csv.reader(csvfile, delimiter=',', quotechar='|')
    for index, row in enumerate(musical_works):
        add_new_product(row[0], row[1], row[2])