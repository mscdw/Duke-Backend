%% Phase 2 Enhancements (TODO)
%% - Person Identity Management UI: Interface within the Hub for analysts to merge, unmerge, and curate person identities in the re-identification collection.
%% - Rules Engine Management UI: Allow analysts to create, edit, and manage deterministic rules via the Hub interface.
%% - Collector Management UI: A section in the Hub to register new collectors, monitor their status, and manage site configurations.
%% - Enterprise Authentication Integration: Connect the RBAC service to an external identity provider (e.g., SAML, OIDC) for single sign-on.

%% System Responsibilities
%% - Use a Collector to interact with AWS Rekognition, indexing and searching against its internal Face Collection to achieve person re-identification.
%% - Use a Hub to broker all data flow, sending events to a unified Threat Intel Engine.
%% - The Threat Intel Engine—a single logical service composed of rules, ML, and optional GenAI—processes this data and returns complete Anomaly Reports to the Hub.
%% - The Hub stores all raw data, curated identities, and final anomaly reports in the database.
%% - Enable Threat Analysts to consume the final intelligence via the Hub's UI.

graph LR

    human_analyst["Threat Analyst (User)"]

    subgraph "SUBSTATION 1"
        direction TB
        cameras_s1["Cameras 1...N"] --> avigilon1a["Avigilon Server A"]
        cameras_s1 --> avigilon1b["Avigilon Server B"]
    end

    subgraph "SUBSTATION 2"
        direction TB
        cameras_s2["Cameras 1...N"] --> avigilon2a["Avigilon Server A"]
        cameras_s2 --> avigilon2b["Avigilon Server B"]
    end

    subgraph "AWS VPC"
        rbac["Authentication / RBAC"]
        
        subgraph "EC2 or EKS Compute"
            direction TB
            collector["Collector"]
            hub["Hub (API & UI)"]
            threat_intel_engine["Threat Intel Engine\n(Rules, ML Models,\nOptional GenAI)"]
        end

        subgraph "AWS Rekognition"
             rekognition_collection["Face Collection\n(for Re-ID)"]
        end

        subgraph "MongoDB-Compatible (DocumentDB)"
            direction TB
            persons_collection["Collection: Persons (Identities)"]
            appearances_events["Collection: Appearances & Events"]
            anomaly_reports["Collection: Anomaly Reports"]
        end
        
        subgraph "Security"
            direction TB
            iam["IAM Roles & Policies"]
            sg["Security Groups / ACLs"]
        end
    end

    avigilon1a -- "Poll for Appearances,\nEvents, Media" --> collector
    avigilon1b -- "Poll for Appearances,\nEvents, Media" --> collector
    avigilon2a -- "Poll for Appearances,\nEvents, Media" --> collector
    avigilon2b -- "Poll for Appearances,\nEvents, Media" --> collector

    collector -- "Face Search & Index" --> rekognition_collection
    collector -- "POST Enriched Data" --> hub
    hub -- "Stores Raw Data" --> appearances_events
    hub -- "Stores AI/ML Results" --> anomaly_reports
    hub <--> persons_collection
    hub <--> threat_intel_engine

    human_analyst -- "All UI/API Requests (View, Curate, Manage Rules)" --> rbac
    rbac -- "Authenticated & Authorized Requests" --> hub
