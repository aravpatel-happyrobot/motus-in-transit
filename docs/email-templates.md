# Email Templates - Motus In-Transit

Two email templates for post-call follow-ups.

---

## Template A: Checkin Call (3-4 Hours Before Delivery)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Motus Freight - Load Update</title>
  <style type="text/css">
    body {
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .email-container {
      max-width: 560px;
      margin: 0 auto;
    }
    @media only screen and (max-width: 600px) {
      .email-container {
        width: 100% !important;
      }
      .content-padding {
        padding: 30px 20px !important;
      }
    }
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5;">

  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
    <tr>
      <td style="padding: 40px 15px;">

        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="560" class="email-container" style="margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="padding: 35px 40px 25px 40px; background-color: #1a1a1a; border-radius: 8px 8px 0 0;" class="content-padding">
              <img src="{Logo_URL}" alt="Motus Freight" width="180" style="display: block; max-width: 180px; height: auto;">
            </td>
          </tr>

          <!-- Content -->
          <tr>
            <td style="padding: 35px 40px 40px 40px;" class="content-padding">

              <!-- Call Type Badge -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 24px;">
                <tr>
                  <td>
                    <span style="display: inline-block; padding: 6px 12px; background-color: #e8f4fd; color: #1a73e8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-radius: 4px;">Check-In Call</span>
                  </td>
                </tr>
              </table>

              <!-- Load # -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Load #</p>
                    <p style="margin: 0; font-size: 22px; font-weight: 600; color: #1a1a1a;">{Load_Number}</p>
                  </td>
                </tr>
              </table>

              <!-- Lane -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Lane</p>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Origin_City}, {Origin_State} → {Destination_City}, {Destination_State}</p>
                  </td>
                </tr>
              </table>

              <!-- Current Location -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Current Location</p>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Current_Location}</p>
                  </td>
                </tr>
              </table>

              <!-- ETA Status -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">ETA Status</p>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{ETA_Status}</p>
                  </td>
                </tr>
              </table>

              <!-- Reefer Temperature (if applicable) -->
              {Reefer_Temp_Section}

              <!-- Summary -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Summary</p>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Summary}</p>
                  </td>
                </tr>
              </table>

              <!-- Issues (if any) -->
              {Issues_Section}

              <!-- Driver Information -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 14px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Driver Information</p>
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #fafafa; border-radius: 6px;">
                      <tr>
                        <td style="padding: 16px;">
                          <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #999;">Driver Name</p>
                          <p style="margin: 0 0 14px 0; font-size: 15px; color: #333;">{Driver_Name}</p>

                          <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #999;">Driver Phone</p>
                          <p style="margin: 0; font-size: 15px; color: #333;">{Driver_Phone}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Timestamp -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                  <td>
                    <p style="margin: 0; font-size: 12px; color: #999;">Call completed: {Call_Timestamp}</p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

</body>
</html>
```

### Checkin Email Parameters

| Parameter | Description |
|-----------|-------------|
| `{Logo_URL}` | Motus Freight logo URL |
| `{Load_Number}` | Load number (e.g., M290494) |
| `{Origin_City}` | Pickup city |
| `{Origin_State}` | Pickup state |
| `{Destination_City}` | Delivery city |
| `{Destination_State}` | Delivery state |
| `{Current_Location}` | Driver's reported location (e.g., "Indianapolis, IN") |
| `{ETA_Status}` | "On time for delivery" or "Running late - ETA: 10:00 PM" |
| `{Reefer_Temp_Section}` | HTML block for reefer temp (or empty if not reefer) |
| `{Summary}` | Brief call summary |
| `{Issues_Section}` | HTML block for issues (or empty if none) |
| `{Driver_Name}` | Driver's name |
| `{Driver_Phone}` | Driver's phone number |
| `{Call_Timestamp}` | When the call was completed |

### Reefer Temp Section (include if reefer load)

```html
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
  <tr>
    <td>
      <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Reefer Temperature</p>
      <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Reefer_Temp}°F</p>
    </td>
  </tr>
</table>
```

### Issues Section (include if issues reported)

```html
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
  <tr>
    <td>
      <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Issues Reported</p>
      <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #d93025;">{Issues}</p>
    </td>
  </tr>
