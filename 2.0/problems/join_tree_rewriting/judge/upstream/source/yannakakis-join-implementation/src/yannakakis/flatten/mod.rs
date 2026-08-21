//! The flatten operator, which is used to flatten a nested relation.

// TODO: in a second step, we can also implement here flattening not all but a subset of the columns (corresponding to a non-full join)

mod flatten_binary;
mod flatten_default;
pub mod metrics;

use datafusion::arrow::array::Array;
use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::datatypes::SchemaRef;
use datafusion::arrow::error::ArrowError;
use datafusion::error::DataFusionError;
use datafusion::error::Result;
use datafusion::execution::SendableRecordBatchStream;
use datafusion::execution::TaskContext;
use datafusion::physical_plan::metrics::ExecutionPlanMetricsSet;
use datafusion::physical_plan::metrics::MetricsSet;
use datafusion::physical_plan::stream::RecordBatchStreamAdapter;
use datafusion::physical_plan::DisplayAs;
use datafusion::physical_plan::DisplayFormatType;
use datafusion::physical_plan::Distribution;
use datafusion::physical_plan::ExecutionPlan;
use futures::StreamExt;
use metrics::FlattenMetrics;
use std::sync::Arc;

use crate::take::weighted_u32::take_weighted;
use crate::yannakakis::data::Idx;
use crate::yannakakis::multisemijoin::SendableSemiJoinResultBatchStream;
use crate::yannakakis::util::write_metrics_as_json;

use super::data::Weight;
use super::multisemijoin::MultiSemiJoin;
use super::schema::YannakakisSchema;

#[derive(Debug)]
pub struct Flatten {
    /// the operator that computes the [SemijoinResultBatch]s to flatten
    child: Arc<MultiSemiJoin>,

    /// contains the flattened output schema
    schema: Arc<YannakakisSchema>,

    /// execution metrics
    metrics: ExecutionPlanMetricsSet,

    alternative: bool,
}

impl Flatten {
    /// Creates a new Flatten operator.
    pub fn new(child: Arc<MultiSemiJoin>) -> Self {
        // let schema = Arc::new(child.schema().flatten());
        let schema = Arc::new(YannakakisSchema::new(child.as_ref()));
        Self {
            child,
            schema,
            metrics: ExecutionPlanMetricsSet::new(),
            alternative: false,
        }
    }

    /// Creates a new Flatten operator with alternative unnesting.
    pub fn new_alternative(child: Arc<MultiSemiJoin>) -> Self {
        // let schema = Arc::new(child.schema().flatten());
        let schema = Arc::new(YannakakisSchema::new(child.as_ref()));
        Self {
            child,
            schema,
            metrics: ExecutionPlanMetricsSet::new(),
            alternative: true,
        }
    }

    pub fn metrics(&self) -> MetricsSet {
        self.metrics.clone_inner()
    }

    /// Get a JSON representation of the Flatten node and all its descendants ([MultiSemiJoin] & [GroupBy]), including their metrics.
    /// The JSON representation is a string, without newlines
    pub fn as_json(&self) -> Result<String, std::fmt::Error> {
        use std::fmt::Write;

        let mut output = String::with_capacity(5000);

        write!(output, "{{ \"operator\": \"Flatten\"")?;
        write_metrics_as_json(&Some(self.metrics()), &mut output)?;

        write!(output, ", \"children\": [")?;
        self.child.as_json(&mut output)?;

        write!(output, "]}}")?;

        Ok(output)
    }

    /// Collect metrics from the Flatten node, and all its descendants ([MultiSemiJoin] & [GroupBy]).
    /// Returns a pretty-printed string of the collected metrics.
    pub fn collect_metrics(&self) -> Result<String, std::fmt::Error> {
        use std::fmt::Write;

        let mut output_buffer = String::with_capacity(1000);

        writeln!(
            output_buffer,
            "[FLATTEN] {}",
            self.metrics.clone_inner().to_string()
        )?;

        self.child.collect_metrics(&mut output_buffer, 4);

        Ok(output_buffer)
    }
}

impl DisplayAs for Flatten {
    fn fmt_as(
        &self,
        t: datafusion::physical_plan::DisplayFormatType,
        f: &mut std::fmt::Formatter,
    ) -> std::fmt::Result {
        match t {
            DisplayFormatType::Default | DisplayFormatType::Verbose => {
                write!(f, "Flatten")
            }
        }
    }
}

