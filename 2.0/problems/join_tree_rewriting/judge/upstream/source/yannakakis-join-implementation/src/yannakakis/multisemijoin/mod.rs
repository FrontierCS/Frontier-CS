//! Implementation of the [MultiSemijoin] operator.

use std::pin::Pin;
use std::sync::Arc;
use std::task::Poll;

use datafusion::physical_plan::metrics::MetricsSet;
use futures::ready;
use futures::Stream;
use futures::StreamExt;

use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::array::RecordBatch;
use datafusion::arrow::array::UInt32Array;
use datafusion::error::DataFusionError;
use datafusion::execution::SendableRecordBatchStream;
use datafusion::execution::TaskContext;
use datafusion::physical_plan::metrics::ExecutionPlanMetricsSet;
use datafusion::physical_plan::ExecutionPlan;

use crate::yannakakis::util::write_metrics_as_json;

use super::data::GroupedRel;
use super::data::GroupedRelRef;
use super::data::Idx;
use super::data::NestedBatch;
use super::data::NestedColumn;
use super::data::NestedSchema;
use super::data::NestedSchemaRef;
use super::data::SemiJoinResultBatch;
use super::groupby::GroupBy;
use super::kernel::take_nested_column_inplace;
use super::sel::Sel;
use super::util::once_async::OnceAsync;
use super::util::once_async::OnceFut;

use metrics::SemiJoinMetrics;

pub mod metrics;

#[derive(Debug)]
pub struct MultiSemiJoin {
    /// The guard is the relation that we want to compute the semijoin of.
    guard: Arc<dyn ExecutionPlan>,

    /// The non-empty vector of child nodes.
    children: Vec<Arc<GroupBy>>, // Arc because shared between multiple partitions

    /// For each child, a vector [ A,B ] indicating the indices of the guard columns that form a lookup key in the GroupBy child.
    /// Is of the same length as `children`.
    semijoin_keys: Vec<Vec<usize>>,

    /// The [NestedSchema] of the results produced by the MultiSemijoin
    schema: NestedSchemaRef,

    /// MultiSemiJoin execution metrics
    metrics: ExecutionPlanMetricsSet,

    // / A OnceAsync that does return the list of groupby-children, completed after materialization.
    // / This ensures that we can share the materialized results of the child groupbies across multiple partitions.
    // once_fut: OnceAsync<Vec<GroupedRelRef>>,
    /// For each child, a OnceAsync that returns the materialized result of the child groupby.
    once_futs: Vec<OnceAsync<GroupedRelRef>>,
}

