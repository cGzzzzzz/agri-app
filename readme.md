# 🌾 AgriAI
> AI-Powered Agricultural Assistant for Farmers and Agronomists

AgriAI is a mobile-first, AI-native agricultural advisory platform that allows farmers to interact using voice, images, and text to receive contextual recommendations based on crop type, growth stage, weather conditions, disease symptoms, and historical farm data.

The system is designed as a **modular monolith** for rapid development, easier deployment, and lower operational complexity while maintaining clear domain boundaries for future scaling.

---

# Vision

Agriculture applications today typically suffer from one of two problems:

- Traditional farm management systems are data-entry heavy and difficult for farmers to use.
- AI chatbots provide generic advice without context about the actual farm.

AgriAI aims to bridge this gap by becoming a:

> Context-aware AI Agronomist.

The system combines:

- Field history
- Crop lifecycle information
- Weather conditions
- Disease detection
- Agricultural knowledge bases
- AI reasoning

to provide actionable recommendations rather than generic answers.

---

# Supported Platforms

## Farmer Platform

- Android Application
- iOS Application
- Progressive Web Application

Built using:

```text
Flutter
```

Single codebase for all client applications.

---

## Agronomist Platform

- Flutter Web Dashboard

Features:

- Farmer monitoring
- Case management
- Advisory generation
- Disease reports
- Analytics dashboard

---

# High Level Architecture

```text
                        Flutter Applications
         ┌─────────────────┬──────────────────┐
         │                 │                  │
      Android             iOS               Web
         │                 │                  │
         └─────────────────┴──────────────────┘
                           │
                           ▼
                    FastAPI Backend
                           │
 ┌──────────────┬──────────┼───────────┬──────────────┐
 │              │          │           │              │
Auth        Farm Module  AI Module  Weather Module  Notification
 │              │          │           │              │
 └──────────────┴──────────┴───────────┴──────────────┘
                           │
                           ▼
                Recommendation Engine
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     PostgreSQL         pgVector        Object Storage
          │                │                │
          └────────────────┴────────────────┘
                           │
                           ▼
                    External AI APIs
```

---

# Core Philosophy

The application revolves around three primary actions:

```text
Ask
Scan
Manage
```

Everything in the application exists to support one of these flows.

---

# User Personas

## Farmer

Primary user.

Typical characteristics:

- Android device
- Rural connectivity
- Local language preference
- Prefers voice interaction
- Requires actionable recommendations

Primary goals:

- Diagnose crop issues
- Determine agricultural actions
- Monitor crop health
- Track field history

---

## Agronomist

Secondary user.

Goals:

- Review farmer cases
- Provide expert recommendations
- Monitor disease spread
- Analyze regional trends

---

# User Journey

## First Launch

```text
Splash Screen
    ↓
Language Selection
    ↓
OTP Authentication
    ↓
Farm Creation
    ↓
Crop Registration
    ↓
Location Permission
    ↓
Dashboard
```

---

# Authentication Flow

## Mobile Number Login

```text
Enter Mobile Number
    ↓
Receive OTP
    ↓
Verify OTP
    ↓
Generate JWT
    ↓
Login Success
```

---

# Onboarding Flow

## Step 1

Select preferred language.

Examples:

- English
- Tamil
- Hindi
- Telugu
- Kannada
- Malayalam

---

## Step 2

Create farm profile.

Fields:

```text
Farm Name
Village
District
State
Farm Area
```

---

## Step 3

Register crop.

Fields:

```text
Crop Type
Crop Variety
Sowing Date
Field Size
Irrigation Type
```

---

# Mobile Navigation

```text
Home
Assistant
Scan
Farm
Profile
```

---

# Home Dashboard

The dashboard should answer:

> What requires attention today?

Example:

```text
Weather:
31°C
Rain expected in 5 hours

Crop:
Rice

Growth Stage:
Vegetative

Alerts:
Blast disease risk increasing

Tasks:
Apply fertilizer tomorrow
```

Quick Actions:

```text
Ask AI
Scan Crop
View Farm
```

---

# AI Assistant Flow

## Text Input

```text
User Question
        ↓
Context Builder
        ↓
Knowledge Retrieval
        ↓
Recommendation Engine
        ↓
LLM Response Generation
        ↓
Client Response
```

---

## Example

Input:

```text
My rice leaves are turning yellow.
```

System automatically enriches request using:

```text
Crop Type
Growth Stage
Weather
Location
Historical Diseases
```

Generated context:

```text
Rice
Vegetative Stage
Heavy rainfall yesterday
Nitrogen applied 14 days ago
```

Final response:

```text
Possible nitrogen deficiency detected.
Upload an image for confirmation.
```

---

# Voice Flow

```text
Voice Recording
        ↓
Speech To Text
        ↓
Context Builder
        ↓
Recommendation Engine
        ↓
Response Generation
        ↓
Text To Speech
```

---

# Image Diagnosis Flow

```text
Capture Image
        ↓
Compression
        ↓
Upload
        ↓
Vision Analysis
        ↓
Disease Classification
        ↓
Recommendation Engine
        ↓
Result Screen
```

---

## Example

```text
Disease:
Rice Blast

Confidence:
91%

Severity:
Moderate
```

Recommendation:

