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
  
  // Ensure that all values are defined and if not, set a default value or handle as appropriate
  const ts = timestamp ? `'${timestamp}'` : 'NULL'; // Assuming Timestamp can be NULL
  const dn = deviceName ? `'${deviceName}'` : 'NULL'; // Assuming DeviceName can be NULL
  const did = deviceId ? `'${deviceId}'` : 'NULL';
  const dt = deviceType ? `'${deviceType}'` : 'NULL';
  const gn = gatewayName ? `'${gatewayName}'` : 'NULL';
  const loc = location ? `'${location}'` : 'NULL';
  const dbm = dBm ? `'${dBm}'` : 'NULL'; // dBm should be an integer or float, adjust accordingly
  const pfd = (powerFailureDetected === 'true' || powerFailureDetected === true) ? 1 : 0; // If boolean, 1 or 0; if string, handle as necessary
  
  // Handle channel values and units; ensure they are never undefined
  const c1v = channel1 && channel1.value !== undefined ? channel1.value : 0;
  const c1u = channel1 && channel1.unit ? `'${channel1.unit}'` : 'NULL';
  const c2v = channel2 && channel2.value !== undefined ? channel2.value : 0;
  const c2u = channel2 && channel2.unit ? `'${channel2.unit}'` : 'NULL';
  const c3v = channel3 && channel3.value !== undefined ? channel3.value : 0;
  const c3u = channel3 && channel3.unit ? `'${channel3.unit}'` : 'NULL';
  
  // Create the SQL insert command string
  const sql = `
    INSERT INTO [iot_test].[dbo].[Data] (
      Timestamp, DeviceName, DeviceID, DeviceType, GatewayName, Location, dBm, 
      PowerFailureDetected, Channel1, Channel1_Unit, Channel2, Channel2_Unit, 
      Channel3, Channel3_Unit
    ) VALUES (
      ${ts}, ${dn}, ${did}, ${dt}, ${gn}, ${loc}, ${dbm}, 
      ${pfd}, ${c1v}, ${c1u}, ${c2v}, ${c2u}, 
      ${c3v}, ${c3u}
    )
  `;
  
  msg.payload = sql;
  
  return msg;
  