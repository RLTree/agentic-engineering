//! Pure rollout-gate evaluation for controlled field learning.
//!
//! A feature flag changes exposure; it is not an authorization decision. Callers
//! must still enforce identity, capability, data, and effect policies separately.

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    Info,
    Warning,
    High,
    Critical,
}

#[derive(Clone, Debug, PartialEq)]
pub struct GateSnapshot {
    pub assigned: u64,
    pub exposed: u64,
    pub outcome_valid: u64,
    pub outcome_success: u64,
    pub guardrail_failures: u64,
    pub severe_failures: u64,
    pub ambiguous_effects: u64,
    pub trace_complete: u64,
    pub outcome_join_complete: u64,
    pub error_budget_remaining_fraction: f64,
    pub minimum_observation_elapsed: bool,
    pub sample_ratio_valid: bool,
    pub assignment_exposure_valid: bool,
}

#[derive(Clone, Debug, PartialEq)]
pub struct GatePolicy {
    pub minimum_exposed: u64,
    pub minimum_success_rate: f64,
    pub maximum_guardrail_rate: f64,
    pub maximum_severe_failures: u64,
    pub maximum_ambiguous_effects: u64,
    pub minimum_trace_completeness: f64,
    pub minimum_outcome_join_completeness: f64,
    pub minimum_error_budget_remaining: f64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RolloutDecision {
    Advance,
    Hold { reasons: Vec<String> },
    Narrow { reasons: Vec<String> },
    Revert { reasons: Vec<String> },
    Stop { reasons: Vec<String> },
}

#[derive(Debug, thiserror::Error, PartialEq)]
pub enum GateError {
    #[error("{field} must be within [0, 1]")]
    InvalidFraction { field: &'static str },
    #[error("a count cannot exceed its denominator: {field}")]
    InvalidCount { field: &'static str },
}

fn fraction(numerator: u64, denominator: u64) -> f64 {
    if denominator == 0 {
        0.0
    } else {
        numerator as f64 / denominator as f64
    }
}

impl GatePolicy {
    pub fn validate(&self) -> Result<(), GateError> {
        for (field, value) in [
            ("minimum_success_rate", self.minimum_success_rate),
            ("maximum_guardrail_rate", self.maximum_guardrail_rate),
            ("minimum_trace_completeness", self.minimum_trace_completeness),
            (
                "minimum_outcome_join_completeness",
                self.minimum_outcome_join_completeness,
            ),
            (
                "minimum_error_budget_remaining",
                self.minimum_error_budget_remaining,
            ),
        ] {
            if !(0.0..=1.0).contains(&value) {
                return Err(GateError::InvalidFraction { field });
            }
        }
        Ok(())
    }

    pub fn evaluate(&self, snapshot: &GateSnapshot) -> Result<RolloutDecision, GateError> {
        self.validate()?;
        if snapshot.exposed > snapshot.assigned {
            return Err(GateError::InvalidCount { field: "exposed" });
        }
        if snapshot.outcome_success > snapshot.outcome_valid {
            return Err(GateError::InvalidCount {
                field: "outcome_success",
            });
        }
        if snapshot.trace_complete > snapshot.exposed {
            return Err(GateError::InvalidCount {
                field: "trace_complete",
            });
        }
        if snapshot.outcome_join_complete > snapshot.exposed {
            return Err(GateError::InvalidCount {
                field: "outcome_join_complete",
            });
        }

        let mut stop = Vec::new();
        let mut revert = Vec::new();
        let mut narrow = Vec::new();
        let mut hold = Vec::new();

        if snapshot.severe_failures > self.maximum_severe_failures {
            stop.push("severe-failure hard limit exceeded".to_owned());
        }
        if snapshot.ambiguous_effects > self.maximum_ambiguous_effects {
            revert.push("ambiguous-effect limit exceeded".to_owned());
        }
        if snapshot.error_budget_remaining_fraction < self.minimum_error_budget_remaining {
            revert.push("error-budget gate failed".to_owned());
        }
        if !snapshot.sample_ratio_valid {
            hold.push("sample-ratio mismatch or assignment imbalance".to_owned());
        }
        if !snapshot.assignment_exposure_valid {
            hold.push("assignment and exposure do not match".to_owned());
        }
        if !snapshot.minimum_observation_elapsed {
            hold.push("minimum observation window has not elapsed".to_owned());
        }
        if snapshot.exposed < self.minimum_exposed {
            hold.push("minimum exposed population not reached".to_owned());
        }

        let success_rate = fraction(snapshot.outcome_success, snapshot.outcome_valid);
        if snapshot.outcome_valid > 0 && success_rate < self.minimum_success_rate {
            narrow.push("outcome success rate is below the promotion threshold".to_owned());
        }
        let guardrail_rate = fraction(snapshot.guardrail_failures, snapshot.exposed);
        if snapshot.exposed > 0 && guardrail_rate > self.maximum_guardrail_rate {
            revert.push("guardrail failure rate exceeded".to_owned());
        }
        let trace_completeness = fraction(snapshot.trace_complete, snapshot.exposed);
        if snapshot.exposed > 0 && trace_completeness < self.minimum_trace_completeness {
            hold.push("trace completeness is insufficient for a decision".to_owned());
        }
        let join_completeness = fraction(snapshot.outcome_join_complete, snapshot.exposed);
        if snapshot.exposed > 0
            && join_completeness < self.minimum_outcome_join_completeness
        {
            hold.push("outcome join completeness is insufficient for a decision".to_owned());
        }

        if !stop.is_empty() {
            Ok(RolloutDecision::Stop { reasons: stop })
        } else if !revert.is_empty() {
            Ok(RolloutDecision::Revert { reasons: revert })
        } else if !narrow.is_empty() {
            Ok(RolloutDecision::Narrow { reasons: narrow })
        } else if !hold.is_empty() {
            Ok(RolloutDecision::Hold { reasons: hold })
        } else {
            Ok(RolloutDecision::Advance)
        }
    }
}
