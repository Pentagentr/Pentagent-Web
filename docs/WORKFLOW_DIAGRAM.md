# 🔐 PentAgent AI Tabanlı Penetrasyon Test Workflow Şeması

## 📊 Genel Mimari ve İşleyiş Akışı

```mermaid
graph TB
    subgraph "🎯 KULLANICI KATMANI"
        USER[👤 Kullanıcı]
        CLI[💻 CLI Interface]
        WEB[🌐 Web Interface]
        API[🔌 REST API]
    end

    subgraph "🧠 AI ORCHESTRATION KATMANI"
        MAIN[🎛️ Main Orchestrator<br/>DynamicAgentOrchestrator]
        
        subgraph "⚙️ Core Agent Components"
            PLANNER[📋 Planner<br/>Strategic Planning]
            EXECUTOR[⚡ Executor<br/>Tool Execution]
            ANALYZER[🔍 Analyzer<br/>Result Analysis]
        end
        
        STATE[💾 Agent State<br/>Context Management]
        GEMINI[🤖 Gemini AI<br/>Decision Making]
    end

    subgraph "🛠️ TOOL MANAGEMENT KATMANI"
        MCP[🔧 MCP Server<br/>Enhanced Tool Manager]
        
        subgraph "📦 Tool Categories"
            RECON[🔍 Reconnaissance<br/>- WHOIS<br/>- DNS<br/>- Subdomain]
            ENUM[📊 Enumeration<br/>- Port Scan<br/>- Tech Detection<br/>- Web Crawler]
            VULN[🚨 Vulnerability<br/>- SQL Injection<br/>- XSS<br/>- Header Analysis]
            API_TOOLS[🎯 API Security<br/>- Endpoint Discovery<br/>- JWT Testing<br/>- IDOR]
            INFRA[🏗️ Infrastructure<br/>- Cloud Scanner<br/>- Panel Finder]
        end
    end

    subgraph "📈 REPORTING KATMANI"
        REPORT[📄 Report Generator]
        RAG[🎯 RAG System<br/>CVE Database]
        CVSS[📊 CVSS Calculator]
        PDF[📋 PDF Export]
    end

    USER --> CLI
    USER --> WEB
    USER --> API
    
    CLI --> MAIN
    WEB --> MAIN
    API --> MAIN
    
    MAIN --> STATE
    MAIN --> PLANNER
    MAIN --> EXECUTOR
    MAIN --> ANALYZER
    
    PLANNER <--> GEMINI
    ANALYZER <--> GEMINI
    
    EXECUTOR --> MCP
    
    MCP --> RECON
    MCP --> ENUM
    MCP --> VULN
    MCP --> API_TOOLS
    MCP --> INFRA
    
    ANALYZER --> REPORT
    REPORT --> RAG
    REPORT --> CVSS
    REPORT --> PDF
    
    STATE -.-> PLANNER
    STATE -.-> EXECUTOR
    STATE -.-> ANALYZER
    
    style MAIN fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px,color:#fff
    style GEMINI fill:#4c6ef5,stroke:#364fc7,stroke-width:3px,color:#fff
    style PLANNER fill:#51cf66,stroke:#2f9e44,stroke-width:2px
    style EXECUTOR fill:#ffd43b,stroke:#f59f00,stroke-width:2px
    style ANALYZER fill:#ff8787,stroke:#e03131,stroke-width:2px
    style MCP fill:#a78bfa,stroke:#7c3aed,stroke-width:2px
```

## 🔄 Detaylı İşleyiş Akışı (Adım Adım)

