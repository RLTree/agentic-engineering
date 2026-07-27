//! Provider-independent domain sketch for an agent run.

use std::fmt;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct RunId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct ActionId(pub String);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StateVersion(pub u64);

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RunStatus {
    Queued,
    Running { step: String },
    WaitingApproval { action_id: ActionId },
    Verifying,
    Succeeded,
    Failed { code: &'static str },
    Cancelled,
    Escalated { reason: String },
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ProposedEffect {
    ReadRepository { query: String },
    WriteArtifact { path: String, content: Vec<u8> },
    SendExternalMessage { destination: String, body: String },
}

impl ProposedEffect {
    pub fn requires_approval(&self) -> bool {
        matches!(self, Self::SendExternalMessage { .. })
    }
}

#[derive(Clone, Debug)]
pub struct RunState {
    pub run_id: RunId,
    pub version: StateVersion,
    pub status: RunStatus,
    pub iterations_left: u32,
    pub tool_calls_left: u32,
    pub acceptance_evidence: Vec<String>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum TransitionError {
    TerminalState,
    BudgetExhausted(&'static str),
    StaleVersion { expected: u64, actual: u64 },
    MissingEvidence,
}

impl fmt::Display for TransitionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

impl std::error::Error for TransitionError {}

impl RunState {
    pub fn begin_action(&self, expected: StateVersion) -> Result<Self, TransitionError> {
        if self.version != expected {
            return Err(TransitionError::StaleVersion {
                expected: expected.0,
                actual: self.version.0,
            });
        }
        if matches!(self.status, RunStatus::Succeeded | RunStatus::Failed { .. } | RunStatus::Cancelled) {
            return Err(TransitionError::TerminalState);
        }
        if self.tool_calls_left == 0 {
            return Err(TransitionError::BudgetExhausted("tool_calls"));
        }
        let mut next = self.clone();
        next.version.0 += 1;
        next.tool_calls_left -= 1;
        Ok(next)
    }

    pub fn succeed(&self, required_evidence: usize) -> Result<Self, TransitionError> {
        if self.acceptance_evidence.len() < required_evidence {
            return Err(TransitionError::MissingEvidence);
        }
        let mut next = self.clone();
        next.version.0 += 1;
        next.status = RunStatus::Succeeded;
        Ok(next)
    }
}
