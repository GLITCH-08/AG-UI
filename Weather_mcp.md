# OCCHub Weather MCP API - Project Flow Documentation

## Project Overview

The **OCCHub Weather MCP API** is a comprehensive weather data service system built around the **Model Context Protocol (MCP)** architecture. It provides real-time weather information (METAR/TAF data) through a modern web interface with AI-powered chat capabilities for airline operational control centers.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   Middleware     │    │  Weather MCP    │
│   (React/Vite)  │◄──►│   (FastAPI)      │◄──►│   Server        │
│                 │    │                  │    │  (FastMCP)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │                          │
                               ▼                          ▼
                       ┌──────────────┐         ┌──────────────┐
                       │  MongoDB     │         │  MCP TOOLS   │
                       │  (Chat Log)  │         │              │
                       └──────────────┘         └──────────────┘
                               │                          |
                               ▼                          ▼
                       ┌──────────────┐         ┌──────────────┐
                       │  Azure Redis │         │   MONGODB    │
                       │  (Caching)   │         │              │
                       └──────────────┘         └──────────────┘
```

## Core Components

### 1. **Frontend UI** (`UI/`)
- **Technology Stack**: React 18 + Vite + TailwindCSS
- **Key Features**:
  - Modern chat interface for weather queries
  - Real-time streaming responses via Server-Sent Events (SSE)
  - Chart visualization using Recharts library
  - Responsive design with Framer Motion animations

**Main Files**:
- `App.jsx` - Main application component
- `components/ChatPage.jsx` - Chat interface layout
- `package.json` - Dependencies and build scripts

### 2. **Middleware Layer** (`Middleware/`)
- **Technology Stack**: FastAPI + Azure OpenAI + Redis
- **Purpose**: Acts as the orchestration layer between UI and MCP server

**Key Files**:
- `main.py` - Main FastAPI application with streaming endpoints
- `mongoDB.py` - MongoDB integration for chat logging  
- `variables.py` - Configuration constants and airport data

**Core Functionalities**:
- **Chat Processing**: Handles user queries and converts them to MCP tool calls
- **Stream Management**: Provides real-time streaming responses using Server-Sent Events
- **Authentication**: JWT-based authentication for MCP server communication
- **Caching**: Redis integration for performance optimization
- **Logging**: Comprehensive chat interaction logging to MongoDB

### 3. **Weather MCP Server** (`weather/`)
- **Technology Stack**: FastMCP + Motor (async MongoDB) + JWT Authentication
- **Purpose**: Provides weather data tools and services

**Key Files**:
- `http_app.py` - Main MCP server with weather tools

**Available MCP Tools**:
1. **`search_metar_data`** - Generic METAR data search with multiple filters
2. **`list_available_stations`** - List all available weather stations with ICAO/IATA codes
3. **`get_metar_statistics`** - Get comprehensive statistics about the METAR database
4. **`raw_mongodb_query_find`** - Execute raw MongoDB find queries
5. **`raw_mongodb_query_aggregate`** - Execute MongoDB aggregation pipelines
6. **`table_and_graph_JSON_generater`** - Generate JSON for table and chart visualization
7. **`ping`** - Health check tool for testing authentication

## Data Flow

### 1. **User Interaction Flow**
```
User Input → Frontend → Middleware → MCP Server → Response Stream
```

1. **User submits query** via React chat interface
2. **Frontend sends POST request** to `/get_data` endpoint with query parameters
3. **Middleware processes** the request using Azure OpenAI to determine required tools
4. **MCP Client** authenticates and calls appropriate weather tools
5. **Weather data** is fetched from MongoDB 
6. **Response streams back** via Server-Sent Events to frontend
7. **Chat interaction** is logged to MongoDB for analytics

### 2. **Authentication Flow**
```
Client → Token Request → JWT Verification → MCP Tool Access
```

1. **Token Generation**: MCP server generates JWT tokens for authentication
2. **JWT Verification**: Each tool call is protected by JWT verification

### 3. **Data Storage Flow**
```
Weather Data → MongoDB (METAR Collection) 
Chat Logs → MongoDB (Weather_Chat Collection)
Cache → Azure Redis 
```

## Key Features

### 1. **Real-time Weather Data**
- Live METAR and TAF data for Indian airports
- Support for 139+ airports with ICAO/IATA code mapping
- Weather condition filtering and trend analysis

### 2. **AI-Powered Chat Interface**
- Natural language processing for weather queries
- Contextual responses using Azure OpenAI
- Streaming responses for better user experience

### 3. **Advanced Data Visualization**
- Chart generation for weather trends
- Table views for structured data
  

### 4. **Enterprise Integration**
- JWT authentication for secure access
- MongoDB for persistent data storage
- Redis caching for performance optimization

