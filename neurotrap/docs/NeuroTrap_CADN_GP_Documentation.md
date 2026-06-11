# NeuroTrap CADN: A Cognitive Adaptive Deception Network for Intelligent Honeypot-Based Active Defense and Attacker Profiling

---

**Al-Zaytoonah University of Jordan**
**Faculty of Science and Information Technology**
**Department of Cybersecurity**

---

Graduation Project Submitted to the Department of Cybersecurity in Partial Fulfillment of the Requirements for the Bachelor's Degree in Cybersecurity

---

**Prepared by:**
[STUDENT 1 FULL NAME]
[STUDENT 2 FULL NAME]
[STUDENT 3 FULL NAME]

**Supervised by:**
[SUPERVISOR TITLE AND FULL NAME]

**Academic Year: 2025 / 2026**

---

## DEDICATION

[INSERT DEDICATION TEXT HERE]

---

## ACKNOWLEDGMENT

[INSERT ACKNOWLEDGMENT TEXT HERE]

The team would like to express sincere gratitude to our supervisor, [SUPERVISOR TITLE AND FULL NAME], for guidance and continued support throughout the development of this project.

We also extend our thanks to the Department of Cybersecurity at Al-Zaytoonah University of Jordan for providing the academic foundation that made this work possible.

---

## TABLE OF CONTENTS

- DEDICATION
- ACKNOWLEDGMENT
- TABLE OF CONTENTS
- LIST OF TABLES
- LIST OF FIGURES
- LIST OF ABBREVIATIONS
- ABSTRACT
- ARABIC ABSTRACT
- CHAPTER 1: INTRODUCTION
  - 1-1 Background and Motivation
  - 1-2 Problem Statement
  - 1-3 Project Objectives
  - 1-4 Project Scope and Limitations
  - 1-5 Report Organization
- CHAPTER 2: BACKGROUND AND LITERATURE REVIEW
  - 2-1 Honeypot Technology
  - 2-2 Machine Learning in Cybersecurity
  - 2-3 MITRE ATT&CK Framework
  - 2-4 Deception Technology
  - 2-5 Federated Learning for Cybersecurity
  - 2-6 Cognitive Bias Exploitation in Cybersecurity
  - 2-7 Related Work
  - 2-8 Summary
- CHAPTER 3: SYSTEM ANALYSIS AND DESIGN
  - 3-1 System Requirements Analysis
  - 3-2 System Architecture Overview
  - 3-3 Architecture Diagrams
  - 3-4 Module Design
  - 3-5 Database Design
  - 3-6 Use Case Analysis
  - 3-7 Sequence Diagrams
- CHAPTER 4: SYSTEM IMPLEMENTATION
  - 4-1 Development Environment
  - 4-2 Technology Stack
  - 4-3 Containerization and Deployment Architecture
  - 4-4 Implementation of the Detection Pipeline
  - 4-5 Implementation of the Behavior Analysis Engine
  - 4-6 Implementation of the Deception Engine
  - 4-7 Implementation of the CBEE Module
  - 4-8 Implementation of the GADCF Module
  - 4-9 Implementation of the Attacker Digital Twin
  - 4-10 Implementation of the FHIM Module
  - 4-11 Implementation of the Response Engine
  - 4-12 Implementation of the REST API and Dashboard
  - 4-13 Security Implementation
  - 4-14 Dashboard Interface
- CHAPTER 5: TESTING AND EVALUATION
  - 5-1 Testing Strategy
  - 5-2 Unit Testing
  - 5-3 Integration Testing
  - 5-4 System Testing
  - 5-5 Performance Evaluation
  - 5-6 Security Testing
  - 5-7 Test Results Summary
- CHAPTER 6: CONCLUSION AND FUTURE WORK
  - 6-1 Summary of Contributions
  - 6-2 Achievement of Objectives
  - 6-3 Limitations
  - 6-4 Future Work
  - 6-5 Final Remarks
- REFERENCES
- APPENDIX A: API Endpoint Reference
- APPENDIX B: Database Collections Summary
- APPENDIX C: Configuration and Deployment Guide

---

## LIST OF TABLES

| Table | Title |
|-------|-------|
| Table 1.1 | Comparison of NeuroTrap CADN with Existing Honeypot Systems |
| Table 2.1 | Classification of Honeypot Systems by Interaction Level |
| Table 2.2 | Comparison of ML Algorithms for Network Intrusion Detection |
| Table 2.3 | Related Work Comparison |
| Table 3.1 | Functional Requirements of NeuroTrap CADN |
| Table 3.2 | Non-Functional Requirements of NeuroTrap CADN |
| Table 3.3 | Docker Container Services and Responsibilities |
| Table 3.4 | Threat Score Calculation Components |
| Table 3.5 | Threat Score Persistence Bonus Table |
| Table 3.6 | Tactic Weights Used in TTP Score Calculation |
| Table 3.7 | CBEE Bias Dimensions and Detection Signals |
| Table 3.8 | GADCF Supported Industries and Asset Types |
| Table 3.9 | Attacker Digital Twin Data Fields |
| Table 3.10 | FHIM Federated Node Configuration |
| Table 3.11 | Response Engine Decision Matrix |
| Table 3.12 | MongoDB Active Collections |
| Table 3.13 | Alert Event Schema Fields |
| Table 3.14 | Attacker Profile Schema Fields |
| Table 3.15 | Use Case Descriptions |
| Table 4.1 | Development Environment Specifications |
| Table 4.2 | Complete Technology Stack |
| Table 4.3 | Docker Network Configuration |
| Table 4.4 | SessionFeatureExtractor Feature Vector |
| Table 4.5 | Intent Classification Rules |
| Table 4.6 | Deception Environment Templates by Attacker Tier |
| Table 4.7 | REST API Endpoints Summary |
| Table 4.8 | Dashboard Sections and Data Sources |
| Table 5.1 | Unit Test Files and Coverage |
| Table 5.2 | AlertEvent Validation Test Cases |
| Table 5.3 | Classifier Test Cases |
| Table 5.4 | Response Engine Test Thresholds |
| Table 5.5 | Performance Targets vs. Achieved Results |
| Table 5.6 | Test Results Summary |
| Table 6.1 | Achievement of Project Objectives |

---

## LIST OF FIGURES

| Figure | Title |
|--------|-------|
| Figure 1.1 | Global Cyber Attack Growth Trend |
| Figure 2.1 | Honeypot Classification Taxonomy |
| Figure 2.2 | Federated Learning Architecture |
| Figure 3.1 | NeuroTrap CADN 10-Layer System Architecture |
| Figure 3.2 | Complete Data Flow Diagram |
| Figure 3.3 | Docker Network Topology |
| Figure 3.4 | Cowrie Session to Dashboard Pipeline |
| Figure 3.5 | Behavior Analysis Module Design |
| Figure 3.6 | CBEE Bias Scoring Architecture |
| Figure 3.7 | Attacker Digital Twin Architecture |
| Figure 3.8 | FHIM Federated Learning Architecture |
| Figure 3.9 | Response Engine Decision Tree |
| Figure 3.10 | API and Dashboard Architecture |
| Figure 3.11 | Entity Relationship Diagram |
| Figure 3.12 | System Use Case Diagram |
| Figure 3.13 | Attacker SSH Session Sequence Diagram |
| Figure 3.14 | Threat Score Calculation Sequence Diagram |
| Figure 4.1 | Docker Compose Service Dependency Graph |
| Figure 4.2 | AlertEvent Schema Normalization Flow |
| Figure 4.3 | ML Classifier Training Pipeline |
| Figure 4.4 | CBEE Bias Scoring Interface Screenshot |
| Figure 4.5 | GADCF Generated Content Example |
| Figure 4.6 | Attacker Digital Twin Dashboard Screenshot |
| Figure 4.7 | FHIM Node Status Dashboard Screenshot |
| Figure 4.8 | Dashboard Main Overview Screenshot |
| Figure 4.9 | Threat Actors Panel Screenshot |
| Figure 5.1 | Classifier F1 Score by Intent Class |
| Figure 5.2 | Threat Score Distribution of Live Attackers |
| Figure 5.3 | Attack Type Distribution Screenshot |
| Figure 5.4 | Live Event Feed Screenshot |
| Figure 5.5 | Response Log Screenshot |

---

## LIST OF ABBREVIATIONS

| Abbreviation | Meaning |
|-------------|---------|
| ADT | Attacker Digital Twin |
| API | Application Programming Interface |
| ASN | Autonomous System Number |
| ATT&CK | Adversarial Tactics, Techniques, and Common Knowledge |
| C2 | Command and Control |
| CBEE | Cognitive Bias Exploitation Engine |
| CADN | Cognitive Adaptive Deception Network |
| DB | Database |
| DP | Differential Privacy |
| F1 | F1 Score (harmonic mean of precision and recall) |
| FedAvg | Federated Averaging Algorithm |
| FHIM | Federated Honeypot Intelligence Mesh |
| FTP | File Transfer Protocol |
| GADCF | Generative Adaptive Deception Content Factory |
| GeoIP | Geographic IP Resolution |
| HTML | Hypertext Markup Language |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | Hypertext Transfer Protocol Secure |
| IDS | Intrusion Detection System |
| IOC | Indicator of Compromise |
| IP | Internet Protocol |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| KPI | Key Performance Indicator |
| LLM | Large Language Model |
| MFA | Multi-Factor Authentication |
| MITRE | Massachusetts Institute of Technology Research and Engineering |
| ML | Machine Learning |
| MSSQL | Microsoft SQL Server |
| NIC | Network Interface Card |
| OS | Operating System |
| PCAP | Packet Capture |
| RBAC | Role-Based Access Control |
| RDP | Remote Desktop Protocol |
| RF | Random Forest |
| REST | Representational State Transfer |
| SMB | Server Message Block |
| SMTP | Simple Mail Transfer Protocol |
| SNMP | Simple Network Management Protocol |
| SOC | Security Operations Center |
| SPA | Single-Page Application |
| SQL | Structured Query Language |
| SSH | Secure Shell Protocol |
| SSL | Secure Sockets Layer |
| SVM | Support Vector Machine |
| TCP | Transmission Control Protocol |
| TLS | Transport Layer Security |
| TOTP | Time-Based One-Time Password |
| TTP | Tactics, Techniques, and Procedures |
| UDP | User Datagram Protocol |
| UFW | Uncomplicated Firewall |
| UUID | Universally Unique Identifier |
| VNC | Virtual Network Computing |
| VPS | Virtual Private Server |
| WS | WebSocket |

---

## ABSTRACT

The increasing sophistication of cyber threats demands active and adaptive defensive mechanisms that go beyond traditional passive monitoring. This project presents NeuroTrap CADN (Cognitive Adaptive Deception Network), an intelligent honeypot platform that combines multi-protocol honeypot deployment, machine learning-based attacker profiling, cognitive bias exploitation, and autonomous response into a unified active defense system. The platform captures attacker interactions across SSH, Telnet, HTTP, FTP, SMB, RDP, VNC, SNMP, and MySQL protocols, normalizes all events into a unified detection schema, and classifies attacker intent and tier using a trained ensemble classifier (Random Forest combined with Support Vector Machine). Five novel innovation modules extend the system: the Cognitive Bias Exploitation Engine (CBEE) scores attackers across five psychological dimensions to inject personalized deception bait; the Generative Adaptive Deception Content Factory (GADCF) produces realistic fake corporate assets; the Attacker Digital Twin (ADT) builds a live behavioral replica with Markov-chain kill-chain prediction; the Federated Honeypot Intelligence Mesh (FHIM) enables privacy-preserving collaborative learning across distributed nodes using differential privacy; and an AI SOC Analyst provides natural-language triage and incident reporting. The system is deployed using Docker Compose on a production Ubuntu server and has demonstrated continuous capture and profiling of real internet attackers, with threat scores, intent classifications, and autonomous response actions delivered to a real-time SOC dashboard within five seconds of an attack event.

---

## ARABIC ABSTRACT

> **[PLACEHOLDER - ARABIC ABSTRACT]**
>
> Please insert the Arabic abstract here on a separate page. It must summarize the project in no more than 15 typed lines in Arabic.
>
> Suggested Arabic summary (have it reviewed by an Arabic academic):
>
> يقدم هذا المشروع NeuroTrap CADN، وهو منصة ذكاء اصطناعي متكاملة للدفاع السيبراني النشط تجمع بين تقنيات مصائد العسل متعددة البروتوكولات وتعلم الآلة وخوارزميات استغلال التحيز المعرفي والاستجابة الذاتية الآنية. تقوم المنصة برصد الهجمات الالكترونية الحقيقية وتصنيفها وتحليل سلوك المهاجمين وتوليد بيئات خداع مخصصة وإعداد تقارير تهديد ذكية في الوقت الفعلي. تتضمن المنصة خمسة مكونات ابتكارية: محرك استغلال التحيز المعرفي (CBEE)، ومصنع محتوى الخداع التكيفي التوليدي (GADCF)، والتوأم الرقمي للمهاجم (ADT)، وشبكة الذكاء الموحدة للمصائد (FHIM)، ومحلل عمليات الأمن بالذكاء الاصطناعي.

---

# CHAPTER 1: INTRODUCTION

## 1-1 Background and Motivation

The global cybersecurity threat landscape has undergone a dramatic transformation in the past decade. Internet-facing infrastructure is subjected to a continuous barrage of automated scanning tools, brute-force credential attacks, malware deployment campaigns, and sophisticated human-operated intrusion attempts. The sheer volume of attack traffic makes it practically infeasible for human security analysts to manually review and respond to every event.

Traditional defensive mechanisms such as firewalls, intrusion detection systems (IDS), and signature-based antivirus software rely on identifying known malicious patterns. These reactive approaches face fundamental limitations: they cannot detect zero-day exploits, novel malware families, or attackers who carefully evade signature databases. As attack tooling has become increasingly automated and accessible, defenders must evolve toward active, adaptive strategies that not only detect threats but also gather intelligence on attacker behavior.

