SELECT TOP (1) [DeviceLocation],[DeviceValues] FROM [iot_test].[dbo].[data]


INSERT INTO [iot_test].[dbo].[data] (DeviceLocation, DeviceValues) VALUES ('Shopfloor', '52' )


// Extract sensor data from the payload
const {
  DeviceName, // Assuming this is equivalent to DeviceIdentifier
  DeviceID, // Assuming you need to store this as well
  DeviceType, // Assuming you need to store this as well
  GatewayName,
  DeviceLocation,
  DeviceValues,
  DeviceValuesUnit,
  SignalStrengthdBm: SignalStrength // Renaming to match your database column names
} = msg.payload;

// Create a timestamp for the SQL query
const timestamp = new Date().toISOString(); // Proper format for MSSQL

// Prepare the SQL query with parameters
const query = `
  INSERT INTO [iot_test].[dbo].[Data] (
    Timestamp,
    DeviceName,
    DeviceID,
    DeviceType,
    GatewayName,
    DeviceLocation,
    DeviceValues,
    DeviceValuesUnit,
    SignalStrengthdBm
  ) VALUES (
    @timestamp,
    @deviceName,
    @deviceID,
    @deviceType,
    @gatewayName,
    @deviceLocation,
    @deviceValues,
    @deviceValuesUnit,
    @signalStrength
  )
`;

// Assign the query and parameters to msg.payload for the MSSQL node
msg.payload = {
  query: query,
  parameters: {
    timestamp: { value: timestamp, type: 'DateTime' },
    deviceName: { value: DeviceName, type: 'VarChar' },
    deviceID: { value: DeviceID, type: 'VarChar' },
    deviceType: { value: DeviceType, type: 'VarChar' },
    gatewayName: { value: GatewayName, type: 'VarChar' },
    deviceLocation: { value: DeviceLocation, type: 'VarChar' },
    deviceValues: { value: DeviceValues, type: 'Float' }, // Assuming DeviceValues is a numeric type
    deviceValuesUnit: { value: DeviceValuesUnit, type: 'VarChar' },
    signalStrength: { value: SignalStrength, type: 'Int' } // Assuming SignalStrength is an integer
  }
};

// Pass the message to the next node (MSSQL node)
return msg;
