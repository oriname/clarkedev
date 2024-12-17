// Constants for the energy calculation
const voltage = 200; // Voltage in volts
const powerFactor = 0.8; // Power factor, dimensionless

// Helper function to calculate energy in kilowatt-hours
function calculateEnergy(current, voltage, powerFactor, timeIntervalHours) {
    return (current * voltage * powerFactor * timeIntervalHours) / 1000;
}

// Adjusted helper function to round timestamp to the end of the nearest hour interval
function roundUpToNearestHour(timestamp) {
    let adjustedTimestamp = new Date(timestamp);
    if (adjustedTimestamp.getMinutes() > 0 || adjustedTimestamp.getSeconds() > 0) {
        adjustedTimestamp.setHours(adjustedTimestamp.getHours() + 1);
    }
    adjustedTimestamp.setMinutes(0);
    adjustedTimestamp.setSeconds(0);
    adjustedTimestamp.setMilliseconds(0);
    return adjustedTimestamp;
}

// Ensure msg.payload is an array of readings
const readings = Array.isArray(msg.payload) ? msg.payload : [msg.payload];

// Object to accumulate energy consumption by device and hour
let energyByHour = {};

// Debugging: Log the number of readings being processed
node.warn(`Processing ${readings.length} readings`);

// Process each reading for hourly intervals
readings.forEach(reading => {
    let timestamp = new Date(reading.timestamp);
    let roundedTimestamp = roundUpToNearestHour(timestamp);
    let formattedTimestamp = `${roundedTimestamp.getFullYear()}-${String(roundedTimestamp.getMonth() + 1).padStart(2, '0')}-${String(roundedTimestamp.getDate()).padStart(2, '0')} ${String(roundedTimestamp.getHours()).padStart(2, '0')}:00:00`;

    const current1 = parseFloat(reading.channel1);
    const current2 = parseFloat(reading.channel2);
    const current3 = parseFloat(reading.channel3);
    
    if (!isNaN(current1) && !isNaN(current2) && !isNaN(current3)) {
        const totalCurrent = current1 + current2 + current3;
        // Use 1 hour as the time interval for hourly energy consumption calculation
        const energyConsumed = calculateEnergy(totalCurrent, voltage, powerFactor, 1);
        const deviceHourKey = `${reading.deviceName}_${formattedTimestamp}`;

        if (!energyByHour[deviceHourKey]) {
            energyByHour[deviceHourKey] = {
                deviceName: reading.deviceName,
                timestamp: formattedTimestamp,
                energyConsumed: 0
            };
        }
        energyByHour[deviceHourKey].energyConsumed += energyConsumed;
    }
});

// Debugging: Log the keys being processed
node.warn(`Aggregated keys: ${Object.keys(energyByHour)}`);

// Prepare the SQL insert statements for hourly energy consumption
let insertSQL = "";
Object.values(energyByHour).forEach(entry => {
    insertSQL += `INSERT INTO [iot_test].[dbo].[consumption] (DeviceName, Timestamp, EnergyConsumed) VALUES ('${entry.deviceName}', '${entry.timestamp}', ${entry.energyConsumed}); `;
});

msg.payload = insertSQL;

return msg; // Return the message to be used by the next node
