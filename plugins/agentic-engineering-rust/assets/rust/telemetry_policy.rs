//! Privacy, cardinality, and sampling policy for agent telemetry.
//!
//! The policy is pure and testable. Export adapters should apply it before
//! serializing workload-derived values or constructing metric labels.

use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PrivacyClass {
    Public,
    Internal,
    Confidential,
    Restricted,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OutcomeClass {
    Success,
    Partial,
    Failure,
    Abandoned,
    Denied,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EffectState {
    None,
    Confirmed,
    Ambiguous,
    Failed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SamplingDecision {
    Drop,
    AggregateOnly,
    RetainTrace,
    RetainIncidentEvidence,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SamplingFacts {
    pub outcome: OutcomeClass,
    pub effect_state: EffectState,
    pub human_intervened: bool,
    pub security_event: bool,
    pub trace_complete: bool,
    pub rare_high_risk_task: bool,
    /// Stable deterministic bucket in `0..10_000`, derived from a domain ID.
    pub deterministic_bucket: u16,
}

#[derive(Clone, Debug)]
pub struct TelemetryPolicy {
    pub version: String,
    pub prohibited_fields: BTreeSet<String>,
    pub metric_label_allowlist: BTreeSet<String>,
    pub maximum_metric_labels: usize,
    pub baseline_trace_rate_per_10k: u16,
    pub success_trace_rate_per_10k: u16,
    pub allow_raw_content: bool,
}

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum TelemetryError {
    #[error("telemetry policy version must not be empty")]
    EmptyVersion,
    #[error("sampling rate {field} must be no greater than 10,000")]
    InvalidSamplingRate { field: &'static str },
    #[error("metric label is not allowed: {0}")]
    LabelDenied(String),
    #[error("too many metric labels: {actual} > {maximum}")]
    TooManyLabels { actual: usize, maximum: usize },
    #[error("raw content collection is prohibited")]
    RawContentProhibited,
    #[error("prohibited telemetry field: {0}")]
    ProhibitedField(String),
}

impl TelemetryPolicy {
    pub fn validate(&self) -> Result<(), TelemetryError> {
        if self.version.trim().is_empty() {
            return Err(TelemetryError::EmptyVersion);
        }
        if self.baseline_trace_rate_per_10k > 10_000 {
            return Err(TelemetryError::InvalidSamplingRate {
                field: "baseline_trace_rate_per_10k",
            });
        }
        if self.success_trace_rate_per_10k > 10_000 {
            return Err(TelemetryError::InvalidSamplingRate {
                field: "success_trace_rate_per_10k",
            });
        }
        Ok(())
    }

    pub fn validate_fields<'a>(
        &self,
        fields: impl IntoIterator<Item = &'a str>,
        contains_raw_content: bool,
    ) -> Result<(), TelemetryError> {
        self.validate()?;
        if contains_raw_content && !self.allow_raw_content {
            return Err(TelemetryError::RawContentProhibited);
        }
        for field in fields {
            if self.prohibited_fields.contains(field) {
                return Err(TelemetryError::ProhibitedField(field.to_owned()));
            }
        }
        Ok(())
    }

    pub fn validate_metric_labels(
        &self,
        labels: &BTreeMap<String, String>,
    ) -> Result<(), TelemetryError> {
        self.validate()?;
        if labels.len() > self.maximum_metric_labels {
            return Err(TelemetryError::TooManyLabels {
                actual: labels.len(),
                maximum: self.maximum_metric_labels,
            });
        }
        for key in labels.keys() {
            if !self.metric_label_allowlist.contains(key) {
                return Err(TelemetryError::LabelDenied(key.clone()));
            }
        }
        Ok(())
    }

    pub fn sampling_decision(
        &self,
        facts: &SamplingFacts,
    ) -> Result<SamplingDecision, TelemetryError> {
        self.validate()?;
        if facts.security_event
            || facts.effect_state == EffectState::Ambiguous
            || facts.rare_high_risk_task
        {
            return Ok(SamplingDecision::RetainIncidentEvidence);
        }
        if facts.effect_state == EffectState::Failed
            || facts.human_intervened
            || !facts.trace_complete
            || matches!(facts.outcome, OutcomeClass::Failure | OutcomeClass::Abandoned)
        {
            return Ok(SamplingDecision::RetainTrace);
        }

        let threshold = if facts.outcome == OutcomeClass::Success {
            self.success_trace_rate_per_10k
        } else {
            self.baseline_trace_rate_per_10k
        };
        if facts.deterministic_bucket < threshold {
            Ok(SamplingDecision::RetainTrace)
        } else {
            Ok(SamplingDecision::AggregateOnly)
        }
    }
}