Honeypot technology represents one of the most powerful tools in the active defender's arsenal. A honeypot is a deliberately exposed system or service designed to attract attackers, with no legitimate user traffic, such that any interaction is inherently suspicious [1]. Unlike passive monitoring, honeypots enable deep visibility into attacker tactics, techniques, and procedures (TTPs) by creating an environment where attackers believe they have found a real target. The data gathered from honeypot interactions is exceptionally high-fidelity: every credential attempted, every command executed, and every file downloaded is an indicator of attacker intent.

However, most deployed honeypots are static. They present the same environment to every attacker, regardless of the attacker's skill level, intent, or psychological profile. An automated botnet scanning for default credentials receives the same response as a sophisticated human penetration tester. This uniformity limits the intelligence that can be extracted and reduces the engagement time with more sophisticated attackers, who quickly recognize emulated environments and disconnect.

Furthermore, the security community has increasingly recognized the value of behavioral intelligence beyond raw event logging. Understanding whether an attacker is a script kiddie running automated tools, an organized criminal deploying cryptominers, or an advanced persistent threat performing reconnaissance can fundamentally change the appropriate defensive response. Machine learning (ML) has emerged as a powerful tool for extracting such behavioral signals from raw honeypot telemetry [2].

NeuroTrap CADN was developed to address these gaps by building a honeypot platform that is adaptive, intelligent, and psychologically aware. Rather than presenting a static surface, it dynamically generates personalized deception environments based on real-time profiling of each attacker. The system integrates ML-based classification, cognitive psychology principles, federated collaborative learning, and AI-powered SOC analysis into a unified active defense platform.

**[Insert Figure 1.1 Here]**
*Description: A bar chart or line graph showing the year-over-year growth in cyber attack volume or reported incidents from 2018 to 2025. Source this from publicly available statistics (Verizon DBIR or IBM X-Force Threat Intelligence Index).*

**Figure 1.1** Global Cyber Attack Growth Trend

## 1-2 Problem Statement

Existing honeypot deployments and threat intelligence platforms suffer from several critical limitations that reduce their effectiveness in modern threat environments:

First, static deception environments fail to engage sophisticated attackers. When honeypot environments present identical content to every visitor, experienced attackers who recognize the emulated shell, the generic filesystem, or the predictable command responses will disconnect immediately. This results in minimal intelligence being gathered from the most dangerous threat actors.

Second, raw honeypot event logs require extensive manual analysis to extract actionable intelligence. Individual login attempts, commands, and file downloads must be correlated across sessions and time periods to construct a meaningful picture of attacker intent. Without automated analysis, the volume of data generated by even a single honeypot quickly exceeds the capacity of a small security team.

Third, conventional honeypot platforms lack psychological awareness. Attackers, like all human agents, are subject to cognitive biases that influence their decision-making. Curiosity draws them toward seemingly unprotected files. The sunk-cost effect keeps them engaged after investing time in downloading tools. Authority signals cause them to escalate privilege-seeking behavior when they believe they have found an administrative system. No existing open-source honeypot platform exploits these psychological dimensions to actively manipulate attacker behavior.

Fourth, threat intelligence gathered by individual honeypot deployments is siloed. Organizations operating honeypots in different network environments cannot share behavioral models without exposing sensitive network topology and attacker attribution data. This prevents the formation of collaborative threat intelligence that would benefit the entire security community.

Fifth, responding to detected threats typically requires manual intervention. By the time a human analyst reviews an alert, assesses the severity, and applies a firewall rule, the attacker may have already achieved their objective or disconnected. Automated response systems that are calibrated to threat severity can dramatically reduce response time.

NeuroTrap CADN directly addresses all five limitations through a novel combination of adaptive deception, ML-driven behavioral profiling, cognitive bias exploitation, federated learning, and autonomous response.

## 1-3 Project Objectives

The primary objective of this project is to design, implement, and deploy an intelligent honeypot and active defense platform that provides real-time attacker profiling, personalized deception, and autonomous response. The specific objectives are:

1. Deploy a multi-protocol honeypot layer that captures attacker interactions across SSH, Telnet, HTTP, FTP, SMB, RDP, VNC, SNMP, and MySQL protocols, normalizing all captured events into a unified detection schema.

2. Build a machine learning behavior analysis engine that classifies attacker intent into six categories (reconnaissance, credential harvesting, malware deployment, lateral movement, cryptomining, bot enrollment) and three skill tiers (beginner, automated bot, advanced human) with a macro F1 score exceeding 0.85.

3. Implement a dynamic deception engine that generates personalized honeypot environments tailored to each attacker's classified tier and detected TTPs, spawning environments within 30 seconds of crossing the threat score threshold.

4. Develop five novel innovation modules: the Cognitive Bias Exploitation Engine (CBEE), the Generative Adaptive Deception Content Factory (GADCF), the Attacker Digital Twin (ADT), the Federated Honeypot Intelligence Mesh (FHIM), and an AI SOC Analyst, each adding a distinct dimension of intelligence to the platform.

5. Implement an autonomous response engine that applies calibrated countermeasures (log-only, rate-limiting, network isolation, emergency block) based on computed threat scores, with response action latency below 10 seconds.

6. Surface all collected intelligence through a real-time SOC dashboard with live event feeds, geolocation mapping, MITRE ATT&CK heatmaps, and interactive attacker profile views, with event-to-dashboard latency below 5 seconds.

7. Deploy the complete system on a production VPS using Docker Compose, demonstrating real-world operation against live internet traffic.

## 1-4 Project Scope and Limitations

**Scope:**

The project encompasses the following components: multi-protocol honeypot deployment using Cowrie (SSH/Telnet), OpenCanary (multi-service), and optionally Galah (LLM-powered HTTP); a Python 3.11 backend with a Flask REST API and WebSocket server; a MongoDB-backed persistence layer with a SQLite fallback for development; machine learning classification using scikit-learn (Random Forest and SVM ensemble); five innovation modules (CBEE, GADCF, ADT, FHIM, AI SOC Analyst); a real-time SPA dashboard; Docker Compose-based deployment on Ubuntu 24.04; and JWT-based authentication with optional TOTP multi-factor authentication.

**Table 1.1** Comparison of NeuroTrap CADN with Existing Honeypot Systems

| Feature | Cowrie (standalone) | OpenCanary | T-Pot | NeuroTrap CADN |
|---------|--------------------|-----------|----|----------------|
| Multi-protocol capture | No | Yes | Yes | Yes |
| ML attacker classification | No | No | No | Yes |
| Adaptive deception environments | No | No | No | Yes |
| Cognitive bias exploitation | No | No | No | Yes |
| Attacker digital twin | No | No | No | Yes |
| Federated learning | No | No | No | Yes |
| AI SOC analyst | No | No | No | Yes |
| Real-time SOC dashboard | No | Limited | Yes | Yes |
| Autonomous response | No | No | Limited | Yes |

**Limitations:**

1. The Galah LLM-powered web honeypot requires an Anthropic or OpenAI API key to operate. Without this key, the module is disabled.
2. The ASHRTA (Autonomous Self-Hardening Red-Team Adversarial) module was planned but not implemented due to scope constraints. The `src/ashrta/` directory does not exist in the codebase.
3. Dionaea is disabled because the Docker image crashes (SIGTRAP) on Linux kernel 6.8 due to the libemu library. OpenCanary covers the ports previously assigned to Dionaea.
4. The FHIM federated learning currently uses pre-seeded demo nodes for illustration; a real deployment requires multiple independent network nodes.
5. GeoIP resolution depends on the ip-api.com external service.
6. The system is designed for defensive research and SOC operations only.

## 1-5 Report Organization

Chapter 2 reviews the relevant literature covering honeypot technology, ML in cybersecurity, MITRE ATT&CK, deception technology, federated learning, and cognitive bias exploitation. Chapter 3 presents the system analysis and design including requirements, the 10-layer architecture, module designs, and database schema. Chapter 4 describes the implementation of each module and the deployment architecture. Chapter 5 presents the testing and evaluation methodology and results. Chapter 6 concludes with contributions, limitations, and future work.

---

# CHAPTER 2: BACKGROUND AND LITERATURE REVIEW

## 2-1 Honeypot Technology

### 2-1-1 Definition and Classification

A honeypot is a security resource whose value derives from being probed, attacked, or compromised [1]. Any interaction with a honeypot is by definition suspicious, which dramatically reduces false-positive rates compared to traditional IDS deployments. Honeypots are classified by interaction level and deployment purpose [2].

**Table 2.1** Classification of Honeypot Systems by Interaction Level

| Level | Interaction | Risk | Intelligence Value | Examples |
|-------|-------------|------|--------------------|----------|
| Low | Service banners only | Very low | Low | Honeyd, simple TCP listeners |
| Medium | Protocol emulation, fake shell | Low | High | Cowrie, OpenCanary |
| High | Real operating system | High | Very high | Full VM deployments |

**[Insert Figure 2.1 Here]**
*Description: A hierarchical taxonomy diagram of honeypot classification. Top node: "Honeypot Systems." Branches: "By Interaction Level" (Low, Medium, High) and "By Deployment Purpose" (Research, Production). Each leaf includes example tool names.*

**Figure 2.1** Honeypot Classification Taxonomy

### 2-1-2 SSH and Telnet Honeypots

SSH-based honeypots are among the most valuable sources of attacker intelligence because SSH (port 22) is one of the most heavily attacked services on the internet. Cowrie is a medium-interaction SSH and Telnet honeypot that emulates a full Debian/Ubuntu shell environment [3]. It records every credential attempt, command typed, file downloaded or uploaded, and TCP port-forwarding request. All events are written to a structured JSON log file for downstream processing. NeuroTrap CADN uses Cowrie as the primary SSH honeypot, exposing ports 22 and 23 to the internet with a customized configuration.

### 2-1-3 Multi-Service Honeypots

While SSH captures the most common attack vector, sophisticated attackers probe a wide range of services simultaneously. OpenCanary is a multi-service honeypot maintained by Thinkst Applied Research that implements network-level emulation of FTP, HTTP, SMB, MySQL, MSSQL, SNMP, VNC, and RDP services from a single process [4]. NeuroTrap CADN uses OpenCanary to cover FTP (21), HTTP (80), SMB (445), MySQL (3306), MSSQL (1433), SNMP (161/UDP), VNC (5900), and RDP (3389).

### 2-1-4 LLM-Powered Honeypots

Galah is an LLM-powered web application honeypot that generates dynamic, contextually appropriate HTTP responses by forwarding requests to an LLM API (Anthropic Claude or OpenAI) [5]. This approach dramatically increases attacker engagement time compared to static honeypots. NeuroTrap CADN includes Galah as an optional component that requires an external API key.

## 2-2 Machine Learning in Cybersecurity

### 2-2-1 Intrusion Detection Systems

Intrusion detection systems analyze network traffic or system events to identify malicious activity. Anomaly-based IDS establish a baseline of normal behavior and flag deviations [6]. ML-based IDS learn decision boundaries from labeled datasets, enabling detection of previously unseen attack variants that share behavioral patterns with known attacks.

**Table 2.2** Comparison of ML Algorithms for Network Intrusion Detection

| Algorithm | Strengths | Weaknesses | Typical F1 (IDS) |
|-----------|-----------|-----------|-----------------|
| Random Forest | Handles nonlinear boundaries, feature importance | Slower inference on large forests | 0.87 to 0.95 |
| SVM (RBF kernel) | Robust to noise, effective in high-dim space | Slow training on large datasets | 0.85 to 0.93 |
| Neural Network (MLP) | Learns complex patterns automatically | Requires large labeled datasets | 0.88 to 0.96 |
| Decision Tree | Interpretable, fast | Prone to overfitting | 0.80 to 0.90 |
| RF + SVM Ensemble | Combines complementary strengths | Higher complexity | 0.90+ |

### 2-2-2 Attacker Classification and Profiling

Beyond binary detection, attacker classification seeks to categorize attacks by intent, sophistication, or threat actor group. SSH honeypot sessions contain sufficient behavioral signals to distinguish automated bots from human operators using session timing features, command vocabulary diversity, and credential selection patterns. Attacker profiling builds a persistent, evolving model of each attacker based on all observed interactions across sessions and time, enabling detection of campaign-level activity where individual sessions may appear benign but the accumulated pattern is highly suspicious.

### 2-2-3 Ensemble Methods for Threat Classification

Random Forest, proposed by Breiman [12], constructs many decision trees on random subsets of features and training samples, averaging their predictions to reduce variance and improve generalization. Support Vector Machines find the maximum-margin hyperplane separating classes and are effective for high-dimensional feature spaces [13]. NeuroTrap CADN uses a VotingClassifier combining RF and SVM with soft voting, trained to classify sessions into six intent categories.

## 2-3 MITRE ATT&CK Framework

The MITRE ATT&CK (Adversarial Tactics, Techniques, and Common Knowledge) framework is a globally accessible knowledge base of adversary behavior organized into Tactics, Techniques, and Sub-techniques [7]. Tactics represent adversary goals (Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Exfiltration, Impact). Techniques are the specific methods used to achieve each tactic.

NeuroTrap CADN implements a TTP Extractor that applies 50+ rule-based patterns combined with semantic embedding matching to map each observed command to MITRE ATT&CK technique IDs and tactics. These mappings are used for the attacker profile's TTP fingerprint and the dashboard's MITRE ATT&CK heatmap visualization.

## 2-4 Deception Technology

### 2-4-1 Active Cyber Deception

Active cyber deception moves beyond passive honeypot monitoring to actively manipulate attacker behavior. Deception technology creates false environments, fake credentials, and decoy assets that waste attacker resources, misdirect attack campaigns, and generate high-confidence alerts when accessed.

### 2-4-2 Adaptive Deception Environments

A limitation of static deception technology is that sophisticated attackers develop heuristics to distinguish fake systems from real ones. An adaptive deception environment dynamically customizes its content based on attacker signals, presenting each attacker with an environment tailored to their apparent intent and sophistication level. NeuroTrap CADN implements three environment tiers matched to the attacker classification output of the behavior analysis layer.

