"""
analyzer.py - Taxonomy classification, metadata synthesis, and NLP heuristic analyzer.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import re
from typing import List, Tuple, Dict, Optional

from harvester.models import Paper

# 37 Specialized Fuzzy Categories (matching Fuzzy Research - Materials Database.xlsx)
FUZZY_CATEGORIES: Dict[str, str] = {
    "1.0": "Fuzzy Systems & Fuzzy-Related Research",
    "1.1": "Fuzzy Machine Learning & Neuro-Fuzzy Systems",
    "1.2": "Fuzzy Logic & Reasoning",
    "1.3": "Fuzzy Set Extensions",
    "1.5": "Fuzzy Inference Systems",
    "1.7": "Fuzzy Decision-Making & Multi-Criteria Decision-Making",
    "1.8": "Fuzzy Classification, Clustering & Pattern Recognition",
    "1.9": "Fuzzy Optimization & Computational Methods",
    "1.11": "Fuzzy Time-Series, Forecasting & Sequential Models",
    "1.13": "Fuzzy AI, Knowledge Representation & Intelligent Systems",
    "1.14": "Fuzzy Image Processing, Computer Vision & Multimedia",
    "1.15": "Fuzzy Data Mining, Knowledge Discovery & Big Data",
    "1.16": "Fuzzy Optimization in Engineering, Operations & Industrial Systems",
    "1.18": "Fuzzy Deep Learning Architectures & Representation Learning",
    "1.19": "Fuzzy Evolutionary Computing, Swarm Intelligence & Metaheuristic Systems",
    "1.21": "Fuzzy Explainable AI, Trustworthy AI & Human-Centred Intelligence",
    "1.22": "Fuzzy Graphs, Networks, Social Systems & Complex Network Intelligence",
    "1.23": "Fuzzy Rough Sets, Granular Computing & Hybrid Uncertainty Models",
    "1.24": "Fuzzy Automata, Formal Languages, Computing & Fuzzy Algorithms",
    "1.25": "Fuzzy Mathematical Modelling, Differential Equations & Dynamical Systems",
    "1.26": "Fuzzy Bioinformatics, Computational Biology & Biomedical Intelligence",
    "1.27": "Fuzzy Agriculture, Food Systems, Environmental Intelligence & Smart Sustainability",
    "1.28": "Fuzzy Transportation, Traffic Systems, Logistics & Smart Mobility",
    "1.29": "Fuzzy Healthcare, Medical Diagnosis, Biomedical Engineering & Clinical Decision Support",
    "1.31": "Fuzzy Cybersecurity, Network Security & Intelligent Threat Detection",
    "1.32": "Fuzzy Education, E-Learning, Student Modelling & Intelligent Tutoring Systems",
    "1.33": "Fuzzy Manufacturing, Industry 4.0, Industrial IoT & Smart Factories",
    "1.34": "Fuzzy Energy Systems, Renewable Energy, Power Systems & Smart Grids",
    "1.35": "Fuzzy Water Resources, Hydrology, Flood Management & Environmental Risk",
    "1.36": "Fuzzy Air Pollution, Climate Intelligence, Remote Sensing & Earth Observation",
    "1.37": "Fuzzy Geology, Landslides, Earthquake Risk, Geological Hazards & Geospatial Intelligence",
    "1.39": "Fuzzy Space Science, Astronomy, Satellite Systems & Aerospace Intelligence",
    "1.42": "Fuzzy Mathematics, Fuzzy Analysis, Algebra, Topology & Mathematical Structures",
    "1.45": "Fuzzy Human–Computer Interaction, Affective Computing, Cognitive Systems & Human Intelligence",
    "1.47": "Fuzzy Machine Learning Theory, Learning Paradigms & Generalization",
    "1.55": "Fuzzy Transfer Learning, Domain Adaptation & Continual Learning",
}

# Universal Scientific & Engineering Categories
UNIVERSAL_CATEGORIES: Dict[str, str] = {
    "2.1": "Deep Learning Architectures, Representation Learning & Transformers",
    "2.2": "Reinforcement Learning, Decision Making & Autonomous Agents",
    "2.3": "Generative AI, Large Language Models & Foundation Models",
    "2.4": "Machine Learning Theory, Statistical Foundations & Generalization",
    "2.5": "Transfer Learning, Domain Adaptation & Continual Learning",
    "2.6": "Explainable AI (XAI), Trustworthy AI & Model Interpretability",
    "3.1": "Computer Vision, Object Detection & Scene Understanding",
    "3.2": "Image Processing, Denoising, Super-Resolution & Reconstruction",
    "4.1": "Natural Language Processing, Text Mining & Information Extraction",
    "4.2": "Information Retrieval, Semantic Search & Knowledge Graphs",
    "5.1": "Robotics, Autonomous Navigation, SLAM & Motion Planning",
    "5.2": "Control Systems, Dynamical Modeling & State Estimation",
    "6.1": "Healthcare Decision Support, Clinical AI & Medical Informatics",
    "6.2": "Computational Biology, Bioinformatics, Genomics & Drug Discovery",
    "7.1": "Cybersecurity, Network Security, Malware & Intrusion Detection",
    "7.2": "Cryptography, Privacy-Preserving Systems & Blockchain",
    "8.1": "Data Mining, Big Data Analytics & Database Engineering",
    "8.2": "Combinatorial Optimization, Metaheuristics & Operations Research",
    "9.1": "Smart Grids, Energy Systems & Power Engineering",
    "9.2": "IoT, Edge Computing, Sensor Networks & Embedded Systems",
    "9.3": "Environmental Intelligence, Remote Sensing & Climate Science",
    "9.4": "Materials Science, Nanotechnology & Physical Simulations"
}

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "1.1": ["neuro-fuzzy", "anfis", "fuzzy neural", "fuzzy deep", "fuzzy c-means", "fuzzy svm"],
    "1.2": ["fuzzy logic", "fuzzy reasoning", "approximate reasoning", "truth value", "fuzzy implication", "t-norm"],
    "1.3": ["type-2", "intuitionistic", "hesitant", "neutrosophic", "pythagorean", "q-rung", "spherical", "rough fuzzy", "complex fuzzy"],
    "1.5": ["fuzzy inference", "mamdani", "takagi-sugeno", "sugeno", "tsk", "fuzzy rule", "rule base"],
    "1.7": ["mcdm", "mcda", "topsis", "ahp", "promethee", "electre", "vikor", "bwm", "multi-criteria", "decision-making"],
    "1.8": ["fuzzy clustering", "fcm", "fuzzy c-means", "pattern recognition", "fuzzy classifier"],
    "1.9": ["fuzzy optimization", "fuzzy programming", "fuzzy linear programming", "fuzzy constraint"],
    "1.14": ["fuzzy image", "image segmentation", "edge detection", "fuzzy filter", "image enhancement"],
    "1.15": ["fuzzy data mining", "fuzzy association rules", "association rule mining"],
    "1.21": ["explainable", "interpretability", "transparent fuzzy", "xai", "fuzzy rule extraction"],
    "1.23": ["rough set", "fuzzy rough", "granular computing", "information granules", "three-way decisions"],
    "1.26": ["bioinformatics", "gene expression", "biomedical signal", "protein"],
    "1.29": ["medical diagnosis", "healthcare", "clinical", "disease", "covid", "cancer", "ecg", "eeg"],
    "1.31": ["cybersecurity", "intrusion detection", "malware", "network security", "ddos", "phishing"],
    "1.34": ["smart grid", "power system", "photovoltaic", "solar", "wind power", "renewable energy"],
    "2.1": ["transformer", "bert", "attention mechanism", "diffusion model", "resnet", "convolutional neural"],
    "2.2": ["reinforcement learning", "q-learning", "policy gradient", "markov decision", "agent"],
    "2.3": ["large language model", "llm", "generative ai", "gpt", "rag", "prompt engineering"],
    "2.6": ["explainability", "shap", "lime", "feature attribution", "counterfactual", "interpretability"],
    "3.1": ["object detection", "yolo", "segmentation", "scene understanding", "camera", "visual"],
    "4.1": ["natural language processing", "nlp", "sentiment analysis", "named entity", "text classification"],
    "6.1": ["clinical", "patient", "medical informatics", "diagnosis", "health", "hospital"],
    "7.1": ["malware", "intrusion", "vulnerability", "firewall", "cyber", "attack detection"]
}


class PaperAnalyzer:
    """Enriches paper records with analytical metadata and categories."""

    @classmethod
    def classify_categories(cls, paper: Paper, query: str = "") -> Tuple[Tuple[str, str], List[Tuple[str, str]]]:
        """Classifies paper into primary category and up to 5 secondary categories."""
        combined_text = f"{paper.title} {paper.abstract} {query}".lower()
        scored_cats: List[Tuple[int, str, str]] = []

        is_fuzzy_context = "fuzzy" in combined_text or "neuro-fuzzy" in combined_text
        all_categories = {**FUZZY_CATEGORIES, **UNIVERSAL_CATEGORIES}

        for cat_id, keywords in CATEGORY_KEYWORDS.items():
            cat_name = all_categories.get(cat_id, "Specialized Research")
            score = 0
            for kw in keywords:
                if kw in combined_text:
                    score += 2 if kw in paper.title.lower() else 1
            if score > 0:
                scored_cats.append((score, cat_id, cat_name))

        scored_cats.sort(key=lambda x: x[0], reverse=True)

        if scored_cats:
            primary = (scored_cats[0][1], scored_cats[0][2])
            secondaries = [(c[1], c[2]) for c in scored_cats[1:6]]
        else:
            if is_fuzzy_context:
                primary = ("1.0", FUZZY_CATEGORIES["1.0"])
            else:
                primary = ("2.1", UNIVERSAL_CATEGORIES["2.1"])
            secondaries = []

        return primary, secondaries

    @classmethod
    def extract_problem(cls, paper: Paper) -> str:
        """Derives research problem statement from abstract or title."""
        text = paper.abstract or paper.title
        match = re.search(r"(?:address|solve|tackle|investigate|focus(?:es)? on|propose(?:s)?)\s+([^.;]+)", text, re.IGNORECASE)
        if match:
            clean = match.group(1).strip()
            return f"Addresses {clean[:120]}"
        return f"Investigation and methodology in {paper.title[:100]}"

    @classmethod
    def extract_application(cls, paper: Paper) -> str:
        """Derives target domain or application area."""
        text = f"{paper.title} {paper.abstract}".lower()
        domains = [
            ("Healthcare / Clinical Decision Support", ["medical", "health", "clinical", "disease", "patient"]),
            ("Robotics & Autonomous Systems", ["robot", "uav", "autonomous vehicle", "slam", "navigation"]),
            ("Cybersecurity & Network Defense", ["security", "malware", "intrusion", "threat", "cyber"]),
            ("Smart Energy & Renewable Systems", ["power grid", "energy", "solar", "wind", "renewable"]),
            ("Image Processing & Computer Vision", ["image", "video", "computer vision", "segmentation"]),
            ("Industrial Automation & Manufacturing", ["industry 4.0", "manufacturing", "fault detection", "sensor"])
        ]
        for name, keywords in domains:
            if any(k in text for k in keywords):
                return name
        return "Applied Computing & Intelligent Systems"

    @classmethod
    def analyze_paper(cls, paper: Paper, query: str = "", material_idx: int = 1) -> Paper:
        """Enriches Paper instance with analytical fields."""
        paper.material_id = f"M-{material_idx:04d}"
        primary, secondaries = cls.classify_categories(paper, query)
        paper.primary_category_id = primary[0]
        paper.primary_category_name = primary[1]
        paper.secondary_cats = secondaries

        paper.main_problem = cls.extract_problem(paper)
        paper.main_application = cls.extract_application(paper)

        # Learning Level
        title_lower = paper.title.lower()
        if any(w in title_lower for w in ["survey", "review", "introduction", "tutorial", "foundations"]):
            paper.learning_level = "Foundational"
            paper.importance = "Very High"
        elif any(w in title_lower for w in ["advanced", "novel", "framework", "architecture"]):
            paper.learning_level = "Advanced"
            paper.importance = "High"
        else:
            paper.learning_level = "Intermediate"
            paper.importance = "High"

        # Relevance Score (1-10)
        paper.relevance_score = 10 if (paper.scopus_indexed or paper.wos_indexed or paper.ieee_indexed) else 8
        paper.notes = f"Harvested via {paper.source} pipeline. Verification: {paper.verification_source or 'Open Access'}"

        return paper