impl MultiSemiJoin {
    pub fn new(
        guard: Arc<dyn ExecutionPlan>,
        children: Vec<Arc<GroupBy>>,
        equijoin_keys: Vec<Vec<(usize, usize)>>,
    ) -> Self {
        // Check that children and equijoin_keys have the same length
        assert_eq!(
            children.len(),
            equijoin_keys.len(),
            "children and equijoin_keys must have the same length"
        );

        // Check if semijoin is valid
        //      - equijoin keys are not out of bounds, and
        //      - joining columns have equal types
        let guard_schema = guard.schema();

        for (i, keys) in equijoin_keys.iter().enumerate() {
            let child_schema = children[i].schema();

            // Each equi-join must be between a field in guard and a *regular* field in child
            for (guard_col, child_col) in keys {
                let guard_field = guard_schema.field(*guard_col); // panics if out of bounds
                let child_field = child_schema.regular_fields.field(*child_col); // panics if out of bounds
                assert!(
                    guard_field
                        .data_type()
                        .equals_datatype(child_field.data_type()),
                    "Joining columns should have equal types, but column {} of guard has type {:?} and column {} of child has type {:?}", guard_col, guard_field.data_type(), child_col, child_field.data_type()
                );
            }

            // Each regular field in child must be part of an equi-join -- otherwise this is not a valid semijoin
            for j in 0..child_schema.regular_fields.fields().len() {
                if !keys.iter().any(|(_, child_col)| *child_col == j) {
                    panic!("To be a valid semi-join regular field of a childe [GroupBy] must be part of an equi-join, but field {} in child {} is not", j, i);
                }
            }
        }

        // The semijoin_keys is a vector of vectors of guard column indices, each inner vector specifying the indices of the
        // guard columns that form a lookup key in the GroupBy child.
        let mut equijoin_keys = equijoin_keys;
        let semijoin_keys = equijoin_keys
            .iter_mut()
            .map(|keys| {
                keys.sort_by_key(|(_guard_col, child_col)| *child_col);
                keys.iter()
                    .map(|(guard_col, _child_col)| *guard_col)
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();

        // Create the result nested schema
        let child_schemas: Vec<_> = children.iter().map(|c| c.schema()).collect();
        let result_schema = NestedSchema::semijoin(&guard_schema, &child_schemas);

        let once_futs = (0..children.len()).map(|_| Default::default()).collect();

        MultiSemiJoin {
            guard,
            children,
            semijoin_keys,
            schema: Arc::new(result_schema),
            metrics: ExecutionPlanMetricsSet::new(),
            // once_fut: Default::default(),
            once_futs,
        }
    }

    /// The output schema of the [NestedRel] produced by this [MultiSemiJoin]
    pub fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    pub fn guard(&self) -> &Arc<dyn ExecutionPlan> {
        &self.guard
    }

    pub fn children(&self) -> &[Arc<GroupBy>] {
        &self.children
    }

    pub fn semijoin_keys(&self) -> &Vec<Vec<usize>> {
        &self.semijoin_keys
    }

    pub fn metrics(&self) -> MetricsSet {
        self.metrics.clone_inner()
    }

    /// Get a JSON representation of the MultiSemiJoin node and all its descendants ([MultiSemiJoin] & [GroupBy]), including their metrics.
    /// The JSON representation is a string, without newlines, and is appended to `output`.
    pub fn as_json(&self, output: &mut String) -> Result<(), std::fmt::Error> {
        use std::fmt::Write;

        write!(output, "{{ \"operator\": \"SEMIJOIN\"")?;
        write_metrics_as_json(&Some(self.metrics()), output)?;

        write!(output, ", \"children\": [")?;
        let n_children = self.children.len();

        if n_children >= 1 {
            for child in &self.children[..n_children - 1] {
                child.as_json(output)?;
                write!(output, ",")?;
            }
            let _ = &self.children[n_children - 1].as_json(output)?; // skip comma for last child
        }

        write!(output, "]}}")?;

        Ok(())
    }

    /// Collect metrics from this MultiSemiJoin node and all its descendants as a pretty-printed string.
    /// The string is appended to `output_buffer` with an indentation of `indent` spaces.
    pub fn collect_metrics(&self, output_buffer: &mut String, indent: usize) {
        use std::fmt::Write;

        (0..indent).for_each(|_| output_buffer.push(' '));

        writeln!(output_buffer, "[MULTISEMIJOIN] {}", self.metrics())
            .expect("Failed to write multisemijoin metrics to string.");

        for child in &self.children {
            child.collect_metrics(output_buffer, indent + 4);
        }
    }

    /// When it executes, a multisemijoin will return a stream of [MultiSemiJoinResultBatch]s.
    pub fn execute(
        &self,
        partition: usize,
        context: Arc<TaskContext>,
    ) -> Result<SendableSemiJoinResultBatchStream, DataFusionError> {
        async fn materialize_child(
            child: Arc<GroupBy>,
            context: Arc<TaskContext>,
        ) -> Result<GroupedRelRef, DataFusionError> {
            child.materialize(context).await
        }

        let materialized_children_futs = self
            .once_futs
            .iter()
            .zip(self.children.iter())
            .map(|(onceasync, child)| {
                onceasync.once(|| materialize_child(child.clone(), context.clone()))
            })
            .collect();

        let guard_stream = self.guard.execute(partition, context)?;
        let schema = self.schema.clone();
        let semijoin_keys = self.semijoin_keys.clone();
        let semijoin_metrics = SemiJoinMetrics::new(partition, &self.metrics);
        let hashes_buffer = Vec::new();

        Ok(Box::pin(MultiSemiJoinStream {
            schema,
            guard_stream,
            materialized_children_futs,
            semijoin_keys,
            semijoin_metrics,
            hashes_buffer,
            guard_batch_cache: None,
        }))
    }
}

pub type SendableSemiJoinResultBatchStream = Pin<Box<MultiSemiJoinStream>>;

/// A [`Stream`] of [SemiJoinResultBatch] that does the actual work
pub struct MultiSemiJoinStream {
    schema: NestedSchemaRef,
    guard_stream: SendableRecordBatchStream,
    // materialized_children_fut: OnceFut<Vec<GroupedRelRef>>,
    materialized_children_futs: Vec<OnceFut<GroupedRelRef>>,
    semijoin_keys: Vec<Vec<usize>>,
    semijoin_metrics: SemiJoinMetrics,
    hashes_buffer: Vec<u64>,

    /// Cache for the guard batch, only used in the multi-semijoin case
    ///
    /// Useful in the following situation:
    /// The first `x` children are materialized and the guard batch is probed.
    /// This guard batch is successfully semijoined with the first `x` children and has a nonempty result.
    /// We have to materialze the `x+1`th child. If that child is not ready yet,
    /// the poll_next function will return Poll:Pending and the current guard batch and selection vector will be lost.
    /// To avoid this, we cache them and use it in the next poll_next call.
    guard_batch_cache: Option<RecordBatch>,
}

impl Stream for MultiSemiJoinStream {
    type Item = Result<SemiJoinResultBatch, DataFusionError>;

    fn poll_next(
        mut self: Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<Option<Self::Item>> {
        self.poll_next_impl(cx)
    }
}

/// poll_next_impl variant for MultiSemiJoinStream without children (i.e, leaf stream)
#[inline(always)]
fn poll_next_leaf(
    guard_stream: &mut SendableRecordBatchStream,
    semijoin_metrics: &SemiJoinMetrics,
    cx: &mut std::task::Context<'_>,
) -> Poll<Option<Result<SemiJoinResultBatch, DataFusionError>>> {
    // Probe next guard input batch
    // Returns early if:
    // - the guard input batch is not yet available
    // - the guard stream returned an error
    let guard_batch = match ready!(guard_stream.poll_next_unpin(cx)) {
        Some(Ok(guard_batch)) => guard_batch,
        Some(Err(e)) => return Poll::Ready(Some(Err(e))),
        None => return Poll::Ready(None),
    };

    semijoin_metrics
        .guard_input_rows
        .add(guard_batch.num_rows());

    // Return the guard batch as is
    semijoin_metrics.output_rows.add(guard_batch.num_rows());
    Poll::Ready(Some(Ok(SemiJoinResultBatch::Flat(guard_batch))))
}

/// poll_next_impl variant for MultiSemiJoinStream with a single child
/// (i.e., single semijoin)
#[inline(always)]
fn poll_next_single_semijoin(
    guard_stream: &mut SendableRecordBatchStream,
    child: &mut OnceFut<Arc<dyn GroupedRel>>,
    semijoin_on: &[usize],
    hashes_buffer: &mut Vec<u64>,
    schema: &NestedSchemaRef,
    semijoin_metrics: &SemiJoinMetrics,
    cx: &mut std::task::Context<'_>,
) -> Poll<Option<Result<SemiJoinResultBatch, DataFusionError>>> {
    // Get child (groupby) result, if available
    // Return early if:
    // - the child is not yet materialized (see the ready! macro)
    // - the child is materialized, but returned an error
    let grouped_rel = match ready!(child.get(cx)) {
        Ok(grouped_rel) => grouped_rel,
        Err(e) => {
            return Poll::Ready(Some(Err(e)));
        }
    };

    // At this point, the child groupby result is materialized and ready to be used for the semijoin
    // So we can now probe the next guard input batch
    // Returns early if:
    // - the guard input batch is not yet available (see the ready! macro)
    // - the guard stream returned an error
    let guard_batch = match ready!(guard_stream.poll_next_unpin(cx)) {
        Some(Ok(guard_batch)) => guard_batch,
        Some(Err(e)) => return Poll::Ready(Some(Err(e))),
        None => return Poll::Ready(None),
    };

    semijoin_metrics
        .guard_input_rows
        .add(guard_batch.num_rows());

    // We have the guard batch and the child groupby result.
    // so we can perform the actual semijoin operation.
    let semijoin_time = semijoin_metrics.semijoin_time.timer();
    let mut keys: Vec<ArrayRef> = Vec::with_capacity(semijoin_on.len());

    create_keys(&guard_batch, semijoin_on, &mut keys);
    let (sel, nested_col) = grouped_rel.lookup(&keys, hashes_buffer, guard_batch.num_rows());

    // We now have a final selection vector that contains the row numbers of the non-dangling tuples in the guard batch.
    // To ensure that each regular and nested column has only non-dangling tuples we need to:
    // - apply a take operation on the regular columns in the guard batch
    // Datafusion's take works only on UInt32Array, so we need to convert the selection vector to UInt32Array
    let sel = UInt32Array::from(sel.into_vec());

    let regular_cols: Vec<ArrayRef> = guard_batch
        .columns()
        .iter()
        .map(|col| datafusion::arrow::compute::take(col, &sel, None).unwrap())
        .collect();

    let nestedbatch = NestedBatch::new(schema.clone(), regular_cols, vec![nested_col]);

    semijoin_time.done();
    semijoin_metrics.output_rows.add(nestedbatch.num_rows());

    Poll::Ready(Some(Ok(SemiJoinResultBatch::Nested(nestedbatch))))
}

/// poll_next_impl variant for MultiSemiJoinStream with at least two children
///
/// Performs the actual semijoin between a guard batch and a list of 2 or more child groupby results.
/// The children may not be materialized yet (hence the OnceFut). So we need to materialize them first if not yet done.
/// Stop early: if an intermediate semijoin result is empty, do not semijoin with the remaining children (and also do not materialize them!)
#[inline]
fn poll_next_multi_semijoin(
    guard_stream: &mut SendableRecordBatchStream,
    grouped_rels: &mut [OnceFut<GroupedRelRef>],
    semijoin_keys: &[Vec<usize>],
    hashes_buffer: &mut Vec<u64>,
    schema: &NestedSchemaRef,
    cx: &mut std::task::Context<'_>,
    metrics: &SemiJoinMetrics,
    guard_batch_cache: &mut Option<RecordBatch>,
) -> Poll<Option<Result<SemiJoinResultBatch, DataFusionError>>> {
    assert!(
        grouped_rels.len() >= 2,
        "Expected >= 2 children for multisemijoin, found {}",
        grouped_rels.len()
    );

    // Create a vector to store the nested columns resulting from the semijoin.
    let mut nested_cols: Vec<NestedColumn> = Vec::with_capacity(grouped_rels.len());

    // Create a vector to hold the lookup keys
    let mut keys: Vec<ArrayRef> = Vec::new();

    if guard_batch_cache.is_none() {
        // Poll next guard input batch
        // Returns early if:
        // - the guard input batch is not yet available
        // - the guard stream returned an error
        let guard_batch = match ready!(guard_stream.poll_next_unpin(cx)) {
            Some(Ok(guard_batch)) => guard_batch,
            Some(Err(e)) => return Poll::Ready(Some(Err(e))),
            None => return Poll::Ready(None),
        };

        let input_rows = guard_batch.num_rows();
        metrics.guard_input_rows.add(input_rows);

        *guard_batch_cache = Some(guard_batch);
    }

    let guard_batch = guard_batch_cache.as_ref().unwrap();

    // Initially, the selection vector contains all the rows.
    // It will be refined by lookup_sel to contain only the rows that are not dangling.
    let mut sel = Sel::all(guard_batch.num_rows() as Idx);

    for (grouped_rel_fut, semijoin_rel_on) in grouped_rels.iter_mut().zip(semijoin_keys.iter()) {
        // Compute grouped_rel if not yet done
        // Returns early if:
        // - the child is not yet materialized (see the ready! macro)
        // - the child is materialized, but returned an error
        // - the grouped_rel is empty
        let grouped_rel = match ready!(grouped_rel_fut.get(cx)) {
            Ok(grouped_rel) => {
                if grouped_rel.is_empty() {
                    // Since the grouped_rel is empty, the multisemijoin result will always be empty, also for the following batches...
                    // End the stream.
                    return Poll::Ready(None);
                }
                grouped_rel
            }
            Err(e) => return Poll::Ready(Some(Err(e))),
        };

        // Perform the semijoin operation with this child.
        let semijoin_timer = metrics.semijoin_time.timer();
        create_keys(guard_batch, &semijoin_rel_on, &mut keys);
        nested_cols.push(grouped_rel.lookup_sel(
            &keys,
            &mut sel,
            hashes_buffer,
            guard_batch.num_rows(),
        ));
        semijoin_timer.done();
    }

    // Empty the cache
    let guard_batch = guard_batch_cache.take().unwrap();

    let semijoin_timer = metrics.semijoin_time.timer();

    // We now have a final selection vector that contains the row numbers of the non-dangling tuples in the guard batch.
    // All of the regular columns, as well as all of the nested columns, have as many rows as the original `record_batch.num_rows()`
    // To ensure that each regular and nested column has only non-dangling tuples we need to:
    // - apply a take operation on the regular columns in the guard batch
    // - apply a take operation on all nested_columns
    // but only when the selection vector did not select everything
    let nestedbatch = if sel.len() == guard_batch.num_rows() {
        // No dangling tuples, we can return the guard batch as is
        NestedBatch::new(schema.clone(), guard_batch.columns().to_vec(), nested_cols)
    } else {
        // Some dangling tuples, we need to apply a take operation
        for col in nested_cols.iter_mut() {
            take_nested_column_inplace(col, &sel);
        }

        // Datafusion's take works only on UInt32Array, so we need to convert the selection vector to UInt32Array
        let sel = UInt32Array::from(sel.into_vec());
        let regular_cols: Vec<ArrayRef> = guard_batch
            .columns()
            .iter()
            .map(|col| datafusion::arrow::compute::take(col, &sel, None).unwrap())
            .collect();

        NestedBatch::new(schema.clone(), regular_cols, nested_cols)
    };

    semijoin_timer.done();
    metrics.output_rows.add(nestedbatch.num_rows());

    Poll::Ready(Some(Ok(SemiJoinResultBatch::Nested(nestedbatch))))
}

impl MultiSemiJoinStream {
    /// Separate implementation function that unpins the [`HashJoinStream`] so
    /// that partial borrows work correctly
    fn poll_next_impl(
        &mut self,
        cx: &mut std::task::Context<'_>,
    ) -> Poll<Option<Result<SemiJoinResultBatch, DataFusionError>>> {
        let total_time = self.semijoin_metrics.total_time.timer();
        let n_children = self.materialized_children_futs.len();

        let result = if n_children == 0 {
            poll_next_leaf(&mut self.guard_stream, &self.semijoin_metrics, cx)
        } else if n_children == 1 {
            let child = &mut self.materialized_children_futs[0];
            poll_next_single_semijoin(
                &mut self.guard_stream,
                child,
                &self.semijoin_keys[0],
                &mut self.hashes_buffer,
                &self.schema,
                &self.semijoin_metrics,
                cx,
            )
        } else {
            // two or more children (we are not a leaf, so ...)
            poll_next_multi_semijoin(
                &mut self.guard_stream,
                &mut self.materialized_children_futs,
                &self.semijoin_keys,
                &mut self.hashes_buffer,
                &self.schema,
                cx,
                &self.semijoin_metrics,
                &mut self.guard_batch_cache,
            )
        };

        total_time.done();
        result
    }
}

/// Create the keys for the semijoin operation.
/// `semijoin_on` is a slice of indices of the guard columns that form a lookup key in the GroupBy child.
/// The keys are stored in the `keys` vector.
#[inline]
fn create_keys(guard_batch: &RecordBatch, semijoin_on: &[usize], keys: &mut Vec<ArrayRef>) {
    keys.clear();
    for &col_idx in semijoin_on {
        keys.push(guard_batch.column(col_idx).clone());
    }
}

#[cfg(test)]
mod tests {

    use std::error::Error;

    use datafusion::{
        arrow::{
            array::{Int8Array, UInt8Array},
            datatypes::{DataType, Field, Schema},
            error::ArrowError,
        },
        physical_plan::memory::MemoryExec,
    };

    use super::*;

    /// | a | b  | c |
    /// | - | -- | - |
    /// | 1 | 1  | 1 |
    /// | 1 | 2  | 2 |
    /// | 1 | 3  | 3 |
    /// | 1 | 4  | 4 |
    /// | 1 | 5  | 5 |
    /// | 1 | 6  | 1 |
    /// | 1 | 7  | 2 |
    /// | 1 | 8  | 3 |
    /// | 1 | 9  | 4 |
    /// | 1 | 10 | 5 |
    fn example_batch() -> Result<RecordBatch, ArrowError> {
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::Int8, false),
            Field::new("c", DataType::UInt8, false),
        ]));
        let a = UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);
        let b = Int8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
        let c = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
        RecordBatch::try_new(schema.clone(), vec![Arc::new(a), Arc::new(b), Arc::new(c)])
    }

    /// | a | b  | c |
    /// | - | -- | - |
    /// | 1 | 1  | 1 |
    /// | 1 | 2  | 2 |
    /// | 1 | 3  | 3 |
    /// | 1 | 4  | 4 |
    /// | 1 | 5  | 5 |
    /// | 1 | 6  | 1 |
    /// | 1 | 7  | 2 |
    /// | 1 | 8  | 3 |
    /// | 1 | 9  | 4 |
    /// | 1 | 10 | 5 |
    fn example_guard() -> Result<Arc<dyn ExecutionPlan>, DataFusionError> {
        let batch = example_batch()?;
        let schema = batch.schema();
        let partition = vec![batch];
        Ok(Arc::new(MemoryExec::try_new(&[partition], schema, None)?))
    }

    /// Groupby R(a,b,c) on `groupby_cols`
    fn example_child(group_columns: Vec<usize>) -> Result<Arc<GroupBy>, DataFusionError> {
        let leaf = MultiSemiJoin::new(example_guard()?, vec![], vec![]);
        let groupby = GroupBy::new(leaf, group_columns);
        Ok(Arc::new(groupby))
    }

    /// MultiSemiJoin::new with valid equijoin keys.
    /// Should not panic
    #[test]
    fn test_multisemijoin_new() {
        // R(a,b,c)
        let guard = example_guard().unwrap();
        // R(a,b,c) groupby a
        let child_a = example_child(vec![0]).unwrap();
        // R(a,b,c) groupby (a,b)
        let child_ab = example_child(vec![0, 1]).unwrap();

        let _semijoin = MultiSemiJoin::new(guard.clone(), vec![child_a], vec![vec![(0, 0)]]);
        let _semijoin = MultiSemiJoin::new(guard, vec![child_ab], vec![vec![(0, 0), (1, 1)]]);
    }

    /// MultiSemiJoin::new with invalid equijoin keys.
    /// Two relations are equijoined on columns of different types
    #[test]
    #[should_panic]
    fn test_multisemijoin_invalid_keys() {
        // R(a,b,c)
        // Schema of guard: {a: u8, b: i8, c: u8}
        let guard = example_guard().unwrap();
        // R(a,b,c) groupby a
        // Schema of child: {a: u8}
        let child = example_child(vec![0]).unwrap();

        let _semijoin = MultiSemiJoin::new(guard, vec![child], vec![vec![(1, 0)]]);
    }

    /// MultiSemiJoin::new with invalid equijoin keys.
    /// Key invalid because out of bounds
    #[test]
    #[should_panic]
    fn test_multisemijoin_equijoin_key_out_of_bounds() {
        // R(a,b,c)
        // Schema of guard: {a: u8, b: i8, c: u8}
        let guard = example_guard().unwrap();
        // R(a,b,c) groupby a
        // Schema of child: {a: u8}
        let child = example_child(vec![0]).unwrap();

        let _semijoin = MultiSemiJoin::new(guard, vec![child], vec![vec![(0, 1)]]);
    }

    /// Test unary multisemijoin (leaf node)
    #[tokio::test]
    async fn test_unary_semijoin() -> Result<(), Box<dyn Error>> {
        // R(a,b,c)
        // Schema of guard: {a: u8, b: i8, c: u8}
        let guard = example_guard().unwrap();

        let semijoin = MultiSemiJoin::new(guard, vec![], vec![]);
        let result = semijoin.execute(0, Arc::new(TaskContext::default()))?;

        let batches = result
            .collect::<Vec<Result<SemiJoinResultBatch, DataFusionError>>>()
            .await;

        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();
        match batch {
            SemiJoinResultBatch::Flat(b) => assert_eq!(b, &example_batch().unwrap()),
            SemiJoinResultBatch::Nested(_) => panic!("Expected a flat batch"),
        }

        Ok(())
    }

    /// Test binary semijoin (single equijoin key).
    /// Special case: cartesian product
    #[tokio::test]
    async fn test_cartesian_prod_single_key() -> Result<(), Box<dyn Error>> {
        // R(a,b,c)
        let guard = example_guard()?;
        // R(a,b,c) groupby a
        let child_a = example_child(vec![0])?;

        let semijoin = MultiSemiJoin::new(guard.clone(), vec![child_a], vec![vec![(0, 0)]]);
        let result = semijoin.execute(0, Arc::new(TaskContext::default()))?;

        let batches = result
            .collect::<Vec<Result<SemiJoinResultBatch, DataFusionError>>>()
            .await;

        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();
        match batch {
            SemiJoinResultBatch::Flat(_) => panic!("Expected a nested batch"),
            SemiJoinResultBatch::Nested(nested_batch) => {
                // The guard batch has 10 rows
                assert_eq!(nested_batch.num_rows(), 10);
                // Each row has weight 10 (it joins with 10 other tuples)
                nested_batch
                    .total_weights()
                    .iter()
                    .for_each(|w| assert_eq!(*w, 10));
                // Next vector is none because top-level
                let inner = &nested_batch.inner;
                assert!(inner.next.is_none());
                // The nested batch has 1 nested column
                assert_eq!(nested_batch.schema().nested_fields.len(), 1);
                let nested_col = nested_batch.nested_column(0).as_non_singular();
                // All hols point to the same group
                nested_col.hols.iter().for_each(|hol| assert_eq!(*hol, 10));
            }
        }

        Ok(())
    }

    /// Test binary semijoin (equijoin on 2 columns)
    /// (1-1 relationship) -> Each tuple in the guard joins with exactly one tuple in child.
    #[tokio::test]
    async fn test_binary_semijoin_2keycols() -> Result<(), Box<dyn Error>> {
        // R1(a,b,c)
        let guard = example_guard()?;
        // R2(a,b,c) groupby a,b
        let child_a = example_child(vec![0, 1])?;

        let semijoin = MultiSemiJoin::new(guard.clone(), vec![child_a], vec![vec![(0, 0), (1, 1)]]);
        let result = semijoin.execute(0, Arc::new(TaskContext::default()))?;

        let batches = result
            .collect::<Vec<Result<SemiJoinResultBatch, DataFusionError>>>()
            .await;

        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();
        match batch {
            SemiJoinResultBatch::Flat(_) => panic!("Expected a nested batch"),
            SemiJoinResultBatch::Nested(nested_batch) => {
                // The guard batch has 10 rows
                assert_eq!(nested_batch.num_rows(), 10);
                // Each row has weight 1 (it joins with 1 other tuple)
                nested_batch
                    .total_weights()
                    .iter()
                    .for_each(|w| assert_eq!(*w, 1));
                // Next vector is none because top-level
                let inner = &nested_batch.inner;
                assert!(inner.next.is_none());
                // The nested batch has 1 nested column
                assert_eq!(nested_batch.schema().nested_fields.len(), 1);
                let nested_col = nested_batch.nested_column(0).as_non_singular();
                // All hols point to another group
                nested_col
                    .hols
                    .iter()
                    .enumerate()
                    .for_each(|(i, hol)| assert_eq!(*hol as usize - 1, i));
            }
        }

        Ok(())
    }

    /// Test binary semijoin (equijoin on 4 columns)
    /// (1-1 relationship) -> Each tuple in the guard joins with exactly one tuple in child.
    #[tokio::test]
    async fn test_binary_semijoin_multikeycols() -> Result<(), Box<dyn Error>> {
        let example_batch = || {
            let schema = Arc::new(Schema::new(vec![
                Field::new("a", DataType::UInt8, false),
                Field::new("b", DataType::UInt8, false),
                Field::new("c", DataType::UInt8, false),
                Field::new("d", DataType::UInt8, false),
                Field::new("e", DataType::UInt8, false),
            ]));
            let a = UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);
            let b = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
            let c = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
            let d = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
            let e = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
            let batch = RecordBatch::try_new(
                schema.clone(),
                vec![
                    Arc::new(a),
                    Arc::new(b),
                    Arc::new(c),
                    Arc::new(d),
                    Arc::new(e),
                ],
            )
            .unwrap();
            batch
        };

        let batch = example_batch();
        let schema = batch.schema();
        let memoryexec = Arc::new(MemoryExec::try_new(&[vec![batch]], schema, None).unwrap());
        let input = MultiSemiJoin::new(memoryexec.clone(), vec![], vec![]);

        // GroupBy on columns "a", "b", "c", "d"
        let groupby = Arc::new(GroupBy::new(input, vec![0, 1, 2, 3]));

        let semijoin = MultiSemiJoin::new(
            memoryexec,
            vec![groupby],
            vec![vec![(0, 0), (1, 1), (2, 2), (3, 3)]],
        );
        let result = semijoin.execute(0, Arc::new(TaskContext::default()))?;

        let batches = result
            .collect::<Vec<Result<SemiJoinResultBatch, DataFusionError>>>()
            .await;

        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();

        match batch {
            SemiJoinResultBatch::Flat(_) => panic!("Expected a nested batch"),
            SemiJoinResultBatch::Nested(nested_batch) => {
                // The guard batch has 10 rows
                assert_eq!(nested_batch.num_rows(), 10);
                // Each row has weight 1 (it joins with 1 other tuple)
                nested_batch
                    .total_weights()
                    .iter()
                    .for_each(|w| assert_eq!(*w, 1));
                // Next vector is none because top-level
                let inner = &nested_batch.inner;
                assert!(inner.next.is_none());
                // The nested batch has 1 nested column
                assert_eq!(nested_batch.schema().nested_fields.len(), 1);
                let nested_col = nested_batch.nested_column(0).as_non_singular();
                // All hols point to another group
                nested_col
                    .hols
                    .iter()
                    .enumerate()
                    .for_each(|(i, hol)| assert_eq!(*hol as usize - 1, i));
            }
        }

        Ok(())
    }

    /// Test binary semijoin (equijoin on NO columns).
    /// This is basically a cartesian product, followed by a projection on the LHS of the semijoin.
    #[tokio::test]
    async fn binary_semijoin_no_key_cols() -> Result<(), Box<dyn Error>> {
        // R(a,b,c)
        let guard = example_guard()?;
        // R(a,b,c) groupby {}
        let child_a = example_child(vec![])?;

        let semijoin = MultiSemiJoin::new(guard.clone(), vec![child_a], vec![vec![]]);
        let result = semijoin.execute(0, Arc::new(TaskContext::default()))?;

        let batches = result
            .collect::<Vec<Result<SemiJoinResultBatch, DataFusionError>>>()
            .await;

        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();
        match batch {
            SemiJoinResultBatch::Flat(_) => panic!("Expected a nested batch"),
            SemiJoinResultBatch::Nested(nested_batch) => {
                // The result batch has 10 rows
                assert_eq!(nested_batch.num_rows(), 10);
                // Each row has weight 10 (it joins with 10 other tuples)
                nested_batch
                    .total_weights()
                    .iter()
                    .for_each(|w| assert_eq!(*w, 10));
                // Next vector is none because top-level
                let inner = &nested_batch.inner;
                assert!(inner.next.is_none());
                // The nested batch has 1 nested column
                assert_eq!(nested_batch.schema().nested_fields.len(), 1);
                let nested_col = nested_batch.nested_column(0).as_non_singular();
                // All hols point to the same group
                nested_col.hols.iter().for_each(|hol| assert_eq!(*hol, 10));
            }
        }

        Ok(())
    }
}
