# MindBridge — Student Support & Case Coordination

MindBridge is a privacy-first student support and case coordination system designed to help students raise concerns and track their progress.

## Features

- Submit concerns related to ragging and bullying, emotional support, academics, hostel issues, and financial assistance.
- Choose an identity-sharing preference when submitting a concern.
- View submitted cases and their current statuses.
- Access notifications and case details.
- Manage privacy preferences.
- Responsive interface with student-focused navigation.

## Tech Stack

- React
- Vite
- React Router
- Lucide React
- CSS

## Getting Started

### Prerequisites

Install [Node.js](https://nodejs.org/) and npm.

### Installation

From the `frontend` directory, run:

```bash
npm install
npm run dev
```

Open the local URL displayed in the terminal, usually `http://localhost:5173/`.

### Production Build

To verify the production build, run:

```bash
npm run build
```

## Current Development Status

The frontend currently uses mock data and browser storage for demonstration. Case submissions, notification read status, and identity preferences are not yet connected to a live backend or shared database.

Backend API integration, server-side authentication, persistent storage, and role-based authorization remain dependent on the backend implementation.

**Privacy note:** The current frontend is a development prototype, not a production-ready system for real or sensitive student reports. Browser storage is not a secure substitute for backend access controls.

## Project Structure

```text
frontend/
├── public/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── App.jsx
│   ├── App.css
│   └── index.css
├── package.json
└── README.md
```

## Team Workflow

Coordinate backend API endpoints, request/response formats, authentication, and case data models with the team before integrating the frontend with the backend.
