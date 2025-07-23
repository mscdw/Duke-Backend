## Overview
- Use a Collector to interact with AWS Rekognition, indexing and searching against its internal Face Collection to achieve person re-identification.
- Use a Hub to broker all data flow, sending events to a unified Threat Intel Engine.
- The Threat Intel Engine—a single logical service composed of rules, ML, and optional GenAI—processes this data and returns complete Anomaly Reports to the Hub.
- The Hub stores all raw data, curated identities, and final anomaly reports in the database.
- Enable Threat Analysts to consume the final intelligence via the Hub's UI.

### Phase 2 Enhancements (TODO)

- **Person Identity Management UI:** Interface within the Hub for analysts to merge, unmerge, and curate person identities in the re-identification collection.
- **Rules Engine Management UI:** Allow analysts to create, edit, and manage deterministic rules via the Hub interface.
- **Collector Management UI:** A section in the Hub to register new collectors, monitor their status, and manage site configurations.
- **Enterprise Authentication Integration:** Connect the RBAC service to an external identity provider (e.g., SAML, OIDC) for single sign-on.

---

### Diagram

```mermaid
%%{init: { 'theme': 'neutral' }}%%
graph LR
    %% Define External User
    human_analyst["fa:fa-user-shield Threat Analyst (User)"]

    %% On-Premise Substations
    subgraph SUBSTATION 1
        direction TB
        cameras_s1["fa:fa-video Cameras 1...N"] --> avigilon1a["fa:fa-server Avigilon Server A"]
        cameras_s1 --> avigilon1b["fa:fa-server Avigilon Server B"]
    end

    subgraph SUBSTATION 2
        direction TB
        cameras_s2["fa:fa-video Cameras 1...N"] --> avigilon2a["fa:fa-server Avigilon Server A"]
        cameras_s2 --> avigilon2b["fa:fa-server Avigilon Server B"]
    end

    %% Cloud Infrastructure
    subgraph "fa:fa-cloud AWS VPC"
        rbac["fa:fa-key Authentication / RBAC"]
        
        subgraph "EC2 or EKS Compute"
            direction TB
            collector["fa:fa-clock Collector"]
            hub["fa:fa-window-maximize Hub (API & UI)"]
            threat_intel_engine["fa:fa-microchip Threat Intel Engine<br>(Rules, ML Models,<br>Optional GenAI)"]
        end

        %% Rekognition shown with its internal collection
        subgraph "fa:fa-search AWS Rekognition"
             rekognition_collection["fa:fa-id-badge Face Collection<br>(for Re-ID)"]
        end

        subgraph "MongoDB-Compatible (DocumentDB)"
            direction TB
            persons_collection["fa:fa-users Collection: Persons (Identities)"]
            appearances_events["fa:fa-file-alt Collection: Appearances & Events"]
            anomaly_reports["fa:fa-flag Collection: Anomaly Reports"]
        end
        
        subgraph "Security"
            direction TB
            iam["fa:fa-id-card IAM Roles & Policies"]
            sg["fa:fa-lock Security Groups / ACLs"]
        end
    end

    %% --- Data Flow & Connections ---

    %% On-Prem to Cloud
    avigilon1a -- "Poll for Appearances,<br>Events, Media" --> collector
    avigilon1b -- "Poll for Appearances,<br>Events, Media" --> collector
    avigilon2a -- "Poll for Appearances,<br>Events, Media" --> collector
    avigilon2b -- "Poll for Appearances,<br>Events, Media" --> collector

    %% Internal Cloud Flow
    collector -- "Face Search & Index" --> rekognition_collection
    collector -- "POST Enriched Data" --> hub
    hub -- "Stores Raw Data" --> appearances_events
    hub -- "Stores AI/ML Results" --> anomaly_reports
    hub <--> |"Manages Curated Identities"| persons_collection
    
    %% Simplified interaction with the unified Threat Intel Engine
    hub <--> |"GET Events / POST Anomalies"| threat_intel_engine
    
    %% User Interaction (Routed through RBAC & Hub)
    human_analyst -- "All UI/API Requests<br>(View, Curate, Manage Rules)" --> rbac
    rbac -- "Authenticated & Authorized Requests" --> hub
