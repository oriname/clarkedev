USE [DTrack]
GO

IF OBJECT_ID('MapToDtrack_Shipping', 'TR') IS NOT NULL
    DROP TRIGGER MapToDtrack_Shipping;
GO

CREATE TRIGGER MapToDtrack_Shipping
ON [dbo].[Shipment]
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        -- Insert new records or update existing ones in [Dtrack_Shipping]
        MERGE [dbo].[Dtrack_Shipping] AS target
        USING (
            SELECT 
                JobNumber AS do_number,
                CAST(ShipmentNumber AS NVARCHAR(255)) AS tracking_number,
                ShipName AS company_name,
                CONCAT(ShipAddress1, ' ', ShipAddress2, ' ', ShipAddress3, ' ', ShipCountry) AS address_1,
                ShipCity AS city,
                ShipState AS state,
                ShipZip AS postal_code,
                ShipContact AS [First Name],
                Instructions AS instructions,
                ShipPhone AS phone_number,
                Email AS notify_email,
                ShipVia,
                IsPartial,
                Shipped,
                ShipViaService,
                ScheduledShipDate AS delivery_date,
                ScheduledShipQuantity AS quantity,
                GETDATE() AS entry_date
            FROM 
                inserted
        ) AS source
        ON 
            target.tracking_number = source.tracking_number
        WHEN MATCHED THEN
            -- Existing record will be updated (if necessary)
            UPDATE SET
                target.do_number = source.do_number,
                target.company_name = source.company_name,
                target.address_1 = source.address_1,
                target.city = source.city,
                target.state = source.state,
                target.postal_code = source.postal_code,
                target.[First Name] = source.[First Name],
                target.instructions = source.instructions,
                target.phone_number = source.phone_number,
                target.notify_email = source.notify_email,
                target.ShipVia = source.ShipVia,
                target.IsPartial = source.IsPartial,
                target.Shipped = source.Shipped,
                target.ShipViaService = source.ShipViaService,
                target.delivery_date = source.delivery_date,
                target.quantity = source.quantity,
                target.entry_date = GETDATE()
        WHEN NOT MATCHED BY TARGET THEN
            -- Insert a new record with a unique DetrackJobNumber
            INSERT (
                do_number,
                DetrackJobNumber,
                tracking_number,
                company_name,
                address_1,
                city,
                state,
                postal_code,
                [First Name],
                instructions,
                phone_number,
                notify_email,
                ShipVia,
                IsPartial,
                Shipped,
                ShipViaService,
                delivery_date,
                quantity,
                entry_date
            )
            VALUES (
                source.do_number,
                -- Logic to generate the unique DetrackJobNumber
                COALESCE(
                    (
                        SELECT TOP 1 
                            CASE 
                                -- If the last part of DetrackJobNumber is a number, increment it
                                WHEN DetrackJobNumber LIKE source.do_number + '(%' THEN 
                                    source.do_number + '(' + CAST(CAST(SUBSTRING(DetrackJobNumber, LEN(source.do_number) + 2, CHARINDEX(')', DetrackJobNumber) - LEN(source.do_number) - 1) AS INT) + 1 AS VARCHAR(10)) + ')'
                                -- If no suffix exists, create the first one
                                ELSE source.do_number + '(1)'
                            END
                        FROM dbo.Dtrack_Shipping
                        WHERE do_number = source.do_number
                        ORDER BY DetrackJobNumber DESC
                    ),
                    -- If no match is found, use the original do_number
                    source.do_number
                ),
                source.tracking_number,
                source.company_name,
                source.address_1,
                source.city,
                source.state,
                source.postal_code,
                source.[First Name],
                source.instructions,
                source.phone_number,
                source.notify_email,
                source.ShipVia,
                source.IsPartial,
                source.Shipped,
                source.ShipViaService,
                source.delivery_date,
                source.quantity,
                GETDATE()
            );
    END TRY
    BEGIN CATCH
        -- Log the error
        INSERT INTO ErrorLog (
            ErrorMessage, 
            ErrorSeverity, 
            ErrorState, 
            ErrorProcedure, 
            ErrorLine
        )
        VALUES (
            ERROR_MESSAGE(), 
            ERROR_SEVERITY(), 
            ERROR_STATE(), 
            ERROR_PROCEDURE(), 
            ERROR_LINE()
        );

        -- Raise the error to the calling application
        THROW;
    END CATCH;
END;
GO