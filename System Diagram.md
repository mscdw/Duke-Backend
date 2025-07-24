## Threat Intelligence Platform Overview

-   **Ingestion & Enrichment:** A Collector polls Avigilon for event data, uploads the associated image directly to S3, and enriches the event metadata with a face signature from AWS Rekognition.
-   **Persistence for Analysis:** A central Hub receives the complete metadata package (including the S3 image link and Rekognition results) from the Collector and persists it to the database, staging the data for the analysis engine.
-   **Batch Analysis & Reporting:** The Threat Intel Engine operates as an independent batch process. It periodically queries the database for new events, performs its analysis, and writes the resulting Anomaly Reports directly back to the database.
-   **Consumption:** Finally, the Hub's UI provides a unified view, allowing Threat Analysts to consume the raw events, curated identities, and final Anomaly Reports from the database.

### Duke IT Integration Plan & Decisions

A technical review between CDW and Duke IT confirmed the proposed software architecture is compatible with Duke's environment. The following decisions and requirements were established:

*   **Action Item: Database Selection:** A final decision on the database is required.
    *   **CDW Preference:** AWS DocumentDB.
    *   **Alternative:** If DocumentDB is not feasible, CDW can run MongoDB in a dedicated container on EKS.
*   **Code & CI/CD:** GitHub will be used for the code repository and GitHub Actions for CI/CD.
*   **Container Orchestration:** The platform will run on **AWS EKS**.
*   **Resource Requirements:** The deployment will require **4 application containers**, each with 4 vCPU ("4000m") and 16 GiB of memory ("16384Mi"). If the MongoDB alternative is chosen, the total will increase to **5 containers**.
*   **Authentication:** **Azure Entra** will be used for authentication.
*   **Secrets Management:** The platform will integrate with Duke's standard secrets management tool. Duke uses both **AWS Secrets Manager** and **HashiCorp Vault**; the specific integration will be implemented in Phase 2.
*   **Logging:** **Splunk** is the standard for log aggregation. Logs written to the container's standard output will be collected.
*   **API Behavior:** For multi-server Avigilon sites, API requests will be made to all available servers in the site.

### Phase 2 Enhancements (TODO)

-   **Enterprise Authentication Integration:** Connect the RBAC service to an external identity provider (e.g., SAML, OIDC) for single sign-on.
-   **Secrets Management Integration:** Integrate with Duke's standard secrets management tool (**AWS Secrets Manager** or **HashiCorp Vault**) for handling all application credentials.
-   **Dedicated Image Storage:** Store images in an AWS S3 bucket instead of MongoDB for cost-effective and scalable storage.
-   **Person Identity Management UI:** Interface within the Hub for analysts to merge, unmerge, and curate person identities in the re-identification collection.
-   **Rules Engine Management UI:** Allow analysts to create, edit, and manage deterministic rules via the Hub interface.

### Post–Phase 2 PoV (Collector Scaling)

-   **Collector Management UI:** A section in the Hub to register new collectors, monitor their status, and manage site configurations.
-   **(Tentative): Scalability with Message Queues:** Refactor the internal data flow to use a message queue (e.g., Amazon SQS) to enable horizontal collector scaling. This decouples data ingestion from processing, improving reliability and throughput under load. Estimated effort: **1–2 weeks**.

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
 subgraph subGraph4["EC2 or EKS Compute"]
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
    cloudwatch["fa:fa-chart-area<br>Logging &amp; Monitoring"]
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
  collector1 -- Logs --> cloudwatch
  collector2 -- Logs --> cloudwatch
  hub -- Writes Events --> events_coll
  hub -- "Generates<br>Pre-signed URLs" --> s3_bucket
  hub -- Gets Secrets --> secrets_manager
  hub -- Logs --> cloudwatch
  threat_intel_engine -- Reads Threat Rules --> rules_coll
  threat_intel_engine -- Writes Threat Reports --> reports_coll
  threat_intel_engine -- Gets Secrets --> secrets_manager
  threat_intel_engine -- Reads Events --> events_coll
  threat_intel_engine -- Logs --> cloudwatch
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
  style cloudwatch fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style iam fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style sg fill:#e53935,stroke:#b71c1c,stroke-width:2px,color:#fff
  style rbac fill:#00838f,stroke:#005662,stroke-width:2px,color:#fff
  style note_analyst_flow fill:#fff9c4,stroke:#333,stroke-width:1px
