from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import tempfile
from datetime import datetime
import asyncio
from typing import Optional
import resend
import base64

app = FastAPI(title="SNAK Scorecard API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}

# Resend configuration - USES ENVIRONMENT VARIABLES
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "re_your-fallback-key")  # Set in Railway
resend.api_key = RESEND_API_KEY

EMAIL_CONFIG = {
    "from_email": os.getenv("FROM_EMAIL", "SNAK Scorecard <noreply@yourdomain.com>"),
    "to_email": os.getenv("TO_EMAIL", "contact@snak.vc")
}

async def send_email_with_attachment(
    company_name: str, 
    user_email: str, 
    file_content: bytes, 
    filename: str
) -> bool:
    """Send email using Resend"""
    try:
        print(f"📧 Sending email via Resend...")
        print(f"   Company: {company_name}")
        print(f"   User Email: {user_email}")
        print(f"   File: {filename}")
        
        # Create email content
        subject = f"{company_name} + SNAK Scorecard Request"
        
        html_content = f"""
        <h2>🎯 New SNAK Scorecard Analysis Request</h2>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>📋 Submission Details:</h3>
            <p><strong>Company Name:</strong> {company_name}</p>
            <p><strong>Contact Email:</strong> {user_email}</p>
            <p><strong>Submission Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>File Name:</strong> {filename}</p>
            <p><strong>File Size:</strong> {len(file_content) / 1024 / 1024:.2f} MB</p>
        </div>
        
        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3>📊 Required Excel Fields:</h3>
            <ul>
                <li><strong>buyer_id</strong> - Unique identifier for buyers</li>
                <li><strong>seller_id</strong> - Unique identifier for sellers</li>
                <li><strong>purchase_date</strong> - Date of transaction</li>
                <li><strong>net_revenue</strong> - Revenue amount</li>
            </ul>
        </div>
        
        <p>Please find the attached Excel file for scorecard analysis.</p>
        
        <hr style="margin: 30px 0;">
        <p style="color: #666; font-size: 14px;">
            <em>Best regards,<br>
            SNAK Scorecard System</em>
        </p>
        """
        
        # Encode file for attachment
        encoded_file = base64.b64encode(file_content).decode()
        
        # Send email using Resend
        email_response = resend.Emails.send({
            "from": EMAIL_CONFIG["from_email"],
            "to": [EMAIL_CONFIG["to_email"]],
            "subject": subject,
            "html": html_content,
            "attachments": [{
                "filename": filename,
                "content": encoded_file
            }]
        })
        
        print(f"✅ Resend email sent successfully!")
        print(f"   Email ID: {email_response.get('id', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Resend email error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

def validate_file(file: UploadFile) -> Optional[str]:
    """Validate uploaded file"""
    if not file.filename:
        return "No file selected"
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return "Invalid file type. Please upload .xlsx or .xls files only"
    
    return None

@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file"""
    return FileResponse("index.html")

@app.get("/api")
async def root():
    """API info endpoint"""
    return {"message": "SNAK Scorecard API is running"}

@app.post("/submit-scorecard")
async def submit_scorecard(
    companyName: str = Form(...),
    email: str = Form(...),
    excelFile: UploadFile = File(...)
):
    """Submit scorecard analysis request"""
    try:
        # Validate inputs
        if not companyName.strip():
            raise HTTPException(status_code=400, detail="Company name is required")
        
        if not email.strip():
            raise HTTPException(status_code=400, detail="Email address is required")
        
        # Validate file
        file_error = validate_file(excelFile)
        if file_error:
            raise HTTPException(status_code=400, detail=file_error)
        
        # Read file content
        file_content = await excelFile.read()
        
        # Check file size
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )
        
        # Send email
        success = await send_email_with_attachment(
            companyName.strip(),
            email.strip(),
            file_content,
            excelFile.filename
        )
        
        if success:
            return JSONResponse(
                content={"message": "Scorecard request submitted successfully!"}, 
                status_code=200
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to send email. Please try again later."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SNAK Scorecard API...")
    print("📧 Email service: Resend")
    print("🌐 Access your app at: http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)