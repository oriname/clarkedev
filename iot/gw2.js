// Extract the data from the payload
const {
  timestamp,
  deviceName,
  deviceId,
  deviceType,
  gatewayName,
  location,
  dBm,
  powerFailureDetected,
  channel1,
  channel2,
  channel3
} = msg.payload;

// Function to handle undefined values and ensure correct SQL data type formatting
const toSqlValue = (value, type) => {
  if (value === undefined) return 'NULL';
  switch (type) {
    case 'string':
      return `'${value.replace(/'/g, "''")}'`; // Escape single quotes by doubling them
    case 'boolean':
      return value === 'true' || value === true ? 1 : 0;
    case 'number':
      return isNaN(parseFloat(value)) ? 'NULL' : parseFloat(value);
    default:
      return 'NULL';
  }
};

// Prepare values for SQL command
const ts = toSqlValue(timestamp, 'string');
const dn = toSqlValue(deviceName, 'string');
const did = toSqlValue(deviceId, 'string');
const dt = toSqlValue(deviceType, 'string');
const gn = toSqlValue(gatewayName, 'string');
const loc = toSqlValue(location, 'string');
const dbmValue = toSqlValue(dBm, 'number');
const pfdValue = toSqlValue(powerFailureDetected, 'boolean');
const c1v = toSqlValue(channel1 ? channel1.value : undefined, 'number');
const c1u = toSqlValue(channel1 ? channel1.unit : undefined, 'string');
const c2v = toSqlValue(channel2 ? channel2.value : undefined, 'number');
const c2u = toSqlValue(channel2 ? channel2.unit : undefined, 'string');
const c3v = toSqlValue(channel3 ? channel3.value : undefined, 'number');
const c3u = toSqlValue(channel3 ? channel3.unit : undefined, 'string');

// Create the SQL insert command string
const sql = `
  INSERT INTO [iot_test].[dbo].[Data] (
    Timestamp, DeviceName, DeviceID, DeviceType, GatewayName, Location, dBm,
    PowerFailureDetected, Channel1, Channel1_Unit, Channel2, Channel2_Unit,
    Channel3, Channel3_Unit
  ) VALUES (
    ${ts}, ${dn}, ${did}, ${dt}, ${gn}, ${loc}, ${dbmValue},
    ${pfdValue}, ${c1v}, ${c1u}, ${c2v}, ${c2u}, 
    ${c3v}, ${c3u}
  )
`;

msg.payload = sql;

return msg;
