// Constants for the energy calculation
const voltage = 200; // Voltage in volts
//const powerFactor = 0.8; // Power factor, dimensionless

// Helper function to calculate energy in kilowatt-hours
function calculateEnergy(current, voltage, timeIntervalHours) {
    return (current * voltage * timeIntervalHours) / 1000;
}

// Adjusted Timestamp Rounding Logic
function adjustRoundingBasedOnDataTimestamp(timestamp) {
    const adjustedTimestamp = new Date(timestamp);
    // Always round up to the end of the current half-hour interval
    if (adjustedTimestamp.getMinutes() < 30) {
        adjustedTimestamp.setMinutes(30); // This will set it to the end of the first half-hour
    } else {
        adjustedTimestamp.setHours(adjustedTimestamp.getHours() + 1); // Move to the next hour
        adjustedTimestamp.setMinutes(0); // Set minutes to 00 to indicate the end of the second half-hour
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
    let roundedTimestamp = adjustRoundingBasedOnDataTimestamp(timestamp); // Corrected function name
    let formattedTimestamp = `${roundedTimestamp.getFullYear()}-${String(roundedTimestamp.getMonth() + 1).padStart(2, '0')}-${String(roundedTimestamp.getDate()).padStart(2, '0')} ${String(roundedTimestamp.getHours()).padStart(2, '0')}:${String(roundedTimestamp.getMinutes()).padStart(2, '0')}:00`;

    const current1 = parseFloat(reading.channel1);
    const current2 = parseFloat(reading.channel2);
    const current3 = parseFloat(reading.channel3);
    
    if (!isNaN(current1) && !isNaN(current2) && !isNaN(current3)) {
        const totalCurrent = current1 + current2 + current3;
        // Use 0.5 hours as the time interval for 30-minute energy consumption calculation
        const energyConsumed = calculateEnergy(totalCurrent, voltage, 0.5);
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

// Prepare the SQL insert statements for half-hourly energy consumption
let insertSQL = "BEGIN TRANSACTION; ";

Object.values(energyByHalfHour).forEach(entry => {
    insertSQL += `INSERT INTO [iot_data].[dbo].[energy_data] (DeviceName, Timestamp, EnergyConsumed) VALUES ('${entry.deviceName}', '${entry.timestamp}', ${entry.energyConsumed}); `;
});

insertSQL += " COMMIT;";


msg.payload = insertSQL;

return msg; // Return the message to be used by the next node