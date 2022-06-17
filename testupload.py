#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, csv
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django
django.setup()

from products.models import Product, ProductCategory, ProductsStock
from administration.models import Company

def add_new_product(description, price, cost, quantity, company, category):
    description = description.strip()
    print(f'description: {description} -- price: {price} -- cost: {cost} -- quantity: {quantity}')

    product = Product()
    product.description = description
    product.price = price if len(price) > 0 else 0
    product.cost = cost if len(cost) > 0 else 0
    product.itbis = 0
    product.category = category
    product.company = company
    product.updated = False
    product.save()

    _quantity = float(quantity) if float(quantity) > 0 else 0

    stock = ProductsStock()
    stock.product = product
    stock.company = company
    stock.quantityAvailable = _quantity
    stock.modifiedUser = 'rafaelmersant@yahoo.com'
    stock.save()
    
        
# Main Process        
with open('productsFull.csv', encoding='ISO-8859-1', newline='') as csvfile:
    products = csv.reader(csvfile, delimiter=',', quotechar='|')
    company = Company.objects.get(pk=1)
    category = ProductCategory.objects.get(pk=1)

    for product in products:
        add_new_product(product[0], product[1], product[2], product[3], company, category)
