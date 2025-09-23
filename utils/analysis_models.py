"""Pydantic models for structured image analysis outputs"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from enum import Enum


class ConcernLevel(str, Enum):
    """Humanitarian concern level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EnvironmentType(str, Enum):
    """Type of environment in the image"""
    UNKNOWN = "unknown"
    INDUSTRIAL = "industrial"
    MILITARY = "military"
    EDUCATIONAL = "educational"
    RESIDENTIAL = "residential"
    CONSTRUCTION = "construction"
    AGRICULTURAL = "agricultural"
    COMMERCIAL = "commercial"


class ActivityType(str, Enum):
    """Type of activity observed"""
    UNKNOWN = "unknown"
    CONSTRUCTION = "construction"
    MILITARY = "military"
    EDUCATIONAL = "educational"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    RESIDENTIAL = "residential"
    TRANSPORT = "transport"
    MEETING = "meeting"
    ADMINISTRATIVE = "administrative"
    COMMERCIAL = "commercial"
    RECREATION = "recreation"
    OTHER = "other"


class ImageAnalysisResult(BaseModel):
    """Structured output for image analysis"""

    # Core descriptions
    scene_description: str = Field(
        default="",
        description="Detailed description of what is visible in the image"
    )
    location_assessment: str = Field(
        default="",
        description="Assessment of the location and setting"
    )

    # Environmental classification
    environment_type: str = Field(
        default="unknown",
        description="Type of environment shown"
    )

    # Personnel information
    personnel_count: int = Field(
        default=0,
        ge=0,
        description="Number of people visible in the image"
    )
    personnel_types: List[str] = Field(
        default_factory=list,
        description="Types of personnel observed (workers, supervisors, guards, etc.)"
    )
    uniform_identification: str = Field(
        default="",
        description="Description of any uniforms or identifying clothing"
    )

    # Activity assessment
    activity_type: str = Field(
        default="unknown",
        description="Primary type of activity observed"
    )
    activity_description: str = Field(
        default="",
        description="Detailed description of activities taking place"
    )

    # Humanitarian concerns
    concern_level: str = Field(
        default="low",
        description="Overall humanitarian concern level"
    )
    concern_indicators: List[str] = Field(
        default_factory=list,
        description="Specific indicators of humanitarian concern"
    )

    # Control and supervision
    supervision_present: bool = Field(
        default=False,
        description="Whether supervisors or guards are visible"
    )
    restriction_indicators: List[str] = Field(
        default_factory=list,
        description="Indicators of movement restriction or control"
    )

    # Working conditions (if applicable)
    safety_equipment_present: bool = Field(
        default=False,
        description="Whether safety equipment is visible"
    )
    safety_concerns: List[str] = Field(
        default_factory=list,
        description="Specific safety concerns observed"
    )

    # Living conditions (if applicable)
    living_conditions_visible: bool = Field(
        default=False,
        description="Whether living conditions are visible in the image"
    )
    living_condition_issues: List[str] = Field(
        default_factory=list,
        description="Specific issues with living conditions"
    )

    # Health and welfare
    health_concerns: List[str] = Field(
        default_factory=list,
        description="Visible health or welfare concerns"
    )

    # Metadata
    confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the analysis (0-1)"
    )

    @field_validator('scene_description', 'location_assessment', 'activity_description')
    def non_empty_descriptions(cls, v):
        """Ensure key descriptions are not just whitespace"""
        if v and v.strip():
            return v.strip()
        return ""

    @field_validator('concern_indicators', 'restriction_indicators', 'safety_concerns',
                     'living_condition_issues', 'health_concerns', mode='before')
    def clean_string_lists(cls, v):
        """Clean and filter empty strings from lists"""
        if not v:
            return []
        if isinstance(v, str):
            # Split string into list if needed
            v = [item.strip() for item in v.split(',') if item.strip()]
        return [item for item in v if item and str(item).strip()]

    @field_validator('confidence_score')
    def calculate_confidence(cls, v, info):
        """Calculate confidence based on amount of detail provided"""
        if v > 0:
            return v

        # Auto-calculate based on completeness
        score = 0.3  # Base score
        values = info.data

        # Add points for detailed descriptions
        if values.get('scene_description', ''):
            score += 0.2
        if values.get('activity_description', ''):
            score += 0.15
        if values.get('personnel_count', 0) > 0:
            score += 0.1
        if values.get('concern_indicators', []):
            score += 0.15
        if values.get('concern_level', 'low') != 'low':
            score += 0.1

        return min(0.95, score)


class AnalysisPrompt(BaseModel):
    """Structured prompt for JSON response"""

    prompt: str = Field(
        default="",
        description="The analysis prompt"
    )

    response_format: str = Field(
        default="json",
        description="Expected response format"
    )

    schema_description: str = Field(
        default="",
        description="Description of expected JSON structure"
    )


def create_json_prompt() -> str:
    """Create a prompt that requests JSON formatted response"""
    return """Analyze this image and provide a JSON response with the following structure:

{
    "scene_description": "Detailed description of the scene",
    "location_assessment": "Assessment of the location and setting",
    "environment_type": "industrial|military|educational|residential|construction|agricultural|commercial|unknown",
    "personnel_count": <number of people visible>,
    "personnel_types": ["workers", "supervisors", "guards", etc.],
    "uniform_identification": "Description of uniforms if any",
    "activity_type": "construction|military|educational|industrial|agricultural|residential|transport|unknown",
    "activity_description": "Description of activities",
    "concern_level": "low|medium|high|critical",
    "concern_indicators": ["list of specific concerns"],
    "supervision_present": true|false,
    "restriction_indicators": ["indicators of restriction"],
    "safety_equipment_present": true|false,
    "safety_concerns": ["safety issues observed"],
    "living_conditions_visible": true|false,
    "living_condition_issues": ["living condition problems"],
    "health_concerns": ["health/welfare issues"],
    "confidence_score": 0.0-1.0
}

Focus on humanitarian conditions:
1. Working conditions and safety
2. Living conditions if visible
3. Signs of supervision or control
4. Health and welfare indicators
5. Any concerning elements

Respond ONLY with valid JSON, no additional text."""