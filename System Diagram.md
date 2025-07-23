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

### System Diagram

```mermaid
%%{init: { 'theme': 'neutral' }}%%
graph LR
    %% External User
    human_analyst["fa:fa-user-shield<br>Threat Analyst (User)"]

    %% On-Premise Substations
    subgraph SUBSTATION 1
        direction TB
        cameras_s1["fa:fa-video<br>Cameras 1...N"] --> avigilon1a["fa:fa-server<br>Avigilon Server A"]
        cameras_s1 --> avigilon1b["fa:fa-server<br>Avigilon Server B"]
    end

    subgraph SUBSTATION 2
        direction TB
        cameras_s2["fa:fa-video<br>Cameras 1...N"] --> avigilon2a["fa:fa-server<br>Avigilon Server A"]
        cameras_s2 --> avigilon2b["fa:fa-server<br>Avigilon Server B"]
    end

    %% Cloud Infrastructure
    subgraph "fa:fa-cloud AWS VPC"
        rbac["fa:fa-key<br>Authentication / RBAC"]
        
        subgraph "EC2 or EKS Compute"
            direction TB
            collector["fa:fa-clock<br>Collector"]
            hub["fa:fa-window-maximize<br>Hub (API & UI)"]
            threat_intel_engine["fa:fa-microchip<br>Threat Intel Engine<br>(Rules, ML, GenAI)"]
        end

        subgraph "fa:fa-search AWS Rekognition"
            rekognition_collection["fa:fa-id-badge<br>Face Collection<br>(for Re-ID)"]
        end

        subgraph "MongoDB-Compatible (DocumentDB)"
            direction TB
            persons_collection["fa:fa-users<br>Collection: Persons"]
            appearances_events["fa:fa-file-alt<br>Collection: Events"]
            anomaly_reports["fa:fa-flag<br>Collection: Anomaly Reports"]
        end
        
        subgraph "Security"
            direction TB
            iam["fa:fa-id-card<br>IAM Roles & Policies"]
            sg["fa:fa-lock<br>Security Groups / ACLs"]
        end
    end

    %% Data Flow & Connections (with line breaks in labels)

    %% On-Prem to Cloud
    avigilon1a -- "Poll for<br>Appearances,<br>Events, Media" --> collector
    avigilon1b -- "Poll for<br>Appearances,<br>Events, Media" --> collector
    avigilon2a -- "Poll for<br>Appearances,<br>Events, Media" --> collector
    avigilon2b -- "Poll for<br>Appearances,<br>Events, Media" --> collector

    %% Internal Cloud Flow
    collector -- "Face Search<br>& Index" --> rekognition_collection
    collector -- "POST Raw &<br>Enriched Data" --> hub
    hub -- "Stores Raw<br>& Enriched Data" --> appearances_events
    hub -- "Stores AI/ML<br>Results" --> anomaly_reports
    hub <--> |"Manages<br>Curated Identities"| persons_collection
    hub <--> |"GET Events /<br>POST Anomalies"| threat_intel_engine

    %% User Interaction
    human_analyst -- "All UI/API<br>Requests" --> rbac
    rbac -- "Authenticated &<br>Authorized Requests" --> hub
