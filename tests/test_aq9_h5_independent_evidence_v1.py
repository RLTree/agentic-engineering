"""Closed, result-blind checks for the AQ9/H5 E0 evidence packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = ROOT / "evals/foundation-v4/aq9-h5-independent-evidence-v1.json"

EXPECTED_TOP_LEVEL_ORDER = [
    "schema_version",
    "packet_id",
    "status",
    "claim_ceiling",
    "amendment_authority",
    "foundation_snapshot_authority",
    "zero_access_declaration",
    "provenance_families",
    "sources",
    "excluded_sources",
    "cross_source_tensions",
    "mechanism_families",
    "prospective_discriminators",
    "design_firewall",
    "claims_proven",
]
AMENDMENT_KEYS = ["commit", "tree", "path", "blob", "sha256", "byte_count"]
SNAPSHOT_KEYS = ["commit", "tree", "artifacts"]
SNAPSHOT_ARTIFACT_KEYS = ["role", "path", "blob", "sha256", "byte_count"]
ZERO_ACCESS_KEYS = [
    "scope",
    "sole_permitted_prior_fact",
    "prohibited_material",
    "accessed_any_prohibited_material",
    "received_prohibited_disclosure_or_summary",
    "used_role_transfer_or_intermediary_to_access",
    "used_any_aq8_result_beyond_permitted_fact",
]
PROVENANCE_KEYS = [
    "provenance_family_id",
    "label",
    "independence_basis",
    "source_ids",
]
SOURCE_KEYS = [
    "source_id",
    "title",
    "provenance_family_id",
    "source_kind",
    "provenance_owner",
    "authors",
    "publication_date",
    "publication_date_precision",
    "identity",
    "artifact",
    "supported_claims",
    "unsupported_extrapolations",
    "uncertainties",
    "tension_ids",
    "prospective_discriminator_ids",
]
IDENTITY_KEYS = ["doi", "arxiv_id", "proceedings_identity"]
ARTIFACT_KEYS = [
    "uri",
    "version",
    "retrieved_on",
    "media_type",
    "byte_count",
    "sha256",
    "retrieval_disposition",
]
TENSION_KEYS = ["tension_id", "source_ids", "statement"]
MECHANISM_FAMILY_KEYS = [
    "family_id",
    "label",
    "status",
    "evidence_source_ids",
    "non_isomorphism_to_h4",
    "supported_constraints",
    "unsupported_extrapolations",
    "prospective_discriminator_ids",
]
DISCRIMINATOR_KEYS = [
    "discriminator_id",
    "family_ids",
    "observable",
    "falsifying_observation",
    "claim_boundary",
]
DESIGN_FIREWALL_KEYS = [
    "family_order_semantics",
    "mechanism_choice_made",
    "mechanism_composition_made",
    "h5_prompt_authored",
    "h5_threshold_authored",
    "h5_schema_authored",
    "h5_corpus_authored",
    "h5_tuning_performed",
]
CLAIMS_PROVEN_KEYS = [
    "source_identity_and_digest_metadata_frozen",
    "source_artifact_bytes_retained",
    "source_artifact_byte_reverification_in_test",
    "independent_external_provenance_families",
    "h5_mechanism_selected",
    "h5_mechanism_composed",
    "h5_efficacy",
    "runtime",
    "provider",
    "model",
    "security",
    "product",
    "promotion",
    "authority_effect",
]

EXPECTED_AMENDMENT = {
    "commit": "e7ca9e9b89aad1a1933da5378d11d84240c210f7",
    "tree": "475d93faf9b4853eb120a6230f5e5cef36178f84",
    "path": "EXECPLAN.md",
    "blob": "9d26f09877ea55ddc17eddd8b97ce8b387b96f1b",
    "sha256": "acf1b68b3194ee4852f773aac7c18b8e7222fd47f6091e5858b5e06eea0bc141",
    "byte_count": 46262,
}
EXPECTED_FOUNDATION_COMMIT = "56f42c2b134fa961bbe6f986428fd57e9271f082"
EXPECTED_FOUNDATION_TREE = "f905601840e370c4fc94baf0e3440fc7ac513670"
EXPECTED_FOUNDATION_ARTIFACTS = [
    {
        "role": "current_foundation_authority",
        "path": "docs/foundations/current-2026-08-08.md",
        "blob": "f6add640a93090b9297444fa5eb5c96f4374907e",
        "sha256": ("48791730f64ca4a452a686a9078e6bf14a0ac2ccc6d0cec1c2b9c69924df3b27"),
        "byte_count": 16372,
    },
    {
        "role": "foundation_register",
        "path": "docs/foundations/register.csv",
        "blob": "eade50e09f117bb7c40e394f5c7b8b2686fb48ad",
        "sha256": ("3043ad8ff93cbf35779638be9e8a7c8e7082d14166297fdddab9b9d1ddadeaf3"),
        "byte_count": 21203,
    },
    {
        "role": "foundation_update_policy",
        "path": "UPDATE-POLICY.md",
        "blob": "4cad2ea965621a5d78cbefc804d719d2f1023b9f",
        "sha256": ("7ab2b9f627236e5adab2368a44ec476a77442186709894a0006e8129021e2ebe"),
        "byte_count": 2504,
    },
]

EXPECTED_SOURCE_ORDER = [
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    "E8",
    "E9",
    "E10",
    "E11",
]
EXPECTED_SOURCE_CUSTODY = {
    "E1": {
        "title": "Selective Classification for Deep Neural Networks",
        "family": "PF1-selective-prediction-calibration",
        "kind": "primary_method_and_empirical_paper",
        "owner": "Yonatan Geifman and Ran El-Yaniv; arXiv",
        "authors": ["Yonatan Geifman", "Ran El-Yaniv"],
        "date": "2017-05-23",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.1705.08500",
            "arxiv_id": "1705.08500",
            "proceedings_identity": None,
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/1705.08500v2",
            "version": "arXiv:1705.08500v2, revised 2017-06-01",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 614365,
            "sha256": (
                "91899dfcbc41553f571f7a491839733e4d16f81d82e9274278e8f06ffc42022b"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "b1f0ddaf79fe05725bfc4439a54bf340f0392c04801569d92db95f1f521248e1"
        ),
    },
    "E2": {
        "title": "Conformal Risk Control",
        "family": "PF1-selective-prediction-calibration",
        "kind": "primary_method_and_empirical_paper",
        "owner": (
            "Anastasios N. Angelopoulos, Stephen Bates, Adam Fisch, Lihua Lei, "
            "and Tal Schuster; arXiv"
        ),
        "authors": [
            "Anastasios N. Angelopoulos",
            "Stephen Bates",
            "Adam Fisch",
            "Lihua Lei",
            "Tal Schuster",
        ],
        "date": "2022-08-04",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.2208.02814",
            "arxiv_id": "2208.02814",
            "proceedings_identity": None,
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/2208.02814v4",
            "version": "arXiv:2208.02814v4, revised 2025-06-13",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 1623636,
            "sha256": (
                "32c3b9689cb69dbec96ce87ba8b0fe98293bb1c9a59247480b16dbae6aa37df2"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "7d5576a5918c5e2e312dda5e6f2f04d48b604b454065a8cda6fec2118d71bc9b"
        ),
    },
    "E3": {
        "title": "On Calibration of Modern Neural Networks",
        "family": "PF1-selective-prediction-calibration",
        "kind": "primary_method_and_empirical_paper",
        "owner": ("Chuan Guo, Geoff Pleiss, Yu Sun, and Kilian Q. Weinberger; PMLR"),
        "authors": [
            "Chuan Guo",
            "Geoff Pleiss",
            "Yu Sun",
            "Kilian Q. Weinberger",
        ],
        "date": "2017-08-06",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.1706.04599",
            "arxiv_id": "1706.04599",
            "proceedings_identity": (
                "Proceedings of Machine Learning Research 70:1321-1330, ICML 2017"
            ),
        },
        "artifact": {
            "uri": "https://proceedings.mlr.press/v70/guo17a/guo17a.pdf",
            "version": "PMLR volume 70 proceedings artifact, ICML 2017",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 828420,
            "sha256": (
                "df7c93f97204f8a3c2b10f6d5bf5265baac25f00c1ae3b473a3e1dbc102dacb2"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "490555302e6ce2fa10abfe406193af7fa25e054d78c65ce74dea384fbda6bfac"
        ),
    },
    "E4": {
        "title": (
            "Can You Trust Your Model's Uncertainty? Evaluating Predictive "
            "Uncertainty Under Dataset Shift"
        ),
        "family": "PF1-selective-prediction-calibration",
        "kind": "primary_empirical_benchmark_paper",
        "owner": "Yaniv Ovadia and coauthors; arXiv and NeurIPS 2019",
        "authors": [
            "Yaniv Ovadia",
            "Emily Fertig",
            "Jie Ren",
            "Zachary Nado",
            "D Sculley",
            "Sebastian Nowozin",
            "Joshua V. Dillon",
            "Balaji Lakshminarayanan",
            "Jasper Snoek",
        ],
        "date": "2019-06-06",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.1906.02530",
            "arxiv_id": "1906.02530",
            "proceedings_identity": (
                "Advances in Neural Information Processing Systems 2019"
            ),
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/1906.02530v2",
            "version": "arXiv:1906.02530v2, revised 2019-12-17",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 5887184,
            "sha256": (
                "1610d04d7f69d10751f0e9ff1db9fbd8b3fdf5306798879016192eb2dbf17a6f"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "efe255cd8f7cfb7667cb9024601952f89d73ceb80462d6ea287e359af34c4d97"
        ),
    },
    "E5": {
        "title": "Hierarchical Mixtures of Experts and the EM Algorithm",
        "family": "PF2-staged-routing",
        "kind": "primary_method_and_empirical_paper",
        "owner": (
            "Michael I. Jordan and Robert A. Jacobs; Neural Computation and "
            "the Berkeley author archive"
        ),
        "authors": ["Michael I. Jordan", "Robert A. Jacobs"],
        "date": "1994-03-01",
        "precision": "day",
        "identity": {
            "doi": "10.1162/neco.1994.6.2.181",
            "arxiv_id": None,
            "proceedings_identity": "Neural Computation 6(2):181-214",
        },
        "artifact": {
            "uri": (
                "https://web.archive.org/web/20230521045924id_/https://people."
                "eecs.berkeley.edu/~jordan/papers/hierarchies.ps"
            ),
            "version": (
                "Wayback timestamp 20230521045924 immutable capture of the "
                "author-hosted primary PostScript"
            ),
            "retrieved_on": "2026-08-10",
            "media_type": "application/postscript",
            "byte_count": 478612,
            "sha256": (
                "afb5abbefaffbf6538369c9c488f57ff4859f5d15ddd14826794ba9b06670278"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "9f9db17fdb0cf6fc8d4883431e60df3355ad9874a31a6323eacb50906546c695"
        ),
    },
    "E6": {
        "title": (
            "BranchyNet: Fast Inference via Early Exiting from Deep Neural Networks"
        ),
        "family": "PF2-staged-routing",
        "kind": "primary_method_and_empirical_paper",
        "owner": ("Surat Teerapittayanon, Bradley McDanel, and H. T. Kung; arXiv"),
        "authors": [
            "Surat Teerapittayanon",
            "Bradley McDanel",
            "H. T. Kung",
        ],
        "date": "2017-09-06",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.1709.01686",
            "arxiv_id": "1709.01686",
            "proceedings_identity": None,
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/1709.01686v1",
            "version": "arXiv:1709.01686v1, submitted 2017-09-06",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 2197768,
            "sha256": (
                "afd580e5df49906874c104b6dcaab361a8650569126997b90146b4d27dca9613"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "ea3fff4618312050824a4a18e5d487266db47ed85b10a601dab19a3e2c7ae610"
        ),
    },
    "E7": {
        "title": "Classifier Chains for Multi-label Classification",
        "family": "PF3-decomposition-local-classification",
        "kind": "primary_method_and_empirical_paper",
        "owner": (
            "Jesse Read, Bernhard Pfahringer, Geoffrey Holmes, and Eibe Frank; "
            "University of Waikato Research Commons"
        ),
        "authors": [
            "Jesse Read",
            "Bernhard Pfahringer",
            "Geoffrey Holmes",
            "Eibe Frank",
        ],
        "date": "2009",
        "precision": "year",
        "identity": {
            "doi": "10.1007/978-3-642-04174-7_17",
            "arxiv_id": None,
            "proceedings_identity": "ECML PKDD 2009, pages 254-269",
        },
        "artifact": {
            "uri": (
                "https://researchcommons.waikato.ac.nz/bitstreams/"
                "defdb423-a83f-4851-aeeb-034b6339a9f2/download"
            ),
            "version": (
                "ECML PKDD 2009 author-accepted manuscript deposited under DOI "
                "10.1007/978-3-642-04174-7_17"
            ),
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 183762,
            "sha256": (
                "2e4cae545c49690547a35b1a0ec522f46f202a4187cef6c6a7cef60c5cad3de2"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "9040b7721944410d1b50a305f660cb01b12d96233add093be689cfe44c37d3f9"
        ),
    },
    "E8": {
        "title": "Decomposed Prompting: A Modular Approach for Solving Complex Tasks",
        "family": "PF3-decomposition-local-classification",
        "kind": "primary_method_and_empirical_paper",
        "owner": "Tushar Khot and coauthors; arXiv and ICLR 2023",
        "authors": [
            "Tushar Khot",
            "Harsh Trivedi",
            "Matthew Finlayson",
            "Yao Fu",
            "Kyle Richardson",
            "Peter Clark",
            "Ashish Sabharwal",
        ],
        "date": "2022-10-05",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.2210.02406",
            "arxiv_id": "2210.02406",
            "proceedings_identity": "ICLR 2023 camera-ready paper",
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/2210.02406v2",
            "version": (
                "arXiv:2210.02406v2, ICLR 2023 camera ready, revised 2023-04-11"
            ),
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 1634349,
            "sha256": (
                "93cb61f35249c60a9e91a5fac66673c373d30070925ba05ac9f79098dd2e7d87"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "fd0460d827362b8845d19dbcba0fc31a9c11cb788be7d6cfe307a5558a82d774"
        ),
    },
    "E9": {
        "title": "StruQ: Defending Against Prompt Injection with Structured Queries",
        "family": "PF4-adversarial-prompt-isolation",
        "kind": "primary_method_and_empirical_paper",
        "owner": (
            "Sizhe Chen, Julien Piet, Chawin Sitawarin, and David Wagner; "
            "USENIX Association"
        ),
        "authors": [
            "Sizhe Chen",
            "Julien Piet",
            "Chawin Sitawarin",
            "David Wagner",
        ],
        "date": "2025-08-13",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.2402.06363",
            "arxiv_id": "2402.06363",
            "proceedings_identity": (
                "34th USENIX Security Symposium, ISBN 978-1-939133-52-6, "
                "pages 2383-2400"
            ),
        },
        "artifact": {
            "uri": (
                "https://www.usenix.org/system/files/usenixsecurity25-chen-sizhe.pdf"
            ),
            "version": (
                "USENIX Security 2025 proceedings version, 2025-08-13 to 2025-08-15"
            ),
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 560992,
            "sha256": (
                "322be0fd6d305a362fc2571fb7b779df6ed3761a19f75f9828d9498d3fc71926"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "676abb47caa3fce9f7669b52fb8e20733523577e9641a0dc734d0ab1060664d7"
        ),
    },
    "E10": {
        "title": (
            "The Instruction Hierarchy: Training LLMs to Prioritize Privileged "
            "Instructions"
        ),
        "family": "PF4-adversarial-prompt-isolation",
        "kind": "primary_method_and_empirical_paper",
        "owner": (
            "Eric Wallace, Kai Xiao, Reimar Leike, Lilian Weng, Johannes "
            "Heidecke, and Alex Beutel; arXiv"
        ),
        "authors": [
            "Eric Wallace",
            "Kai Xiao",
            "Reimar Leike",
            "Lilian Weng",
            "Johannes Heidecke",
            "Alex Beutel",
        ],
        "date": "2024-04-19",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.2404.13208",
            "arxiv_id": "2404.13208",
            "proceedings_identity": None,
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/2404.13208v1",
            "version": "arXiv:2404.13208v1, submitted 2024-04-19",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 488381,
            "sha256": (
                "fbc2d65e913e75b8f0ae74e83e3443c36a727636d1038a071a2f10d8be63dac4"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "ff08cb4b017994fd393c9635b971e32d5a5cb6091afeeddf7d49a3493a5fd2e5"
        ),
    },
    "E11": {
        "title": "Defeating Prompt Injections by Design",
        "family": "PF4-adversarial-prompt-isolation",
        "kind": "primary_method_and_empirical_paper",
        "owner": "Edoardo Debenedetti and coauthors; arXiv",
        "authors": [
            "Edoardo Debenedetti",
            "Ilia Shumailov",
            "Tianqi Fan",
            "Jamie Hayes",
            "Nicholas Carlini",
            "Daniel Fabian",
            "Christoph Kern",
            "Chongyang Shi",
            "Andreas Terzis",
            "Florian Tramèr",
        ],
        "date": "2025-03-24",
        "precision": "day",
        "identity": {
            "doi": "10.48550/arXiv.2503.18813",
            "arxiv_id": "2503.18813",
            "proceedings_identity": None,
        },
        "artifact": {
            "uri": "https://arxiv.org/pdf/2503.18813v2",
            "version": "arXiv:2503.18813v2, revised 2025-06-24",
            "retrieved_on": "2026-08-10",
            "media_type": "application/pdf",
            "byte_count": 5531468,
            "sha256": (
                "c3719f6ce73eecf45e3764debef8a3d8ff8c9233b37d128c558b694ec3790cc7"
            ),
            "retrieval_disposition": "directly-retrieved-hashed-not-vendored",
        },
        "semantic_sha256": (
            "0f6870aff25c0539a988329640d98519b13b3a58b4314e26ce75b4bf1f03145f"
        ),
    },
}

EXPECTED_PROVENANCE_ORDER = [
    "PF1-selective-prediction-calibration",
    "PF2-staged-routing",
    "PF3-decomposition-local-classification",
    "PF4-adversarial-prompt-isolation",
]
EXPECTED_PROVENANCE_SHA256 = {
    "PF1-selective-prediction-calibration": (
        "65c4bc27e828ec974ee078be505b8d4ec3c67261d81d13f7f0d274a28b07bad9"
    ),
    "PF2-staged-routing": (
        "8a5cb4a42c21cb2b5169684cfd88e13cae80da11981c5cc7735c48cae2bc7cc0"
    ),
    "PF3-decomposition-local-classification": (
        "75b1f3d57a1089c387f23b1c1cf7ef6cf728fb5a8b37478d117e6949de344303"
    ),
    "PF4-adversarial-prompt-isolation": (
        "4e9f7646439c78dee816a5b7a6bde949713669feeeab15d1db54487d56b4efdd"
    ),
}
EXPECTED_TENSION_ORDER = [
    "C1-calibration-under-shift",
    "C2-selective-guarantee-scope",
    "C3-staged-confidence-risk",
    "C4-decomposition-propagation",
    "C5-security-benchmark-ceiling",
]
EXPECTED_TENSION_SHA256 = {
    "C1-calibration-under-shift": (
        "1eec062ede2fb6a52137ed3c674c933cfeaa7f14a71f47e906caf631f971caa8"
    ),
    "C2-selective-guarantee-scope": (
        "2ed585d8afe39ceae297dc2bbbc1c0a3bd7892179a3370934bbd974ae14b960c"
    ),
    "C3-staged-confidence-risk": (
        "cc96cd8987ef43b34f7a51de3a15602972c9561d65295562a2ffcfffb8c6bc88"
    ),
    "C4-decomposition-propagation": (
        "e3d13ddcc48ffa51c0f5ee2685139b3a918bb796eec2364f9a2341e69731e798"
    ),
    "C5-security-benchmark-ceiling": (
        "83d85e0ba12129fad9b93308eeda9ef11cc73fde50a36d2858adb617c65219b2"
    ),
}
EXPECTED_MECHANISM_FAMILY_ORDER = [
    "F1-calibrated-selective-prediction",
    "F2-staged-hierarchical-routing",
    "F3-local-decomposition-recomposition",
    "F4-privilege-separated-control-data",
]
EXPECTED_MECHANISM_FAMILY_SHA256 = {
    "F1-calibrated-selective-prediction": (
        "bd2ec01719c47409409ba882aaea65fcf619b6bf753815de7fafb4abc9aad270"
    ),
    "F2-staged-hierarchical-routing": (
        "074b18e48301f0876cdb176e1579242e4987a4033b7d6e3bb8ab64d3ad1742fe"
    ),
    "F3-local-decomposition-recomposition": (
        "e031373b2353c0ec9a8af24fbe63721750c119e11fc622c25dcbeca139525b74"
    ),
    "F4-privilege-separated-control-data": (
        "7aab4438613530b3a58efcf0326d429a3c2ffbc5e24d9166468ba2eb08cd268d"
    ),
}
EXPECTED_DISCRIMINATOR_ORDER = [
    "D1-selective-risk-coverage",
    "D2-calibration-under-shift",
    "D3-staged-exit-behavior",
    "D4-decomposition-locality",
    "D5-adaptive-prompt-injection",
    "D6-privileged-control-flow-invariance",
]
EXPECTED_DISCRIMINATOR_SHA256 = {
    "D1-selective-risk-coverage": (
        "68ed87e6a2135b971570ec79fc434071038a7d22560e9eefaa78779d2ca43499"
    ),
    "D2-calibration-under-shift": (
        "ec64c11f9f83235946ca5375a10b08f9383c02257a04c54de0d54697619c0812"
    ),
    "D3-staged-exit-behavior": (
        "55281733318e013bb04a595920cb4ce0dcde091aa514cf60e0e483119bb60ca2"
    ),
    "D4-decomposition-locality": (
        "de07fdcbce3765d6609500745ba9cde763baed0217bb154a8c5ab98b5b30fac8"
    ),
    "D5-adaptive-prompt-injection": (
        "71636a18703df0fa52ca2860972e218fb1ffe67c496681605a971420b94a29d8"
    ),
    "D6-privileged-control-flow-invariance": (
        "e91811b77fdfdfd09d58a03fc74907cda74966112b9e3f84708ddb2449e398e9"
    ),
}

EXPECTED_ZERO_ACCESS_SHA256 = (
    "c22e0c51b94b8aeeb4fc6e8b445c3bf16aee890fead025eec878e4e2ea81405a"
)
EXPECTED_DESIGN_FIREWALL_SHA256 = (
    "6b9ef420b00580b35d830cc74883780d7e571c58f90d47bbda23cae94b44dcb6"
)
EXPECTED_CLAIMS_PROVEN_SHA256 = (
    "1423482b0431b145416fb5cc2edebc600a98ad51c1d766f71feed43dd023420e"
)
EXPECTED_PROHIBITED_MATERIAL = [
    "corpus I task text",
    "corpus J task text",
    "corpus I outputs",
    "corpus J outputs",
    "I/J per-case observations",
    "I/J metrics",
    "I/J provider logs",
    "I/J trajectories",
    "any other I/J result",
]
ALLOWED_SOURCE_KINDS = {
    "primary_method_and_empirical_paper",
    "primary_empirical_benchmark_paper",
    "official_standard",
    "reproducible_external_observation",
}
SOURCE_SEMANTIC_FIELDS = [
    "source_id",
    "title",
    "supported_claims",
    "unsupported_extrapolations",
    "uncertainties",
    "tension_ids",
    "prospective_discriminator_ids",
]
FORBIDDEN_KEY_FRAGMENTS = {
    "task_text",
    "provider_log",
    "trajectory_binding",
    "per_case_observation",
    "aq8_metric",
    "aq8_output",
    "aq8_result",
    "corpus_i_binding",
    "corpus_j_binding",
    "corpus_k_binding",
    "result_binding",
    "selected_mechanism",
    "mechanism_rank",
    "mechanism_score",
    "mechanism_recommendation",
    "h5_candidate",
}
FORBIDDEN_VALUE_FRAGMENTS = {
    "future-activation-v8",
    "activation-authoring.json",
    "activation-heldout.json",
    "selected mechanism:",
    "ranked mechanism:",
    "aq8 metric=",
    "aq8 result=",
}
ALLOWED_FORBIDDEN_KEY_PATHS = {
    (
        "zero_access_declaration",
        "used_any_aq8_result_beyond_permitted_fact",
    ),
}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_packet() -> dict[str, Any]:
    value = json.loads(
        PACKET_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError("packet root must be an object")
    return value


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_keys(value: Any, expected: list[str], context: str) -> dict[str, Any]:
    require(type(value) is dict, f"{context} must be an object")
    require(list(value) == expected, f"{context} key order/closure mismatch")
    return value


def require_nonempty_strings(value: Any, context: str) -> list[str]:
    require(type(value) is list and value, f"{context} must be a non-empty array")
    require(
        all(type(item) is str and item.strip() for item in value),
        f"{context} must contain only non-empty strings",
    )
    require(len(value) == len(set(value)), f"{context} must contain unique values")
    return value


def require_unique_ids(rows: list[dict[str, Any]], key: str, context: str) -> list[str]:
    values = [row[key] for row in rows]
    require(
        all(type(value) is str and value for value in values),
        f"{context} ids must be non-empty strings",
    )
    require(len(values) == len(set(values)), f"{context} ids must be unique")
    return values


def assert_no_forbidden_bindings(value: Any, path: tuple[str, ...] = ()) -> None:
    if type(value) is dict:
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            child_path = (*path, key)
            require(
                child_path in ALLOWED_FORBIDDEN_KEY_PATHS
                or not any(
                    fragment in normalized for fragment in FORBIDDEN_KEY_FRAGMENTS
                ),
                f"forbidden key binding at {'.'.join(child_path)}",
            )
            assert_no_forbidden_bindings(child, child_path)
    elif type(value) is list:
        for index, child in enumerate(value):
            assert_no_forbidden_bindings(child, (*path, str(index)))
    elif type(value) is str:
        lowered = value.lower()
        require(
            not any(fragment in lowered for fragment in FORBIDDEN_VALUE_FRAGMENTS),
            f"forbidden value binding at {'.'.join(path)}",
        )


def validate_packet(packet: dict[str, Any]) -> None:
    require_keys(packet, EXPECTED_TOP_LEVEL_ORDER, "packet")
    require(packet["schema_version"] == "1.0", "schema version drift")
    require(
        packet["packet_id"] == "AQ9-H5-E0-INDEPENDENT-EVIDENCE-V1",
        "packet id drift",
    )
    require(
        packet["status"] == "frozen-evidence-awaiting-independent-verdict",
        "packet status drift",
    )
    require(
        packet["claim_ceiling"] == "structural-external-evidence-only",
        "claim ceiling widened",
    )

    amendment = require_keys(
        packet["amendment_authority"], AMENDMENT_KEYS, "amendment_authority"
    )
    require(amendment == EXPECTED_AMENDMENT, "amendment custody drift")

    snapshot = require_keys(
        packet["foundation_snapshot_authority"],
        SNAPSHOT_KEYS,
        "foundation_snapshot_authority",
    )
    require(
        snapshot["commit"] == EXPECTED_FOUNDATION_COMMIT,
        "foundation commit drift",
    )
    require(snapshot["tree"] == EXPECTED_FOUNDATION_TREE, "foundation tree drift")
    require(type(snapshot["artifacts"]) is list, "foundation artifacts must be array")
    for index, row in enumerate(snapshot["artifacts"]):
        require_keys(row, SNAPSHOT_ARTIFACT_KEYS, f"foundation artifact {index}")
    require(
        snapshot["artifacts"] == EXPECTED_FOUNDATION_ARTIFACTS,
        "foundation artifact custody drift",
    )

    zero_access = require_keys(
        packet["zero_access_declaration"],
        ZERO_ACCESS_KEYS,
        "zero_access_declaration",
    )
    require(
        zero_access["sole_permitted_prior_fact"] == "AQ8 aggregate=fail",
        "sole permitted prior fact drift",
    )
    require(
        zero_access["prohibited_material"] == EXPECTED_PROHIBITED_MATERIAL,
        "zero-access prohibited-material closure weakened",
    )
    for key in ZERO_ACCESS_KEYS[3:]:
        require(type(zero_access[key]) is bool, f"zero access {key} must be bool")
        require(zero_access[key] is False, f"zero access {key} must be false")
    require(
        canonical_sha256(zero_access) == EXPECTED_ZERO_ACCESS_SHA256,
        "zero-access declaration drift",
    )

    provenance = packet["provenance_families"]
    require(type(provenance) is list, "provenance_families must be array")
    provenance_ids = require_unique_ids(
        provenance, "provenance_family_id", "provenance families"
    )
    require(provenance_ids == EXPECTED_PROVENANCE_ORDER, "provenance order drift")
    require(len(provenance_ids) >= 2, "provenance-family collapse")
    for index, row in enumerate(provenance):
        require_keys(row, PROVENANCE_KEYS, f"provenance family {index}")
        require_nonempty_strings(row["source_ids"], f"provenance source ids {index}")
        require(
            canonical_sha256(row)
            == EXPECTED_PROVENANCE_SHA256[row["provenance_family_id"]],
            f"provenance family {row['provenance_family_id']} drift",
        )

    sources = packet["sources"]
    require(type(sources) is list, "sources must be array")
    source_ids = require_unique_ids(sources, "source_id", "sources")
    require(source_ids == EXPECTED_SOURCE_ORDER, "source order or membership drift")
    represented_families: set[str] = set()
    for index, source in enumerate(sources):
        source_id = source["source_id"]
        expected = EXPECTED_SOURCE_CUSTODY[source_id]
        require_keys(source, SOURCE_KEYS, f"source {source_id}")
        require(source["title"] == expected["title"], f"{source_id} title drift")
        require(
            source["provenance_family_id"] == expected["family"],
            f"{source_id} provenance drift",
        )
        represented_families.add(source["provenance_family_id"])
        require(source["source_kind"] == expected["kind"], f"{source_id} kind drift")
        require(
            source["source_kind"] in ALLOWED_SOURCE_KINDS,
            f"{source_id} is not an eligible external source",
        )
        require(
            source["provenance_owner"] == expected["owner"],
            f"{source_id} owner drift",
        )
        require(source["authors"] == expected["authors"], f"{source_id} author drift")
        require_nonempty_strings(source["authors"], f"{source_id} authors")
        require(
            source["publication_date"] == expected["date"],
            f"{source_id} date drift",
        )
        require(
            source["publication_date_precision"] == expected["precision"],
            f"{source_id} date precision drift",
        )
        require(
            re.fullmatch(r"\d{4}(?:-\d{2}-\d{2})?", source["publication_date"])
            is not None,
            f"{source_id} publication date malformed",
        )
        identity = require_keys(
            source["identity"], IDENTITY_KEYS, f"{source_id} identity"
        )
        require(identity == expected["identity"], f"{source_id} identity drift")
        require(
            type(identity["doi"]) is str and identity["doi"],
            f"{source_id} DOI missing",
        )
        artifact = require_keys(
            source["artifact"], ARTIFACT_KEYS, f"{source_id} artifact"
        )
        require(artifact == expected["artifact"], f"{source_id} artifact custody drift")
        require(
            artifact["uri"].startswith("https://") and artifact["version"],
            f"{source_id} immutable URI/version missing",
        )
        require(
            artifact["media_type"] in {"application/pdf", "application/postscript"},
            f"{source_id} media type invalid",
        )
        require(
            type(artifact["byte_count"]) is int and artifact["byte_count"] > 0,
            f"{source_id} byte count invalid",
        )
        require(
            re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is not None,
            f"{source_id} digest malformed",
        )
        for field in (
            "supported_claims",
            "unsupported_extrapolations",
            "uncertainties",
            "tension_ids",
            "prospective_discriminator_ids",
        ):
            require_nonempty_strings(source[field], f"{source_id} {field}")
        semantic_projection = {key: source[key] for key in SOURCE_SEMANTIC_FIELDS}
        require(
            canonical_sha256(semantic_projection) == expected["semantic_sha256"],
            f"{source_id} claim/uncertainty/discriminator closure drift",
        )
    require(len(represented_families) >= 2, "source provenance-family collapse")
    require(
        any(source["source_kind"] in ALLOWED_SOURCE_KINDS for source in sources),
        "no eligible primary/official/reproducible source",
    )

    grouped_source_ids = {
        row["provenance_family_id"]: row["source_ids"] for row in provenance
    }
    for source in sources:
        require(
            source["source_id"] in grouped_source_ids[source["provenance_family_id"]],
            f"{source['source_id']} missing from provenance family",
        )
    require(packet["excluded_sources"] == [], "relied source unexpectedly excluded")

    tensions = packet["cross_source_tensions"]
    require(type(tensions) is list, "cross_source_tensions must be array")
    tension_ids = require_unique_ids(tensions, "tension_id", "tensions")
    require(tension_ids == EXPECTED_TENSION_ORDER, "tension order drift")
    for index, row in enumerate(tensions):
        require_keys(row, TENSION_KEYS, f"tension {index}")
        require_nonempty_strings(row["source_ids"], f"tension source ids {index}")
        require(set(row["source_ids"]) <= set(source_ids), "unknown tension source id")
        require(
            canonical_sha256(row) == EXPECTED_TENSION_SHA256[row["tension_id"]],
            f"tension {row['tension_id']} drift",
        )
    for source in sources:
        require(
            set(source["tension_ids"]) <= set(tension_ids),
            f"{source['source_id']} has unknown tension",
        )

    families = packet["mechanism_families"]
    require(type(families) is list, "mechanism_families must be array")
    family_ids = require_unique_ids(families, "family_id", "mechanism families")
    require(
        family_ids == EXPECTED_MECHANISM_FAMILY_ORDER,
        "mechanism family order or membership drift",
    )
    for index, row in enumerate(families):
        require_keys(row, MECHANISM_FAMILY_KEYS, f"mechanism family {index}")
        require(
            row["status"] == "independent-evidence-only",
            f"mechanism family {row['family_id']} status drift",
        )
        require_nonempty_strings(
            row["evidence_source_ids"], f"mechanism family source ids {index}"
        )
        require(
            set(row["evidence_source_ids"]) <= set(source_ids),
            f"mechanism family {row['family_id']} has unknown source",
        )
        require_nonempty_strings(
            row["supported_constraints"], f"mechanism family constraints {index}"
        )
        require_nonempty_strings(
            row["unsupported_extrapolations"],
            f"mechanism family unsupported extrapolations {index}",
        )
        require_nonempty_strings(
            row["prospective_discriminator_ids"],
            f"mechanism family discriminator ids {index}",
        )
        require(
            canonical_sha256(row) == EXPECTED_MECHANISM_FAMILY_SHA256[row["family_id"]],
            f"mechanism family {row['family_id']} drift",
        )

    discriminators = packet["prospective_discriminators"]
    require(type(discriminators) is list, "prospective_discriminators must be array")
    discriminator_ids = require_unique_ids(
        discriminators, "discriminator_id", "discriminators"
    )
    require(
        discriminator_ids == EXPECTED_DISCRIMINATOR_ORDER,
        "discriminator order or membership drift",
    )
    for index, row in enumerate(discriminators):
        require_keys(row, DISCRIMINATOR_KEYS, f"discriminator {index}")
        require_nonempty_strings(row["family_ids"], f"discriminator family ids {index}")
        require(
            set(row["family_ids"]) <= set(family_ids),
            f"discriminator {row['discriminator_id']} has unknown family",
        )
        for key in ("observable", "falsifying_observation", "claim_boundary"):
            require(
                type(row[key]) is str and row[key].strip(),
                f"discriminator {row['discriminator_id']} {key} missing",
            )
        require(
            canonical_sha256(row)
            == EXPECTED_DISCRIMINATOR_SHA256[row["discriminator_id"]],
            f"discriminator {row['discriminator_id']} drift",
        )
    for source in sources:
        require(
            set(source["prospective_discriminator_ids"]) <= set(discriminator_ids),
            f"{source['source_id']} has unknown discriminator",
        )
    for family in families:
        require(
            set(family["prospective_discriminator_ids"]) <= set(discriminator_ids),
            f"{family['family_id']} has unknown discriminator",
        )

    firewall = require_keys(
        packet["design_firewall"], DESIGN_FIREWALL_KEYS, "design_firewall"
    )
    require(
        firewall["family_order_semantics"]
        == "identifier order only; no preference, score, or rank",
        "family ordering became a ranking",
    )
    for key in DESIGN_FIREWALL_KEYS[1:]:
        require(type(firewall[key]) is bool, f"design firewall {key} must be bool")
        require(firewall[key] is False, f"design firewall {key} must be false")
    require(
        canonical_sha256(firewall) == EXPECTED_DESIGN_FIREWALL_SHA256,
        "design firewall drift",
    )

    claims = require_keys(packet["claims_proven"], CLAIMS_PROVEN_KEYS, "claims_proven")
    require(
        claims["source_identity_and_digest_metadata_frozen"] is True,
        "source digest metadata not frozen",
    )
    require(
        claims["source_artifact_bytes_retained"] is False,
        "external source bytes must not be retained",
    )
    require(
        claims["source_artifact_byte_reverification_in_test"] is False,
        "test must not claim external byte reverification",
    )
    require(
        claims["independent_external_provenance_families"] is True,
        "external provenance unproven",
    )
    for key in CLAIMS_PROVEN_KEYS[4:]:
        require(type(claims[key]) is bool, f"claims_proven {key} must be bool")
        require(claims[key] is False, f"claim ceiling exceeded at {key}")
    require(
        canonical_sha256(claims) == EXPECTED_CLAIMS_PROVEN_SHA256,
        "claims-proven closure drift",
    )
    assert_no_forbidden_bindings(packet)


def git_bytes(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


class AQ9H5IndependentEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = load_packet()

    def test_packet_is_closed_and_valid(self) -> None:
        validate_packet(self.packet)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            json.loads(
                '{"schema_version":"1.0","schema_version":"2.0"}',
                object_pairs_hook=reject_duplicate_keys,
            )

    def test_amendment_and_foundation_git_custody(self) -> None:
        amendment = self.packet["amendment_authority"]
        amendment_tree = (
            git_bytes("show", "-s", "--format=%T", amendment["commit"]).decode().strip()
        )
        self.assertEqual(amendment_tree, amendment["tree"])
        amendment_spec = f"{amendment['commit']}:{amendment['path']}"
        self.assertEqual(
            git_bytes("rev-parse", amendment_spec).decode().strip(),
            amendment["blob"],
        )
        amendment_bytes = git_bytes("show", amendment_spec)
        self.assertEqual(len(amendment_bytes), amendment["byte_count"])
        self.assertEqual(raw_sha256(amendment_bytes), amendment["sha256"])

        snapshot = self.packet["foundation_snapshot_authority"]
        snapshot_tree = (
            git_bytes("show", "-s", "--format=%T", snapshot["commit"]).decode().strip()
        )
        self.assertEqual(snapshot_tree, snapshot["tree"])
        for artifact in snapshot["artifacts"]:
            spec = f"{snapshot['commit']}:{artifact['path']}"
            self.assertEqual(
                git_bytes("rev-parse", spec).decode().strip(),
                artifact["blob"],
            )
            source_bytes = git_bytes("show", spec)
            self.assertEqual(len(source_bytes), artifact["byte_count"])
            self.assertEqual(raw_sha256(source_bytes), artifact["sha256"])

    def test_missing_source_identity_author_date_uri_version_digest_reds(self) -> None:
        mutations = [
            ("identity", lambda row: row["identity"].pop("doi")),
            ("author", lambda row: row.__setitem__("authors", [])),
            ("date", lambda row: row.pop("publication_date")),
            ("uri", lambda row: row["artifact"].pop("uri")),
            ("version", lambda row: row["artifact"].pop("version")),
            ("digest", lambda row: row["artifact"].pop("sha256")),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = deepcopy(self.packet)
                mutate(changed["sources"][0])
                with self.assertRaises(ValueError):
                    validate_packet(changed)

    def test_artifact_digest_type_and_byte_spoof_reds(self) -> None:
        mutations = [
            ("digest", "sha256", "0" * 64),
            ("type", "media_type", "text/html"),
            ("bytes", "byte_count", 1),
        ]
        for label, field, value in mutations:
            with self.subTest(label=label):
                changed = deepcopy(self.packet)
                changed["sources"][0]["artifact"][field] = value
                with self.assertRaises(ValueError):
                    validate_packet(changed)

    def test_provenance_family_collapse_is_red(self) -> None:
        changed = deepcopy(self.packet)
        retained = changed["provenance_families"][0]
        retained["source_ids"] = [row["source_id"] for row in changed["sources"]]
        changed["provenance_families"] = [retained]
        for source in changed["sources"]:
            source["provenance_family_id"] = retained["provenance_family_id"]
        with self.assertRaises(ValueError):
            validate_packet(changed)

    def test_selected_ranked_or_composed_mechanism_reds(self) -> None:
        changed = deepcopy(self.packet)
        changed["design_firewall"]["mechanism_choice_made"] = True
        with self.assertRaises(ValueError):
            validate_packet(changed)

        changed = deepcopy(self.packet)
        changed["mechanism_families"][0]["mechanism_rank"] = 1
        with self.assertRaises(ValueError):
            validate_packet(changed)

        changed = deepcopy(self.packet)
        changed["design_firewall"]["mechanism_composition_made"] = True
        with self.assertRaises(ValueError):
            validate_packet(changed)

    def test_result_or_corpus_binding_is_red(self) -> None:
        for forbidden_key in ("aq8_result", "corpus_k_binding"):
            with self.subTest(forbidden_key=forbidden_key):
                changed = deepcopy(self.packet)
                changed["mechanism_families"][0][forbidden_key] = "forbidden"
                with self.assertRaises(ValueError):
                    validate_packet(changed)

    def test_recursive_forbidden_key_and_value_scans_are_red(self) -> None:
        changed = deepcopy(self.packet)
        changed["zero_access_declaration"]["nested"] = {"aq8_result": "forbidden"}
        with self.assertRaisesRegex(ValueError, "forbidden key binding"):
            assert_no_forbidden_bindings(changed)

        changed = deepcopy(self.packet)
        changed["zero_access_declaration"]["scope"] = {
            "nested": ["selected mechanism: F1"]
        }
        with self.assertRaisesRegex(ValueError, "forbidden value binding"):
            assert_no_forbidden_bindings(changed)

    def test_weakened_zero_access_declaration_is_red(self) -> None:
        changed = deepcopy(self.packet)
        changed["zero_access_declaration"]["accessed_any_prohibited_material"] = True
        with self.assertRaises(ValueError):
            validate_packet(changed)

        changed = deepcopy(self.packet)
        changed["zero_access_declaration"]["prohibited_material"].pop()
        with self.assertRaises(ValueError):
            validate_packet(changed)

        changed = deepcopy(self.packet)
        changed["zero_access_declaration"]["sole_permitted_prior_fact"] = (
            "more than aggregate bit"
        )
        with self.assertRaises(ValueError):
            validate_packet(changed)

    def test_claim_ceiling_widening_is_red(self) -> None:
        changed = deepcopy(self.packet)
        changed["claim_ceiling"] = "efficacy-qualified"
        with self.assertRaises(ValueError):
            validate_packet(changed)

        changed = deepcopy(self.packet)
        changed["claims_proven"]["h5_efficacy"] = True
        with self.assertRaises(ValueError):
            validate_packet(changed)


if __name__ == "__main__":
    unittest.main()
