from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import resend
import base64
import os
import tempfile
from datetime import datetime
import asyncio
from typing import Optional

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
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "re_your-fallback-key")
resend.api_key = RESEND_API_KEY

EMAIL_CONFIG = {
    "from_email": os.getenv("FROM_EMAIL", "SNAK Scorecard <noreply@snak.vc>"),
    "to_email": os.getenv("TO_EMAIL", "contact@snak.vc")
}

async def send_email_with_attachment(
    company_name: str, 
    user_email: str, 
    file_content: bytes, 
    filename: str
) -> bool:
    """Send email using Resend - sends to both SNAK team and submitter"""
    try:
        # EMAIL 1: Send to SNAK team with attachment
        subject_to_snak = f"{company_name} + SNAK Scorecard Request"
        
        html_content_to_snak = f"""
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
        
        # Send email to SNAK team with attachment
        email_to_snak = resend.Emails.send({
            "from": EMAIL_CONFIG["from_email"],
            "to": [EMAIL_CONFIG["to_email"]],
            "subject": subject_to_snak,
            "html": html_content_to_snak,
            "attachments": [{
                "filename": filename,
                "content": encoded_file
            }]
        })
        
        # Small delay between emails
        await asyncio.sleep(1)
        
        # EMAIL 2: Send confirmation to submitter (no attachment)
        subject_to_user = f"✅ SNAK Scorecard Submission Confirmed"
        
        html_content_to_user = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; font-size: 2.5rem; margin: 0; font-weight: 700;">SNAK Machine</h1>
                <p style="color: white; font-size: 1.2rem; margin: 10px 0 0 0; opacity: 0.9;">Scorecard Analysis</p>
            </div>
            
            <div style="background: white; padding: 40px; border-radius: 0 0 10px 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; margin-bottom: 20px;">🎉 Submission Received Successfully!</h2>
                
                <p style="color: #34495e; font-size: 1.1rem; line-height: 1.6;">
                    Hi there <strong>{company_name}</strong> team,
                </p>
                
                <p style="color: #34495e; font-size: 1.1rem; line-height: 1.6;">
                    Great news! We've successfully received your scorecard data submission.
                </p>
                
                    <h3 style="color: #2c3e50;">📋 What happens next:</h3>
                    <ul style="color: #34495e; line-height: 1.8; padding-left: 20px;">
                        <li>🔥 <strong>The SNAK Machine is now running</strong> your analysis</li>
                        <li>📊 Our team will process your data and generate insights</li>
                        <li>📧 <strong>Expect your results within 24 hours</strong></li>
                        <li>🎯 You'll receive a detailed scorecard report via email</li>
                    </ul>
                
                
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 25px 0;">
                    <p style="color: #2d5a27; margin: 0; font-weight: 600;">
                        ✅ <strong>File received:</strong> {filename} ({len(file_content) / 1024 / 1024:.1f} MB)
                    </p>
                </div>
                
                <p style="color: #34495e; font-size: 1rem; line-height: 1.6;">
                    If you have any questions feel free to reach out to us.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 25px; border-radius: 25px; display: inline-block; font-weight: 600;">
                        🚀 Analysis in progress...
                    </div>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 0.9rem; text-align: center; margin: 0;">
                    Best regards,<br>
                    <strong>The SNAK Team</strong><br>
                    
                </p>
            </div>
        </div>
        """
        
        # Send confirmation email to user
        email_to_user = resend.Emails.send({
            "from": EMAIL_CONFIG["from_email"],
            "to": [user_email],
            "subject": subject_to_user,
            "html": html_content_to_user
        })
        
        return True
        
    except Exception as e:
        print(f"Error sending emails: {str(e)}")
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
        
        # Send emails
        success = await send_email_with_attachment(
            companyName.strip(),
            email.strip(),
            file_content,
            excelFile.filename
        )
        
        if success:
            return JSONResponse(
                content={"message": "Scorecard request submitted successfully! Check your email for confirmation."}, 
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
