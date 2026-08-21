//! Metrics for tracking the performance of the semi-join operator.

use datafusion::physical_plan::metrics::{self, ExecutionPlanMetricsSet, MetricBuilder};

#[derive(Clone, Debug)]
pub(super) struct SemiJoinMetrics {
    /// Total time spent by this operator.
    /// This includes the build time (groupby time) of children and the semijoin time.
    pub total_time: metrics::Time,

    /// Total time spent by semijoining the guard tuples with the child groupby results,
    /// includes building the final SemiJoinResultBatches, but
    /// excludes build time (groupby time) of the children
    ///
    /// Semijoin time is not measured when there are no children (because there is no actual semijoin to do)
    pub semijoin_time: metrics::Time,

    /// Number of rows in guard batch
    pub guard_input_rows: metrics::Count,

    /// Number of output rows
    pub output_rows: metrics::Count,
}

impl SemiJoinMetrics {
    pub fn new(partition: usize, metrics: &ExecutionPlanMetricsSet) -> Self {
        let total_time = MetricBuilder::new(metrics).elapsed_compute(partition);
        let semijoin_time: metrics::Time =
            MetricBuilder::new(metrics).subset_time("semijoin", partition);
        let guard_input_rows = MetricBuilder::new(metrics).counter("guard_input_rows", partition);
        let output_rows = MetricBuilder::new(metrics).counter("output_rows", partition);

        Self {
            total_time,
            semijoin_time,
            guard_input_rows,
            output_rows,
        }
    }
}