```mermaid
sequenceDiagram
    participant User as 👤 Kullanıcı
    participant Main as 🎛️ Main Orchestrator
    participant AI as 🤖 Gemini AI
    participant Planner as 📋 Planner
    participant Executor as ⚡ Executor
    participant Analyzer as 🔍 Analyzer
    participant MCP as 🔧 MCP Server
    participant Tools as 🛠️ Security Tools
    participant State as 💾 Agent State

    User->>Main: 1. Start Pentest<br/>(Target + Task)
    
    activate Main
    Main->>State: 2. Initialize State
    State-->>Main: State Created
    
    Main->>AI: 3. Analyze Target<br/>(Domain/IP/URL)
    AI-->>Main: Target Type + Risk Assessment
    
    Main->>Planner: 4. Create Initial Plan
    activate Planner
    Planner->>AI: Request Strategic Plan
    AI-->>Planner: Optimal Tool Sequence
    Planner->>State: Store Plan
    Planner-->>Main: Initial Plan Ready<br/>(3-5 tools)
    deactivate Planner
    
    loop Autonomous Execution Loop (Max 15 steps)
        Main->>Executor: 5. Execute Next Tool
        activate Executor
        
        Executor->>AI: Generate Custom Payloads?
        AI-->>Executor: Contextual Payloads
        
        Executor->>MCP: Execute Tool<br/>(with params)
        activate MCP
        MCP->>Tools: Run Security Tool
        Tools-->>MCP: Raw Results
        MCP-->>Executor: Processed Results
        deactivate MCP
        
        Executor->>State: Update Results
        Executor-->>Main: Execution Complete
        deactivate Executor
        
        Main->>Analyzer: 6. Analyze Results
        activate Analyzer
        
        Analyzer->>AI: Deep Analysis Request
        AI-->>Analyzer: Technical Insights<br/>+ Vulnerabilities<br/>+ Next Steps
        
        Analyzer->>State: Store Findings
        Analyzer-->>Main: Analysis + Suggestion
        deactivate Analyzer
        
        Main->>Planner: 7. Adapt Plan?
        activate Planner
        Planner->>AI: Should we adapt?<br/>(based on findings)
        AI-->>Planner: New Tools to Add
        Planner->>State: Update Plan
        Planner-->>Main: Plan Adapted
        deactivate Planner
        
        alt Critical Finding Detected
            Analyzer->>User: 🚨 CRITICAL ALERT
        end
        
        alt Loop Control
            Main->>Main: Check Stop Conditions<br/>(AI decision or max steps)
        end
    end
    
    Main->>Analyzer: 8. Final Analysis
    activate Analyzer
    Analyzer->>AI: Generate Report
    AI-->>Analyzer: Comprehensive Report
    Analyzer-->>Main: Final Report Ready
    deactivate Analyzer
    
    Main->>User: 9. Deliver Results<br/>(Report + Metrics)
    deactivate Main
    
    Note over User,State: 🎯 Process Complete: AI-Driven Autonomous Pentest
```

## 🧠 AI Karar Verme Süreci

```mermaid
graph TD
    START[🎯 Hedef Alındı] --> CLASSIFY{Hedef Tipi<br/>Belirleme}
    
    CLASSIFY -->|Domain| DOMAIN_STRATEGY[📋 Domain Stratejisi<br/>WHOIS → Subdomain → Port]
    CLASSIFY -->|IP Address| IP_STRATEGY[🌐 IP Stratejisi<br/>Port → Service → Tech]
    CLASSIFY -->|URL| URL_STRATEGY[🔗 URL Stratejisi<br/>Tech → Vuln → Headers]
    CLASSIFY -->|API| API_STRATEGY[🎯 API Stratejisi<br/>Endpoints → Auth → IDOR]
    
    DOMAIN_STRATEGY --> EXECUTE_TOOL[⚡ Tool Çalıştır]
    IP_STRATEGY --> EXECUTE_TOOL
    URL_STRATEGY --> EXECUTE_TOOL
    API_STRATEGY --> EXECUTE_TOOL
    
    EXECUTE_TOOL --> ANALYZE_RESULT{Sonuç<br/>Analizi}
    
    ANALYZE_RESULT -->|Success| EXTRACT_INFO[📊 Bilgi Çıkarma<br/>- Open Ports<br/>- Technologies<br/>- Vulnerabilities]
    ANALYZE_RESULT -->|Failed| FALLBACK[🔄 Alternatif<br/>Strateji]
    
    EXTRACT_INFO --> AI_DECISION{AI Karar<br/>Süreci}
    
    AI_DECISION -->|Port 80/443 Found| WEB_TOOLS[🌐 Web Tools<br/>enum_tech_detector]
    AI_DECISION -->|WordPress Found| WP_TOOLS[📦 WordPress Tools<br/>dependency_scanner]
    AI_DECISION -->|API Found| API_TEST_TOOLS[🎯 API Tests<br/>JWT + IDOR]
    AI_DECISION -->|DB Port Found| DB_TOOLS[💾 DB Tools<br/>SQL Injection]
    AI_DECISION -->|Sufficient Info| STOP[🛑 Test Complete]
    
    WEB_TOOLS --> NEXT_CYCLE[🔄 Sonraki Döngü]
    WP_TOOLS --> NEXT_CYCLE
    API_TEST_TOOLS --> NEXT_CYCLE
    DB_TOOLS --> NEXT_CYCLE
    FALLBACK --> NEXT_CYCLE
    
    NEXT_CYCLE --> EXECUTE_TOOL
    
    STOP --> FINAL_REPORT[📄 Final Report]
    
    style START fill:#4ecdc4,stroke:#006d75,stroke-width:3px
    style AI_DECISION fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px
    style FINAL_REPORT fill:#51cf66,stroke:#2f9e44,stroke-width:3px
```

