# Windows Setup Guide

This guide explains the detailed setup procedures for using Photoshop MCP Server in a Windows environment.

## Prerequisites

- Windows 10/11
- Python 3.11 or higher
- Adobe Photoshop 2023 or higher

## 1. PowerShell Configuration

### Changing Execution Policy

To run PowerShell scripts, you need to change the execution policy:

1. Open PowerShell with administrator privileges
2. Run the following command:
   ```powershell
   Set-ExecutionPolicy RemoteSigned
   ```
3. Enter "Y" to confirm

### Verifying Script Execution

Run the following command to verify that scripts can be executed:

```powershell
Write-Output "Hello, World!"
```

## 2. Photoshop Configuration

### Enabling COM Automation

1. Launch Photoshop
2. Edit > Preferences > Plugins
3. Check "Allow Legacy Scripts to Run"
4. Restart Photoshop

### Security Settings

1. Windows Security > App & Browser Control
2. Check "SmartScreen" settings
3. Allow PowerShell script execution if necessary

## 3. Installing Dependencies

### Installing pywin32

```bash
pip install pywin32
```

### Other Dependencies

```bash
pip install -r requirements.txt
```

## 4. Starting the Server

### Using PowerShell Backend

```bash
photoshop-mcp-server start --bridge-mode powershell
```

### Using UXP Backend

```bash
photoshop-mcp-server start --bridge-mode uxp
```

## 5. Path Format Considerations

In Windows environments, escape backslashes (\) or use forward slashes (/) in file paths:

```json
// Correct path format examples
{
  "path": "C:/Users/username/Documents/file.psd"
}

// Or
{
  "path": "C:\\Users\\username\\Documents\\file.psd"
}
```

## Troubleshooting

### COM Object Creation Error

Error message: `Cannot create COM object 'Photoshop.Application'`

Solutions:
1. Ensure Photoshop is running
2. Run PowerShell with administrator privileges
3. Verify that your Photoshop version is 2023 or higher

### Script Execution Error

Error message: `Script execution is disabled on this system`

Solutions:
1. Open PowerShell with administrator privileges
2. Run `Set-ExecutionPolicy RemoteSigned`
3. Enter "Y" to confirm

### Path-Related Errors

Error message: `The specified path cannot be found`

Solutions:
1. Verify that the path is correctly specified in Windows format
2. Escape backslashes (\) or use forward slashes (/)

### Communication Error with Photoshop

Error message: `Failed to communicate with Photoshop`

Solutions:
1. Ensure Photoshop is running
2. Restart Photoshop
3. Verify that COM automation is enabled
4. Run the server with administrator privileges

### UXP Plugin Connection Error

Error message: `Cannot connect to UXP plugin`

Solutions:
1. Verify that the plugin is correctly installed
2. Restart Photoshop
3. Reinstall the plugin
   ```bash
   photoshop-mcp-server package_plugin
   photoshop-mcp-server install_plugin
   ```

## Enabling Detailed Logs

Enabling detailed logs can help diagnose issues:

```bash
photoshop-mcp-server start --bridge-mode powershell --log-level debug
```

Logs are saved in the following location:
```
%USERPROFILE%\.photoshop-mcp-server\logs\
```

## Windows-Specific Features

### Automating Registry Settings

Photoshop MCP Server can automatically configure necessary registry settings:

```bash
photoshop-mcp-server setup_windows
```

This command performs the following settings:
- Sets PowerShell execution policy
- Enables Photoshop COM automation
- Adds necessary security exceptions

### Batch Processing Optimization

In Windows environments, there are settings to optimize batch processing performance:

```bash
photoshop-mcp-server start --bridge-mode powershell --win-optimize-batch
```

This setting improves performance when processing multiple files.

## Advanced Configuration

### Installing as a Service

In Windows environments, you can install Photoshop MCP Server as a service:

```bash
photoshop-mcp-server install_service
```

This will automatically start the server when the system boots.

### Firewall Settings

If you need to access from external sources, you need to open ports in the Windows Firewall:

1. Control Panel > System and Security > Windows Defender Firewall
2. Click "Advanced settings"
3. Select "Inbound Rules" and click "New Rule"
4. Select "Port" and click "Next"
5. Select "TCP" and enter "5001" for "Specific local ports"
6. Select "Allow the connection" and click "Next"
7. Select the network types to apply and click "Next"
8. Enter a name and description, then click "Finish"

## Next Steps

- Check the [Basic Usage](../README.en.md#usage) guide
- Refer to the [API Reference](api_reference.md) (coming soon)
- Try the [Tutorials](tutorials.md) (coming soon)