-- Store A DDL — Database: ecom-store-a (Standard column naming)
CREATE DATABASE [ecom-store-a];
GO
USE [ecom-store-a];
GO

CREATE TABLE dbo.product_categories (
    CategoryID NVARCHAR(10) NOT NULL PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL,
    ParentCategory NVARCHAR(10) NULL
);

CREATE TABLE dbo.customers (
    CustomerID NVARCHAR(20) NOT NULL PRIMARY KEY,
    FirstName NVARCHAR(50) NOT NULL, LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL, Phone NVARCHAR(20) NULL,
    Address NVARCHAR(200) NOT NULL, City NVARCHAR(50) NOT NULL,
    State NVARCHAR(10) NOT NULL, ZipCode NVARCHAR(10) NOT NULL,
    CreatedDate DATE NOT NULL, ModifiedDate DATE NOT NULL
);

CREATE TABLE dbo.products (
    ProductID NVARCHAR(20) NOT NULL PRIMARY KEY,
    ProductName NVARCHAR(200) NOT NULL, Category NVARCHAR(100) NOT NULL,
    SubCategory NVARCHAR(100) NOT NULL, Price DECIMAL(10,2) NOT NULL,
    StockQty INT NOT NULL, Supplier NVARCHAR(100) NOT NULL,
    CreatedDate DATE NOT NULL, ModifiedDate DATE NOT NULL
);

CREATE TABLE dbo.orders (
    OrderID NVARCHAR(20) NOT NULL PRIMARY KEY,
    CustomerID NVARCHAR(20) NOT NULL REFERENCES dbo.customers(CustomerID),
    OrderDate DATE NOT NULL, ShipDate DATE NULL, Status NVARCHAR(20) NOT NULL,
    TotalAmount DECIMAL(12,2) NOT NULL, PaymentMethod NVARCHAR(30) NOT NULL,
    ShippingAddress NVARCHAR(300) NULL, InsertDate DATE NOT NULL, ModifiedDate DATE NOT NULL
);

CREATE TABLE dbo.order_items (
    OrderItemID NVARCHAR(20) NOT NULL PRIMARY KEY,
    OrderID NVARCHAR(20) NOT NULL REFERENCES dbo.orders(OrderID),
    ProductID NVARCHAR(20) NOT NULL REFERENCES dbo.products(ProductID),
    Quantity INT NOT NULL, UnitPrice DECIMAL(10,2) NOT NULL,
    Discount DECIMAL(5,2) DEFAULT 0, LineTotal DECIMAL(12,2) NOT NULL,
    InsertDate DATE NOT NULL
);