impl ExecutionPlan for Flatten {
    fn as_any(&self) -> &dyn std::any::Any {
        self
    }

    fn schema(&self) -> SchemaRef {
        self.schema.output_schema()
    }

    fn required_input_distribution(&self) -> Vec<Distribution> {
        // We are currently single-threaded.
        let n_children = self.children().len();
        vec![Distribution::SinglePartition; n_children]
    }

    fn output_partitioning(&self) -> datafusion::physical_plan::Partitioning {
        self.child.guard().output_partitioning()
    }

    fn output_ordering(&self) -> Option<&[datafusion::physical_expr::PhysicalSortExpr]> {
        None
    }

    fn children(&self) -> Vec<Arc<dyn ExecutionPlan>> {
        fn children_recursive(
            node: &MultiSemiJoin,
            children_buffer: &mut Vec<Arc<dyn ExecutionPlan>>,
        ) {
            children_buffer.push(node.guard().clone());
            for grand_child in node.children() {
                children_recursive(grand_child.child(), children_buffer);
            }
        }

        let mut children: Vec<Arc<dyn ExecutionPlan>> = Vec::new();
        children_recursive(&self.child, &mut children);
        children
    }

    fn with_new_children(
        self: Arc<Self>,
        children: Vec<Arc<dyn ExecutionPlan>>,
    ) -> datafusion::error::Result<Arc<dyn ExecutionPlan>> {
        todo!()
    }

    fn execute(
        &self,
        partition: usize,
        context: Arc<TaskContext>,
    ) -> Result<SendableRecordBatchStream, DataFusionError> {
        let metrics = FlattenMetrics::new(partition, &self.metrics);

        // Get stream of SemiJoinResultBatches
        let batches = self.child.execute(partition, context)?;
        let yann_schema = &self.schema;

        // Flatten each batch, resulting in a stream of RecordBatches
        flatten_batches(batches, yann_schema.clone(), metrics, self.alternative)
    }
}

/// Maps a stream of [SemiJoinResultBatch]es to a stream of [RecordBatch]es by flattening each batch.
#[inline(always)]
fn flatten_batches(
    batches: SendableSemiJoinResultBatchStream,
    output_schema: Arc<YannakakisSchema>, // the *flat* output schema
    metrics: FlattenMetrics,
    alternative: bool,
) -> Result<SendableRecordBatchStream, DataFusionError> {
    let schema = output_schema.clone(); // clone for usage after closure

    if output_schema.all_multisemijoins_unary_or_binary() {
        // Use specialized Flatten implementation that only works for unary or binary multisemijoins
        let stream = batches
            .map(move |batch| flatten_binary::flatten_batch(batch?, &output_schema, &metrics));
        return Ok(Box::pin(RecordBatchStreamAdapter::new(
            schema.output_schema(),
            stream,
        )));
    } else if alternative {
        // Use alternative variant of default Flatten implementation
        unimplemented!("No alternative variant available");
    } else {
        // Use default Flatten implementation
        let stream = batches
            .map(move |batch| flatten_default::flatten_batch(batch?, &output_schema, &metrics));
        return Ok(Box::pin(RecordBatchStreamAdapter::new(
            schema.output_schema(),
            stream,
        )));
    }
}

////////////////////////////////////////////////////////////////////////////////////////////////////
//                                             UTIL                                               //
////////////////////////////////////////////////////////////////////////////////////////////////////

/// Take values from an [Array] using the given `weights`.
/// `output_size` should be the sum of all `weights`.
/// For performance reasons, it is the caller's responsibility to ensure that output_size is correct.
///
/// # Panics
/// If values.len() != weights.len().
#[inline(always)]
fn take_all_weighted(
    values: &dyn Array,
    weights: &[Weight],
    output_size: usize,
) -> Result<ArrayRef, ArrowError> {
    debug_assert_eq!(values.len(), weights.len());
    // No row_ids are needed!
    let row_ids: Vec<Idx> = (0..weights.len() as Idx).collect();
    take_weighted(values, &row_ids, weights, output_size)
}

#[cfg(test)]
mod tests {
    use std::error::Error;

