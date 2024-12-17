// Constants for the energy calculation
const voltage = 200; // Voltage in volts
const powerFactor = 0.8; // Power factor, dimensionless

// Helper function to calculate energy in kilowatt-hours
function calculateEnergy(current, voltage, powerFactor, timeIntervalHours) {
    return (current * voltage * powerFactor * timeIntervalHours) / 1000;
}

// Adjusted helper function to correctly handle rounding based on current time
function adjustRoundingBasedOnCurrentTime(timestamp) {
    const now = new Date();
    const adjustedTimestamp = new Date(timestamp);
    const halfHourInMilliseconds = 1800000; // 30 minutes in milliseconds

    // Check if the current time is past the next half-hour mark
    if (now - adjustedTimestamp >= halfHourInMilliseconds || now.getMinutes() < 30 && adjustedTimestamp.getMinutes() >= 30 || now.getMinutes() >= 30 && adjustedTimestamp.getMinutes() < 30) {
        // If true, round up to the next half-hour
        if (adjustedTimestamp.getMinutes() < 30) {
            adjustedTimestamp.setMinutes(30);
        } else {
            adjustedTimestamp.setHours(adjustedTimestamp.getHours() + 1);
            adjustedTimestamp.setMinutes(0);
        }
    } else {
        // If false, round down to the start of the current half-hour
        if (adjustedTimestamp.getMinutes() < 30) {
            adjustedTimestamp.setMinutes(0);
        } else {
            adjustedTimestamp.setMinutes(30);
        }
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
    let roundedTimestamp = adjustRoundingBasedOnCurrentTime(timestamp);
    let formattedTimestamp = `${roundedTimestamp.getFullYear()}-${String(roundedTimestamp.getMonth() + 1).padStart(2, '0')}-${String(roundedTimestamp.getDate()).padStart(2, '0')} ${String(roundedTimestamp.getHours()).padStart(2, '0')}:${String(roundedTimestamp.getMinutes()).padStart(2, '0')}:00`;

    const current1 = parseFloat(reading.channel1);
    const current2 = parseFloat(reading.channel2);
    const current3 = parseFloat(reading.channel3);
    
    if (!isNaN(current1) && !isNaN(current2) && !isNaN(current3)) {
        const totalCurrent = current1 + current2 + current3;
        // Use 0.5 hours as the time interval for 30-minute energy consumption calculation
        const energyConsumed = calculateEnergy(totalCurrent, voltage, powerFactor, 0.5);
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
let insertSQL = "";
Object.values(energyByHalfHour).forEach(entry => {
    insertSQL += `INSERT INTO [iot_test].[dbo].[consumption] (DeviceName, Timestamp, EnergyConsumed) VALUES ('${entry.deviceName}', '${entry.timestamp}', ${entry.energyConsumed}); `;
});

msg.payload = insertSQL;

return msg; // Return the message to be used by the next node