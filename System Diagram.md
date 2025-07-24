## Duke Advanced Threat Intelligence Platform

### Functional Overview

- **Ingestion & Enrichment:** A Collector polls Avigilon for event data, uploads associated images directly to S3, and enriches event metadata with face signatures from AWS Rekognition.  
- **Persistence for Analysis:** A central Hub receives the complete metadata package (including S3 image links and Rekognition results) from the Collector and persists it to the database, preparing the data for analysis.  
- **Batch Analysis & Reporting:** The Threat Intel Engine runs as an independent batch process. It periodically queries the database for new events, performs analysis, and writes resulting Anomaly Reports back to the database.  
- **Consumption:** The Hub’s UI provides a unified interface for Threat Analysts to access raw events, curated identities, and final Anomaly Reports from the database.

---

### System Diagram

```mermaid
---
config:
 theme: neutral
 layout: fixed
---
flowchart LR
 subgraph subGraph0["SUBSTATION 1"]
  direction TB
    avigilon1["fa:fa-server<br>Avigilon Server"]
    cameras_s1["fa:fa-video<br>Cameras"]
 end
 subgraph subGraph1["SUBSTATION 2"]
  direction TB
    avigilon2["fa:fa-server<br>Avigilon Server"]
    cameras_s2["fa:fa-video<br>Cameras"]
 end
 subgraph subGraph2["On-Premise Sites"]
  direction LR
    subGraph0
    subGraph1
 end
 subgraph subGraph3["Secure On-Prem to Cloud Link"]
    vpn["fa:fa-shield-alt<br>VPN / Direct Connect"]
 end
 subgraph subGraph4["EKS Compute"]
  direction TB
    collector1["fa:fa-cogs<br>Collector (Our Code)<br>Substation 1"]
    collector2["fa:fa-cogs<br>Collector (Our Code)<br>Substation 2"]
    hub["fa:fa-window-maximize<br>Hub (Our Code)"]
    threat_intel_engine["fa:fa-microchip<br>Threat Intel Engine (Our Code)"]
 end
 subgraph subGraph5["Managed Services"]
    rekognition_collection["fa:fa-id-badge<br>Rekognition<br>Face Collection"]
 end
 subgraph subGraph6["fa:fa-database DocumentDB"]
    persons_coll["fa:fa-users<br>Collection: Persons"]
    events_coll["fa:fa-file-alt<br>Collection: Events"]
    reports_coll["fa:fa-flag<br>Collection: Reports"]
    rules_coll["fa:fa-list-alt<br>Collection: Rules"]
 end
 subgraph Storage["Storage"]
  direction TB
    s3_bucket["fa:fa-archive<br>S3 Bucket<br>(Image Store)"]
    subGraph6
 end
 subgraph subGraph8["Security & Operations"]
  direction TB
    secrets_manager["fa:fa-user-secret<br>Secrets Manager"]
    splunk["fa:fa-chart-area<br>Logging &amp; Monitoring"]
    iam["fa:fa-id-card<br>IAM Roles &amp; Policies"]
    sg["fa:fa-lock<br>Security Groups / ACLs"]
 end
 subgraph subGraph9["fa:fa-cloud Customer's AWS VPC"]
    rbac["fa:fa-key<br>Authentication / RBAC"]
    subGraph4
    subGraph5
    Storage
    subGraph8
 end
  cameras_s1 --> avigilon1
  cameras_s2 --> avigilon2
  avigilon1 -- HTTPS Poll --> vpn
  avigilon2 -- HTTPS Poll --> vpn
  vpn -- Secure Tunnel (S1) --> collector1
  vpn -- Secure Tunnel (S2) --> collector2
  collector1 -- Uploads Images --> s3_bucket
  collector2 -- Uploads Images --> s3_bucket
  collector1 -- Face Search/Index --> rekognition_collection
  collector2 -- Face Search/Index --> rekognition_collection
  collector1 -- Gets Secrets --> secrets_manager
  collector2 -- Gets Secrets --> secrets_manager
  collector1 -- POST Metadata --> hub
  collector2 -- POST Metadata --> hub
  collector1 -- Logs --> splunk
  collector2 -- Logs --> splunk
  hub -- Writes Events --> events_coll
  hub -- "Generates<br>Pre-signed URLs" --> s3_bucket
  hub -- Gets Secrets --> secrets_manager
  hub -- Logs --> splunk
  threat_intel_engine -- Reads Threat Rules --> rules_coll
  threat_intel_engine -- Writes Threat Reports --> reports_coll
  threat_intel_engine -- Gets Secrets --> secrets_manager
  threat_intel_engine -- Reads Events --> events_coll
  threat_intel_engine -- Logs --> splunk
  human_analyst["fa:fa-user-shield<br>Threat Analyst (User)"] -- UI/API Requests --> rbac
  rbac -- Authorized Requests --> hub
  human_analyst -. Reads Events<br>(via Hub) .-> events_coll
  human_analyst -. Reads Reports<br>(via Hub) .-> reports_coll
  human_analyst -. |Manages Threat Rules|<br>(via Hub) .-> rules_coll
  human_analyst -. "|Manages Person Re-ID Service<br>(Merge/Unmerge)|<br>(via Hub)" .-> persons_coll
  note_analyst_flow["<br><b>Note on Analyst Actions:</b><br>All analyst data interactions<br>(reads/writes to storage)<br>are proxied through the <b>Hub</b>.<br>Dashed lines represent this<br>simplified logical flow.<br>"]
  style vpn fill:#1976d2,stroke:#1976d2,stroke-width:2px,color:#fff
  style collector1 fill:#43a047,stroke:#388e3c,stroke-width:3px,color:#fff
  style collector2 fill:#43a047,stroke:#388e3c,stroke-width:3px,color:#fff
  style hub fill:#43a047,stroke:#388e3c,stroke-width:3px,color:#fff
  style threat_intel_engine fill:#43a047,stroke:#388e3c,stroke-width:3px,color:#fff
  style rekognition_collection fill:#8e24aa,stroke:#6d1b7b,stroke-width:2px,color:#fff
  style s3_bucket fill:#ffd600,stroke:#ffa000,stroke-width:2px
  style subGraph6 fill:#ffd600,stroke:#ffa000,stroke-width:2px
  style secrets_manager fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style splunk fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style iam fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style sg fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style rbac fill:#00838f,stroke:#005662,stroke-width:2px,color:#fff
  style note_analyst_flow fill:#fff9c4,stroke:#333,stroke-width:1px
```