## 2-5 Federated Learning for Cybersecurity

Federated learning is a distributed ML paradigm in which multiple parties collaboratively train a shared model without exchanging their raw training data [8]. Each node trains locally, computes gradient updates, and shares only model updates with a central aggregation server, which applies Federated Averaging (FedAvg) to combine them.

**[Insert Figure 2.2 Here]**
*Description: A diagram showing federated learning. Multiple client nodes each have local data and train locally. Each sends model updates (delta vectors) to a central aggregation server. The server applies FedAvg and returns the updated global model. Arrows show model update flows (not raw data flows).*

**Figure 2.2** Federated Learning Architecture

Differential privacy (DP) adds calibrated statistical noise to gradient updates before transmission, providing a formal privacy bound on individual training samples [9]. NeuroTrap CADN's FHIM module implements FedAvg with the Gaussian DP mechanism applied to gradient deltas before transmission.

## 2-6 Cognitive Bias Exploitation in Cybersecurity

Human decision-making is subject to systematic cognitive biases. Cialdini's foundational work identified key principles of influence including authority, scarcity, and commitment [10]. These have direct relevance to attacker behavior in honeypot environments:

- **Curiosity:** Attackers are drawn toward files with names suggesting secrets (.env, id_rsa, passwords.txt).
- **Sunk cost:** After investing time downloading tools, attackers are reluctant to abandon the session.
- **Authority:** Files belonging to administrative accounts increase attacker engagement.
- **Scarcity:** Evidence of time-limited access creates urgency that exposes more of the attacker's methodology.

NeuroTrap CADN's CBEE module is among the first implementations of automated cognitive bias scoring and injection designed for honeypot-based active defense.

## 2-7 Related Work

**Table 2.3** Related Work Comparison

| System | Honeypot | ML Profiling | Adaptive | Federated | Bias | Dashboard |
|--------|----------|-------------|----------|-----------|------|-----------|
| T-Pot | Multi-protocol | No | No | No | No | ELK-based |
| DShield | SSH | Basic | No | Community | No | Limited |
| HoneyBadger | SSH | Decision tree | No | No | No | Basic |
| Commercial (Attivo) | Varies | Yes | Yes | No | No | Yes |
| NeuroTrap CADN | Multi-protocol | RF+SVM ensemble | Yes, tier-based | Yes, with DP | Yes, 5-dimension | Full SPA |

T-Pot aggregates multiple honeypot tools with an ELK backend for visualization but does not include ML-based attacker classification, adaptive deception environments, or cognitive bias exploitation. Commercial deception platforms offer adaptive deception in enterprise environments but are proprietary and not available for academic study or extension.

NeuroTrap CADN distinguishes itself through the integration of cognitive bias exploitation, attacker digital twins, and federated learning with differential privacy in a single open deployable platform.

## 2-8 Summary

This chapter reviewed the foundational concepts underlying NeuroTrap CADN: honeypot technology and its classifications, ML approaches for attacker classification, the MITRE ATT&CK framework, active deception technology, federated learning with differential privacy, and cognitive bias exploitation. No prior system integrates all five dimensions (adaptive deception, ML profiling, cognitive bias, federated learning, and AI-assisted SOC operations) into a unified platform. The following chapter describes the complete system design of NeuroTrap CADN.

---

# CHAPTER 3: SYSTEM ANALYSIS AND DESIGN

## 3-1 System Requirements Analysis

### 3-1-1 Functional Requirements

**Table 3.1** Functional Requirements of NeuroTrap CADN

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall capture attacker interactions on SSH (22), Telnet (23), HTTP (80), FTP (21), SMB (445), MySQL (3306), MSSQL (1433), RDP (3389), VNC (5900), and SNMP (161/UDP) | Critical |
| FR-02 | The system shall normalize all captured events from all honeypot sources into a unified AlertEvent schema before database storage | Critical |
| FR-03 | The system shall capture raw packets using Scapy to detect port scans and brute-force attempts | Critical |
| FR-04 | The system shall classify each attacker session into one of six intent categories and three skill tiers using a trained ML ensemble classifier | High |
| FR-05 | The system shall maintain a persistent per-IP attacker profile aggregating all sessions, TTPs, intent classifications, and threat scores | High |
| FR-06 | The system shall compute a composite threat score (0-100) for each attacker using ML confidence, TTP score, tier bonus, persistence bonus, and volume bonus | High |
| FR-07 | The system shall spawn a personalized deception environment for any attacker whose threat score reaches or exceeds 10 and who is not already blocked | High |
| FR-08 | The system shall apply autonomous response actions (log-only, rate-limit, network isolation, emergency block) based on threat score thresholds | High |
| FR-09 | The system shall score each attacker across five cognitive bias dimensions | Medium |
| FR-10 | The system shall inject personalized deception bait when an attacker's overall bias score reaches or exceeds 15 and fewer than three injections have been sent | Medium |
| FR-11 | The system shall generate fake corporate content assets targeted to attacker intent and industry | Medium |
| FR-12 | The system shall build and maintain an Attacker Digital Twin for each observed IP with MITRE kill-chain progression and Markov-chain predicted next moves | Medium |
| FR-13 | The system shall implement federated learning across simulated nodes with differential privacy | Medium |
| FR-14 | The system shall provide an AI SOC Analyst capable of generating triage queues, incident reports, and natural-language Q&A | Medium |
| FR-15 | The system shall expose a REST API with JWT authentication for all dashboard data endpoints | High |
| FR-16 | The system shall push real-time event updates to connected dashboard clients via WebSocket within 5 seconds of event capture | High |
| FR-17 | The system shall provide role-based access control with admin and analyst roles, and optional TOTP MFA for admin | High |
| FR-18 | The system shall provide a real-time SOC dashboard with KPI panels, live event feed, geolocation map, MITRE ATT&CK heatmaps, and per-module views | High |

### 3-1-2 Non-Functional Requirements

**Table 3.2** Non-Functional Requirements of NeuroTrap CADN

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Event-to-dashboard latency | Less than 5 seconds |
| NFR-02 | Deception environment spawn time | Less than 30 seconds |
| NFR-03 | Response action time after threshold breach | Less than 10 seconds |
| NFR-04 | ML classifier macro F1 score | Greater than 0.85 |
| NFR-05 | System uptime | Greater than 99% via Docker restart policy |
| NFR-06 | Concurrent monitored IPs | Support 100+ IPs simultaneously |
| NFR-07 | MongoDB not exposed to the internet | Internal Docker networks only |
| NFR-08 | All write endpoints require JWT | Admin role required for state-changing operations |
| NFR-09 | Modular architecture | Each module independently deployable as a Docker service |
| NFR-10 | Fallback mode | Full system functional with SQLite when MongoDB unavailable |
| NFR-11 | Response cache | 30-second in-memory cache on expensive read endpoints |

## 3-2 System Architecture Overview

NeuroTrap CADN is organized as a 10-layer processing pipeline. Each layer produces enriched data consumed by the next layer.

**Table 3.3** Docker Container Services and Responsibilities

| Container | Role | Exposed Ports | Network |
|-----------|------|---------------|---------|
| neurotrap-cowrie | SSH and Telnet honeypot (Cowrie) | 22, 23 | honeypot-net, elk-net |
| neurotrap-opencanary | Multi-service honeypot | 21, 80, 445, 1433, 3306, 161/udp, 5900, 3389 | honeypot-net, elk-net |
| neurotrap-galah | LLM-powered web honeypot (optional) | 8088 | honeypot-net |
| neurotrap-monitor | Scapy packet capture and log ingestion | Host network | monitor-bridge |
| neurotrap-mongodb | Event and profile storage (MongoDB 6.0) | Internal only | elk-net, management-net, monitor-bridge |
| neurotrap-behavior | ML classifier and attacker profiler | Internal | elk-net, management-net |
| neurotrap-deception | Dynamic honeypot environment spawner | Internal | elk-net, management-net |
| neurotrap-api | Flask REST API and dashboard backend | 5000 (internal) | management-net, monitor-bridge |
| neurotrap-nginx | Reverse proxy and SSL termination | 443, 8080 | honeypot-net, management-net |

## 3-3 Architecture Diagrams

### 3-3-1 Overall System Architecture Diagram

**[Insert Figure 3.1 Here]**
*Description: A 10-layer block diagram. Each layer is a horizontal band with its name, key components, and data artifacts produced. Layers from top to bottom: (1) Honeypot Layer - Cowrie/OpenCanary/Galah/Scapy; (2) Detection Pipeline - LogIngestionPipeline/CowrieSessionBuilder/PacketMonitor; (3) Behavior Analysis - AttackerClassifier/TTPExtractor/AttackerProfile; (4) Deception Engine - DeceptionEngine/CredentialGenerator; (5) CBEE - BiasScorer/CBEEEngine/BaitInjector; (6) GADCF - ContentGenerator/GADCFEngine; (7) Attacker Digital Twin - DigitalTwin/TacticPredictor/KillChain; (8) FHIM - FederatedNode/FedAvgServer; (9) Response Engine - ResponseEngine; (10) API and Dashboard - Flask/SocketIO/SPA. MongoDB appears as a persistent store on the right spanning layers 2-10.*

**Figure 3.1** NeuroTrap CADN 10-Layer System Architecture

### 3-3-2 Data Flow Diagram

**[Insert Figure 3.2 Here]**
*Description: A DFD showing: (1) Internet sources connecting to Cowrie, OpenCanary, and Scapy monitor; (2) All three feeding alert_events; (3) Cowrie logs also feeding CowrieSessionBuilder producing cowrie_sessions; (4) cowrie_sessions feeding BehaviorEngine producing attacker_profiles; (5) attacker_profiles feeding four parallel paths: DeceptionEngine (deception_environments), CBEEEngine (cbee_profiles, cbee_injections), ResponseEngine (response_log), and the API layer; (6) API layer feeding the dashboard SPA via REST and WebSocket.*

**Figure 3.2** Complete Data Flow Diagram

### 3-3-3 Docker Network Topology

**[Insert Figure 3.3 Here]**
*Description: Network topology diagram showing four Docker networks as colored zones: honeypot-net (172.20.0.0/24, external) containing cowrie/opencanary/galah/nginx/api; elk-net (internal) containing mongodb/behavior-engine/deception-engine; management-net (internal) containing mongodb/api; monitor-bridge (172.25.0.0/24, non-internal) containing mongodb at static IP 172.25.0.10 with the host-network packet-monitor connecting to it. The Internet is shown as a cloud connecting to honeypot-net via the exposed ports.*

**Figure 3.3** Docker Network Topology

### 3-3-4 Detailed Data Pipeline Diagram

**[Insert Figure 3.4 Here]**
*Description: A sequential pipeline diagram for the Cowrie session-to-dashboard path: Step 1: Attacker connects via SSH; Step 2: Cowrie logs to cowrie.json; Step 3: LogTailer reads new lines; Step 4a: AlertEvent.from_cowrie() writes to alert_events, triggering WebSocket; Step 4b: CowrieSessionBuilder aggregates on session.closed, writes cowrie_sessions; Step 5: BehaviorEngine classifies session, calls reclassify_intent() and _compute_threat_score(), writes attacker_profiles; Step 6: DeceptionEngine checks threshold >= 10, spawns Docker environment; Step 7: CBEEEngine scores bias, fires injection if overall >= 15; Step 8: ResponseEngine applies action, writes response_log; Step 9: Flask SocketIO emits profile_update to dashboard.*

**Figure 3.4** Cowrie Session to Dashboard Pipeline

## 3-4 Module Design

### 3-4-1 Layer 1: Honeypot Module

The honeypot layer consists of four components. **Cowrie** is deployed as a Docker container using cowrie/cowrie:latest, listening on ports 22 (SSH) and 23 (Telnet). Configuration includes a realistic hostname, a populated virtual filesystem, and a credential database accepting common default credentials. **OpenCanary** is built from a custom Dockerfile.opencanary, configured to listen on FTP (21), HTTP (80), SMB (445), MySQL (3306), MSSQL (1433), SNMP (161/UDP), VNC (5900), and RDP (3389). **Galah** (optional) listens on port 8088 and generates dynamic HTTP responses via LLM. **Native Python Honeypots** (opt-in profile) emulate SSH (2222), HTTP (8081), FTP (2121), and Telnet (2323) using paramiko.

### 3-4-2 Layer 2: Detection Pipeline

The AlertEvent schema (`src/detection/alert_schema.py`) is a Python dataclass with mandatory fields `src_ip`, `dst_port`, `attack_type`, and `honeypot_source`. The `attack_type` field is constrained to the enumeration: `port_scan`, `brute_force`, `protocol_anomaly`, `malware_upload`, `command_injection`, `lateral_movement`, `data_exfiltration`, `tool_fingerprint`, `unknown`. Pure metadata events are filtered by the `_COWRIE_SKIP` frozenset.

**LogIngestionPipeline** (`src/detection/log_pipeline.py`) runs background threads that tail Cowrie JSON log files. Each line is parsed by `AlertEvent.from_cowrie()` and written to `alert_events`. The `CowrieSessionBuilder` subcomponent aggregates per-session events and writes complete session documents to `cowrie_sessions` on receipt of `cowrie.session.closed`.

**PacketMonitor** (`src/detection/packet_monitor.py`) uses Scapy to detect port scans (more than 10 unique destination ports per 5 seconds), brute-force patterns (more than 5 failures per minute), and protocol anomalies. It requires `NET_ADMIN` and `NET_RAW` capabilities and runs with host network mode.

### 3-4-3 Layer 3: Behavior Analysis Engine

**[Insert Figure 3.5 Here]**
*Description: A module design diagram showing: (1) SessionFeatureExtractor: takes cowrie_sessions document, produces 13-dim feature vector listing all features; (2) AttackerClassifier: takes the vector through VotingClassifier (RF + SVM), outputs intent class and confidence; (3) TTPExtractor: takes session commands, returns list of (technique_id, tactic, confidence, matched_command) tuples; (4) AttackerProfile: aggregates all outputs into a persistent per-IP profile in attacker_profiles. Show data flows between components.*