</table>
```

---

## Template B: Final Call (0-30 Minutes Before Delivery)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Motus Freight - Delivery Update</title>
  <style type="text/css">
    body {
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .email-container {
      max-width: 560px;
      margin: 0 auto;
    }
    @media only screen and (max-width: 600px) {
      .email-container {
        width: 100% !important;
      }
      .content-padding {
        padding: 30px 20px !important;
      }
    }
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5;">

  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
    <tr>
      <td style="padding: 40px 15px;">

        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="560" class="email-container" style="margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="padding: 35px 40px 25px 40px; background-color: #1a1a1a; border-radius: 8px 8px 0 0;" class="content-padding">
              <img src="{Logo_URL}" alt="Motus Freight" width="180" style="display: block; max-width: 180px; height: auto;">
            </td>
          </tr>

          <!-- Content -->
          <tr>
            <td style="padding: 35px 40px 40px 40px;" class="content-padding">

              <!-- Call Type Badge -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 24px;">
                <tr>
                  <td>
                    <span style="display: inline-block; padding: 6px 12px; background-color: #e6f4ea; color: #1e8e3e; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-radius: 4px;">Final Delivery Check</span>
                  </td>
                </tr>
              </table>

              <!-- Load # -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Load #</p>
                    <p style="margin: 0; font-size: 22px; font-weight: 600; color: #1a1a1a;">{Load_Number}</p>
                  </td>
                </tr>
              </table>

              <!-- Delivery Location -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Delivering To</p>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Destination_City}, {Destination_State}</p>
                  </td>
                </tr>
              </table>

              <!-- Arrival Status -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Arrival Status</p>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Arrival_Status}</p>
                  </td>
                </tr>
              </table>

              <!-- Check-in Time (if at facility) -->
              {Checkin_Time_Section}

              <!-- Reefer Temperature (if applicable) -->
              {Reefer_Temp_Section}

              <!-- Issues (if any) -->
              {Issues_Section}

              <!-- Driver Information -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 14px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Driver Information</p>
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #fafafa; border-radius: 6px;">
                      <tr>
                        <td style="padding: 16px;">
                          <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #999;">Driver Name</p>
                          <p style="margin: 0 0 14px 0; font-size: 15px; color: #333;">{Driver_Name}</p>

                          <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #999;">Driver Phone</p>
                          <p style="margin: 0; font-size: 15px; color: #333;">{Driver_Phone}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Timestamp -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                  <td>
                    <p style="margin: 0; font-size: 12px; color: #999;">Call completed: {Call_Timestamp}</p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

</body>
</html>
```

### Final Email Parameters

| Parameter | Description |
|-----------|-------------|
| `{Logo_URL}` | Motus Freight logo URL |
| `{Load_Number}` | Load number (e.g., M290494) |
| `{Destination_City}` | Delivery city |
| `{Destination_State}` | Delivery state |
| `{Arrival_Status}` | "At facility", "10 minutes out", or "ETA: 2:30 PM" |
| `{Checkin_Time_Section}` | HTML block for check-in time (or empty if not at facility) |
| `{Reefer_Temp_Section}` | HTML block for reefer temp (or empty if not reefer) |
| `{Issues_Section}` | HTML block for issues (or empty if none) |
| `{Driver_Name}` | Driver's name |
| `{Driver_Phone}` | Driver's phone number |
| `{Call_Timestamp}` | When the call was completed |

### Check-in Time Section (include if driver checked in)

```html
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
  <tr>
    <td>
      <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Facility Check-In</p>
      <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Checkin_Time}</p>
    </td>
  </tr>
</table>
```

### Reefer Temp Section (include if reefer load)

```html
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
  <tr>
    <td>
      <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Reefer Temperature</p>
      <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">{Reefer_Temp}°F</p>
    </td>
  </tr>
</table>
```

### Issues Section (include if issues reported)

```html
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 28px;">
  <tr>
    <td>
      <p style="margin: 0 0 6px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888;">Issues Reported</p>
      <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #d93025;">{Issues}</p>
    </td>
  </tr>
</table>
```

---

## Key Differences

| Element | Checkin (3-4h) | Final (0-30min) |
|---------|----------------|-----------------|
| **Badge Color** | Blue (#1a73e8) | Green (#1e8e3e) |
| **Badge Text** | "Check-In Call" | "Final Delivery Check" |
| **Lane Info** | Full origin → destination | Just destination |
| **Location** | Current location field | Arrival status field |
| **ETA** | ETA status (on time/late) | Check-in time if at facility |
