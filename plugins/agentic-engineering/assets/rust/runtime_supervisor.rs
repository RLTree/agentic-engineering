//! Tracked Tokio supervision with cooperative cancellation and bounded drain.

use std::{future::Future, sync::Arc, time::Duration};
use tokio::{sync::Semaphore, task::JoinSet, time::Instant};
use tokio_util::sync::CancellationToken;

#[derive(Debug, thiserror::Error)]
pub enum RuntimeError {
    #[error("operation was cancelled")]
    Cancelled,
    #[error("deadline elapsed")]
    Deadline,
    #[error("task failed to join: {0}")]
    Join(String),
}

pub struct Supervisor {
    cancel: CancellationToken,
    tasks: JoinSet<Result<(), RuntimeError>>,
    permits: Arc<Semaphore>,
}

impl Supervisor {
    pub fn new(max_concurrency: usize) -> Self {
        Self {
            cancel: CancellationToken::new(),
            tasks: JoinSet::new(),
            permits: Arc::new(Semaphore::new(max_concurrency)),
        }
    }

    pub fn child_token(&self) -> CancellationToken {
        self.cancel.child_token()
    }

    pub fn spawn<F>(&mut self, deadline: Instant, work: F)
    where
        F: Future<Output = Result<(), RuntimeError>> + Send + 'static,
    {
        let cancel = self.child_token();
        let permits = Arc::clone(&self.permits);
        self.tasks.spawn(async move {
            let permit = tokio::select! {
                _ = cancel.cancelled() => return Err(RuntimeError::Cancelled),
                acquired = permits.acquire_owned() => acquired.map_err(|_| RuntimeError::Cancelled)?,
                _ = tokio::time::sleep_until(deadline) => return Err(RuntimeError::Deadline),
            };
            let _permit = permit;
            tokio::select! {
                _ = cancel.cancelled() => Err(RuntimeError::Cancelled),
                _ = tokio::time::sleep_until(deadline) => Err(RuntimeError::Deadline),
                result = work => result,
            }
        });
    }

    pub async fn shutdown(mut self, drain_for: Duration) -> Result<(), RuntimeError> {
        self.cancel.cancel();
        let drain = async {
            while let Some(joined) = self.tasks.join_next().await {
                match joined {
                    Ok(Ok(())) | Ok(Err(RuntimeError::Cancelled)) => {}
                    Ok(Err(error)) => return Err(error),
                    Err(error) => return Err(RuntimeError::Join(error.to_string())),
                }
            }
            Ok(())
        };
        tokio::time::timeout(drain_for, drain)
            .await
            .map_err(|_| RuntimeError::Deadline)?
    }
}
