DECLARE @CurrentTime DATETIME = GETDATE();
DECLARE @StartOfCurrentHalfHour DATETIME;
DECLARE @StartOfPreviousHalfHour DATETIME;

-- Calculate the start of the current half-hour
SET @StartOfCurrentHalfHour = DATEADD(MINUTE, DATEDIFF(MINUTE, 0, @CurrentTime) / 30 * 30, 0);

-- Calculate the start time of the most recent completed half-hour interval
SET @StartOfPreviousHalfHour = DATEADD(MINUTE, -30, @StartOfCurrentHalfHour);

SELECT 
  [timestamp], 
  [gatewayName], 
  [location], 
  [powerfailureDetected], 
  [dbm], 
  [id], 
  [channel1_unit], 
  [channel2_Unit], 
  [channel3_Unit], 
  [deviceName], 
  [deviceType], 
  [channel1], 
  [channel2], 
  [channel3]
FROM 
  [iot_test].[dbo].[Data]
WHERE 
  [timestamp] >= @StartOfPreviousHalfHour AND 
  [timestamp] < @StartOfCurrentHalfHour;
