/*
 * Structurizr DSL — Lubega Power Theft Detection System
 * Repo: https://github.com/RincolTech-Solutions-ltd/Lubega_code
 * Version: v4.0.0 (system FULLY LIVE — 2026-05-04)
 *
 * Milestone: End-to-end system operational.
 *   Pi: meter.service + theft-detector.service both running on nfetestpi2.
 *   Inference: detect.py (JSON polling, 10s cadence) active. VotingClassifier live.
 *   Cloud: Neon readings + alerts tables populated in real time.
 *   Dashboard: lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app live. Alerts visible.
 *   Local monitor: monitor.py (Streamlit) runs on Pi for on-site diagnostics.
 *   Known issue: I_L2 reads 0.000A permanently — false positive investigation pending.
 *
 * C4 Levels: Context → Container → Component
 * Render: https://structurizr.com/dsl  |  structurizr-cli export -f plantuml
 */

workspace "Lubega Power Theft Detection" "AI-powered real-time electricity theft detection for Uganda's distribution grid (UEDCL). Detects CT bypass tampering using a trained ensemble ML model on a Raspberry Pi, surfacing alerts via a Streamlit dashboard hosted on free cloud infrastructure." {

    model {

        # ── People ─────────────────────────────────────────────────────────────
        utility = person "Utility Operator (UEDCL)" "Monitors the Streamlit dashboard for theft alerts. Dispatches field teams to investigate flagged meters." "Operator"

        engineer = person "System Engineer / Developer" "Hillary or Dennis. Deploys updates to Pi and cloud. Trains and updates the ML model. Maintains the codebase." "Engineer"

        thief = person "Electricity Thief" "Bypasses one or more CT clamps on the CHINT meter to steal electricity. This is what the system detects." "External"

        # ── External Systems ────────────────────────────────────────────────────
        neon = softwareSystem "Neon PostgreSQL (Free Tier)" "Cloud-hosted PostgreSQL database. Stores theft alert records (alerts table) and live readings (readings table). Acts as the data bridge between the Pi and the Streamlit dashboard. Compute scales to zero on idle but DB is always reachable — no inactivity pause. Project: lubega-production." "External"

        streamlitCloud = softwareSystem "Streamlit Community Cloud" "Free cloud hosting for the Streamlit dashboard. Connects to Neon via st.connection and displays live meter readings and theft alert history to the utility operator. URL: lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app" "External"

        zerotier = softwareSystem "ZeroTier VPN" "Software-defined private network connecting the Raspberry Pi to the development machine for remote access and deployment. Free up to 25 nodes." "External"

        chintMeter = softwareSystem "CHINT DTSU666 3-Phase Meter" "Physical energy meter measuring voltages (L1/L2/L3), currents, active power, power factor, and frequency. Communicates via Modbus RTU over RS485 at 9600 baud." "Hardware"

        # ── The System ──────────────────────────────────────────────────────────
        lubegaSystem = softwareSystem "Lubega Power Theft Detection System" "End-to-end system that reads live meter data, runs ML inference to detect CT bypass theft, stores alerts to the cloud, and displays them on a web dashboard — all at zero ongoing cloud cost." {

            # ── Containers ────────────────────────────────────────────────────
            piApp = container "Raspberry Pi 4 — Edge Node" "Headless Linux device (Debian 13 Trixie). Runs the meter polling loop and ML inference loop as systemd services. Connected to the CHINT meter via RS485/USB." "Python 3 / Debian Linux" "Pi" {

                # ── Metering subsystem ────────────────────────────────────────
                meterService = component "meter.service (systemd)" "Systemd unit that runs src/main.py. Auto-restarts on failure. Starts on boot. Depends on /dev/ttyUSB0 being available." "systemd"

                mainLoop = component "main.py" "Main event loop. Orchestrates polling, aggregation, and CSV writing. Runs indefinitely with a configurable poll_interval (default 10s) and log_interval (default 900s = 15 min). Also writes latest_reading_{meter_id}.json after each raw poll for detect.py to consume." "Python"

                meterReader = component "meter_reader.py" "Modbus RTU register reader for CHINT DTSU666 (3-phase) and DDSU666 (1-phase). Reads 9 register groups: V_L1/L2/L3 (0x2006), I_L1/L2/L3 (0x200C), P_total/L1/L2/L3 (0x2012), PF (0x2020), F (0x2044), E (0x4000). Decodes IEEE 754 floats from 32-bit register pairs. Returns uppercase keys: I_L1, V_L1, etc." "Python"

                modbusClient = component "modbus_client.py / modbus_factory.py" "PyModbus wrapper. Supports two backends: pymodbus (default, production) and mbpoll (alternative). Factory pattern selects backend from config.yaml. Retry logic on CRC or timeout errors." "Python"

                aggregator = component "aggregator.py (FifteenMinuteAggregator)" "Buffers 10-second poll readings in memory. Every 15 minutes, computes: average V/I/P/PF/F across all readings in the window. Passes aggregate row to the CSV logger." "Python"

                energyCalc = component "energy_calc.py" "Trapezoidal integration of power readings to compute per-phase energy (E_L1_cal, E_L2_cal, E_L3_cal) over the 15-minute window. More accurate than relying on meter's cumulative register alone for partial-window billing." "Python"

                csvLogger = component "rotating_csv_logger.py" "Writes 15-min aggregate rows to per-meter CSV files (data/meter_NNN/meter_NNN_YYYY-MM-DD.csv). Auto-rotates at 50,000 rows. Gzip-compresses old files. Writes BILL-EXACT markers at start of each billing month." "Python"

                stateManager = component "state_manager.py" "Persists energy accumulation state to JSON (data/state/meter_NNN_state.json). Survives process restarts and power cuts. Restores integration continuity on startup." "Python"

                latestReading = component "data/latest_reading_{meter_id}.json" "Overwritten every 10 seconds by main.py with the freshest raw poll reading (uppercase keys: I_L1, V_L1, etc.). detect.py reads this file to get the same data distribution the model was trained on — avoids the 15-min averaging problem." "JSON file"

                localMonitor = component "monitor.py" "Local Streamlit diagnostic dashboard. Runs on the Pi for on-site inspection. Reads latest_reading_{meter_id}.json every 5s. Shows metric tiles (V/I/P per phase) and rolling 60-reading line charts (Current, Voltage, Power tabs). Not deployed to cloud — used by field engineers during commissioning and maintenance." "Python / Streamlit"

                # ── Inference subsystem (LIVE) ────────────────────────────────
                detectorService = component "theft-detector.service" "Systemd unit wrapping detect.py. Runs after meter.service stabilises. Restarts on failure. Polls detect.py every POLL_INTERVAL seconds (10s)." "systemd"

                detectScript = component "detect.py" "Main inference loop. Every 10s: reads latest_reading_{meter_id}.json, engineers 20 features, scales with scaler.pkl, runs theft_detector.pkl. INSERTs every reading into the readings table. If prob > threshold (0.5), also INSERTs into the alerts table. Skips if reading unchanged since last cycle." "Python"

                featureEngineer = component "feature_engineering.py" "20-feature engineering pipeline. Takes one raw reading dict (uppercase keys from meter_reader.py) and returns 20 features: I_L1/L2/L3, V_L1/L2/L3, P_total, PF_total, frequency + I_imbalance, V_imbalance, I_L1/L2/L3_zero (flags), V_L1/L2/L3_zero (flags), PF_zero, I_total, P_per_I." "Python"

                # ── ML Model artefacts ────────────────────────────────────────
                theftDetectorModel = component "theft_detector.pkl" "Trained VotingClassifier (soft voting): RandomForestClassifier (200 trees, max_depth=15, balanced class weights) + XGBClassifier (200 rounds, max_depth=6, scaled_pos_weight). Test AUC=1.0000. 14.4 MB on disk." "Joblib / scikit-learn"

                scalerModel = component "scaler.pkl" "StandardScaler fitted on all 20 features from the ~160K-row training set. Must be applied before inference. 1.5 KB." "Joblib / scikit-learn"

                featuresFile = component "features.pkl" "Ordered list of 20 feature names (uppercase). Used to ensure feature ordering matches what the model was trained on. Keys: I_L1, I_L2, I_L3, V_L1, V_L2, V_L3, P_total, PF_total, frequency, I_imbalance, V_imbalance, I_L1_zero, I_L2_zero, I_L3_zero, V_L1_zero, V_L2_zero, V_L3_zero, PF_zero, I_total, P_per_I." "Joblib / Python list"

                # ── Data storage on Pi ────────────────────────────────────────
                csvStore = component "data/ (CSV files)" "Per-meter daily CSV files. 96 rows/day (4/hour at 15-min intervals). ~10-15 KB/day per meter. Rotated and gzip-compressed at 50,000 rows (~17 months)." "FileSystem"

                configFile = component "config/config.prod.yaml" "YAML config: Modbus port (/dev/ttyUSB0), meter definitions (id, name, type, enabled), poll_interval, log_interval, logging paths. Not committed to Git (environment-specific)." "YAML"
            }

            # ── Development Machine ───────────────────────────────────────────
            devMachine = container "Development Machine (Windows/Mac)" "Hillary's laptop. Runs model training, report generation, and code development. Not part of the live inference path." "Python / scikit-learn / XGBoost" "Laptop" {

                trainScript = component "scripts/train_model.py" "Full ML training pipeline. Loads all 8 scenario CSVs from docs/, engineers 20 features, splits 80/20, trains VotingClassifier, evaluates (AUC, confusion matrix, ROC), saves model/scaler/features.pkl to model/." "Python"

                collectScript = component "scripts/collect_data.py" "Field data collection. Reads live meter, writes labelled CSV (--label bypass_red etc). Used to grow the training dataset on-site." "Python"

                reportScripts = component "scripts/generate_*_report.py (9 scripts)" "PDF report generators using ReportLab + Matplotlib. Produces model_report.pdf and 8 scenario bypass analysis reports. Output goes to docs/." "Python / ReportLab"
            }

            # ── Streamlit Dashboard (LIVE) ─────────────────────────────────────
            streamlitApp = container "Streamlit Dashboard (LIVE)" "Web dashboard for utility operators. Hosted on Streamlit Community Cloud. Reads alert data from Neon PostgreSQL. Shows KPI metrics, colour-coded alerts table, live readings charts, and alert trend. URL: lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app" "Python / Streamlit" "Web App" {

                dashboardMain = component "streamlit_app.py" "Streamlit main app. KPI row (total alerts, 24h count, latest probability, last alert time). Left column: colour-coded theft alerts table (red >=90%, yellow >=70%). Right column: live readings tabs (Current/Voltage/Power line charts). Alert trend bar chart. Auto-refreshes every 30s. NEON_DATABASE_URL loaded from st.secrets." "Python / Streamlit"

                neonConn = component "st.connection (neon, type=sql)" "Streamlit built-in SQL connection using psycopg2 under the hood. Connects to Neon PostgreSQL via NEON_DATABASE_URL secret. Queries alerts and readings tables with TTL=30s caching." "Python / SQLAlchemy"
            }
        }

        # ── Relationships — Context ─────────────────────────────────────────────
        thief -> chintMeter "Bypasses CT clamp on" "Physical tampering"
        chintMeter -> lubegaSystem "Reports altered readings to"
        lubegaSystem -> utility "Sends theft alert to" "Streamlit dashboard"
        lubegaSystem -> neon "Stores alerts in" "psycopg2 direct connection"
        streamlitCloud -> neon "Reads alerts from" "st.connection / psycopg2"
        utility -> streamlitCloud "Monitors dashboard on"
        engineer -> lubegaSystem "Deploys, trains, and maintains"
        engineer -> zerotier "Uses for remote Pi access"
        zerotier -> piApp "Provides secure tunnel to"

        # ── Relationships — Container ───────────────────────────────────────────
        chintMeter -> piApp "Sends Modbus RTU readings to" "RS485 / 9600 baud"
        piApp -> neon "INSERTs theft alerts to" "psycopg2 direct TCP connection"
        streamlitApp -> neon "Reads alerts and readings from" "st.connection (psycopg2 / SQLAlchemy)"
        utility -> streamlitApp "Views on browser"
        engineer -> devMachine "Trains models and writes code on"
        devMachine -> piApp "Deploys code and model to" "SSH / SCP via ZeroTier"

        # ── Relationships — Component (Pi metering) ─────────────────────────────
        meterService -> mainLoop "Runs as systemd process"
        mainLoop -> meterReader "Calls every poll_interval (10s)"
        mainLoop -> aggregator "Feeds readings into"
        mainLoop -> csvLogger "Triggers log write every log_interval (900s)"
        mainLoop -> latestReading "Overwrites with raw reading every 10s"
        mainLoop -> configFile "Reads at startup"
        meterReader -> modbusClient "Issues register reads via"
        modbusClient -> chintMeter "Sends Modbus RTU requests to" "RS485"
        aggregator -> energyCalc "Calls for trapezoidal integration"
        aggregator -> csvLogger "Passes 15-min aggregate row to"
        csvLogger -> csvStore "Writes rows to"
        csvLogger -> stateManager "Reads/writes energy state via"

        # ── Relationships — Component (Pi inference, LIVE) ─────────────────────
        detectorService -> detectScript "Runs every POLL_INTERVAL seconds"
        detectScript -> latestReading "Reads latest raw reading from"
        detectScript -> featureEngineer "Passes raw reading dict to"
        featureEngineer -> featuresFile "Uses feature order from"
        detectScript -> scalerModel "Scales feature vector with"
        detectScript -> theftDetectorModel "Runs predict_proba() on"
        detectScript -> neon "INSERTs every reading; INSERTs alert if prob > threshold" "psycopg2 TCP"
        localMonitor -> latestReading "Reads latest raw reading every 5s"

        # ── Relationships — Component (dev machine) ─────────────────────────────
        trainScript -> theftDetectorModel "Produces"
        trainScript -> scalerModel "Produces"
        trainScript -> featuresFile "Produces"
        collectScript -> csvStore "Writes labelled data to (field use)"
        reportScripts -> theftDetectorModel "Reads for evaluation reports"

        # ── Relationships — Component (dashboard) ───────────────────────────────
        dashboardMain -> neonConn "Queries via"
        neonConn -> neon "Reads alerts + readings from" "psycopg2 / SQLAlchemy"
    }

    views {

        # ── Context ──────────────────────────────────────────────────────────────
        systemContext lubegaSystem "SystemContext" {
            include *
            autoLayout lr
            title "Power Theft Detection — System Context"
            description "The Lubega system in its operational environment: meter, Pi, cloud, operator, thief."
        }

        # ── Container ────────────────────────────────────────────────────────────
        container lubegaSystem "Containers" {
            include *
            autoLayout lr
            title "Power Theft Detection — Containers"
            description "Four main containers: Pi (edge), Dev Machine (training), Streamlit dashboard (LIVE), Neon PostgreSQL (alert store)."
        }

        # ── Component — Pi full ───────────────────────────────────────────────────
        component piApp "Components_Pi" {
            include *
            autoLayout tb
            title "Raspberry Pi — All Components"
            description "Metering subsystem (LIVE) + inference subsystem (LIVE) + local monitor. Full end-to-end pipeline active on nfetestpi2."
        }

        # ── Component — metering only ─────────────────────────────────────────────
        component piApp "Components_Metering" {
            include meterService mainLoop meterReader modbusClient aggregator energyCalc csvLogger stateManager csvStore configFile chintMeter latestReading
            autoLayout tb
            title "Metering Subsystem (COMPLETE)"
            description "The complete data collection pipeline: Modbus poll → 15-min aggregate → CSV. Also writes latest_reading.json for inference."
        }

        # ── Component — inference path (critical path) ────────────────────────────
        component piApp "Components_Inference" {
            include detectorService detectScript featureEngineer scalerModel theftDetectorModel featuresFile latestReading neon
            autoLayout tb
            title "Inference Subsystem (LIVE)"
            description "The live inference pipeline. detect.py polls every 10s, engineers 20 features, runs VotingClassifier, INSERTs every reading to Neon. Alerts inserted when prob > 0.5. Known issue: I_L2=0.000A causing false positives — field investigation pending."
        }

        # ── Component — dashboard ─────────────────────────────────────────────────
        component streamlitApp "Components_Dashboard" {
            include dashboardMain neonConn neon utility
            autoLayout lr
            title "Streamlit Dashboard (LIVE — lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app)"
            description "The operator-facing alert and monitoring dashboard. Live. Showing real alerts and readings from the Pi inference pipeline."
        }

        # ── Component — training pipeline ─────────────────────────────────────────
        component devMachine "Components_Training" {
            include trainScript collectScript reportScripts theftDetectorModel scalerModel featuresFile
            autoLayout lr
            title "Model Training Pipeline (COMPLETE)"
            description "Offline training workflow on dev machine."
        }

        styles {
            element "Person" {
                shape Person
                background "#103A61"
                color "#ffffff"
            }
            element "Operator" {
                shape Person
                background "#1A6B2A"
                color "#ffffff"
            }
            element "Engineer" {
                shape Person
                background "#103A61"
                color "#ffffff"
            }
            element "External" {
                background "#999999"
                color "#ffffff"
            }
            element "Hardware" {
                shape Box
                background "#7B5C00"
                color "#ffffff"
            }
            element "Pi" {
                shape MobileDevicePortrait
                background "#C0392B"
                color "#ffffff"
            }
            element "Laptop" {
                background "#2C3E50"
                color "#ffffff"
            }
            element "Web App" {
                shape WebBrowser
                background "#1A6B2A"
                color "#ffffff"
            }
            element "Software System" {
                background "#1168BD"
                color "#ffffff"
            }
            element "Container" {
                background "#438DD5"
                color "#ffffff"
            }
            element "Component" {
                background "#85BBF0"
                color "#000000"
            }
        }
    }

    configuration {
        scope softwaresystem
    }
}
