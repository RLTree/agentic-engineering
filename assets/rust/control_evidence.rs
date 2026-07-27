//! Adaptable control-plane evidence types for bounded agent work.

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct PacketId(pub String);
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct CandidateDigest(pub String);
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct TaskId(pub String);
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct LeaseId(pub String);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WorkStatus { Issued, Running, Complete, Blocked, Failed, Cancelled }

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WorkBudget {
    pub turns: u32,
    pub tool_calls: u32,
    pub repair_attempts: u32,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Ownership {
    pub paths: Vec<String>,
    pub semantic_authority: Vec<String>,
    pub forbidden_surfaces: Vec<String>,
    pub root_owned_interfaces: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TaskEvidencePacket {
    pub packet_id: PacketId,
    pub candidate: CandidateDigest,
    pub task_id: TaskId,
    pub lease_id: LeaseId,
    pub worker_id: String,
    pub context_digest: String,
    pub ownership: Ownership,
    pub permissions: Vec<String>,
    pub budget: WorkBudget,
    pub required_verification: Vec<String>,
    pub status: WorkStatus,
    pub evidence: Vec<String>,
    pub blockers: Vec<String>,
    pub residual_risks: Vec<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReviewDecision { Pass, PassWithFindings, Reject, Blocked }

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReviewVerdict {
    pub candidate: CandidateDigest,
    pub reviewed_scope: Vec<String>,
    pub reviewer: String,
    pub independent: bool,
    pub evidence_inspected: Vec<String>,
    pub findings: Vec<String>,
    pub unverifiable_claims: Vec<String>,
    pub decision: ReviewDecision,
    pub claim_ceiling: String,
}

impl ReviewVerdict {
    pub fn supports_acceptance(&self) -> bool {
        self.independent && matches!(self.decision, ReviewDecision::Pass | ReviewDecision::PassWithFindings)
    }
}
