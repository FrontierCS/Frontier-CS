//! Metrics of the YannakakisFullJoinExec

use datafusion::physical_plan::metrics::{self, ExecutionPlanMetricsSet, MetricBuilder};

/// Metrics for the YannakakisFullJoinExec operator.
#[derive(Clone, Debug)]
pub(super) struct YannakakisMetrics {
    /// Total time spent by this operator.
    pub total_time: metrics::Time,

    /// Total time spent by grouping the children
    pub groupby_time: metrics::Time,
    /// Total time spent by lookup guard tuples in children
    pub lookup_time: metrics::Time,
    /// Total time spent by allocating output buffers (arraybuilders)
    pub allocate_buffer_time: metrics::Time,
    /// Total time spent by filling output buffers for guard columns
    /// (using `take_weighted_unchecked`)
    pub guard_take_time: metrics::Time,
    /// Total time spent by unnesting
    pub unnest_time: metrics::Time,
    /// Total time spent by finishing the arraybuilder and creating the final arrays
    pub finish_builder_time: metrics::Time,

    /// Number of input rows (i.e., guard tuples)
    pub input_rows: metrics::Count,
    /// Number of output rows
    pub output_rows: metrics::Count,
}

impl YannakakisMetrics {
    pub fn new(partition: usize, metrics: &ExecutionPlanMetricsSet) -> Self {
        let total_time = MetricBuilder::new(metrics).elapsed_compute(partition);

        let groupby_time = MetricBuilder::new(metrics).subset_time("groupby_children", partition);
        let lookup_time = MetricBuilder::new(metrics).subset_time("lookup", partition);
        let allocate_buffer_time =
            MetricBuilder::new(metrics).subset_time("allocate_buffers", partition);
        let guard_append_time =
            MetricBuilder::new(metrics).subset_time("guard_take_weighted", partition);
        let unnest_time = MetricBuilder::new(metrics).subset_time("unnest", partition);
        let finish_builder_time =
            MetricBuilder::new(metrics).subset_time("finish_builders", partition);

        let input_rows = MetricBuilder::new(metrics).counter("input_rows", partition);
        let output_rows = MetricBuilder::new(metrics).counter("output_rows", partition);

        Self {
            total_time,
            groupby_time,
            lookup_time,
            allocate_buffer_time,
            guard_take_time: guard_append_time,
            unnest_time,
            finish_builder_time,
            input_rows,
            output_rows,
        }
    }
}
