use datafusion::physical_plan::metrics::{self, ExecutionPlanMetricsSet, MetricBuilder};

pub(super) struct GroupByMetrics {
    /// Total time spent by the `materialize(...)` function,
    /// which includes collecting the input batches and grouping.
    pub materialize_total_time: metrics::Time,

    /// Total time spent collecting the input batches from the semijoin child operator
    pub semijoin_collect_time: metrics::Time,

    /// Time spent by grouping the input tuples (i.e., hashing on the keys).
    /// This is a subset of `materialize_time`.
    /// This does not include the time required to construct the inner [NestedRel]
    pub groupby_time: metrics::Time,

    /// Time spent by creating the nested [NestedRel] (this includes concatenating the semijoin batches)
    pub nested_state_building_time: metrics::Time,

    /// Time spent by concatenating nested columns across batches
    /// Subset of `nested_state_building_time`
    pub concat_nested_columns_time: metrics::Time,

    /// Number of input rows, i.e., number of guard tuples that passed the semijoin
    pub input_rows: metrics::Count,

    /// Number of input batches, i.e., number of semijoin batches that passed the semijoin
    pub input_batches: metrics::Count,
}

impl GroupByMetrics {
    pub fn new(partition: usize, metrics: &ExecutionPlanMetricsSet) -> Self {
        let materialize_time = MetricBuilder::new(metrics).elapsed_compute(partition);
        let semijoin_collect_time =
            MetricBuilder::new(metrics).subset_time("semijoin_collect_time", partition);
        let groupby_time = MetricBuilder::new(metrics).subset_time("grouping_time", partition);
        let nested_state_building_time =
            MetricBuilder::new(metrics).subset_time("nested_state_building_time", partition);
        let concat_nested_columns_time =
            MetricBuilder::new(metrics).subset_time("concat_nested_columns_time", partition);

        let input_rows = MetricBuilder::new(metrics).counter("input_rows", partition);
        let input_batches = MetricBuilder::new(metrics).counter("input_batches", partition);

        Self {
            materialize_total_time: materialize_time,
            semijoin_collect_time,
            groupby_time,
            nested_state_building_time,
            concat_nested_columns_time,
            input_rows,
            input_batches,
        }
    }
}
