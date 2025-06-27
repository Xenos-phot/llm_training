# Google Sheets Setup Guide

This guide will help you set up Google Sheets API access to automatically populate your TestData spreadsheet with Amazon product details.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console
3. The TestData spreadsheet shared with the service account (or made public)

## Setup Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it
   - Search for "Google Drive API" and enable it

### Step 3: Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Give it a name (e.g., "sheets-populator")
4. Click "Create and Continue"
5. Skip role assignment for now and click "Continue"
6. Click "Done"

### Step 4: Create Service Account Key

1. In the Credentials page, click on your service account email
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Download the JSON file and save it as `credentials.json` in your project root

### Step 5: Share Your Spreadsheet

1. Open your Google Spreadsheet "TestData"
2. Click the "Share" button
3. Add the service account email (found in the credentials.json file) as an editor
4. OR make the spreadsheet publicly viewable/editable

### Step 6: Set Environment Variable

Create a `.env` file in your project root and add:

```
GOOGLE_CREDENTIALS_FILE=./credentials.json
```

## Usage

### Method 1: Using the Script Directly

```bash
cd testing_data
python google_sheets_populator.py
```

### Method 2: Using as a Module

```python
from testing_data.google_sheets_populator import GoogleSheetsPopulator

# Initialize with your spreadsheet name
populator = GoogleSheetsPopulator(spreadsheet_name="TestData")

# Process all URLs
populator.process_all_urls(delay_seconds=2.0)
```

## Expected Spreadsheet Format

Your Google Spreadsheet should have the following columns:

| Index | amazon_url | product_name | product_description | product_price | product_image |
|-------|------------|--------------|---------------------|---------------|---------------|
| 1     | https://... | (will be filled) | (will be filled) | (will be filled) | (will be filled) |

## Features

- **Automatic Product Detection**: Reads Amazon URLs from the spreadsheet
- **Batch Processing**: Processes all URLs in the spreadsheet
- **Image Display**: Uses Google Sheets IMAGE() formula to display product images
- **Rate Limiting**: Configurable delay between requests to avoid rate limiting
- **Error Handling**: Continues processing even if some URLs fail
- **Progress Tracking**: Shows progress as it processes each URL

## Troubleshooting

### Authentication Issues
- Ensure the credentials.json file path is correct
- Check that the service account has access to the spreadsheet
- Verify that both Google Sheets API and Google Drive API are enabled

### Spreadsheet Access Issues
- Make sure the spreadsheet name matches exactly
- Ensure the service account email has edit access to the spreadsheet
- Check that the spreadsheet has the expected column headers

### Rate Limiting
- If you get rate limiting errors, increase the delay_seconds parameter
- Amazon may block requests if too many are made too quickly

## Security Notes

- Keep your credentials.json file secure and never commit it to version control
- Add `credentials.json` to your `.gitignore` file
- Consider using environment variables for production deployments 