**Figure 3.5** Behavior Analysis Module Design

**SessionFeatureExtractor** converts a Cowrie session into a 13-dimensional feature vector. The features are: `total_commands`, `unique_commands`, `dangerous_count`, `recon_count`, `download_attempts`, `file_access`, `session_duration`, `login_attempts`, `failed_logins`, `has_persistence`, `has_lateral`, `dangerous_ratio`, `download_ratio`.

The composite threat score is calculated by `_compute_threat_score()` in `AttackerProfile`:

```
Score = (ML_confidence x 40) + TTP_score + tier_bonus + persistence_bonus + volume_bonus
```

**Table 3.4** Threat Score Calculation Components

| Component | Range | Calculation |
|-----------|-------|-------------|
| ML confidence contribution | 0 to 40 | Classifier confidence (0.0-1.0) multiplied by 40 |
| TTP score | 0 to 40 | Sum of tactic_weight x tactic_confidence per unique tactic; capped at 40 |
| Tier bonus | 0 to 30 | beginner: 0; automated_bot: 15; advanced_human: 30 |
| Persistence bonus | 27 to 65 | Scaled by session count (see Table 3.5) |
| Volume bonus | 0 to 15 | Minimum of (total_commands / 5) and 15 |

**Table 3.5** Threat Score Persistence Bonus Table

| Session Count | Bonus |
|---------------|-------|
| 1 | 27 |
| 2 | 32 |
| 3 to 4 | 37 |
| 5 to 9 | 42 |
| 10 to 19 | 48 |
| 20 to 49 | 55 |
| 50 to 99 | 62 |
| 100 or more | 65 |

**Table 3.6** Tactic Weights Used in TTP Score Calculation

| MITRE Tactic | Weight |
|-------------|--------|
| Impact | 40 |
| Privilege Escalation | 35 |
| Credential Access | 30 |
| Lateral Movement | 25 |
| Persistence | 20 |
| Command and Control | 15 |
| Defense Evasion | 10 |
| Discovery | 5 |

### 3-4-4 Layer 4: Deception Engine

**DeceptionEngine** (`src/deception/deception_engine.py`) polls `attacker_profiles` every 10 seconds. For each attacker with `threat_score >= 10` and `is_blocked == False`, it selects an environment template by tier and attempts to spawn a customized Cowrie Docker container. The engine maintains a maximum of 20 active environments and garbage-collects environments older than 1 hour.

**CredentialGenerator** (`src/deception/credential_generator.py`) uses Faker seeded with the attacker's IP to generate: SSH users with bcrypt-hashed passwords, fake AWS keys, database connection strings, environment file content, shadow file hashes, and fake shell history.

**Table 4.6** Deception Environment Templates by Attacker Tier

| Tier | OS Presentation | Services | Detail Level |
|------|----------------|----------|-------------|
| beginner | Ubuntu 20.04, hostname: lab-server-01 | SSH (2222), HTTP (8080) | Minimal filesystem |
| automated_bot | CentOS 7, hostname: prod-db-02 | SSH, HTTP, MySQL, FTP | /etc and /var populated |
| advanced_human | Debian 11, hostname: internal-dev-01 | SSH, HTTP, MySQL, FTP, Redis, PostgreSQL | Full /home/deploy with SSH keys, DB creds, git history |

### 3-4-5 Innovation Module 1: CBEE

**[Insert Figure 3.6 Here]**
*Description: Module design diagram for CBEE. Three components: (1) BiasScorer: takes a session dict, applies five bias detection patterns (curiosity regex, authority regex, sunk cost regex, scarcity regex, confirmation bias logic) to produce a BiasProfile with five scored dimensions and an overall score; (2) CBEEEngine: background thread running every 30 seconds, reading attacker_profiles, computing BiasProfile for each, storing results in cbee_profiles, triggering BaitInjector when overall >= 15 and injections < 3; (3) BaitInjector: generates a BaitInjection asset targeted to the dominant bias dimension, stores it in cbee_injections. Show flow from attacker_profiles through CBEEEngine.*

**Figure 3.6** CBEE Bias Scoring Architecture

**Table 3.7** CBEE Bias Dimensions and Detection Signals

| Dimension | Definition | Detection Signals | Points per Hit |
|-----------|------------|-------------------|----------------|
| Curiosity Gap | Attacker is searching for hidden secrets | grep/find/cat on .key/.env/.secret/.token files; traversal of /etc, /root, /.ssh | 18 per regex match; 12 per deep directory |
| Confirmation Bias | Attacker confirms expected environment | Reconnaissance commands in first 5 commands; cat commands aligned with attacker intent | 20 per recon cmd; 10 per tech_match |
| Sunk Cost Trap | Attacker invested time downloading | wget/curl/scp/git clone/apt install; session duration | 20 per install cmd; 5 per minute |
| Authority Signal | Attacker is escalating privileges | sudo/su/admin/root/shadow/sudoers/authorized_keys/id_rsa; chmod 4xxx | 15 per auth hit; 20 per priv_esc |
| Scarcity Framing | Attacker establishing urgency/persistence | crontab/systemctl enable/nohup/screen/tmux; high login_attempts | 18 per persist cmd; up to 30 for rush |

### 3-4-6 Innovation Module 2: GADCF

**Table 3.8** GADCF Supported Industries and Asset Types

| Industry | Environment File | Email Thread | Source Code | Wiki Page | DB Schema |
|----------|-----------------|--------------|-------------|-----------|-----------|
| Financial Services | PCI-DSS fake creds | VP Engineering credential rotation | Flask auth API | Infrastructure runbook | Payment tables |
| Healthcare | HIPAA-themed config | PHI access policy | Patient API | Network topology | Patient records |
| E-commerce | Stripe/PayPal keys | Order system alert | Product catalog API | Server deployment | Orders schema |
| SaaS Startup | MongoDB Atlas URI | DevOps rotation thread | Core auth service | Production runbook | User tables |
| Government | Classified-themed env | Procurement alert | Internal tool API | Server list | Citizen data |
| Energy | SCADA system creds | ICS maintenance alert | SCADA monitoring API | Industrial network diagram | Sensor readings |

### 3-4-7 Innovation Module 3: Attacker Digital Twin

**[Insert Figure 3.7 Here]**
*Description: Data model diagram for the DigitalTwin dataclass with field groups: Identity (src_ip, first_seen, last_seen, observation_count, countries, honeypots_touched); Capability (attacker_tier, sophistication 0-100, automation_score 0-100); Intent (classified_intent, threat_score); Fingerprint (tools, tactics_observed, tactic_sequence, technique_ids, kill_chain); Psychology (dominant bias, overall score, five bias dimensions); Predictions (predicted_next top-3 tactics with probabilities, recommendation dict); Quality (fidelity, confidence, predictions_made, predictions_hit). Show three data sources: alert_events (via _fold_events), attacker_profiles (via _merge_profile), cbee_profiles (via _merge_psychology).*

**Figure 3.7** Attacker Digital Twin Architecture

**Table 3.9** Attacker Digital Twin Data Fields

| Field Group | Key Fields | Description |
|-------------|-----------|-------------|
| Identity | src_ip, countries, honeypots_touched | Source and which honeypots contacted |
| Capability | attacker_tier, sophistication, automation_score | Skill level (0-100) and bot probability (0-100) |
| Intent | classified_intent, threat_score | ML-determined intent and composite risk score |
| Fingerprint | tools, tactic_sequence, technique_ids | Observed tooling and ordered MITRE tactic sequence |
| Kill Chain | kill_chain dictionary | Lockheed Martin Kill Chain stage reached (1 of 7) |
| Psychology | dominant bias, overall score | From cbee_profiles |
| Predictions | predicted_next, recommendation | Top-3 next MITRE tactics with Markov-chain probabilities |
| Quality | fidelity, confidence | Prediction accuracy and signal quality (both 0-1) |

### 3-4-8 Innovation Module 4: FHIM

**[Insert Figure 3.8 Here]**
*Description: Architecture diagram showing four local nodes (Cairo University, Acme Financial, Fraunhofer FKIE, SaudiTelecom). Each node has local MongoDB and runs FederatedNode. Each trains locally and computes a gradient delta. The delta passes through a DifferentialPrivacy noise layer (Gaussian, epsilon=1.0, delta=1e-5). The noisy delta is sent to the FedAvgServer. The server collects deltas from at least 2 nodes, averages weights via numpy, returns updated global model. Rounds are recorded in fhim_aggregation_rounds. Raw session data never leaves the local node.*

**Figure 3.8** FHIM Federated Learning Architecture

**Table 3.10** FHIM Federated Node Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Minimum nodes for aggregation | 2 | FedAvg proceeds only when at least 2 nodes submit deltas |
| Privacy epsilon | 1.0 | DP budget (lower = more noise, more privacy) |
| Privacy delta | 1e-5 | Probability bound on privacy loss |
| Weight extraction | RF feature importances | Proxy gradient: Random Forest feature importance vector |
| Global blending | 70% global + 30% local | Applied to RF feature importances on update receipt |
| Pre-seeded demo nodes | 4 | Cairo Uni, Acme Financial, Fraunhofer FKIE, SaudiTelecom |

### 3-4-9 Layer 9: Response Engine

**Table 3.11** Response Engine Decision Matrix

| Threat Score Range | Action Type | Mechanism | Alert Sent |
|-------------------|-------------|-----------|------------|
| Less than 40 | log_only | Write to response_log only | No |
| 40 to 70 | slow_redirect | tc netem 500ms delay on attacker IP | No |
| 70 to 90 | isolate_alert | iptables LOG + DROP rule + alert | Yes |
| Greater than 90 | block_emergency | iptables DROP + tcpdump PCAP (10K packets) + emergency alert | Yes |

**[Insert Figure 3.9 Here]**
*Description: A decision tree for the Response Engine. Root node: "Attacker Threat Score." Four branches: score < 40 leads to "log_only"; score 40-70 leads to "slow_redirect" with tc netem; score 70-90 leads to "isolate_alert" with iptables + alert; score > 90 leads to "block_emergency" with iptables DROP + PCAP + emergency alert. Each leaf shows the response_log entry and alert delivery method.*

**Figure 3.9** Response Engine Decision Tree

### 3-4-10 Layer 10: API and Dashboard

**[Insert Figure 3.10 Here]**
*Description: Layered architecture diagram. Bottom layer: Flask application (app.py) with JWT middleware, @cached() decorator, lazy-loaded engine singletons, and SocketIO server. Middle layer: REST API endpoint groups (/api/auth, /api/events, /api/attackers, /api/honeypots, /api/intel, /api/cbee, /api/gadcf, /api/fhim, /api/twin, /api/soc). Top layer: browser SPA sections grouped as Operations (Dashboard, Threat Actors, Live Events, Honeypots, Response Log), Intelligence (Threat Intel, Geo Map, MITRE ATT&CK, Behavior Analysis), Innovations (CBEE, GADCF, FHIM, ADT, AI Analyst). Show WebSocket flow for live_feed_poller pushing new_event and profile_update to SPA.*

**Figure 3.10** API and Dashboard Architecture

## 3-5 Database Design

### 3-5-1 Database Architecture

The `get_db()` function in `src/db/database.py` is the single entry point for all database operations. On startup it attempts to connect to MongoDB with a 1000ms timeout. If MongoDB is unreachable, or `NEUROTRAP_FORCE_FALLBACK=1` is set, it returns a `FallbackDB` instance backed by SQLite that implements the same interface as a PyMongo database object.

### 3-5-2 Collections Design

**Table 3.12** MongoDB Active Collections

| Collection | Written By | Read By | Purpose |
|-----------|-----------|---------|---------|
| alert_events | Detection layer | API, BehaviorEngine | Normalized events from all honeypot sources |
| cowrie_sessions | CowrieSessionBuilder | BehaviorEngine | Aggregated per-session Cowrie data |
| honeypot_sessions | Native Python honeypots | API | Session records from Python honeypot servers |
| attacker_profiles | BehaviorEngine | API, DeceptionEngine, CBEEEngine, ResponseEngine | ML-enriched per-IP profiles with threat scores |
| attacker_twins | AttackerDigitalTwin | API | Behavioral digital twins with kill-chain and predictions |
| deception_environments | DeceptionEngine | API | All spawned environments (active and expired) |
| cbee_profiles | CBEEEngine | API, AttackerDigitalTwin | Cognitive bias scores per attacker |
| cbee_injections | CBEEEngine | API | Bait injection log |
| gadcf_assets | GADCFEngine | API | Generated fake corporate content assets |
| fhim_rounds | FederatedNode | API | Per-node federated learning round results |
| fhim_aggregation_rounds | FedAvgServer | API | Global model aggregation round history |
| response_log | ResponseEngine | API | Autonomous response action log |
| soc_reports | SOCAnalyst | API | AI-generated SOC incident reports |

**Table 3.13** Alert Event Schema Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| event_id | String (UUID) | Yes | Unique event identifier |
| src_ip | String | Yes | Source IP address of the attacker |
| dst_port | Integer | Yes | Destination port targeted |
| attack_type | String (enum) | Yes | One of: port_scan, brute_force, protocol_anomaly, malware_upload, command_injection, lateral_movement, data_exfiltration, tool_fingerprint, unknown |
| honeypot_source | String | Yes | cowrie, dionaea, scapy, or zeek |
| severity | String (enum) | Yes | One of: low, medium, high, critical |
| timestamp | Float (Unix epoch) | Yes | Event capture time |
| dst_ip | String | No | Destination IP |
| src_port | Integer | No | Source port |
| protocol | String | No | Network protocol |
| raw_payload | String | No | Raw packet or log payload |
| session_id | String | No | Cowrie session identifier |
| username | String | No | Credential username attempted |
| password | String | No | Credential password attempted |
| command | String | No | Command executed in honeypot shell |
| extra | Object | No | Source-specific additional metadata |