## 🔧 Tool Execution Pipeline

```mermaid
graph LR
    subgraph "🎯 Tool Selection"
        SELECT[Tool Seçimi<br/>AI Decision]
        PARAMS[Parametre<br/>Hazırlama]
    end
    
    subgraph "⚡ Execution Phase"
        PAYLOAD[Custom Payload<br/>Generation]
        WORDLIST[Dynamic Wordlist<br/>Creation]
        EXEC[Tool Execution<br/>MCP Server]
    end
    
    subgraph "📊 Result Processing"
        PARSE[Sonuç<br/>Parse]
        VALIDATE[Validasyon]
        STORE[State'e<br/>Kaydet]
    end
    
    subgraph "🔍 Analysis Phase"
        EXTRACT[Kritik Bilgi<br/>Çıkarma]
        CORRELATE[Bulguları<br/>İlişkilendir]
        RISK[Risk<br/>Skorlama]
    end
    
    SELECT --> PARAMS
    PARAMS --> PAYLOAD
    PARAMS --> WORDLIST
    PAYLOAD --> EXEC
    WORDLIST --> EXEC
    
    EXEC --> PARSE
    PARSE --> VALIDATE
    VALIDATE --> STORE
    
    STORE --> EXTRACT
    EXTRACT --> CORRELATE
    CORRELATE --> RISK
    
    RISK --> DECISION{Sonraki<br/>Adım?}
    DECISION -->|Continue| SELECT
    DECISION -->|Stop| END[Rapor]
    
    style SELECT fill:#ffd43b
    style EXEC fill:#ff6b6b
    style EXTRACT fill:#a78bfa
    style DECISION fill:#51cf66
```

## 📦 MCP Server Tool Management

```mermaid
graph TD
    subgraph "🔧 MCP Server Architecture"
        MCP_MAIN[MCP Server Main]
        
        subgraph "📋 Tool Registry"
            REG_RECON[Reconnaissance<br/>Tools Registry]
            REG_ENUM[Enumeration<br/>Tools Registry]
            REG_VULN[Vulnerability<br/>Tools Registry]
            REG_API[API Security<br/>Tools Registry]
            REG_INFRA[Infrastructure<br/>Tools Registry]
        end
        
        subgraph "⚙️ Tool Execution Engine"
            VALIDATE[Parameter<br/>Validation]
            EXECUTE[Tool<br/>Execution]
            TIMEOUT[Timeout<br/>Management]
            ERROR[Error<br/>Handling]
        end
        
        subgraph "🛠️ Actual Tools"
            T1[enum_port_scanner]
            T2[enum_tech_detector]
            T3[recon_whois_tool]
            T4[vuln_http_header_analyzer]
            T5[verify_sqli]
            T6[verify_xss]
            T7[api_vuln_idor_scanner]
            T8[cloud_s3_bucket_scanner]
        end
    end
    
    MCP_MAIN --> REG_RECON
    MCP_MAIN --> REG_ENUM
    MCP_MAIN --> REG_VULN
    MCP_MAIN --> REG_API
    MCP_MAIN --> REG_INFRA
    
    REG_RECON --> VALIDATE
    REG_ENUM --> VALIDATE
    REG_VULN --> VALIDATE
    REG_API --> VALIDATE
    REG_INFRA --> VALIDATE
    
    VALIDATE --> EXECUTE
    EXECUTE --> TIMEOUT
    EXECUTE --> ERROR
    
    EXECUTE --> T1
    EXECUTE --> T2
    EXECUTE --> T3
    EXECUTE --> T4
    EXECUTE --> T5
    EXECUTE --> T6
    EXECUTE --> T7
    EXECUTE --> T8
    
    T1 -.-> RESULT[Tool Results]
    T2 -.-> RESULT
    T3 -.-> RESULT
    T4 -.-> RESULT
    T5 -.-> RESULT
    T6 -.-> RESULT
    T7 -.-> RESULT
    T8 -.-> RESULT
    
    style MCP_MAIN fill:#a78bfa,stroke:#7c3aed,stroke-width:3px
    style EXECUTE fill:#ff6b6b
    style RESULT fill:#51cf66
```

