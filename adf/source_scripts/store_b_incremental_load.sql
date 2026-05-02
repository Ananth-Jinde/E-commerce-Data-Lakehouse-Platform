-- Store B Incremental Load (Day 2+ simulation)
USE [ecom-store-b];
GO
INSERT INTO dbo.customer_info VALUES ('CB-01501','Alex','Sharma','alex.sharma@gmail.com','555-8801','321 River Rd','Seattle','WA','98101','2025-03-20','2025-03-20');
GO
UPDATE dbo.customer_info SET Street='777 Updated Blvd', Town='Dallas', Region='TX', UpdateDt='2025-03-22' WHERE CustID='CB-00001';
GO
UPDATE dbo.product_catalog SET ListPrice=899.99, UpdateDt='2025-03-22' WHERE ProdID='PB-00001';
GO
INSERT INTO dbo.order_log VALUES ('OB-006001','CB-01501','2025-03-22','2025-03-28','PROCESSING',899.99,'UPI','321 River Rd, Seattle, WA','2025-03-22','2025-03-22');
GO
INSERT INTO dbo.order_details VALUES ('DB-015001','OB-006001','PB-00001',1,899.99,0.0,899.99,'2025-03-22');
GO