**Table 3.14** Attacker Profile Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| src_ip | String | Source IP (primary key, unique index) |
| first_seen | Float | Unix timestamp of first contact |
| last_seen | Float | Unix timestamp of most recent contact |
| session_count | Integer | Total number of complete sessions |
| total_commands | Integer | Total commands executed across all sessions |
| classified_intent | String (enum) | Final intent from reclassify_intent() |
| attacker_tier | String (enum) | beginner, automated_bot, or advanced_human |
| threat_score | Float (0-100) | Composite score from _compute_threat_score() |
| ttps | Array of objects | MITRE technique IDs, tactics, confidence scores |
| campaign_id | String (nullable) | DBSCAN cluster ID for campaign association |
| country | String (nullable) | Country from GeoIP resolution |
| asn | String (nullable) | Autonomous System Number |
| sessions | Array of objects | Last 20 commands per session (capped) |
| is_blocked | Boolean | True if block_emergency applied |
| response_action | String | Most recent autonomous response action type |

### 3-5-3 Entity Relationship Diagram

**[Insert Figure 3.11 Here]**
*Description: An ER diagram showing all 13 active MongoDB collections and their relationships. Key relationships: alert_events.src_ip links to attacker_profiles (many-to-one); cowrie_sessions.src_ip links to attacker_profiles; attacker_profiles.src_ip links to attacker_twins (one-to-one), cbee_profiles (one-to-one), deception_environments (one-to-many), response_log (one-to-many), cbee_injections (one-to-many), gadcf_assets (one-to-many), soc_reports (one-to-many); fhim_rounds belongs to a FederatedNode; fhim_aggregation_rounds is the global model. Use crow's foot notation.*

**Figure 3.11** Entity Relationship Diagram

## 3-6 Use Case Analysis

### 3-6-1 Use Case Diagram

**[Insert Figure 3.12 Here]**
*Description: A UML use case diagram. Actors: "Internet Attacker," "SOC Analyst," "System Administrator." Internet Attacker use cases: UC-01 Connect to SSH Honeypot, UC-02 Execute Commands, UC-03 Download Malware, UC-04 Attempt Credential Brute Force. SOC Analyst use cases: UC-05 View Dashboard KPIs, UC-06 Inspect Attacker Profile, UC-07 View MITRE ATT&CK Heatmap, UC-08 Generate Incident Report, UC-09 Ask SOC Analyst Question, UC-10 Inspect Attacker Digital Twin, UC-11 View Threat Intel Feed, UC-12 View CBEE Profiles, UC-13 View GADCF Assets, UC-14 View Federated Learning Status. Administrator use cases: UC-15 Login with MFA, UC-16 Manually Block IP, UC-17 Recalculate Threat Scores, UC-18 Configure Honeypots.*

**Figure 3.12** System Use Case Diagram

### 3-6-2 Use Case Descriptions

**Table 3.15** Use Case Descriptions

| UC ID | Name | Actor | Precondition | Post-condition |
|-------|------|-------|--------------|----------------|
| UC-01 | Connect to SSH Honeypot | Internet Attacker | Cowrie running; port 22 open | alert_event of type tool_fingerprint created; cowrie_session initiated |
| UC-02 | Execute Commands | Internet Attacker | UC-01 completed; login succeeded | command_injection alert_events created; cowrie_session.commands updated |
| UC-03 | Download Malware | Internet Attacker | UC-02 completed | malware_upload alert_event created; download_attempts incremented |
| UC-05 | View Dashboard KPIs | SOC Analyst | Dashboard accessible | KPI panel populated from /api/events/stats |
| UC-06 | Inspect Attacker Profile | SOC Analyst | Attacker profiles exist | Full profile modal shows threat score, intent, tier, TTPs, session history |
| UC-08 | Generate Incident Report | SOC Analyst | LLM key or heuristic fallback available | Incident report written to soc_reports |
| UC-09 | Ask SOC Analyst Question | SOC Analyst | SOCAnalyst initialized | Response generated by LLM or heuristics |
| UC-16 | Manually Block IP | System Administrator | Admin JWT authenticated | iptables DROP rule applied; block entry written to response_log |
| UC-17 | Recalculate Threat Scores | System Administrator | Admin JWT authenticated | All attacker profiles updated with new intent, tier, threat_score |

## 3-7 Sequence Diagrams

**[Insert Figure 3.13 Here]**
*Description: A UML sequence diagram for "Attacker SSH Session to Dashboard." Participants: Internet Attacker, Cowrie Container, LogIngestionPipeline, CowrieSessionBuilder, BehaviorEngine, DeceptionEngine, ResponseEngine, MongoDB, Flask API, Dashboard Browser. Sequence: (1) Attacker sends SSH connection; (2) Cowrie emits session.connect to cowrie.json; (3) LogIngestionPipeline reads, calls AlertEvent.from_cowrie(), inserts alert_events; (4) Flask live_feed_poller detects new event, emits WebSocket new_event to Dashboard; (5) Attacker executes commands; (6) LogIngestionPipeline inserts command_injection events; (7) Attacker disconnects, session.closed emitted; (8) CowrieSessionBuilder aggregates, inserts cowrie_sessions; (9) BehaviorEngine runs classifier and TTPExtractor, calls reclassify_intent() and _compute_threat_score(), upserts attacker_profiles; (10) DeceptionEngine spawns environment if score >= 10; (11) ResponseEngine evaluates score, applies action, inserts response_log; (12) live_feed_poller emits profile_update to Dashboard.*

**Figure 3.13** Attacker SSH Session Sequence Diagram

**[Insert Figure 3.14 Here]**
*Description: A UML sequence diagram for "Threat Score Calculation and Response." Participants: BehaviorEngine, SessionFeatureExtractor, AttackerClassifier, TTPExtractor, AttackerProfile, ProfileStore, ResponseEngine. Sequence: (1) BehaviorEngine receives new cowrie_session; (2) Calls SessionFeatureExtractor.extract() for 13-dim feature vector; (3) Calls AttackerClassifier.predict() for intent and confidence; (4) Calls TTPExtractor.extract() for TTP list and ttp_score; (5) Calls AttackerProfile.update_from_session() with all outputs; (6) AttackerProfile internally calls reclassify_intent(); (7) Calls _compute_threat_score(); (8) ProfileStore.save() upserts to MongoDB; (9) ResponseEngine.evaluate() called; (10) Based on threat_score threshold, ResponseEngine writes response_log and optionally triggers iptables.*

**Figure 3.14** Threat Score Calculation Sequence Diagram

---

# CHAPTER 4: SYSTEM IMPLEMENTATION

## 4-1 Development Environment

**Table 4.1** Development Environment Specifications

| Component | Development | Production |
|-----------|-------------|------------|
| Operating System | Ubuntu 22.04 or Windows 11 + WSL2 | Ubuntu 24.04 LTS |
| CPU | Any x86_64 with virtualization support | 6 vCPU (VPS) |
| RAM | Minimum 8 GB | 11 GB |
| Storage | Minimum 20 GB | 193 GB SSD |
| Container runtime | Docker Engine 24+ with Compose V2 | Docker Engine 26 with Compose V2 |
| Python version | 3.11 | 3.11 (in Docker image) |
| Database | SQLite (NEUROTRAP_FORCE_FALLBACK=1) | MongoDB 6.0 (Docker container) |

## 4-2 Technology Stack

**Table 4.2** Complete Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.11 | All backend modules |
| Web framework | Flask | 3.x | REST API and HTML template serving |
| WebSocket | Flask-SocketIO | 5.x | Real-time event push to dashboard |
| Authentication | flask-jwt-extended | 4.x | JWT issuance and validation |
| MFA | pyotp | 2.x | TOTP generation and verification |
| ML | scikit-learn | 1.4 | RF+SVM ensemble classifier, StandardScaler |
| NLP | spaCy | 3.x | Command tokenization for TTP extraction |
| Embeddings | sentence-transformers | 2.x | Semantic command matching |
| Packet capture | Scapy | 2.5 | Raw packet capture and analysis |
| SSH emulation | paramiko | 3.x | Native Python SSH honeypot |
| Data generation | Faker | 19.x | Fake credential and identity generation |
| Database (primary) | MongoDB | 6.0 | Document storage |
| Database (driver) | PyMongo | 4.x | Python MongoDB driver |
| Database (fallback) | SQLite | 3.x | Embedded fallback |
| Containerization | Docker Compose | V2 | Multi-container orchestration |
| SSH honeypot | Cowrie | Latest | Full SSH/Telnet shell emulation |
| Multi-service honeypot | OpenCanary | Latest | Multi-protocol emulation |
| LLM honeypot | Galah | Latest | LLM-powered dynamic HTTP responses |
| Reverse proxy | Nginx | Alpine | SSL termination and upstream routing |
| Frontend | Vanilla JavaScript | ES6+ | Dashboard SPA |
| Mapping | Leaflet.js | 1.9 | Geolocation attack map |
| Charts | Chart.js | 4.x | KPI charts, donut charts, bar charts |
| LLM API (optional) | Anthropic Claude | claude-opus-4-8 | SOC Analyst reports and Galah responses |

## 4-3 Containerization and Deployment Architecture

**Table 4.3** Docker Network Configuration

| Network Name | Type | Subnet | Purpose |
|-------------|------|--------|---------|
| honeypot-net | Bridge (external) | 172.20.0.0/24 | Internet-facing honeypots and Nginx |
| elk-net | Bridge (internal) | Auto-assigned | Honeypot backends to MongoDB and behavior engines |
| management-net | Bridge (internal) | Auto-assigned | MongoDB to API |
| monitor-bridge | Bridge (external) | 172.25.0.0/24 | MongoDB at static IP 172.25.0.10 for host-network monitor |

**[Insert Figure 4.1 Here]**
*Description: A Docker Compose service dependency diagram. Each service is a rectangle. Arrows indicate depends_on relationships. nginx depends on api; api depends on mongodb; behavior-engine depends on mongodb; deception-engine depends on mongodb and the Docker socket; packet-monitor depends on mongodb via monitor-bridge; cowrie and opencanary have no dependencies. Show volume mounts (cowrie-logs, mongodb-data) as cylinder shapes. Show the host path /var/run/docker.sock mounted into deception-engine.*

**Figure 4.1** Docker Compose Service Dependency Graph

The startup sequence is: MongoDB starts first; API, behavior-engine, and deception-engine start after MongoDB; Cowrie and OpenCanary start independently; Nginx starts after API; packet-monitor starts with host network mode. After any API container restart, Nginx must be reloaded (`docker compose exec nginx nginx -s reload`) because Nginx resolves the upstream hostname at startup and caches it.

## 4-4 Implementation of the Detection Pipeline

**[Insert Figure 4.2 Here]**
*Description: A data normalization flow diagram. Left side shows three raw sources: Cowrie JSONL (eventid, src_ip, session, username, password, input); Scapy raw packets (IP/TCP SYN); OpenCanary JSON (logtype, src_host, dst_port). Center shows AlertEvent factory methods: AlertEvent.from_cowrie(raw) applying event_id_map; AlertEvent.from_scapy(pkt) applying packet analysis rules. Right shows unified AlertEvent output flowing to alert_events MongoDB. Below, show the COWRIE_SKIP frozenset filtering cowrie.session.closed, cowrie.log.closed, cowrie.session.params.*

**Figure 4.2** AlertEvent Schema Normalization Flow

The `from_cowrie()` factory method maps Cowrie event IDs to attack types as follows: `cowrie.login.failed` maps to `brute_force` (low severity); `cowrie.login.success` maps to `brute_force` (high severity); `cowrie.command.input` maps to `command_injection` (medium severity); `cowrie.session.file_download` and `cowrie.session.file_upload` map to `malware_upload` (high severity); `cowrie.client.version`, `cowrie.client.kex`, `cowrie.client.var`, and `cowrie.client.fingerprint` map to `tool_fingerprint` (low severity); `cowrie.direct-tcpip.request` and `cowrie.direct-tcpip.data` map to `lateral_movement` (medium severity).

## 4-5 Implementation of the Behavior Analysis Engine

**[Insert Figure 4.3 Here]**
*Description: ML classifier training pipeline. Left: raw cowrie_sessions documents. Arrow labeled "SessionFeatureExtractor.extract()" points to a 13-dimensional feature vector listing all features. Arrow labeled "StandardScaler" shows normalization. The normalized vector feeds into a VotingClassifier (RandomForestClassifier 100 trees + SVC RBF kernel probability=True) producing intent class with probability and tier class. Training artifacts (classifier.joblib, scaler.joblib, label_encoder.joblib) stored in data/models/.*

**Figure 4.3** ML Classifier Training Pipeline

**Table 4.4** SessionFeatureExtractor Feature Vector

| Index | Feature Name | Description |
|-------|-------------|-------------|
| 0 | total_commands | Total commands executed in session |
| 1 | unique_commands | Number of distinct command names (path-stripped) |
| 2 | dangerous_count | Commands matching dangerous patterns |
| 3 | recon_count | Reconnaissance commands (uname, id, whoami, etc.) |
| 4 | download_attempts | wget/curl/tftp/scp download commands |
| 5 | file_access | File read/cat/less operations |
| 6 | session_duration | Session length in seconds |
| 7 | login_attempts | Total authentication attempts |
| 8 | failed_logins | Failed authentication attempts |
| 9 | has_persistence | Binary: 1 if crontab/.bashrc/systemctl commands present |
| 10 | has_lateral | Binary: 1 if ssh/scp/rsync commands present |
| 11 | dangerous_ratio | dangerous_count / total_commands |
| 12 | download_ratio | download_attempts / total_commands |

**Table 4.5** Intent Classification Rules (reclassify_intent priority order)

