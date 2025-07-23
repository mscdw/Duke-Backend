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
