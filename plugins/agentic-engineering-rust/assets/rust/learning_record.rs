//! Provider-independent learning and no-change decision types.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvidenceClass { Isolated, Recurring, CrossContext, Causal, Unresolved }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AdoptionDecision { Adopt, Hold, Narrow, Reject, Supersede, Retire }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ChangeDisposition { NoChange, PartialChange, ChangeRequired, Blocked }

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NoChangeDecision {
    pub request: String,
    pub candidate: String,
    pub reproduction: Vec<String>,
    pub current_behavior: String,
    pub disposition: ChangeDisposition,
    pub evidence: Vec<String>,
    pub invalidation_triggers: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LearningRecord {
    pub record_id: String,
    pub version: String,
    pub owner: String,
    pub observation: String,
    pub provenance: Vec<String>,
    pub operating_envelope: String,
    pub evidence_class: EvidenceClass,
    pub facts: Vec<String>,
    pub hypotheses: Vec<String>,
    pub counterevidence: Vec<String>,
    pub mechanism_hypothesis: String,
    pub intervention: String,
    pub evaluation_evidence: Vec<String>,
    pub decision: AdoptionDecision,
    pub review_date: String,
    pub invalidation_triggers: Vec<String>,
}