    use datafusion::{
        arrow::{
            array::{RecordBatch, UInt8Array},
            datatypes::{DataType, Field, Schema},
            error::ArrowError,
        },
        physical_plan::{empty::EmptyExec, memory::MemoryExec},
    };

    use crate::yannakakis::groupby::GroupBy;

    use super::*;

    #[tokio::test]
    /// Test case: no children.
    /// The output should be the same as the input (i.e., the guard).
    async fn no_children() -> Result<(), DataFusionError> {
        let guard = example_guard()?;
        let multisemijoin = MultiSemiJoin::new(guard, vec![], vec![]);
        let root = Flatten::new(Arc::new(multisemijoin));

        // Execute the plan
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let stream = root.execute(0, context)?;

        let batches = stream
            .collect::<Vec<Result<RecordBatch, DataFusionError>>>()
            .await;

        assert_eq!(batches.len(), 1);
        assert!(batches[0].is_ok());
        let batch = batches[0].as_ref().unwrap();
        assert_eq!(*batch, example_batch()?);

        Ok(())
    }

    #[tokio::test]
    /// Test case: empty input (because guard is an empty stream)
    async fn empty_input_empty_stream() -> Result<(), DataFusionError> {
        // empty guard with schema {a,b}
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
        ]));
        let guard = Arc::new(EmptyExec::new(schema.clone()));

        // R(a,b,c) groupby a
        // nested schema = {a,{b,c}}}
        let child = example_child(vec![0])?;

        // MultiSemijoin node with empty guard
        let multisemijoin = MultiSemiJoin::new(guard, vec![child], vec![vec![(0, 0)]]);
        let root = Flatten::new(Arc::new(multisemijoin));

        // Expected output schema
        // {a,b,{b,c}}
        let output_schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
            Field::new("a", DataType::UInt8, false), // joining column: duplicate of first field
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
        ]));

        // Execute the plan
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let stream = root.execute(0, context)?;

        assert_eq!(stream.schema(), output_schema.clone());

        // Check that the stream contains no batches
        let batches: Vec<Result<RecordBatch, DataFusionError>> = stream.collect().await;

        assert!(batches.is_empty());

        Ok(())
    }

    #[tokio::test]
    /// Test case: empty input (guard stream contains 1 batch with 0 rows)
    async fn empty_input_single_batch() -> Result<(), DataFusionError> {
        // guard batch with 0 rows
        let guard_schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
        ]));
        let empty_batch = RecordBatch::new_empty(guard_schema.clone());
        let guard = Arc::new(MemoryExec::try_new(
            &vec![vec![empty_batch]],
            guard_schema.clone(),
            None,
        )?);

        // R(a,b,c) groupby a
        // nested schema = {a,{b,c}}}
        let child = example_child(vec![0])?;

        // MultiSemijoin node with empty guard
        let multisemijoin = MultiSemiJoin::new(guard, vec![child], vec![vec![(0, 0)]]);
        let root = Flatten::new(Arc::new(multisemijoin));

        // expected output schema
        let output_schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
            Field::new("a", DataType::UInt8, false), // joining column: duplicate of first field
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
        ]));

        // Execute the plan
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let stream = root.execute(0, context).unwrap();
        assert_eq!(stream.schema(), output_schema.clone());
        let batches: Vec<Result<RecordBatch, DataFusionError>> = stream.collect().await;

        // Check that the stream contains one batch with 0 rows

        assert_eq!(batches.len(), 1);
        batches[0].as_ref().unwrap();
        assert!(batches[0].is_ok());
        let batch = batches[0].as_ref().unwrap();
        assert_eq!(batch.num_rows(), 0);
        assert_eq!(batch.schema(), output_schema);

        Ok(())
    }

    #[tokio::test]
    /// Test case: binary join with one guard batch and one child batch.
    /// 1-1 relationship between guard and child.
    /// 2 key columns
    async fn binary_join_single_batch() -> Result<(), Box<dyn Error>> {
        // Guard with 1 batch
        let guard = example_guard()?;

        // R(a,b,c) groupby a,b
        // Such that each guard tuple matches with exactly one child tuple.
        // i.e, 1-1 relationship.
        let child = example_child(vec![0, 1]).unwrap();

        // Create semijoin & flatten nodes
        let multisemijoin = Arc::new(MultiSemiJoin::new(
            guard,
            vec![child],
            vec![vec![(0, 0), (1, 1)]],
        ));
        let output_schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
            Field::new("a", DataType::UInt8, false), // joining column: duplicate of first field
            Field::new("b", DataType::UInt8, false), // joining column: duplicate of second field
            Field::new("c", DataType::UInt8, false),
        ]));

        let root = Flatten::new(multisemijoin.clone());

        // Execute the plan
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let stream = root.execute(0, context).unwrap();
        assert_eq!(stream.schema(), output_schema.clone());
        let batches: Vec<Result<RecordBatch, DataFusionError>> = stream.collect().await;

        // Check that the stream contains 1 batch with correct schema
        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();
        assert_eq!(batch.schema(), output_schema);

        // Check that the output is correct
        let a = Arc::new(UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]));
        let b = Arc::new(UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]));
        let c = Arc::new(UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]));
        let expected_batch = RecordBatch::try_new(
            output_schema.clone(),
            vec![a.clone(), b.clone(), c.clone(), a, b, c],
        )
        .unwrap();
        assert_eq!(batch, &expected_batch);

        Ok(())
    }

    #[tokio::test]
    /// Test case: same as `binary_join_single_batch` , but with multiple batches.
    async fn multiple_batches() -> Result<(), Box<dyn Error>> {
        // Guard with 2 batches
        let guard_batches = vec![example_batch()?, example_batch()?];
        let guard = Arc::new(MemoryExec::try_new(
            &vec![guard_batches],
            example_batch()?.schema(),
            None,
        )?);

        // R(a,b,c) groupby a,b
        // Such that each guard tuple matches with exactly one child tuple.
        // i.e, 1-1 relationship.
        let child = example_child(vec![0, 1]).unwrap();

        // Create semijoin & flatten nodes
        let multisemijoin = MultiSemiJoin::new(guard, vec![child], vec![vec![(0, 0), (1, 1)]]);
        let output_schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
            Field::new("a", DataType::UInt8, false), // joining column: duplicate of first field
            Field::new("b", DataType::UInt8, false), // joining column: duplicate of second field
            Field::new("c", DataType::UInt8, false),
        ]));

        let root = Flatten::new(Arc::new(multisemijoin));

        // Execute the plan
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let stream = root.execute(0, context).unwrap();
        assert_eq!(stream.schema(), output_schema.clone());
        let batches: Vec<Result<RecordBatch, DataFusionError>> = stream.collect().await;

        // Check that the stream contains 2 batches with correct schema
        assert_eq!(batches.len(), 2);
        for batch in batches.iter() {
            let batch = batch.as_ref().unwrap();
            assert_eq!(batch.schema(), output_schema);
        }

        // Check that the output is correct
        let a = Arc::new(UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]));
        let b = Arc::new(UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]));
        let c = Arc::new(UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]));
        let expected_batch = RecordBatch::try_new(
            output_schema.clone(),
            vec![a.clone(), b.clone(), c.clone(), a, b, c],
        )
        .unwrap();
        for batch in batches {
            assert_eq!(batch?, expected_batch);
        }

        Ok(())
    }

    #[tokio::test]
    /// Test ternary join
    /// (1-1 relationships) -> Each tuple in the guard yields 1 output tuple.
    /// Join on 1 key column
    async fn test_ternary_semijoin() -> Result<(), Box<dyn Error>> {
        // Join R2 with R3 on b
        // Resulting schema: {a,b,c,{a,c}}
        let r2 = example_guard()?;
        let r3 = example_child(vec![1])?;
        let semijoin_23 = MultiSemiJoin::new(r2, vec![r3], vec![vec![(1, 0)]]);

        // Join R1 with (R2 join R3) on b
        // Resulting schema:  {a,b,c,{a,c,{a,c}}}
        let r1 = example_guard()?;
        let r1_r2_r3 = MultiSemiJoin::new(
            r1,
            vec![Arc::new(GroupBy::new(semijoin_23, vec![1]))], // Groupby (R2 join R3) on b
            vec![vec![(1, 0)]],
        );

        let root = Flatten::new(Arc::new(r1_r2_r3));

        let output_schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false), // joining column: duplicate of second field
            Field::new("c", DataType::UInt8, false),
            Field::new("a", DataType::UInt8, false),
            Field::new("b", DataType::UInt8, false), // joining column: duplicate of second field
            Field::new("c", DataType::UInt8, false),
        ]));

        // Execute the plan
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let stream = root.execute(0, context).unwrap();
        assert_eq!(stream.schema(), output_schema.clone());
        let batches: Vec<Result<RecordBatch, DataFusionError>> = stream.collect().await;

        // Check that the stream contains 1 batch with correct schema
        assert_eq!(batches.len(), 1);
        let batch = batches[0].as_ref().unwrap();
        assert_eq!(batch.schema(), output_schema);

        // Check that the output is correct
        let a = Arc::new(UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]));
        let b = Arc::new(UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]));
        let c = Arc::new(UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]));
        let expected_batch = RecordBatch::try_new(
            output_schema.clone(),
            vec![
                a.clone(),
                b.clone(),
                c.clone(),
                a.clone(),
                b.clone(),
                c.clone(),
                a,
                b,
                c,
            ],
        )?;
        assert_eq!(batch, &expected_batch);

        let metrics = root.collect_metrics()?;
        println!("{}", metrics);

        let json_metrics = root.as_json()?;
        println!("{}", json_metrics);

        Ok(())
    }

    // #[tokio::test]
    // /// Test quaternary join
    // /// (1-1 relationships) -> Each tuple in the guard yields 1 output tuple.
    // async fn test_quaternary_join() {
    //     let batch = || {
    //         let schema = Arc::new(Schema::new(vec![
    //             Field::new("a", DataType::UInt8, false),
    //             Field::new("b", DataType::UInt8, false),
    //             Field::new("c", DataType::UInt8, false),
    //         ]));
    //         let a = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    //         let b = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    //         let c = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    //         RecordBatch::try_new(schema.clone(), vec![Arc::new(a), Arc::new(b), Arc::new(c)])
    //             .unwrap()
    //     };

    //     let mut rels = Vec::with_capacity(4);
    //     for _ in 0..4 {
    //         rels.push(Arc::new(
    //             MemoryExec::try_new(&[vec![batch()]], batch().schema(), None).unwrap(),
    //         ));
    //     }

    //     let mut node = MultiSemiJoin::new(rels.pop().unwrap(), vec![], vec![]);
    //     for rel in rels.into_iter().rev() {
    //         let groupby = Arc::new(GroupBy::new(node, vec![0]));
    //         node = MultiSemiJoin::new(rel, vec![groupby], vec![vec![(0, 0)]]);
    //     }

    //     let physical_node = YannakakisFullJoinExec::new(node).unwrap();

    //     let context: Arc<TaskContext> = Arc::new(TaskContext::default());
    //     let stream = physical_node.execute(0, context).unwrap();
    //     let batches = stream
    //         .collect::<Vec<Result<RecordBatch, DataFusionError>>>()
    //         .await
    //         .iter()
    //         .map(|b| b.as_ref().unwrap().clone())
    //         .collect::<Vec<_>>();

    //     assert_eq!(batches.len(), 1);
    //     let batch = &batches[0];
    //     assert!(batch.columns().iter().all(|col| col.len() == 10));
    // }

    // ---------------------------------------------------------
    // HELPER FUNCTIONS BELOW
    // ---------------------------------------------------------

    /// UInt8, UInt8, UInt8
    ///
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
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
        ]));
        let a = UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);
        let b = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
        let c = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
        RecordBatch::try_new(schema.clone(), vec![Arc::new(a), Arc::new(b), Arc::new(c)])
    }

    /// R(a,b,c) with 1 batch
    ///
    /// all columns are UInt8
    ///
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

    // #[test]
    // fn test_fill_repeat() {
    //     let mut buffer = vec![0; 3];
    //     let items = vec![1, 2, 3];
    //     fill_repeat(&mut buffer, items.iter().cloned());
    //     assert_eq!(buffer, vec![1, 2, 3]);

    //     let mut buffer = vec![0; 9];
    //     let items = vec![1, 2, 3];
    //     fill_repeat(&mut buffer, items.iter().cloned());
    //     assert_eq!(buffer, vec![1, 2, 3, 1, 2, 3, 1, 2, 3]);
    // }
}
