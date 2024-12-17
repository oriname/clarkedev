// Constants for the energy calculation
const voltage = 200; // Voltage in volts

// Helper function to calculate energy in kilowatt-hours
function calculateEnergy(current, voltage, timeIntervalHours) {
    return (current * voltage * timeIntervalHours) / 1000;
}

// Adjusted Timestamp Rounding Logic
function adjustRoundingBasedOnDataTimestamp(timestamp) {
    const adjustedTimestamp = new Date(timestamp);
    if (adjustedTimestamp.getMinutes() < 30) {
        adjustedTimestamp.setMinutes(30); // This sets it to the end of the first half-hour
    } else {
        adjustedTimestamp.setHours(adjustedTimestamp.getHours() + 1); // Move to the next hour
        adjustedTimestamp.setMinutes(0); // Set minutes to 00, indicating the end of the second half-hour
    }
    adjustedTimestamp.setSeconds(0);
    adjustedTimestamp.setMilliseconds(0);
    return adjustedTimestamp;
}

// Ensure msg.payload is an array of readings
const readings = Array.isArray(msg.payload) ? msg.payload : [msg.payload];

// Object to accumulate energy consumption by device and half-hour
let energyByHalfHour = {};

// Debugging: Log the number of readings being processed
node.warn(`Processing ${readings.length} readings`);

// Process each reading for 30-minute intervals
readings.forEach(reading => {
    let timestamp = new Date(reading.timestamp);
    let roundedTimestamp = adjustRoundingBasedOnDataTimestamp(timestamp);
    let formattedTimestamp = `${roundedTimestamp.getFullYear()}-${String(roundedTimestamp.getMonth() + 1).padStart(2, '0')}-${String(roundedTimestamp.getDate()).padStart(2, '0')} ${String(roundedTimestamp.getHours()).padStart(2, '0')}:${String(roundedTimestamp.getMinutes()).padStart(2, '0')}:00`;

    const current1 = parseFloat(reading.channel1);
    const current2 = parseFloat(reading.channel2);
    const current3 = parseFloat(reading.channel3);
    
    if (!isNaN(current1) && !isNaN(current2) && !isNaN(current3)) {
        const totalCurrent = current1 + current2 + current3;
        const energyConsumed = calculateEnergy(totalCurrent, voltage, 0.5); // For 30-minute intervals
        const deviceIntervalKey = `${reading.deviceName}_${formattedTimestamp}`;

        if (!energyByHalfHour[deviceIntervalKey]) {
            energyByHalfHour[deviceIntervalKey] = {
                deviceName: reading.deviceName,
                timestamp: formattedTimestamp,
                energyConsumed: 0
            };
        }
        energyByHalfHour[deviceIntervalKey].energyConsumed += energyConsumed;
    }
});

// Debugging: Log the keys being processed
node.warn(`Aggregated keys: ${Object.keys(energyByHalfHour)}`);

// Prepare the SQL MERGE statements for half-hourly energy consumption
let mergeStatements = Object.values(energyByHalfHour).map(entry => {
    return `MERGE INTO [iot_data].[dbo].[energy_data] AS target
    USING (SELECT '${entry.deviceName}' AS DeviceName, '${entry.timestamp}' AS Timestamp, ${entry.energyConsumed} AS EnergyConsumed) AS source
    ON (target.DeviceName = source.DeviceName AND target.Timestamp = source.Timestamp)
    WHEN MATCHED THEN 
        UPDATE SET target.EnergyConsumed = source.EnergyConsumed
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (DeviceName, Timestamp, EnergyConsumed)
        VALUES (source.DeviceName, source.Timestamp, source.EnergyConsumed);`;
}).join(" ");

// Combine all MERGE statements into one string and wrap in a transaction
let combinedSQL = `BEGIN TRANSACTION; ${mergeStatements} COMMIT;`;

msg.payload = combinedSQL;
return msg; // Return the message to be used by the next node
