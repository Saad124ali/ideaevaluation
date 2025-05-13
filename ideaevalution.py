import logging
import re
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from io import BytesIO
from docx import Document

app = FastAPI(title="Business Document Analyzer")
logging.basicConfig(level=logging.INFO)

class AnalysisResponse(BaseModel):
    filename: str
    summary: str = "No summary available"
    key_findings: List[str] = ["No key findings identified"]
    scalability_analysis: Dict[str, Any] = {
        "score": 0,
        "rating": "Not assessed",
        "architecture_score": 0,
        "growth_potential": 0,
        "automation_level": 0,
        "identified_limitations": 0
    }
    market_validation: Dict[str, Any] = {
        "existing_usage": False,
        "competitors": [],
        "differentiators": 0,
        "case_studies": False
    }
    feasibility_issues: List[str] = ["No feasibility issues detected"]
    recommendations: List[str] = ["No specific recommendations"]
    viability_score: int = 0
    viability_status: str = "Not assessed"

def safe_extract_text(file: UploadFile) -> str:
    try:
        if not file.filename.lower().endswith('.docx'):
            raise ValueError("Only .docx files are supported")
        doc = Document(BytesIO(file.file.read()))
        paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs) if paragraphs else "Document appears to be empty"
    except Exception as e:
        logging.error(f"Text extraction error: {str(e)}")
        return f"Text extraction failed: {str(e)}"

def robust_summary(text: str) -> str:
    try:
        if not text or text.startswith("Text extraction failed"):
            return "No content available for summary"
        sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
        return ". ".join(sentences[:3]) + ("." if sentences else "")
    except Exception:
        return "Summary generation failed"

def compute_viability_score(analysis: dict) -> tuple[int, str]:
    score = 0
    score += analysis["scalability"]["score"] * 10
    score += analysis["market"]["differentiators"] * 5
    if analysis["market"]["existing_usage"]:
        score += 10
    if not analysis["feasibility"] or "No major feasibility issues detected" in analysis["feasibility"]:
        score += 10

    status = (
        "Strong" if score >= 80 else
        "Promising" if score >= 60 else
        "Needs Improvement"
    )
    return score, status

def analyze_content(text: str) -> dict:
    if not text or text.startswith("Text extraction failed"):
        return {
            "summary": "No content available for analysis",
            "key_findings": ["Document could not be processed"],
            "scalability": {
                "score": 0,
                "rating": "Not assessed",
                "details": {
                    "architecture": 0,
                    "growth": 0,
                    "automation": 0,
                    "limitations": 0
                }
            },
            "market": {
                "existing_usage": False,
                "competitors": [],
                "differentiators": 0,
                "case_studies": False
            },
            "feasibility": ["Analysis unavailable"],
            "recommendations": ["Upload a valid DOCX file"]
        }

    text_lower = text.lower()

    # Scalability
    scalability_keywords = {
        "architecture": ["microservices", "kubernetes", "serverless"],
        "growth": ["expand", "global", "scale"],
        "automation": ["CI/CD", "terraform", "ansible"],
        "limitations": ["bottleneck", "constraint", "limit"]
    }

    scalability_scores = {
        category: sum(text_lower.count(keyword) for keyword in keywords)
        for category, keywords in scalability_keywords.items()
    }

    total_scalability = sum(scalability_scores.values())
    scalability_rating = (
        "High" if total_scalability > 5 else
        "Medium" if total_scalability > 2 else
        "Low"
    )

    # Market validation
    competitors = list(set(
        m.group(1) for m in re.finditer(
            r"(?:similar to|like|competitors?|alternatives?)\s([A-Z]\w+)",
            text, re.IGNORECASE
        )
    ))

    market_validation = {
        "existing_usage": bool(re.search(
            r"(used by|deployed at|implemented with|customers include)",
            text_lower
        )),
        "competitors": competitors[:3],
        "differentiators": len(re.findall(
            r"(unique|different|only|exclusive)\s",
            text_lower
        )),
        "case_studies": bool(re.search(
            r"(case study|success story|testimonial)",
            text_lower
        ))
    }

    # Feasibility
    feasibility_issues = []
    if 'financial' in text_lower and not re.search(r'\$\d+', text):
        feasibility_issues.append("Missing specific financial numbers")
    if 'market' in text_lower and not ('research' in text_lower or 'analysis' in text_lower):
        feasibility_issues.append("Missing market research/analysis")
    if not feasibility_issues:
        feasibility_issues.append("No major feasibility issues detected")

    # Recommendations
    recommendations = []
    if 'scale' in text_lower and not ('test' in text_lower or 'load' in text_lower):
        recommendations.append("Add load testing documentation")
    if 'competitor' in text_lower and not ('compare' in text_lower or 'differentiat' in text_lower):
        recommendations.append("Include competitor comparison")
    if not recommendations:
        recommendations.append("Document appears comprehensive")

    return {
        "summary": robust_summary(text),
        "key_findings": [
            "Contains business content",
            f"Found {len(competitors)} competitors",
            f"Found {market_validation['differentiators']} differentiators"
        ],
        "scalability": {
            "score": total_scalability,
            "rating": scalability_rating,
            "details": scalability_scores
        },
        "market": market_validation,
        "feasibility": feasibility_issues,
        "recommendations": recommendations
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    try:
        text = safe_extract_text(file)
        analysis = analyze_content(text)
        viability_score, viability_status = compute_viability_score(analysis)

        return AnalysisResponse(
            filename=file.filename,
            summary=analysis["summary"],
            key_findings=analysis["key_findings"],
            scalability_analysis={
                "score": analysis["scalability"]["score"],
                "rating": analysis["scalability"]["rating"],
                "architecture_score": analysis["scalability"]["details"]["architecture"],
                "growth_potential": analysis["scalability"]["details"]["growth"],
                "automation_level": analysis["scalability"]["details"]["automation"],
                "identified_limitations": analysis["scalability"]["details"]["limitations"]
            },
            market_validation={
                "existing_usage": analysis["market"]["existing_usage"],
                "competitors": analysis["market"]["competitors"],
                "differentiators": analysis["market"]["differentiators"],
                "case_studies": analysis["market"]["case_studies"]
            },
            feasibility_issues=analysis["feasibility"],
            recommendations=analysis["recommendations"],
            viability_score=viability_score,
            viability_status=viability_status
        )
    except Exception as e:
        logging.error(f"Analysis failed completely: {str(e)}", exc_info=True)
        return AnalysisResponse(
            filename=file.filename,
            summary=f"Analysis failed: {str(e)}",
            key_findings=["Complete analysis failure"],
            feasibility_issues=["System error occurred"],
            recommendations=["Contact support"]
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