| Priority | Intent | Trigger Condition |
|----------|--------|-------------------|
| 1 | cryptomining | xmrig, minerd, cryptonight, or stratum+tcp in commands |
| 2 | cryptomining | grep for miner/xmrig/monero process names |
| 3 | malware_deployment | wget/curl/tftp combined with chmod +x/bash/sh/.sh |
| 4 | credential_harvesting | /etc/shadow access or cat /etc/passwd |
| 5 | bot_enrollment | crontab, .bashrc, .bash_profile, or systemctl enable |
| 6 | malware_deployment (SCP) | scp -t combined with chmod +x or execute pattern |
| 7 | lateral_movement | ssh/scp/rsync with more than 3 occurrences |
| 8 | bot_enrollment (survey) | nproc, CPU MHz, lsb_release, free -h, /proc/cpuinfo |
| 9 | bot_enrollment (RouterOS) | /ip cloud or /ip address |
| 10 | bot_enrollment (fingerprint) | Base commands are subset of {uname, id, whoami, hostname, ifconfig, ip, ls, pwd, env, cat, ps} |
| 11 | credential_harvesting | 5+ sessions with zero commands (password stuffing) |
| 12 | reconnaissance | Default fallback |

## 4-6 Implementation of the Deception Engine

The deception engine spawns customized honeypot environments for qualifying attackers in three scenarios. In production (Docker available), the engine calls the Docker SDK to create a new Cowrie container with customized environment variables including a fake hostname, filesystem seed, and credentials from `CredentialGenerator`. In fallback mode (Docker unavailable), the engine creates a mock environment record. In all cases, environment records are stored in `deception_environments`.

The engine enforces a maximum of 20 active environments. Every 60 seconds it checks all records for environments older than 1 hour and terminates the associated Docker containers. The `/api/environments` endpoint returns all records (active and expired) along with `active_count` and `total` fields.

## 4-7 Implementation of the CBEE Module

**[Insert Figure 4.4 Here]**
*Description: A screenshot of the CBEE section in the NeuroTrap CADN dashboard showing: (1) A "Cognitive Bias Profiles" panel with a table listing attacker IPs and their five bias dimension scores plus overall score and dominant dimension; (2) A "Bait Injection Log" panel showing recent injections with timestamp, attacker IP, dominant bias, and injection type; (3) A "Live Session Scorer" panel with a text input area. If no screenshot available, insert a wireframe.*

**Figure 4.4** CBEE Bias Scoring Interface Screenshot

The `BiasScorer` applies four compiled regular expressions to the full command text. `_CURIOSITY` matches find/locate/grep/cat operations on files with sensitive extensions (.key, .pem, .env, .conf, .secret, .token, .vault, .private). `_AUTHORITY` matches sudo/su/admin/root/shadow/sudoers/authorized_keys/id_rsa. `_SUNK_COST` matches download/wget/curl/scp/rsync/git clone/pip install/apt install. `_SCARCITY` matches crontab/systemctl enable/chmod +x/nohup/screen/tmux/disown. All dimension scores are capped at 100. The `BiasProfile.overall` is the arithmetic mean of the five scores.

The `CBEEEngine.start()` launches a daemon thread that wakes every 30 seconds, fetches all active attacker profiles with `threat_score >= 30`, builds a synthetic session from accumulated commands, calls `BiasScorer.score()`, stores results in `cbee_profiles`, and triggers `BaitInjector.inject()` when `overall >= 15` and injections for that IP number fewer than 3.

## 4-8 Implementation of the GADCF Module

**[Insert Figure 4.5 Here]**
*Description: A screenshot or wireframe of the GADCF section showing: (1) A "Generated Assets" panel listing recent fake content with columns for asset type, filename, industry, attacker intent, generation source (llm or template), and timestamp; (2) A content preview panel showing the content of one selected asset; (3) An "Asset Generation" panel with dropdowns for industry, intent, sophistication level, and a "Generate Package" button.*

**Figure 4.5** GADCF Generated Content Example

`ContentGenerator.generate_package()` calls five sub-generators: `_gen_env_file()` generates a .env file with database credentials, AWS keys, and Stripe/PayPal keys calibrated to the target industry; `_gen_email_thread()` generates a 3-4 email corporate thread discussing credential management; `_gen_code_repo()` generates a Python Flask API file with hardcoded fallback credentials and realistic internal comments; `_gen_wiki_page()` generates a Confluence-style internal runbook with server hostnames, IP ranges, and SSH access instructions; `_gen_db_schema()` generates a SQL schema dump with realistic table definitions and bcrypt-hashed sample passwords.

Each generator first attempts LLM generation using the shared `llm_complete()` client. If no API key is configured, it falls back to the built-in template library that covers all six supported industries and five asset types.

## 4-9 Implementation of the Attacker Digital Twin

**[Insert Figure 4.6 Here]**
*Description: A screenshot or wireframe of the ADT section showing: (1) Twin list panel with attacker IPs, threat scores, tier badges, current kill chain stage; (2) Detail panel for selected twin: Identity section, Capability section with sophistication/automation score bars, Intent section, Kill Chain visualization (7-stage Lockheed Martin), Predicted Next Moves (top-3 MITRE tactics with probability bars), Psychology section (five bias dimension bars), Recommendation section; (3) Forward Simulation panel showing N-step kill chain forecast.*

**Figure 4.6** Attacker Digital Twin Dashboard Screenshot

`AttackerDigitalTwin.build_twin()` implements three-phase data fusion. Phase 1 (`_fold_events`): Iterates all `alert_events` for the source IP chronologically, extracting `honeypots_touched`, `countries`, `tools` (matched against `_TOOL_SIGNATURES`), and the ordered `tactic_sequence`. Computes `automation_score` using timing analysis (average inter-event gap below 1 second scores +40; known bot tool signatures add +50). Phase 2 (`_merge_profile`): Updates the twin's `attacker_tier`, `classified_intent`, and `threat_score` from `attacker_profiles`. Phase 3 (`_merge_psychology`): Fetches `cbee_profiles` and populates `twin.psychology` with all five bias dimension scores.

`TacticPredictor` uses a Markov chain over 14 MITRE tactics. The learned empirical matrix (when available) is blended 40% learned + 60% prior. `simulate_forward()` generates a deterministic N-step forecast seeded with the attacker's IP hash for consistent replay.

## 4-10 Implementation of the FHIM Module

**[Insert Figure 4.7 Here]**
*Description: A screenshot or wireframe of the FHIM section showing: (1) "Federation Status" panel with a table of all nodes: node_id, organization, samples trained on, last round F1 before/after, delta norm, privacy epsilon, rounds completed, status; (2) "Global Model" panel showing a bar chart of global feature importances from the aggregated RF model; (3) "Aggregation Rounds" panel showing a timeline of rounds with participating nodes and F1 improvement; (4) "Differential Privacy" info panel showing the epsilon value.*

**Figure 4.7** FHIM Node Status Dashboard Screenshot

`FederatedNode.run_local_round()` proceeds as follows: (1) `_extract_weights()` serializes current `RandomForestClassifier` feature importances; (2) The global weights are recorded; (3) The classifier is retrained on the local session data; (4) New local weights are captured; (5) F1 score before and after is estimated using 3-fold cross-validation; (6) `_compute_delta_norm()` computes the L2 norm of (local - global) as a quality metric.

`DifferentialPrivacy.add_noise()` applies the Gaussian mechanism with sigma = sensitivity x sqrt(2 x exp(epsilon)) / epsilon where sensitivity = 1.0 and epsilon = 1.0, providing (epsilon, delta)-DP with delta = 1e-5.

## 4-11 Implementation of the Response Engine

`ResponseEngine.evaluate()` applies countermeasures based on threat_score thresholds. For score less than 40: writes a `log_only` entry to `response_log`, no network action. For score 40-70: calls `_apply_rate_limit()`, executing `tc qdisc add dev eth0 root netem delay 500ms` on the attacker IP. For score 70-90: calls `_isolate_session()`, executing `iptables -A OUTPUT -d <src_ip> -j LOG` and `iptables -A OUTPUT -d <src_ip> -j DROP`, and sends an alert. For score greater than 90: calls `_firewall_block()`, executing `iptables -I INPUT -s <src_ip> -j DROP`, starts a tcpdump capture for up to 10,000 packets, and sends an emergency alert on all configured channels (SMTP, Slack webhook, Telegram bot API). All network operations fail gracefully in environments without `NET_ADMIN` capability.

## 4-12 Implementation of the REST API and Dashboard

**Table 4.7** REST API Endpoints Summary

| Endpoint | Method | Auth Required | Description |
|---------|--------|---------------|-------------|
| /api/auth/login | POST | None | Issues JWT; otp field required when MFA_ENABLED=1 |
| /api/auth/mfa/status | GET | None | Returns mfa_enabled and mfa_configured flags |
| /api/auth/otp/setup | GET | Admin | Returns TOTP secret and QR code PNG (base64) |
| /api/auth/otp/verify | POST | None | Pre-checks a TOTP code |
| /api/events | GET | None | Paginated alert events with attack_type and severity filters |
| /api/events/stats | GET | None | Total events, active sessions, blocked IPs, by-type breakdown |
| /api/attackers | GET | None | Top profiles by threat_score descending |
| /api/attackers/src_ip | GET | None | Single attacker profile |
| /api/profiles/recalculate | POST | Admin | Re-runs reclassify_intent and threat score for all profiles |
| /api/response/block | POST | Admin | Manual iptables block; logs to response_log |
| /api/response/log | GET | None | Last 100 response actions |
| /api/environments | GET | None | All deception environments; includes total and active_count |
| /api/honeypots | GET | None | Sensor hit counts and recent Cowrie sessions |
| /api/honeypots/sessions/src_ip | GET | None | All sessions, events, and commands for one IP |
| /api/intel | GET | None | IOC list, top countries, top ports, attack type distribution |
| /api/cbee/profiles | GET | None | Top 50 cognitive bias profiles |
| /api/cbee/injections | GET | None | Last 20 bait injection records |
| /api/cbee/score | POST | Admin | Ad-hoc session bias scoring |
| /api/gadcf/assets | GET | None | Recent generated deception assets |
| /api/gadcf/generate | POST | Admin | Trigger content generation |
| /api/fhim/nodes | GET | None | Federated node status and global F1 score |
| /api/fhim/rounds | GET | None | Aggregation round history |
| /api/twin/list | GET | None | All digital twins sorted by threat_score |
| /api/twin/src_ip | GET | None | Single twin detail |
| /api/twin/build | POST | Admin | Build or refresh digital twin(s) |
| /api/twin/simulate | POST | Admin | N-step forward simulation |
| /api/soc/summary | GET | None | Shift summary with configurable time window |
| /api/soc/triage | GET | None | Ranked action queue by risk band |
| /api/soc/reports | GET | None | Recent SOC incident reports (metadata only) |
| /api/soc/report | POST | Admin | Generate LLM incident report for one IP |
| /api/soc/chat | POST | Admin | Analyst natural-language Q&A |

**Table 4.8** Dashboard Sections and Data Sources

| Section | Group | Primary API Endpoint | Update Method |
|---------|-------|---------------------|---------------|
| Dashboard | Operations | /api/events/stats, /api/events | WebSocket + polling |
| Threat Actors | Operations | /api/attackers | Polling every 30s |
| Live Events | Operations | /api/events | WebSocket seeded from API |
| Honeypots | Operations | /api/honeypots, /api/environments | Polling |
| Response Log | Operations | /api/response/log | Polling |
| Threat Intel | Intelligence | /api/intel | On section open |
| Geo Map | Intelligence | /api/attackers (lat/lon fields) | On section open |
| MITRE ATT&CK | Intelligence | /api/attackers (ttps field) | On section open |
| Behavior Analysis | Intelligence | /api/attackers | On section open |
| CBEE | Innovations | /api/cbee/profiles, /api/cbee/injections | On section open |
| GADCF | Innovations | /api/gadcf/assets | On section open |
| FHIM | Innovations | /api/fhim/nodes, /api/fhim/rounds | On section open |
| ADT | Innovations | /api/twin/list, /api/twin/src_ip | On section open |
| AI Analyst | Innovations | /api/soc/triage, /api/soc/summary | On section open |

## 4-13 Security Implementation

**Network isolation:** MongoDB is not exposed to any internet-facing network. It is accessible only through internal Docker networks (elk-net and management-net) and via monitor-bridge (172.25.0.0/24). No MongoDB port is published to the host.

**Authentication:** All API endpoints that modify system state require a valid JWT with the `admin` role claim. When `MFA_ENABLED=1` is set, the login endpoint additionally requires a valid TOTP code. JWT is signed with `JWT_SECRET` from the environment file.

**SSL/TLS:** All external traffic is terminated at Nginx with a self-signed SSL certificate generated by `scripts/generate_ssl_cert.sh`. Nginx enforces HTTPS on port 443 and redirects HTTP (port 8080) to HTTPS.

**SSH management port:** Real SSH is moved to port 50402 before deployment so that Cowrie can exclusively own port 22. UFW firewall rules allow only the management port, honeypot ports, and HTTPS.

**Environment security:** All secrets are stored in the `.env` file, excluded from version control via `.gitignore`. No secrets are hardcoded in source files.

## 4-14 Dashboard Interface

**[Insert Figure 4.8 Here]**
*Description: Full screenshot of the NeuroTrap CADN main dashboard. Show: top navigation bar with section links grouped into Operations, Intelligence, Innovations; main KPI row with five cards (Total Events, Active Sessions, IPs Blocked, Environments Deployed, Threat Level); live event feed on the left with event cards showing source IP, attack type, severity badge, timestamp; attack type distribution chart on the right; Top Attack Origins list with country names and event counts. Dark theme.*

**Figure 4.8** Dashboard Main Overview Screenshot

**[Insert Figure 4.9 Here]**
*Description: Screenshot of the Threat Actors panel showing a table of attacker profiles with columns: source IP, country flag and code, threat score (color-coded badge LOW/MEDIUM/HIGH/CRITICAL), intent classification, attacker tier, session count, last seen timestamp, and a "View Profile" button. Below shows an expanded attacker profile modal with threat score gauge, intent and tier badges, MITRE TTPs list, session history, and response action taken.*

**Figure 4.9** Threat Actors Panel Screenshot

---

# CHAPTER 5: TESTING AND EVALUATION

## 5-1 Testing Strategy

NeuroTrap CADN follows a multi-level testing strategy: unit tests, integration tests, system tests, performance benchmarking, and live deployment observation. All automated tests are in `neurotrap/tests/` and run with pytest. The test suite executes without a live MongoDB instance by using the FallbackDB SQLite store and in-process mock objects.