## 🎯 Dynamic Plan Adaptation Flow

```mermaid
stateDiagram-v2
    [*] --> InitialPlan: AI creates initial plan<br/>(3-5 tools)
    
    InitialPlan --> ExecuteTool: Start execution
    
    ExecuteTool --> AnalyzeResult: Tool complete
    
    AnalyzeResult --> ExtractFindings: Parse results
    
    ExtractFindings --> AIDecision: AI analyzes findings
    
    AIDecision --> NeedAdaptation: Check if adaptation needed
    
    NeedAdaptation --> AdaptPlan: Yes - New findings require<br/>different approach
    NeedAdaptation --> ContinueCurrent: No - Current plan sufficient
    
    AdaptPlan --> AddTools: AI adds relevant tools
    AddTools --> ExecuteTool: Execute adapted plan
    
    ContinueCurrent --> ExecuteTool: Next tool in plan
    
    ExecuteTool --> CheckStop: After each execution
    
    CheckStop --> ExecuteTool: Continue (< 15 steps)
    CheckStop --> FinalAnalysis: Stop conditions met
    
    FinalAnalysis --> GenerateReport: Compile findings
    
    GenerateReport --> [*]: Pentest complete
    
    note right of AIDecision
        AI Decision Factors:
        - Tool results quality
        - Vulnerabilities found
        - Attack surface discovered
        - Risk level assessment
        - Remaining coverage gaps
    end note
    
    note right of AdaptPlan
        Adaptation Examples:
        - Port 80 found → Add web tools
        - WordPress detected → Add CMS tools
        - API found → Add API security tools
        - SQL injection → Add DB tools
    end note
```

## 📊 Pentest Süreç Metrikleri

```mermaid
graph TB
    subgraph "📈 Real-time Metrics"
        M1[Tools Executed: X/15]
        M2[Findings Found: Y]
        M3[Critical: A<br/>High: B<br/>Medium: C]
        M4[Success Rate: Z%]
        M5[Execution Time: T sec]
    end
    
    subgraph "🎯 Quality Indicators"
        Q1[Coverage Score]
        Q2[Test Depth]
        Q3[AI Decision Quality]
        Q4[Plan Effectiveness]
    end
    
    subgraph "🚨 Risk Assessment"
        R1[Overall Risk Score: 0-100]
        R2[Attack Surface Size]
        R3[Exploitability Index]
        R4[Business Impact]
    end
    
    M1 --> Q1
    M2 --> Q2
    M3 --> R1
    M4 --> Q4
    
    Q1 --> FINAL[📄 Final Report]
    Q2 --> FINAL
    Q3 --> FINAL
    Q4 --> FINAL
    R1 --> FINAL
    R2 --> FINAL
    R3 --> FINAL
    R4 --> FINAL
    
    style FINAL fill:#51cf66,stroke:#2f9e44,stroke-width:3px
```

## 🔄 Tool Kategorileri ve İşlevleri

