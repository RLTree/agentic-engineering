//! Minimal deterministic model fake for scenario tests.

use std::{collections::VecDeque, sync::Mutex};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ModelRequest {
    pub operation: String,
    pub state_version: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ModelDecision {
    pub action: String,
    pub rationale_summary: String,
}

#[derive(Debug, thiserror::Error)]
pub enum FakeError {
    #[error("unexpected model request: {0:?}")]
    Unexpected(ModelRequest),
    #[error("fake model mutex was poisoned")]
    Poisoned,
}

pub struct ScriptedModel {
    script: Mutex<VecDeque<(ModelRequest, ModelDecision)>>,
}

impl ScriptedModel {
    pub fn new(script: impl Into<VecDeque<(ModelRequest, ModelDecision)>>) -> Self {
        Self { script: Mutex::new(script.into()) }
    }

    pub fn decide(&self, request: ModelRequest) -> Result<ModelDecision, FakeError> {
        let mut script = self.script.lock().map_err(|_| FakeError::Poisoned)?;
        let Some((expected, decision)) = script.pop_front() else {
            return Err(FakeError::Unexpected(request));
        };
        if expected != request {
            return Err(FakeError::Unexpected(request));
        }
        Ok(decision)
    }

    pub fn assert_consumed(&self) -> Result<(), FakeError> {
        let script = self.script.lock().map_err(|_| FakeError::Poisoned)?;
        assert!(script.is_empty(), "unconsumed model script entries: {}", script.len());
        Ok(())
    }
}