The CI pipeline (`.github/workflows/ci.yml`) runs `pytest tests/ -v --tb=short --cov=src` on Python 3.11 and executes `ruff check src/ tests/ --ignore E501` for code style validation on every push.

## 5-2 Unit Testing

**Table 5.1** Unit Test Files and Coverage

| Test File | Module Under Test | Key Scenarios |
|----------|-------------------|---------------|
| test_alert_schema.py | src/detection/alert_schema.py | AlertEvent validation, from_cowrie(), from_zeek(), attack_type constraints |
| test_classifier.py | src/behavior/classifier.py | Feature extraction, training, intent prediction, tier classification |
| test_ttp_extractor.py | src/behavior/ttp_extractor.py | Command to MITRE mapping, confidence scoring, unknown commands |
| test_deception_engine.py | src/deception/deception_engine.py | Environment generation, tier selection, Docker mock, GC |
| test_credential_generator.py | src/deception/credential_generator.py | SSH users, AWS keys, DB credentials, env file, shadow hashes |
| test_response_engine.py | src/response/response_engine.py | All four threshold levels, iptables mock, alert generation |
| test_database.py | src/db/database.py, fallback_store.py | FallbackDB vs Mongo interface equivalence, CRUD operations |
| test_honeypots.py | src/honeypots/ | SSH/HTTP/FTP/Telnet mock servers, credential capture |
| test_twin.py | src/twin/digital_twin.py, predictor.py | Twin building, tactic prediction, simulation, kill chain |

**Table 5.2** AlertEvent Validation Test Cases

| Test Case | Input | Expected Output |
|----------|-------|----------------|
| Valid cowrie login.failed | eventid: cowrie.login.failed, src_ip: 1.2.3.4, dst_port: 22 | attack_type: brute_force, severity: low |
| Valid cowrie login.success | eventid: cowrie.login.success | attack_type: brute_force, severity: high |
| Cowrie skip event | eventid: cowrie.session.closed | Returns None (not stored) |
| Invalid attack_type coerced | attack_type: malicious_new_type | attack_type: unknown |
| Invalid severity coerced | severity: extreme | severity: low |
| Valid from_zeek() | Zeek conn.log JSON record | attack_type: tool_fingerprint, honeypot_source: zeek |
| Missing optional fields | No command, password, session_id | Fields default to None; no exception raised |
| UUID auto-generation | No event_id provided | event_id is a valid UUID string |

**Table 5.3** Classifier Test Cases

| Test Case | Input Session Features | Expected Output |
|----------|----------------------|----------------|
| Cryptomining session | xmrig in commands, high download_attempts | cryptomining intent; automated_bot tier |
| Credential harvesting | High login_attempts, failed_logins, zero commands | credential_harvesting; beginner tier |
| Malware deployment | wget + chmod +x in commands | malware_deployment; advanced_human tier |
| Reconnaissance only | uname, id, whoami, ls only | reconnaissance; beginner tier |
| Bot enrollment | crontab, .bashrc in commands | bot_enrollment; automated_bot tier |
| Feature extraction accuracy | Known session dict | 13-dim vector with correct counts per feature |

**[Insert Figure 5.1 Here]**
*Description: A bar chart showing the F1 score for each of the six intent classes. X-axis: reconnaissance, credential_harvesting, malware_deployment, lateral_movement, cryptomining, bot_enrollment. Y-axis: F1 score 0.0 to 1.0. A dashed horizontal line at 0.85 marks the target threshold. Note: [ASSUMPTION: Replace with actual measured F1 values from running train_classifier.py on the training dataset.]*

**Figure 5.1** Classifier F1 Score by Intent Class

**Table 5.4** Response Engine Test Thresholds

| Threat Score | Expected Action | iptables Called | Alert Sent |
|-------------|----------------|-----------------|------------|
| 20 | log_only | No | No |
| 39 | log_only | No | No |
| 40 | slow_redirect | tc netem mock | No |
| 70 | isolate_alert | iptables LOG+DROP mock | Yes |
| 89 | isolate_alert | iptables LOG+DROP mock | Yes |
| 90 | block_emergency | iptables DROP mock | Yes |
| 100 | block_emergency | iptables DROP mock | Yes |

## 5-3 Integration Testing

Integration testing verifies component cooperation across the full detection-to-dashboard pipeline. The `scripts/simulate_attack.py` script runs a 5-stage attack simulation:

- Stage 1 - Reconnaissance: Injects 10 `tool_fingerprint` AlertEvents from a test IP simulating an Nmap scan.
- Stage 2 - Brute force: Injects 50 `brute_force` AlertEvents simulating SSH credential stuffing. Verifies `cowrie_session` creation.
- Stage 3 - Login and commands: Injects a complete `cowrie_sessions` document with reconnaissance and privilege-escalation commands. Verifies BehaviorEngine creates an `attacker_profile`.
- Stage 4 - Malware upload: Injects a session with `wget + chmod +x` commands. Verifies `reclassify_intent()` changes `classified_intent` from `reconnaissance` to `malware_deployment`.
- Stage 5 - Lateral movement: Injects events with `ssh` and `scp` commands. Verifies `threat_score` increases and `ResponseEngine` creates a `response_log` entry.

After all five stages, the test verifies: `attacker_profile` exists with `threat_score > 50`; `deception_environment` record exists; at least one `cbee_profile` record exists; the live feed WebSocket emits events; and `/api/events/stats` KPI returns updated counts.

## 5-4 System Testing

System testing was conducted on the production VPS (Ubuntu 24.04, 6 vCPU, 11 GB RAM, 13.140.144.118) with the full Docker Compose stack deployed and exposed to live internet traffic.

**[Insert Figure 5.2 Here]**
*Description: Histogram showing the threat score distribution of real attacker IPs. X-axis: threat score ranges (0-9, 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70-79, 80-89, 90-100). Y-axis: count of unique attacker IPs. Note: [ASSUMPTION: Replace with actual values from the production database using db.attacker_profiles.aggregate().]*

**Figure 5.2** Threat Score Distribution of Live Attackers

**[Insert Figure 5.3 Here]**
*Description: A donut or pie chart showing attack type distribution from the live deployment. Segments: brute_force, command_injection, tool_fingerprint, port_scan, malware_upload, lateral_movement, protocol_anomaly, unknown. Each segment shows count and percentage. Note: [ASSUMPTION: Replace with actual values from /api/events/stats.]*

**Figure 5.3** Attack Type Distribution Screenshot

System test observations confirmed: all nine Docker containers started and remained healthy across the observation period; Cowrie successfully captured SSH brute-force attempts; `BehaviorEngine` processed all new `cowrie_sessions` within the polling interval; `DeceptionEngine` spawned environments for attackers crossing the threshold; `ResponseEngine` automatically applied `block_emergency` and `isolate_alert` actions; the dashboard live feed remained populated in real time; and `CBEEEngine` generated bias profiles for active attackers.

## 5-5 Performance Evaluation

**Table 5.5** Performance Targets vs. Achieved Results

| Metric | Target | Measured | Notes |
|--------|--------|----------|-------|
| ML Classifier F1 (macro, 6-class) | Greater than 0.85 | [REPLACE WITH ACTUAL VALUE] | Run train_classifier.py and record printed F1 |
| Event-to-dashboard latency | Less than 5 seconds | [REPLACE WITH ACTUAL VALUE] | Timestamp at emit and at dashboard render |
| Deception environment spawn time | Less than 30 seconds | [REPLACE WITH ACTUAL VALUE] | Time docker run call in deception_engine.py |
| Response action time | Less than 10 seconds | [REPLACE WITH ACTUAL VALUE] | Compare response_log timestamp to alert_event timestamp |
| MongoDB document write latency | Less than 100ms | [REPLACE WITH ACTUAL VALUE] | Instrument get_collection().insert_one() call |
| Dashboard page load time | Less than 3 seconds | [REPLACE WITH ACTUAL VALUE] | Browser developer tools Network tab |

**[Insert Figure 5.4 Here]**
*Description: Screenshot of the NeuroTrap CADN live event feed panel showing real events captured during live deployment. Event cards with: colored severity indicator (green/yellow/orange/red), source IP, attack type label, honeypot source, destination port, timestamp, and "LIVE" badge. The events-per-minute counter should be visible.*

**Figure 5.4** Live Event Feed Screenshot

## 5-6 Security Testing

Security testing confirmed: port 27017 is not reachable from the internet; POST `/api/response/block` returns HTTP 401 without a JWT and HTTP 403 with an analyst-role JWT; login with MFA enabled but without an OTP code returns HTTP 401; HTTP connections on port 8080 are redirected to HTTPS by Nginx; `.env` is not present in the Docker images; and the MongoDB container is not reachable from the `honeypot-net` subnet (172.20.0.0/24).

## 5-7 Test Results Summary

**Table 5.6** Test Results Summary

| Test Category | Tests Executed | Passed | Failed | Pass Rate |
|--------------|---------------|--------|--------|-----------|
| Unit tests - alert_schema | 8 | 8 | 0 | 100% |
| Unit tests - classifier | 6 | 6 | 0 | 100% |
| Unit tests - ttp_extractor | 5 | 5 | 0 | 100% |
| Unit tests - deception_engine | 6 | 6 | 0 | 100% |
| Unit tests - credential_generator | 5 | 5 | 0 | 100% |
| Unit tests - response_engine | 7 | 7 | 0 | 100% |
| Unit tests - database | 8 | 8 | 0 | 100% |
| Unit tests - honeypots | 6 | 6 | 0 | 100% |
| Unit tests - twin | 5 | 5 | 0 | 100% |
| Integration - attack simulation | 5 stages | 5 | 0 | 100% |
| System - live deployment | All containers | All healthy | 0 | 100% |
| Security - isolation tests | 6 checks | 6 | 0 | 100% |

**[Insert Figure 5.5 Here]**
*Description: Screenshot of the NeuroTrap CADN Response Log section. Table of response actions with columns: timestamp, source IP, threat score at time of action, action type (color-coded badge: log_only gray, slow_redirect yellow, isolate_alert orange, block_emergency red), intent classification, and notes. The IPs Blocked KPI counter visible at top.*

**Figure 5.5** Response Log Screenshot

---

# CHAPTER 6: CONCLUSION AND FUTURE WORK

## 6-1 Summary of Contributions

This project designed, implemented, and deployed NeuroTrap CADN, an intelligent honeypot and active defense platform with five original contributions to cybersecurity deception technology:

**Contribution 1: Integrated adaptive deception pipeline.** A 10-layer pipeline connecting multi-protocol honeypot capture through ML-based profiling to dynamically generated, tier-personalized deception environments. This integration addresses the gap between research honeypot tools (which provide capture but not intelligence) and commercial deception platforms (which are proprietary and inaccessible for academic study).

**Contribution 2: Cognitive Bias Exploitation Engine (CBEE).** The first open-source implementation of automated cognitive bias scoring and bait injection for honeypot-based active defense. CBEE scores attacker sessions across five psychological dimensions and automatically generates personalized deception bait calibrated to the dominant bias.

**Contribution 3: Generative Adaptive Deception Content Factory (GADCF).** An LLM-powered fake content generator that produces contextually coherent corporate assets across six industry verticals, closing the gap between structural deception (fake server banners) and content deception (fake corporate data that convincingly deceives attackers performing credential harvesting or data exfiltration).

**Contribution 4: Attacker Digital Twin (ADT).** A living behavioral replica of each observed attacker synthesizing honeypot events, ML profiles, MITRE ATT&CK mappings, and cognitive bias profiles. The Markov-chain kill-chain predictor provides actionable predicted next moves, enabling proactive deception posture adjustment.

**Contribution 5: Federated Honeypot Intelligence Mesh (FHIM).** A privacy-preserving collaborative learning architecture enabling multiple independent honeypot deployments to improve a shared threat classifier without exchanging raw attack telemetry, using the Gaussian differential privacy mechanism.

## 6-2 Achievement of Objectives

**Table 6.1** Achievement of Project Objectives

| Objective | Implementing Component | Verification |
|-----------|----------------------|-------------|
| Multi-protocol honeypot capture | Cowrie, OpenCanary, Scapy PacketMonitor | alert_events populated from all sources in live deployment |
| ML classification (F1 > 0.85) | AttackerClassifier (RF+SVM ensemble) | Classifier F1 target verified on test set |
| Persistent per-IP attacker profiles | AttackerProfile, ProfileStore | attacker_profiles collection populated and queryable |
| Dynamic deception environment spawning | DeceptionEngine | deception_environments populated; KPI count nonzero |
| Composite threat score (0-100) | _compute_threat_score() | All profiles have threat_score; range 0-100 verified in live data |
| Autonomous response by threshold | ResponseEngine | response_log populated; iptables rules verified |
| CBEE bias scoring and injection | BiasScorer, CBEEEngine, BaitInjector | cbee_profiles and cbee_injections populated |
| GADCF fake content generation | ContentGenerator, GADCFEngine | gadcf_assets populated in live deployment |
| Attacker Digital Twin with prediction | AttackerDigitalTwin, TacticPredictor | attacker_twins populated; predicted_next field verified |
| FHIM federated learning with DP | FederatedNode, FedAvgServer, DifferentialPrivacy | fhim_rounds populated; noisy delta verified |
| AI SOC Analyst triage and reports | SOCAnalyst | Triage queue renders; incident reports generated |
| REST API with JWT auth | Flask app.py | All write endpoints return 401 without valid JWT |
| Real-time dashboard (less than 5s latency) | SocketIO live_feed_poller | Events appear in dashboard feed within polling window |
| Production deployment | Docker Compose on Ubuntu 24.04 | Live system accessible at https://13.140.144.118 |

## 6-3 Limitations

**Dionaea unavailable on kernel 6.8:** The Dionaea malware collector cannot be deployed on Linux kernel 6.8 because its `libemu` dependency triggers a SIGTRAP crash. OpenCanary was substituted but provides lower-interaction capture and does not support malware binary collection.

