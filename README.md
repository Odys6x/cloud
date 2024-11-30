# Development Environment Setup Guide

## Prerequisites
- GitHub account
- League of Legends account
- PowerShell with administrator privileges
- Python IDE

## Installation Steps

### 1. Initial Setup
1. Clone the GitHub repository:
   
shell

bash
   git clone <repository-url>
   

2. Download and install League of Legends from the official website
   
3. Install all required packages from the repository:
   
shell

bash
   pip install -r requirements.txt
   

### 2. Chocolatey Installation
1. Open PowerShell as administrator and run:
   
powershell

powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   

### 3. Ngrok Setup
1. Install Ngrok using Chocolatey:
   
powershell

bash
   choco install ngrok
   

2. Configure Ngrok:
   - Sign up for a ngrok account at https://ngrok.com
   - Retrieve your authentication token from the ngrok dashboard
   - Configure the auth token:
     
bash
     ngrok config add-authtoken <your-auth-token>
     
   - Add ngrok to your system's PATH environment variables

### 4. Application Setup
1. Launch League of Legends

2. Execute the Send.py script in your IDE

3. Open a new terminal and start ngrok:
   
bash
   ngrok http 5000
   
   This will generate a URL like: https://abcd-123-456-789-12.ngrok-free.app

4. Update the app.py file with your new ngrok URL

### 5. Deployment
1. Push your changes to GitHub:
   
shell

bash
   git add .
   git commit -m "Updated ngrok URL"
   git push
   

2. Access your cloud service dashboard to view the data

## Troubleshooting
- Ensure all services are running before starting the application
- Verify your ngrok authentication token is correctly configured
- Check that League of Legends is properly installed and running
