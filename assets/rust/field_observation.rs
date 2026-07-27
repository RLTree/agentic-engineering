//! Typed field-learning evidence for a Rust agentic application.
//!
//! This fragment deliberately stores domain identities separately from trace IDs.
//! The telemetry backend may sample a trace, while product decisions and external
//! effect reconciliation still require stable run/action/effect identities.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct ObservationId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct TaskId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct EffectId(pub String);

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AutonomyLevel {
    Replay,
    ObserveOnly,
    Shadow,
    Recommendation,
    ApprovalGated,
    BoundedAutonomy,
    BroaderAutonomy,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OutcomeClass {
    Success,
    Partial,
    Failure,
    Abandoned,
    Denied,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterventionKind {
    None,
    Approval,
    Edit,
    Override,
    Escalation,
    Cancel,
    Recovery,
    Abandonment,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EffectState {
    Prepared,
    Dispatched,
    Confirmed,
    Ambiguous,
    Reconciled,
    Compensated,
    Failed,
    Denied,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceStrength {
    Anecdotal,
    Synthetic,
    Replay,
    Observational,
    ControlledField,
    Causal,
    Longitudinal,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PrivacyClass {
    Public,
    Internal,
    Confidential,
    Restricted,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BehaviorVersions {
    pub deployment: String,
    pub model: String,
    pub prompt: Option<String>,
    pub skill: Option<String>,
    pub harness: String,
    pub toolset: Option<String>,
    pub policy: Option<String>,
    pub telemetry_schema: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EffectObservation {
    pub effect_id: EffectId,
    pub effect_class: String,
    pub state: EffectState,
    pub authorization_ref: Option<String>,
    pub evidence_ref: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HumanWork {
    pub intervention: InterventionKind,
    pub review_duration_ms: Option<u64>,
    pub normalized_edit_distance: Option<f64>,
    pub reason_code: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct FieldObservation {
    pub observation_id: ObservationId,
    pub observed_at_unix_ms: u64,
    pub operating_envelope_version: String,
    pub autonomy_level: AutonomyLevel,
    pub cohort: String,
    pub task_id: TaskId,
    pub task_class: String,
    pub risk_class: String,
    pub representativeness_cell: String,
    pub versions: BehaviorVersions,
    pub outcome: OutcomeClass,
    pub outcome_verified: bool,
    /// Bounded, non-sensitive numeric measures. Raw prompts or tool payloads do
    /// not belong here.
    pub measurements: BTreeMap<String, f64>,
    pub effects: Vec<EffectObservation>,
    pub human_work: HumanWork,
    pub trace_ref: Option<String>,
    pub evidence_strength: EvidenceStrength,
    pub trace_complete: bool,
    pub outcome_join_complete: bool,
    pub privacy_class: PrivacyClass,
    pub raw_content_collected: bool,
    pub limitations: Vec<String>,
}

#[derive(Debug, thiserror::Error, PartialEq)]
pub enum ObservationError {
    #[error("{field} must not be empty")]
    Empty { field: &'static str },
    #[error("raw workload content is prohibited by the telemetry policy")]
    RawContentProhibited,
    #[error("normalized edit distance must be in [0, 1]")]
    InvalidEditDistance,
    #[error("confirmed or ambiguous effects require stable effect identifiers")]
    MissingEffectIdentity,
}

impl FieldObservation {
    pub fn validate(&self) -> Result<(), ObservationError> {
        for (field, value) in [
            ("observation_id", self.observation_id.0.as_str()),
            ("operating_envelope_version", self.operating_envelope_version.as_str()),
            ("cohort", self.cohort.as_str()),
            ("task_id", self.task_id.0.as_str()),
            ("task_class", self.task_class.as_str()),
            ("risk_class", self.risk_class.as_str()),
            ("representativeness_cell", self.representativeness_cell.as_str()),
        ] {
            if value.trim().is_empty() {
                return Err(ObservationError::Empty { field });
            }
        }
        if self.raw_content_collected {
            return Err(ObservationError::RawContentProhibited);
        }
        if let Some(distance) = self.human_work.normalized_edit_distance {
            if !(0.0..=1.0).contains(&distance) {
                return Err(ObservationError::InvalidEditDistance);
            }
        }
        if self.effects.iter().any(|effect| {
            matches!(effect.state, EffectState::Confirmed | EffectState::Ambiguous)
                && effect.effect_id.0.trim().is_empty()
        }) {
            return Err(ObservationError::MissingEffectIdentity);
        }
        Ok(())
    }

    pub fn requires_priority_retention(&self) -> bool {
        self.effects.iter().any(|effect| {
            matches!(effect.state, EffectState::Ambiguous | EffectState::Failed)
        }) || self.human_work.intervention != InterventionKind::None
            || matches!(self.outcome, OutcomeClass::Failure | OutcomeClass::Abandoned)
            || !self.trace_complete
            || !self.outcome_join_complete
    }
}
