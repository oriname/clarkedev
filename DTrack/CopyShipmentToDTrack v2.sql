USE [Enterprise32]
GO

-- First create a filtered index for our specific condition
CREATE NONCLUSTERED INDEX IX_Shipment_VanDelivery
ON [dbo].[Shipment] (ShipmentNumber, ShipVia, IsPartial)
INCLUDE (
    JobNumber, ShipName, ShipAddress1, ShipAddress2,
    ShipCity, ShipState, ShipZip, ShipCountry,
    ShipContact, Instructions, ShipAddress3,
    ShipPhone, Email, Shipped, ShipViaService,
    ScheduledShipDate, ScheduledShipQuantity
)
WHERE ShipVia = '10005' AND IsPartial = 1;
GO

IF OBJECT_ID('CopyShipmentToDTrack', 'TR') IS NOT NULL
    DROP TRIGGER CopyShipmentToDTrack;
GO

CREATE TRIGGER CopyShipmentToDTrack
ON [dbo].[Shipment]
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- Early exit if no qualifying records
    IF NOT EXISTS (
        SELECT 1 FROM inserted 
        WHERE [ShipVia] = '10005' AND [isPartial] = 1
    )
        RETURN;

    DECLARE @HasMatches BIT;

    SELECT @HasMatches = CASE 
        WHEN EXISTS (
            SELECT 1 FROM inserted i
            INNER JOIN [DTrack].[dbo].[Shipment] t ON i.ShipmentNumber = t.ShipmentNumber
            WHERE i.[ShipVia] = '10005' AND i.[isPartial] = 1
        ) THEN 1 
        ELSE 0 
    END;

    IF @HasMatches = 1
        SET IDENTITY_INSERT [DTrack].[dbo].[Shipment] ON;

    BEGIN TRY
        MERGE [DTrack].[dbo].[Shipment] AS target
        USING (
            SELECT 
                [JobNumber], [ShipmentNumber], [ShipName],
                [ShipAddress1], [ShipAddress2], [ShipCity],
                [ShipState], [ShipZip], [ShipCountry],
                [ShipContact], [Instructions], [ShipAddress3],
                [ShipPhone], [Email], [ShipVia],
                [IsPartial], [Shipped], [ShipViaService],
                [ScheduledShipDate], [ScheduledShipQuantity]
            FROM 
                inserted WITH (INDEX(IX_Shipment_VanDelivery))
            WHERE 
                [ShipVia] = '10005' AND [isPartial] = 1
        ) AS source
        ON target.[ShipmentNumber] = source.[ShipmentNumber]
        WHEN MATCHED THEN
            UPDATE SET
                target.[JobNumber] = source.[JobNumber],
                target.[ShipName] = source.[ShipName],
                target.[ShipAddress1] = source.[ShipAddress1],
                target.[ShipAddress2] = source.[ShipAddress2],
                target.[ShipCity] = source.[ShipCity],
                target.[ShipState] = source.[ShipState],
                target.[ShipZip] = source.[ShipZip],
                target.[ShipCountry] = source.[ShipCountry],
                target.[ShipContact] = source.[ShipContact],
                target.[Instructions] = source.[Instructions],
                target.[ShipAddress3] = source.[ShipAddress3],
                target.[ShipPhone] = source.[ShipPhone],
                target.[Email] = source.[Email],
                target.[ShipVia] = source.[ShipVia],
                target.[IsPartial] = source.[isPartial],
                target.[Shipped] = source.[Shipped],
                target.[ShipViaService] = source.[ShipViaService],
                target.[ScheduledShipDate] = source.[ScheduledShipDate],
                target.[ScheduledShipQuantity] = source.[ScheduledShipQuantity]
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (
                [JobNumber], [ShipmentNumber], [ShipName],
                [ShipAddress1], [ShipAddress2], [ShipCity],
                [ShipState], [ShipZip], [ShipCountry],
                [ShipContact], [Instructions], [ShipAddress3],
                [ShipPhone], [Email], [ShipVia],
                [IsPartial], [Shipped], [ShipViaService],
                [ScheduledShipDate], [ScheduledShipQuantity]
            )
            VALUES (
                source.[JobNumber], source.[ShipmentNumber], source.[ShipName],
                source.[ShipAddress1], source.[ShipAddress2], source.[ShipCity],
                source.[ShipState], source.[ShipZip], source.[ShipCountry],
                source.[ShipContact], source.[Instructions], source.[ShipAddress3],
                source.[ShipPhone], source.[Email], source.[ShipVia],
                source.[isPartial], source.[Shipped], source.[ShipViaService],
                source.[ScheduledShipDate], source.[ScheduledShipQuantity]
            );

    END TRY
    BEGIN CATCH
        INSERT INTO ErrorLog2 (
            ErrorMessage, ErrorSeverity, ErrorState, ErrorProcedure, ErrorLine
        )
        VALUES (
            ERROR_MESSAGE(), ERROR_SEVERITY(), ERROR_STATE(), ERROR_PROCEDURE(), ERROR_LINE()
        );

        THROW;
    END CATCH;

    IF @HasMatches = 1
        SET IDENTITY_INSERT [DTrack].[dbo].[Shipment] OFF;
END;
GO