### 🔍 Reconnaissance Tools
- **rec_whois_tool**: Domain sahiplik bilgileri, DNS sunucuları
- **recon_dns_analyzer**: DNS kayıtları, MX, TXT records
- **recon_passive_subfinder**: Pasif subdomain keşfi (Certificate Transparency)
- **rec_intel_historical_analyzer**: Wayback Machine, historical data
- **rec_intel_code_scanner**: GitHub/GitLab kod sızıntıları

### 📊 Enumeration Tools
- **enum_port_scanner**: TCP/UDP port tarama, servis tespiti
- **enum_tech_detector**: Web teknolojileri, framework, CMS
- **enum_web_crawler**: Web sitesi yapısı, link keşfi
- **enum_directory_bruteforce**: Gizli dizin/dosya keşfi
- **enum_firewall_detector**: WAF/IDS/IPS tespiti
- **enum_subdomain_bruteforcer**: Aktif subdomain bruteforce

### 🚨 Vulnerability Assessment Tools
- **vuln_http_header_analyzer**: Güvenlik başlıkları (HSTS, CSP, X-Frame)
- **vuln_ssl_tls_analyzer**: SSL/TLS zafiyetleri, cipher suites
- **verify_sqli**: SQL Injection testi (boolean, time-based)
- **verify_xss**: Cross-Site Scripting testi (reflected, stored, DOM)
- **verify_lfi**: Local File Inclusion testi
- **vuln_idor_tester**: Insecure Direct Object Reference
- **vul_depency_scanner**: Third-party kütüphane zafiyetleri

### 🎯 API Security Tools
- **api_finder_active**: API endpoint keşfi
- **api_vuln_idor_scanner**: API IDOR zafiyetleri
- **api_vuln_jwt_tester**: JWT token güvenlik testleri

### 🏗️ Infrastructure Tools
- **infra_exposed_panels_finder**: Admin panel keşfi
- **cloud_s3_bucket_scanner**: AWS S3 bucket güvenliği
- **recon_origin_ip_finder**: CDN bypass, origin IP keşfi

## 🧠 AI Entegrasyonu Detayları

### 1. **Planner AI Prompts**
```
- Target classification (Domain/IP/URL/API)
- Risk assessment (Government/Educational/Commercial)
- Strategic tool selection
- Attack surface mapping
- Test coverage optimization
```

### 2. **Analyzer AI Prompts**
```
- Result interpretation
- Vulnerability categorization (OWASP Top 10)
- CVSS scoring
- Attack chain identification
- Next action recommendation
```

### 3. **Executor AI Enhancement**
```
- Custom payload generation
- WAF bypass techniques
- Dynamic wordlist creation
- Context-aware testing
```

## 📝 Önemli Notlar

### ✅ Sistem Özellikleri
1. **Tamamen Otonom**: Kullanıcı müdahalesi gerektirmez
2. **AI Destekli**: Gemini 2.0 Flash ile stratejik kararlar
3. **Dinamik Adaptasyon**: Sonuçlara göre plan değişir
4. **Kapsamlı Analiz**: OWASP Top 10, CVSS skorlama
5. **Güvenli Tasarım**: Sadece tespit odaklı, sömürü yok

### ⚠️ Güvenlik Kontrolleri
1. **Tehlikeli Tool Filtresi**: RCE, privilege escalation engellendi
2. **Loop Prevention**: Aynı tool tekrar engellidir
3. **Timeout Management**: Her tool için maksimum süre
4. **Rate Limiting**: API abuse önleme
5. **Etik Testler**: Sadece bilgi toplama ve tespit

### 🎯 AI Karar Mantığı
1. **Context-Aware**: Önceki sonuçları dikkate alır
2. **Risk-Based**: Kritik bulgulara öncelik verir
3. **Efficient**: Gereksiz tool'ları atlar
4. **Adaptive**: Her hedef için farklı strateji
5. **Learning**: Sonuçlardan öğrenir ve adapte olur

---

**🔐 PentAgent**: AI-Powered Autonomous Penetration Testing Platform
**📅 Version**: 2.0.0-dynamic
**🤖 AI Model**: Google Gemini 2.0 Flash

