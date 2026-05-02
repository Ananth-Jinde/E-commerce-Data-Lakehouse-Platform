-- Store A Incremental Load (Day 2+ simulation)
USE [ecom-store-a];
GO
-- New Customers
INSERT INTO dbo.customers VALUES ('CUST-A-02001','John','Rivera','john.rivera@gmail.com','555-0201','789 Oak Ave','Austin','TX','73301','2025-03-15','2025-03-15');
INSERT INTO dbo.customers VALUES ('CUST-A-02002','Maria','Chen','maria.chen@yahoo.com','555-0202','456 Pine St','Denver','CO','80201','2025-03-16','2025-03-16');
GO
-- Updated Customers (triggers SCD2)
UPDATE dbo.customers SET Address='999 New Blvd', City='Miami', State='FL', ModifiedDate='2025-03-18' WHERE CustomerID='CUST-A-00001';
GO
-- Updated Products (price change triggers SCD2)
UPDATE dbo.products SET Price=1299.99, ModifiedDate='2025-03-18' WHERE ProductID='PROD-A-00001';
GO
-- New Orders
INSERT INTO dbo.orders VALUES ('ORD-A-008001','CUST-A-02001','2025-03-18','2025-03-25','Processing',459.99,'Credit Card','789 Oak Ave, Austin, TX','2025-03-18','2025-03-18');
GO
INSERT INTO dbo.order_items VALUES ('ITEM-A-020001','ORD-A-008001','PROD-A-00001',1,459.99,0.00,459.99,'2025-03-18');
GO
