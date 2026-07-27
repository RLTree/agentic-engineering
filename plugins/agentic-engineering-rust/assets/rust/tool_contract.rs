//! Schema-first tool boundary. Wire DTOs are converted to validated domain input.

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct LookupIssueWire {
    /// Stable project identifier, not a display name.
    pub project_id: String,
    /// Stable issue identifier.
    pub issue_id: String,
}

#[derive(Clone, Debug)]
pub struct LookupIssue {
    pub project_id: String,
    pub issue_id: String,
}

#[derive(Debug, thiserror::Error)]
pub enum ToolError {
    #[error("{field} must not be empty")]
    InvalidInput { field: &'static str },
    #[error("operation is not authorized")]
    Denied,
    #[error("dependency rate limited the request")]
    RateLimited { retry_after_ms: Option<u64> },
    #[error("effect outcome is unknown; reconcile action {action_id}")]
    AmbiguousEffect { action_id: String },
    #[error("dependency failed")]
    Dependency(#[source] anyhow::Error),
}

impl TryFrom<LookupIssueWire> for LookupIssue {
    type Error = ToolError;

    fn try_from(value: LookupIssueWire) -> Result<Self, Self::Error> {
        if value.project_id.trim().is_empty() {
            return Err(ToolError::InvalidInput { field: "project_id" });
        }
        if value.issue_id.trim().is_empty() {
            return Err(ToolError::InvalidInput { field: "issue_id" });
        }
        Ok(Self { project_id: value.project_id, issue_id: value.issue_id })
    }
}

#[derive(Debug, Serialize, JsonSchema)]
pub struct IssueResult {
    pub id: String,
    pub title: String,
    pub status: String,
    pub provenance: String,
}

#[async_trait]
pub trait IssueLookup: Send + Sync {
    async fn lookup(&self, request: LookupIssue) -> Result<IssueResult, ToolError>;
}