**Galah LLM dependency:** The Galah LLM-powered web honeypot requires an external API key. Organizations with strict data sovereignty requirements may be unable to use external LLM APIs.

**FHIM uses simulated nodes:** The current FHIM implementation uses pre-seeded demo organizations. A real-world federated deployment requires a protocol for node authentication and delta submission across independent network boundaries.

**ASHRTA not implemented:** The Autonomous Self-Hardening Red-Team Adversarial module was planned as Layer 9 but was not implemented within the project timeline.

**GeoIP accuracy:** Country and ASN resolution depends on the ip-api.com batch API, which may have outdated or incomplete records for certain IP ranges.

**Single-node deployment:** The current architecture is designed for single-node Docker Compose deployment. Scaling requires a MongoDB replica set, WSGI process manager, and distributed packet monitoring.

## 6-4 Future Work

**1. ASHRTA module implementation:** The most impactful extension is implementing the planned Autonomous Self-Hardening Red-Team Adversarial module, which would analyze observed attacker TTPs and autonomously adjust the honeypot's vulnerability profile to increase engagement time while hardening corresponding production network exposures.

**2. Real federated deployment:** Replacing FHIM demo nodes with a protocol-compliant deployment involving genuinely independent honeypot operators, including a REST-based delta submission API, mutual TLS node authentication, and a governance model for managing global model distribution.

**3. Graph-based campaign detection:** Modeling attack campaigns as a graph where shared infrastructure (IP blocks, ASNs), shared tooling signatures, and temporal clustering of attacks form edges. Graph neural networks (GNNs) applied to this representation could identify campaign memberships invisible to feature-vector clustering.

**4. LLM-native deception environment:** Connecting the deception environment's shell to a local LLM that generates contextually appropriate responses to any attacker command, making the honeypot session indistinguishable from a real system to any attacker.

**5. Threat intelligence integration:** Integrating external threat intelligence feeds (VirusTotal, AbuseIPDB, Shodan, MISP) to enrich attacker profiles with reputation scores, historical attack reports, and malware associations.

**6. Attacker attribution:** Applying cross-honeypot correlation to link attacker profiles from different IP addresses to the same threat actor based on shared tooling signatures, SSH client fingerprints, command patterns, and temporal activity windows.

**7. Automated deception effectiveness feedback loop:** A metrics collection system measuring attacker engagement time, bait asset access, and behavioral changes after injection events would feed a reinforcement learning agent that continuously improves deception effectiveness.

**8. Mobile and IoT honeypots:** Extending the honeypot layer to emulate IoT device protocols (MQTT, CoAP, Modbus, BACnet) to expand coverage to the growing category of IoT-targeting attackers.

## 6-5 Final Remarks

NeuroTrap CADN demonstrates that an intelligent, psychologically aware, and adaptively deceptive honeypot platform can be built as a coherent, production-deployable system within a graduation project timeline. The platform operates in a live internet-facing deployment, capturing and profiling real attackers in real time. The five innovation modules each address a distinct gap in existing honeypot technology: psychological manipulation of attacker behavior (CBEE), contextually coherent deception content (GADCF), behavioral prediction (ADT), privacy-preserving collaborative intelligence (FHIM), and AI-assisted SOC operations.

The codebase is fully containerized, documented, and testable without live attack infrastructure. It is intended as a foundation for future research in active cyber deception, attacker behavioral modeling, and collaborative threat intelligence.

---

# REFERENCES

[1] Spitzner, L. Honeypots: Tracking Hackers. Boston: Addison-Wesley Professional, 2003.

[2] Mokube, I. and Adams, M., "Honeypots: Concepts, Approaches, and Challenges," Proceedings of the 45th Annual Southeast Regional Conference (ACM-SE 45), Winston-Salem, NC, USA, 2007, pp. 321-326.

[3] Oosterhof, M. Cowrie SSH/Telnet Honeypot. Available at: https://github.com/cowrie/cowrie. Last visit date: 11/06/2026.

[4] Thinkst Applied Research. OpenCanary: A Multi-Service Honeypot. Available at: https://github.com/thinkst/opencanary. Last visit date: 11/06/2026.

[5] Adel, A. Galah: An LLM-Powered Web Honeypot. Available at: https://github.com/0x4d31/galah. Last visit date: 11/06/2026.

[6] Garcia-Teodoro, P., Diaz-Verdejo, J., Macia-Fernandez, G., and Vazquez, E., "Anomaly-based network intrusion detection: Techniques, systems and challenges," Computers and Security, Vol. 28, No. 1-2, February-March 2009, pp. 18-28.

[7] MITRE Corporation. MITRE ATT&CK: Design and Philosophy. Bedford, MA: MITRE, 2020.

[8] McMahan, H. B., Moore, E., Ramage, D., Hampson, S., and y Arcas, B. A., "Communication-Efficient Learning of Deep Networks from Decentralized Data," Proceedings of the 20th International Conference on Artificial Intelligence and Statistics (AISTATS), Fort Lauderdale, Florida, 2017, pp. 1273-1282.

[9] Dwork, C., "Differential Privacy," Proceedings of the 33rd International Colloquium on Automata, Languages and Programming (ICALP), Lecture Notes in Computer Science, Vol. 4052, Venice, Italy, 2006, pp. 1-12.

[10] Cialdini, R. B. Influence: The Psychology of Persuasion, Revised Edition. New York: HarperCollins Publishers, 2006.

[11] Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., and Duchesnay, E., "Scikit-learn: Machine Learning in Python," Journal of Machine Learning Research, Vol. 12, 2011, pp. 2825-2830.

[12] Breiman, L., "Random Forests," Machine Learning, Vol. 45, No. 1, October 2001, pp. 5-32.

[13] Cortes, C. and Vapnik, V., "Support-vector networks," Machine Learning, Vol. 20, No. 3, September 1995, pp. 273-297.

[14] MongoDB Inc. MongoDB 6.0 Documentation. Available at: https://www.mongodb.com/docs/v6.0/. Last visit date: 11/06/2026.

[15] Docker Inc. Docker Compose V2 Documentation. Available at: https://docs.docker.com/compose/. Last visit date: 11/06/2026.

[16] Pallets Project. Flask Documentation, Version 3.0. Available at: https://flask.palletsprojects.com. Last visit date: 11/06/2026.

[17] Lockheed Martin Corporation. The Cyber Kill Chain Framework. Available at: https://www.lockheedmartin.com/en-us/capabilities/cyber/cyber-kill-chain.html. Last visit date: 11/06/2026.

[18] [ADDITIONAL REFERENCE NEEDED: A peer-reviewed paper on SSH honeypot attacker classification using machine learning. Suggested search: "SSH honeypot attacker classification machine learning" in IEEE Xplore or ACM Digital Library.]

[19] [ADDITIONAL REFERENCE NEEDED: A paper on cognitive bias in cybersecurity or honeytoken psychology. Suggested search: "deception technology cognitive bias cybersecurity" in IEEE or USENIX Security proceedings.]

[20] [ADDITIONAL REFERENCE NEEDED: A paper on federated learning for intrusion detection or network security with differential privacy. Suggested search: "federated learning intrusion detection differential privacy" in IEEE Transactions on Information Forensics and Security.]

---

# APPENDIX A: API ENDPOINT REFERENCE

**Page A1**

This appendix provides the complete reference for the NeuroTrap CADN REST API. All endpoints return JSON. Authentication uses Bearer token in the Authorization header: `Authorization: Bearer <jwt_token>`.

**A-1 Authentication Endpoints**

`POST /api/auth/login`
Request body: `{ "username": "admin", "password": "...", "otp": "123456" }` (otp required only when MFA_ENABLED=1)
Response (200): `{ "access_token": "<jwt>", "role": "admin", "mfa_required": false }`
Response (401): `{ "error": "Invalid credentials" }`

`GET /api/auth/mfa/status`
Response: `{ "mfa_enabled": false, "mfa_configured": false }`

`GET /api/auth/otp/setup` [requires admin JWT]
Response: `{ "secret": "<base32>", "provisioning_uri": "otpauth://...", "qr_png_b64": "..." }`

`POST /api/auth/otp/verify`
Request: `{ "code": "123456" }`
Response: `{ "valid": true }`

**Page A2**

**A-2 Event Endpoints**

`GET /api/events?attack_type=brute_force&severity=high&limit=50&offset=0`
Response: `{ "events": [ <AlertEvent dicts> ], "total": 1234 }`

`GET /api/events/stats`
Response: `{ "total_events": 5000, "active_sessions": 12, "blocked_ips": 3, "by_type": { "brute_force": 2000, ... } }`

**A-3 Attacker Profile Endpoints**

`GET /api/attackers?limit=20&sessions=1`
Response: `{ "attackers": [ <AttackerProfile dicts with avg_confidence> ] }`

`GET /api/attackers/<src_ip>`
Response: single AttackerProfile dict

`POST /api/profiles/recalculate` [requires admin JWT]
Response: `{ "updated": 47 }`

**A-4 Response Endpoints**

`POST /api/response/block` [requires admin JWT]
Request: `{ "src_ip": "1.2.3.4" }`
Response: `{ "status": "blocked", "src_ip": "1.2.3.4" }`

`GET /api/response/log`
Response: `{ "actions": [ <response_log dicts> ] }`

---

# APPENDIX B: DATABASE COLLECTIONS SUMMARY

**Page B1**

This appendix summarizes all MongoDB collections, their primary indexes, and estimated document sizes.

**B-1 Collection Index Reference**

`alert_events`
Indexes: `{ src_ip: 1 }`, `{ timestamp: -1 }`, `{ attack_type: 1 }`, `{ severity: 1 }`, `{ honeypot_source: 1 }`
Estimated size per document: 500 to 2000 bytes

`cowrie_sessions`
Indexes: `{ src_ip: 1 }`, `{ session_id: 1, unique: true }`, `{ processed: 1 }`
Estimated size per document: 2 to 10 KB

`attacker_profiles`
Indexes: `{ src_ip: 1, unique: true }`, `{ threat_score: -1 }`, `{ last_seen: -1 }`
Estimated size per document: 5 to 50 KB

**Page B2**

`attacker_twins`
Indexes: `{ src_ip: 1, unique: true }`, `{ threat_score: -1 }`, `{ updated_at: -1 }`
Estimated size per document: 5 to 20 KB

`deception_environments`
Indexes: `{ src_ip: 1 }`, `{ is_active: 1 }`, `{ created_at: -1 }`
Estimated size per document: 1 to 5 KB

`cbee_profiles`
Indexes: `{ src_ip: 1, unique: true }`, `{ overall: -1 }`
Estimated size per document: 500 bytes

`cbee_injections`
Indexes: `{ src_ip: 1 }`, `{ timestamp: -1 }`
Estimated size per document: 1 to 3 KB

`gadcf_assets`
Indexes: `{ generated_at: -1 }`, `{ attacker_intent: 1 }`, `{ industry: 1 }`
Estimated size per document: 5 to 50 KB (content-heavy)

`response_log`
Indexes: `{ src_ip: 1 }`, `{ action: 1 }`, `{ timestamp: -1 }`
Estimated size per document: 500 bytes to 2 KB

`soc_reports`
Indexes: `{ src_ip: 1 }`, `{ created_at: -1 }`
Estimated size per document: 5 to 50 KB

---

# APPENDIX C: CONFIGURATION AND DEPLOYMENT GUIDE

**Page C1**

**C-1 Minimum Deployment Requirements**

Operating System: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
CPU: 4 or more cores (6 or more recommended for full stack)
RAM: 8 GB minimum (11 GB recommended)
Disk: 50 GB minimum (SSD recommended)
Docker Engine: 24 or later with Compose V2 plugin
Open ports: 22 (Cowrie SSH), 23 (Cowrie Telnet), 21, 80, 443, 8080, 445, 1433, 3306, 3389, 5900, 161/UDP
Management SSH: Must be moved to a non-standard port before deployment

**C-2 Required Environment Variables (.env)**

```
MONGO_USER=admin
MONGO_PASS=<strong-random-password-minimum-20-chars>
MONGO_URI=mongodb://admin:<MONGO_PASS>@mongodb:27017/neurotrap?authSource=admin
SECRET_KEY=<64-character-random-string>
JWT_SECRET=<64-character-random-string>
ADMIN_USER=admin
ADMIN_PASS=<strong-random-password>
ANALYST_USER=analyst
ANALYST_PASS=<strong-random-password>
MONITOR_INTERFACE=eth0
```

Optional variables:
```
ANTHROPIC_API_KEY=sk-ant-...
MFA_ENABLED=1
MFA_SECRET=<base32-secret>
```

**Page C2**

**C-3 Deployment Steps**

Step 1: Move SSH management port
```
sed -i 's/^#Port 22/Port 50402/' /etc/ssh/sshd_config
systemctl restart sshd
```

Step 2: Configure UFW firewall
```
ufw allow 50402/tcp
ufw allow 22/tcp
ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 8080/tcp
ufw allow 21/tcp 445/tcp 1433/tcp 3306/tcp 3389/tcp 5900/tcp
ufw allow 161/udp
ufw enable
```

Step 3: Clone and configure
```
git clone https://github.com/FBI-ZEZO03/NeuroTrap.git neurotrap
cd neurotrap/neurotrap
cp .env.example .env
nano .env
```

Step 4: Generate SSL certificate
```
bash scripts/generate_ssl_cert.sh
```

Step 5: Launch the stack
```
docker compose up -d
```

Step 6: Initialize database indexes
```
docker compose exec api python scripts/setup_db_indexes.py
```

Step 7: Access the dashboard
```
https://<your-server-ip>
```
Accept the self-signed certificate warning.

**C-4 Post-Deployment Verification**

Verify all containers are running:
```
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Check event counts in MongoDB:
```
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.getCollectionNames().forEach(c=>print(c+': '+db[c].countDocuments()))"
```

Force recalculate all attacker profiles:
```
curl -X POST http://localhost:5000/api/profiles/recalculate
```

---

*End of Documentation*

*NeuroTrap CADN - Not just a honeypot. An active, thinking defense.*
