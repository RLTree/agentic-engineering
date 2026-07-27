//! Effect journal abstractions. Persist intent before external dispatch.

use async_trait::async_trait;

use crate::agent_domain::{ActionId, RunId, StateVersion};

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EffectStatus {
    Proposed,
    Authorized,
    Prepared,
    Dispatched,
    Confirmed,
    FailedBeforeEffect,
    Ambiguous,
    ReconciledConfirmed,
    ReconciledAbsent,
    Compensated,
}

#[derive(Clone, Debug)]
pub struct EffectRecord {
    pub run_id: RunId,
    pub action_id: ActionId,
    pub operation: String,
    pub normalized_target: String,
    pub arguments_digest: String,
    pub idempotency_key: String,
    pub status: EffectStatus,
    pub provider_request_id: Option<String>,
    pub version: StateVersion,
}

#[derive(Debug, thiserror::Error)]
pub enum JournalError {
    #[error("effect record has a stale version")]
    StaleVersion,
    #[error("effect record conflicts with an existing action")]
    Conflict,
    #[error("journal storage failed")]
    Storage(#[source] anyhow::Error),
}

#[async_trait]
pub trait EffectJournal: Send + Sync {
    async fn prepare(&self, record: EffectRecord) -> Result<EffectRecord, JournalError>;
    async fn update(
        &self,
        expected: StateVersion,
        record: EffectRecord,
    ) -> Result<EffectRecord, JournalError>;
    async fn get(&self, action_id: &ActionId) -> Result<Option<EffectRecord>, JournalError>;
}

#[derive(Clone, Debug)]
pub enum DispatchOutcome<T> {
    Confirmed { value: T, provider_request_id: Option<String> },
    FailedBeforeEffect { code: String },
    Ambiguous { provider_request_id: Option<String>, detail: String },
}

/// The caller must first create a Prepared journal record. An Ambiguous outcome
/// must be reconciled by action/idempotency ID before any redispatch.
#[async_trait]
pub trait EffectExecutor<I, O>: Send + Sync {
    async fn dispatch(&self, action_id: &ActionId, input: I) -> DispatchOutcome<O>;
    async fn reconcile(&self, action_id: &ActionId) -> Result<Option<O>, anyhow::Error>;
}