```

### System Architecture & IT Integration FAQ

This document outlines the deployment and integration of our software within your AWS environment. Our model is to provide you with the **source code** for our platform (Collector, Hub, Threat Intel Engine), which is then deployed and run **entirely within your own AWS account**. You maintain full control over the infrastructure, data, and security. Our role is to partner with your teams to ensure a successful integration.

---

#### **1. Network & Connectivity**

- **On-Prem to Cloud Connection**  
  - Communication from the on-premise Collector (running in your AWS account) to your Avigilon servers is conducted securely over **HTTPS (port 443)**.  
  - This traffic leverages your existing, approved network infrastructure (e.g., VPN, Direct Connect).

- **Bandwidth Consumption**  
  - The Collector polls for **image snapshots (~150KB per image) and metadata**, not full video streams, to minimize bandwidth usage.  
  - A discovery process during the initial engagement will provide a precise bandwidth estimate based on your configuration.

- **Latency Sensitivity**  
  - The system is designed for **batch processing** and is not highly sensitive to network latency.  
  - If real-time or near-real-time processing becomes necessary, we will assess architectural options to meet those needs.

- **Firewall & Security Groups**  
  - We will collaborate with your network and cloud teams to define the necessary firewall rules and AWS Security Group / Network ACL configurations within your environment.

---

#### **2. Cloud Infrastructure & Scalability**

- **Compute Platform (EC2 vs. EKS)**  
  - Our software is flexible and can be deployed on either **EC2 virtual machines** or as **containers within an EKS cluster** in your AWS environment, according to your operational standards.

- **Scalability**  
  - **Phase 2 (Proof of Value):** The PoV architecture will support up to two sites using direct Collector-to-Hub communication.  
  - **Phase 2 Assessment:** A key activity during this phase will be to **assess and validate the technical requirements for scaling beyond two sites**.  
  - **Future Implementation (Post-PoV):** If changes are required to support additional sites, that work will be scoped and planned as a subsequent phase. This is a known refactoring effort estimated at ~2 weeks.

- **Infrastructure as Code (IaC) & CI/CD**  
  - The platform's deployment will integrate with your existing IaC (e.g., Terraform, CloudFormation) and CI/CD pipelines.  
  - We provide the application **source code**, and your teams will manage the build and deployment process, ensuring it meets all internal standards.

---

#### **3. Security & Compliance**

- **Data Encryption & Code Scanning**  
  - All data is **encrypted in transit (using TLS) and at rest** using the native AWS encryption services you have configured for S3, DocumentDB, etc.  
  - Since you will have the **full source code**, you can integrate it directly into your standard Static Analysis Security Testing (SAST) and vulnerability scanning pipelines before any deployment.

- **Identity & Access Management**  
  - We will provide guidance for defining granular **IAM policies that adhere to the Principle of Least Privilege**.  
  - Your security team will implement and manage these policies within your AWS account.  
  - During Phase 2, we will integrate with your team's chosen secrets management solution—either **AWS Secrets Manager** or **HashiCorp Vault**—to manage all application credentials according to your corporate standard.

- **PII & Data Governance**  
  - Because the platform runs **entirely within your AWS account**, you retain 100% ownership and control of your data at all times.  
  - The system operates under your organization's established data governance and PII policies.

---

#### **4. Database & Data Management**

- **Database Choice**  
  - A MongoDB-compatible database (e.g., DocumentDB) is recommended for its flexibility in handling the semi-structured nature of event and report data.  
  - The final choice of database service is up to you.

- **Backup and Recovery Strategy**  
  - Your teams will manage the backup and recovery procedures according to your corporate standards.  
  - **Stateful Data:** The primary backup targets are the S3 bucket (images) and the DocumentDB database (metadata, reports).  
  - **Rekognition Collection:** The Rekognition Face Collection is treated as ephemeral. Resilience is achieved by assigning a stable, unique ID to each identity within your database.  
  - If the collection must be rebuilt, the face images from S3 are simply re-indexed.

---

#### **5. Operations & Maintenance**

- **Deployment & Patching**  
  - Your IT Operations team will manage the full operational lifecycle of the platform.  
  - We will provide guidance and support to align our software with your established processes for deployment, health monitoring, and system patching.

- **Monitoring & Logging**  
  - Our software will be configured to produce **structured logs (e.g., JSON)** that can be ingested by your enterprise logging and monitoring tools (e.g., Splunk, AWS CloudWatch Logs), which your teams will manage.
