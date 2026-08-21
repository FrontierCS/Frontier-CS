//! Metrics for the Flatten operator

use datafusion::physical_plan::metrics::{self, ExecutionPlanMetricsSet, MetricBuilder};

/// Metrics for the Flatten operator.
#[derive(Clone, Debug)]
pub(super) struct FlattenMetrics {
    /// Total time spent by flatten_batch() function calls
    pub flatten_time: metrics::Time,

    /// Total time spent by computing output for guard columns of the root
    pub guard_take_time: metrics::Time,
    /// Total time spent by unnesting
    pub unnest_time: metrics::Time,
    /// Total time spent by unnest_primitive_nestedrel() (excl. recursive calls)
    pub unnest_primitive_nestedrel_time: metrics::Time,
    /// Total time spent by iterating though linked lists in unnest_primitive_nestedrel()
    pub iterate_ll_time: metrics::Time,
    /// Total time spent by filling primitive array buffers in unnest_primitive_nestedrel()
    pub fill_primitive_buffers_time: metrics::Time,
    /// Total time spent by unnest non-flat, non-primitive nested relations  (excl. recursive calls)
    pub unnest_default_nestedrel_time: metrics::Time,
    /// Total time spent by update_repeat_copy()
    pub update_repeat_copy_time: metrics::Time,
    /// Total time spent by cloning arcs of joining columns
    pub clone_join_columns_time: metrics::Time,

    /// Number of input rows
    pub input_rows: metrics::Count,
    /// Number of output rows
    pub output_rows: metrics::Count,
}

impl FlattenMetrics {
    pub fn new(partition: usize, metrics: &ExecutionPlanMetricsSet) -> Self {
        let flatten_time = MetricBuilder::new(metrics).subset_time("flatten_time", partition);

        let guard_take_time = MetricBuilder::new(metrics).subset_time("root", partition);
        let unnest_time = MetricBuilder::new(metrics).subset_time("unnest_nestedcols", partition);
        let unnest_primitive_nestedrel_time =
            MetricBuilder::new(metrics).subset_time("unnest_primitive_nestedrel", partition);
        let iterate_ll_time = MetricBuilder::new(metrics)
            .subset_time("unnest_primitive_nestedrel::iterate_ll", partition);
        let fill_primitive_buffers_time = MetricBuilder::new(metrics)
            .subset_time("unnest_primitive_nestedrel::fill_buffers", partition);
        let unnest_default_nestedrel_time =
            MetricBuilder::new(metrics).subset_time("unnest_default_nestedrel", partition);
        let update_repeat_copy_time =
            MetricBuilder::new(metrics).subset_time("update_repeat_copy", partition);
        let clone_join_columns_time =
            MetricBuilder::new(metrics).subset_time("duplicate_join_cols", partition);

        let input_rows = MetricBuilder::new(metrics).counter("input_rows", partition);
        let output_rows = MetricBuilder::new(metrics).counter("output_rows", partition);

        Self {
            flatten_time,
            guard_take_time,
            unnest_time,
            unnest_primitive_nestedrel_time,
            iterate_ll_time,
            fill_primitive_buffers_time,
            unnest_default_nestedrel_time,
            update_repeat_copy_time,
            clone_join_columns_time,
            input_rows,
            output_rows,
        }
    }
}
