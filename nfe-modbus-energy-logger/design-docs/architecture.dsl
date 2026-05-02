/*
 * Structurizr DSL — Lubega Power Theft Detection System
 * Repo: https://github.com/Lovepankie/Lubega_code
 * Version: v3.0.0 (inference + dashboard — feature/live-inference-dashboard branch)
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
        supabase = softwareSystem "Supabase (Free Tier)" "PostgreSQL database hosted on Supabase cloud. Stores theft alert records. Acts as the data bridge between the Pi and the Streamlit dashboard. 500 MB free tier." "External"

        streamlitCloud = softwareSystem "Streamlit Community Cloud" "Free cloud hosting for the Streamlit dashboard. Reads alerts from Supabase and displays live meter readings and theft alert history to the utility operator." "External"

        zerotier = softwareSystem "ZeroTier VPN" "Software-defined private network connecting the Raspberry Pi to the development machine for remote access and deployment. Free up to 25 nodes." "External"

        chintMeter = softwareSystem "CHINT DTSU666 3-Phase Meter" "Physical energy meter measuring voltages (L1/L2/L3), currents, active power, power factor, and frequency. Communicates via Modbus RTU over RS485 at 9600 baud." "Hardware"

        # ── The System ──────────────────────────────────────────────────────────
        lubegaSystem = softwareSystem "Lubega Power Theft Detection System" "End-to-end system that reads live meter data, runs ML inference to detect CT bypass theft, stores alerts to the cloud, and displays them on a web dashboard — all at zero ongoing cloud cost." {

            # ── Containers ────────────────────────────────────────────────────
            piApp = container "Raspberry Pi 4 — Edge Node" "Headless Linux device (Debian 13 Trixie). Runs the meter polling loop and ML inference loop as systemd services. Connected to the CHINT meter via RS485/USB." "Python 3 / Debian Linux" "Pi" {

                # ── Metering subsystem ────────────────────────────────────────
                meterService = component "meter.service (systemd)" "Systemd unit that runs src/main.py. Auto-restarts on failure. Starts on boot. Depends on /dev/ttyUSB0 being available." "systemd"

                mainLoop = component "main.py" "Main event loop. Orchestrates polling, aggregation, and CSV writing. Runs indefinitely with a configurable poll_interval (default 10s) and log_interval (default 900s = 15 min)." "Python"

                meterReader = component "meter_reader.py" "Modbus RTU register reader for CHINT DTSU666 (3-phase) and DDSU666 (1-phase). Reads 9 register groups: V_L1/L2/L3 (0x2006), I_L1/L2/L3 (0x200C), P_total/L1/L2/L3 (0x2012), PF (0x2020), F (0x2044), E (0x4000). Decodes IEEE 754 floats from 32-bit register pairs." "Python"

                modbusClient = component "modbus_client.py / modbus_factory.py" "PyModbus wrapper. Supports two backends: pymodbus (default, production) and mbpoll (alternative). Factory pattern selects backend from config.yaml. Retry logic on CRC or timeout errors." "Python"

                aggregator = component "aggregator.py (FifteenMinuteAggregator)" "Buffers 10-second poll readings in memory. Every 15 minutes, computes: average V/I/P/PF/F across all readings in the window. Passes aggregate row to the CSV logger." "Python"

                energyCalc = component "energy_calc.py" "Trapezoidal integration of power readings to compute per-phase energy (E_L1_cal, E_L2_cal, E_L3_cal) over the 15-minute window. More accurate than relying on meter's cumulative register alone for partial-window billing." "Python"

                csvLogger = component "rotating_csv_logger.py" "Writes 15-min aggregate rows to per-meter CSV files (data/meter_NNN/meter_NNN_YYYY-MM-DD.csv). Auto-rotates at 50,000 rows. Gzip-compresses old files. Writes BILL-EXACT markers at start of each billing month." "Python"

                stateManager = component "state_manager.py" "Persists energy accumulation state to JSON (data/state/meter_NNN_state.json). Survives process restarts and power cuts. Restores integration continuity on startup." "Python"

                # ── Inference subsystem (TO BUILD) ────────────────────────────
                detectorService = component "theft-detector.service (TO BUILD)" "Systemd unit wrapping detect.py. Runs after meter.service stabilises. Restarts on failure. Runs inference every 15 minutes aligned to aggregation window." "systemd — PLANNED"

                detectScript = component "detect.py (TO BUILD)" "Main inference loop. Every 15 min: reads the latest row from the active CSV, engineers 20 features, scales with scaler.pkl, runs theft_detector.pkl, logs result. If prob > threshold (e.g. 0.7), constructs an alert and POSTs it to Supabase REST API." "Python — PLANNED"

                featureEngineer = component "feature_engineering.py (TO BUILD)" "20-feature engineering pipeline extracted from train_model.py. Takes one raw reading row (9 values) and returns a 20-element feature vector: I_imbalance, V_imbalance, I_L1/L2/L3_zero (flags), V_L1/L2/L3_zero (flags), PF_zero, I_total, P_per_I." "Python — PLANNED"

                # ── ML Model artefacts ────────────────────────────────────────
                theftDetectorModel = component "theft_detector.pkl" "Trained VotingClassifier (soft voting): RandomForestClassifier (200 trees, max_depth=15, balanced class weights) + XGBClassifier (200 rounds, max_depth=6, scaled_pos_weight). Test AUC=1.0000. 14.4 MB on disk." "Joblib / scikit-learn"

                scalerModel = component "scaler.pkl" "StandardScaler fitted on all 20 features from the ~160K-row training set. Must be applied before inference. 1.5 KB." "Joblib / scikit-learn"

                featuresFile = component "features.pkl" "Ordered list of 20 feature names. Used to ensure feature ordering matches what the model was trained on." "Joblib / Python list"

                # ── Data storage on Pi ────────────────────────────────────────
                csvStore = component "data/ (CSV files)" "Per-meter daily CSV files. 96 rows/day (4/hour at 15-min intervals). ~10-15 KB/day per meter. Rotated and gzip-compressed at 50,000 rows (~17 months). detect.py reads the active file's last row." "FileSystem"

                configFile = component "config/config.prod.yaml" "YAML config: Modbus port (/dev/ttyUSB0), meter definitions (id, name, type, enabled), poll_interval, log_interval, logging paths. Not committed to Git (environment-specific)." "YAML"
            }

            # ── Development Machine ───────────────────────────────────────────
            devMachine = container "Development Machine (Windows/Mac)" "Hillary's laptop. Runs model training, report generation, and code development. Not part of the live inference path." "Python / scikit-learn / XGBoost" "Laptop" {

                trainScript = component "scripts/train_model.py" "Full ML training pipeline. Loads all 8 scenario CSVs from docs/, engineers 20 features, splits 80/20, trains VotingClassifier, evaluates (AUC, confusion matrix, ROC), saves model/scaler/features.pkl to model/." "Python"

                collectScript = component "scripts/collect_data.py" "Field data collection. Reads live meter, writes labelled CSV (--label bypass_red etc). Used to grow the training dataset on-site." "Python"

                reportScripts = component "scripts/generate_*_report.py (9 scripts)" "PDF report generators using ReportLab + Matplotlib. Produces model_report.pdf and 8 scenario bypass analysis reports. Output goes to docs/." "Python / ReportLab"
            }

            # ── Streamlit Dashboard (TO BUILD) ────────────────────────────────
            streamlitApp = container "Streamlit Dashboard (TO BUILD)" "Web dashboard for utility operators. Hosted on Streamlit Community Cloud (free tier, GitHub-connected). Reads alert data from Supabase. Shows live-ish meter readings and theft alert log." "Python / Streamlit" "Web App — PLANNED" {

                dashboardMain = component "app/app.py (TO BUILD)" "Streamlit main app. Pages: Live Readings (latest meter values from Supabase), Alert Log (sortable table of theft alerts with timestamp + confidence), Charts (current imbalance trend). Auto-refreshes every 30-60s via st.rerun()." "Python / Streamlit — PLANNED"

                supabaseClient = component "Supabase Python client (TO BUILD)" "supabase-py client connecting to Supabase project. Reads from `alerts` table and `readings` table. Used by Streamlit app." "Python / supabase-py — PLANNED"
            }
        }

        # ── Relationships — Context ─────────────────────────────────────────────
        thief -> chintMeter "Bypasses CT clamp on" "Physical tampering"
        chintMeter -> lubegaSystem "Reports altered readings to"
        lubegaSystem -> utility "Sends theft alert to" "Streamlit dashboard"
        lubegaSystem -> supabase "Stores alerts in" "HTTP POST (REST API)"
        streamlitCloud -> supabase "Reads alerts from" "REST API"
        utility -> streamlitCloud "Monitors dashboard on"
        engineer -> lubegaSystem "Deploys, trains, and maintains"
        engineer -> zerotier "Uses for remote Pi access"
        zerotier -> piApp "Provides secure tunnel to"

        # ── Relationships — Container ───────────────────────────────────────────
        chintMeter -> piApp "Sends Modbus RTU readings to" "RS485 / 9600 baud"
        piApp -> supabase "POSTs theft alerts to" "HTTP REST API (supabase-py)"
        streamlitApp -> supabase "Reads alerts and readings from" "REST API"
        utility -> streamlitApp "Views on browser"
        engineer -> devMachine "Trains models and writes code on"
        devMachine -> piApp "Deploys code and model to" "SSH / SCP via ZeroTier"

        # ── Relationships — Component (Pi metering) ─────────────────────────────
        meterService -> mainLoop "Runs as systemd process"
        mainLoop -> meterReader "Calls every poll_interval (10s)"
        mainLoop -> aggregator "Feeds readings into"
        mainLoop -> csvLogger "Triggers log write every log_interval (900s)"
        mainLoop -> configFile "Reads at startup"
        meterReader -> modbusClient "Issues register reads via"
        modbusClient -> chintMeter "Sends Modbus RTU requests to" "RS485"
        aggregator -> energyCalc "Calls for trapezoidal integration"
        aggregator -> csvLogger "Passes 15-min aggregate row to"
        csvLogger -> csvStore "Writes rows to"
        csvLogger -> stateManager "Reads/writes energy state via"

        # ── Relationships — Component (Pi inference, PLANNED) ───────────────────
        detectorService -> detectScript "Runs every 15 min"
        detectScript -> csvStore "Reads latest aggregate row from"
        detectScript -> featureEngineer "Passes raw row to"
        featureEngineer -> featuresFile "Uses feature order from"
        detectScript -> scalerModel "Scales feature vector with"
        detectScript -> theftDetectorModel "Runs predict_proba() on"
        detectScript -> supabase "POSTs alert record to if prob > threshold" "HTTP REST API"

        # ── Relationships — Component (dev machine) ─────────────────────────────
        trainScript -> theftDetectorModel "Produces"
        trainScript -> scalerModel "Produces"
        trainScript -> featuresFile "Produces"
        collectScript -> csvStore "Writes labelled data to (field use)"
        reportScripts -> theftDetectorModel "Reads for evaluation reports"

        # ── Relationships — Component (dashboard) ───────────────────────────────
        dashboardMain -> supabaseClient "Queries via"
        supabaseClient -> supabase "Reads alerts from" "REST API"
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
            description "Four main containers: Pi (edge), Dev Machine (training), Streamlit (dashboard), Supabase (alert store)."
        }

        # ── Component — Pi full ───────────────────────────────────────────────────
        component piApp "Components_Pi" {
            include *
            autoLayout tb
            title "Raspberry Pi — All Components"
            description "Metering subsystem (built) + inference subsystem (planned). Items marked TO BUILD are the missing critical path to live detection."
        }

        # ── Component — metering only ─────────────────────────────────────────────
        component piApp "Components_Metering" {
            include meterService mainLoop meterReader modbusClient aggregator energyCalc csvLogger stateManager csvStore configFile chintMeter
            autoLayout tb
            title "Metering Subsystem (COMPLETE)"
            description "The complete data collection pipeline: Modbus poll → 15-min aggregate → CSV. All built and deployed."
        }

        # ── Component — inference path (critical path) ────────────────────────────
        component piApp "Components_Inference" {
            include detectorService detectScript featureEngineer scalerModel theftDetectorModel featuresFile csvStore supabase
            autoLayout tb
            title "Inference Subsystem (TO BUILD — Critical Path)"
            description "The missing inference pipeline. detect.py + theft-detector.service + Supabase push = live detection."
        }

        # ── Component — dashboard ─────────────────────────────────────────────────
        component streamlitApp "Components_Dashboard" {
            include dashboardMain supabaseClient supabase utility
            autoLayout lr
            title "Streamlit Dashboard (TO BUILD)"
            description "The operator-facing alert and monitoring dashboard."
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
            element "Web App — PLANNED" {
                shape WebBrowser
                background "#8E44AD"
                color "#ffffff"
                border dashed
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
