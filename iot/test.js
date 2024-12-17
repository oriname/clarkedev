// Constants for the energy calculation
const voltage = 200; // Voltage in volts

// Helper function to calculate energy in kilowatt-hours
function calculateEnergy(current, voltage, timeIntervalHours) {
    return (current * voltage * timeIntervalHours) / 1000;
}

// Ensure msg.payload is an array of readings
const readings = Array.isArray(msg.payload) ? msg.payload : [msg.payload];

// Object to accumulate energy consumption by 30-minute intervals
let energyByInterval = {};

readings.forEach((reading, index) => {
    const current1 = parseFloat(reading.channel1);
    const current2 = parseFloat(reading.channel2);
    const current3 = parseFloat(reading.channel3);
    
    // Only process if all currents are numbers
    if (!isNaN(current1) && !isNaN(current2) && !isNaN(current3)) {
        let timestamp = new Date(reading.timestamp);
        
        // Create a 30 minute interval key for the reading
        let intervalKey = new Date(timestamp);
        intervalKey.setMinutes(intervalKey.getMinutes() - (intervalKey.getMinutes() % 30), 0, 0); // Seconds and milliseconds to 0
        let intervalKeyString = intervalKey.toISOString();

        // Initialize the interval in the energyByInterval object if it doesn't exist
        if (!energyByInterval[intervalKeyString]) {
            energyByInterval[intervalKeyString] = { energy: 0, deviceName: reading.deviceName /* Assuming deviceName is part of the reading */ };
        }

        let timeIntervalHours = 0.5; // Default to 30 minutes
        if (index < readings.length - 1) {
            const nextTimestamp = new Date(readings[index + 1].timestamp);
            if (nextTimestamp < new Date(intervalKeyString).getTime() + (30 * 60 * 1000)) {
                timeIntervalHours = (nextTimestamp - timestamp) / (1000 * 60 * 60);
            }
        }

        energyByInterval[intervalKeyString].energy += calculateEnergy(current1, voltage, timeIntervalHours);
        energyByInterval[intervalKeyString].energy += calculateEnergy(current2, voltage, timeIntervalHours);
        energyByInterval[intervalKeyString].energy += calculateEnergy(current3, voltage, timeIntervalHours);
    }
});

// Debugging: Log the keys being processed
//node.warn(`Aggregated keys: ${Object.keys(energyByInterval)}`);

let mergeStatements = Object.keys(energyByInterval).map(key => {
    const entry = energyByInterval[key];
    // Extract the date and time from the interval key
    let intervalDate = new Date(key);
    let formattedTimestamp = `${intervalDate.getFullYear()}-${String(intervalDate.getMonth() + 1).padStart(2, '0')}-${String(intervalDate.getDate()).padStart(2, '0')} ${String(intervalDate.getHours()).padStart(2, '0')}:${String(intervalDate.getMinutes()).padStart(2, '0')}:00`;

    return `MERGE INTO [iot_data].[dbo].[consumption] AS target
    USING (SELECT '${entry.deviceName}' AS DeviceName, '${formattedTimestamp}' AS Timestamp, ${entry.energy} AS EnergyConsumed) AS source
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
return msg;
