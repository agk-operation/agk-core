from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Company(models.Model):
    name    = models.CharField(max_length=200)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Exporter(models.Model):
    name    = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Customer(models.Model):
    name    = models.CharField(max_length=200)
    email   = models.EmailField()
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name
