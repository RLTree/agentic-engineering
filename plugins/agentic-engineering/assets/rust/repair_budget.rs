//! Pure repair-budget and semantic circuit-breaker logic.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AttemptResult { Improved, Unchanged, Regressed, Blocked, Passed }

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RepairAttempt {
    pub hypothesis: String,
    pub mechanism_class: String,
    pub changed_variable: String,
    pub failure_location: String,
    pub observed_value: String,
    pub admissible_alternatives: Vec<String>,
    pub evidence_gained: Vec<String>,
    pub result: AttemptResult,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RepairDecision {
    Continue,
    ChangeHypothesis,
    ChangeFeedback,
    ChangeToolOrOracle,
    ReduceScope,
    RedesignArchitecture,
    RequestHumanDecision,
    Revert,
    Stop,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RepairPolicy {
    pub max_attempts: usize,
    pub max_repeated_mechanism_without_new_evidence: usize,
    pub stop_on_ambiguous_effect: bool,
}

impl RepairPolicy {
    pub fn decide(&self, attempts: &[RepairAttempt], ambiguous_effect: bool) -> RepairDecision {
        if ambiguous_effect && self.stop_on_ambiguous_effect {
            return RepairDecision::RequestHumanDecision;
        }
        if attempts.last().is_some_and(|a| a.result == AttemptResult::Passed) {
            return RepairDecision::Stop;
        }
        if attempts.len() >= self.max_attempts {
            return RepairDecision::ChangeHypothesis;
        }
        if let Some(last) = attempts.last() {
            let repeated = attempts.iter().rev()
                .take_while(|a| a.mechanism_class == last.mechanism_class)
                .take_while(|a| a.evidence_gained.is_empty())
                .count();
            if repeated >= self.max_repeated_mechanism_without_new_evidence {
                return RepairDecision::ChangeToolOrOracle;
            }
        }
        RepairDecision::Continue
    }
}