```text
Apply Tricyclazole within 48 hours.
Avoid spraying if rainfall occurs within 24 hours.
```

---

# Scan Flow

```text
Home
    ↓
Scan Button
    ↓
Camera Opens
    ↓
Capture Leaf Image
    ↓
Analysis
    ↓
Result
    ↓
Save To Farm History
```

---

# Farm Module

The farm module acts as the contextual memory of the system.

---

## Farm Overview

Contains:

```text
Farm Name
Area
Crop
Growth Stage
Weather
Current Alerts
```

---

## Field Timeline

Example:

```text
Day 1:
Sowing

Day 15:
Nitrogen Application

Day 32:
Disease Detection

Day 35:
Treatment Applied
```

---

## Disease History

Tracks:

```text
Disease
Severity
Treatment
Recovery
Images
```

---

## Expense Tracking

Optional module.

Tracks:

```text
Seeds
Fertilizers
Labor
Machinery
Irrigation
```

---

# Recommendation Engine

This is the intelligence layer.

The LLM never directly decides agricultural actions.

Instead:

```text
Weather
Crop Stage
Disease
Location
Field History
Knowledge Base
```

are combined to produce recommendations.

The LLM converts structured outputs into natural language.

---

## Example

Input:

```json
{
  "crop": "rice",
  "disease": "blast",
  "weather": "rain tomorrow"
}
```

Engine output:

```json
{
  "action": "delay spraying",
  "reason": "rain reduces fungicide effectiveness",
  "urgency": "high"
}
```

LLM output:

```text
Rain is expected tomorrow.
Delay fungicide spraying until rainfall ends.
```

---

# Backend Architecture

Architecture style:

```text
Modular Monolith
```

---

## Directory Structure

```text
backend/
│
├── auth/
├── users/
├── farms/
├── crops/
├── weather/
├── ai/
├── vision/
├── rag/
├── recommendations/
├── analytics/
├── notifications/
└── common/
```

---

# AI Module

Contains:

```text
Conversation Management
Prompt Building
Context Assembly
Response Generation
```

---

# RAG Module

Responsible for:

```text
Document Processing
Chunking
Embedding Generation
Vector Search
Retrieval
```

---

## Data Sources

Examples:

- ICAR Publications
- Agricultural University Advisories
- Government Schemes
- Disease Guides
- Fertilizer Recommendations

---

# Weather Module

Responsible for:

```text
Forecast Retrieval
Rain Alerts
Humidity Analysis
Spraying Recommendations
```

---

# Notification Module

Supports:

```text
Push Notifications
Weather Alerts
Disease Alerts
Task Reminders
```

---

# Database Design

## Users Table

```text
id
phone
name
language
created_at
```

---

## Farms Table

```text
id
user_id
farm_name
district
state
area
created_at
```

---

## Crops Table

```text
id
farm_id
crop_type
crop_variety
sowing_date
growth_stage
```

---

## Conversations Table

```text
id
user_id
question
response
created_at
```

---

## Disease History Table

```text
id
farm_id
disease_name
severity
image_url
detected_at
```

---

## Activities Table

```text
id
farm_id
activity_type
description
activity_date
```

---

# Object Storage

Stores:

```text
images/
audio/
reports/
```

Examples:

```text
leaf_001.jpg
voice_002.wav
report_003.pdf
```

---

# API Architecture

Examples:

```text
POST /api/chat

POST /api/scan

GET /api/weather

GET /api/farms

POST /api/farms

GET /api/history
```

---

# Technology Stack

## Frontend

```text
Flutter
```

---

## Backend

```text
FastAPI
```

---

## Database

```text
PostgreSQL
```

---

## Vector Search

```text
pgvector
```

---

## Object Storage

```text
Cloudflare R2
```

---

## Cache

```text
Redis
```

---

## AI

```text
GPT
Gemini
Qwen
Whisper
```

---

# ML Model Training

The disease classification and severity estimation models are trained on the PlantVillage dataset using EfficientNet-B0 + CBAM architecture.

For full training instructions, see [`backend/TRAINING.md`](backend/TRAINING.md).

Quick start:

```bash
cd backend
pip install -r requirements.txt kagglehub

# Download and prepare dataset
python -m app.models_ml.training.prepare_plantvillage

# Train all models (GPU recommended)
python -m app.models_ml.training.run_training --epochs 30 --device cuda
```

Models are exported as ONNX to `backend/artifacts/` and loaded automatically by the backend.

---

# Deployment Architecture

```text
Flutter Web
        ↓
Cloudflare Pages

FastAPI
        ↓
Railway

PostgreSQL
        ↓
Neon

Storage
        ↓
Cloudflare R2
```

---

# Future Roadmap

## Version 2

- Market Prices
- Marketplace
- Agronomist Consultation
- Government Subsidy Discovery

---

## Version 3

- Yield Prediction
- Satellite Monitoring
- Drone Integration
- IoT Sensors

---

# Design Principles

1. Voice First
2. Context Aware
3. Mobile First
4. Offline Friendly
5. Low Cognitive Load
6. Explainable Recommendations
7. Human Override Capability

---

# Final Goal

The objective of AgriAI is not to become another farm management platform.

The objective is:

> To become the farmer's first source of truth before making any agricultural decision.