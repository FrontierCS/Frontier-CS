//! Implementation of the [GroupBy] operator.

pub mod grouped_rel;
pub mod metrics;

use futures::TryStreamExt;
use std::sync::Arc;

use ahash::RandomState;

use metrics::GroupByMetrics;

use datafusion::error::DataFusionError;
use datafusion::execution::TaskContext;
use datafusion::physical_plan::metrics::ExecutionPlanMetricsSet;
use datafusion::physical_plan::metrics::MetricsSet;

use crate::yannakakis::util::write_metrics_as_json;

use super::multisemijoin::MultiSemiJoin;

use super::data::GroupedRelRef;
use super::data::Idx;
use super::data::NestedColumn;
use super::data::NestedRel;
use super::data::NestedSchemaRef;
use super::data::NonSingularNestedColumn;
use super::data::SemiJoinResultBatch;
use super::data::SingularNestedColumn;
use super::data::Weight;

/// Operator that groups the result of a [MultiSemiJoin] on a given tuple of key columns.
#[derive(Debug)]
pub struct GroupBy {
    /// The child opertor node.
    child: MultiSemiJoin,

    /// The indexes of the regular columns in the child [MultiSemiJoin] schema that we will group by
    group_on: Vec<usize>,

    /// All the regular columns in the child [MultiSemiJoin] schema that are not part of the group_on columns.
    /// These columns will be logically 'nested' together in an additional NestedColumn, together with the nested_columns in `child.schema`
    nest_on: Vec<usize>,

    /// The output [NestedSchema] of the [GroupBy] operator.
    schema: NestedSchemaRef,

    /// Groupby execution metrics
    metrics: ExecutionPlanMetricsSet,
}

impl GroupBy {
    /// Create a new [`GroupBy`].
    /// `group_on` are the indexes of the *regular* columns in `child.schema()` that we want to group by.
    /// Grouping on any (possibly empty and not necessarily strict) subset of the regular fields is allowed.
    pub fn new(child: MultiSemiJoin, group_on: Vec<usize>) -> Self {
        let child_schema = child.schema();
        let number_of_regular_fields = child_schema.regular_fields.fields().len();

        // each index in group_on must refer to a valid regular field in the child's schema
        group_on.iter().for_each(|i| {
            if *i >= number_of_regular_fields {
                panic!("No such regular field to group on: {}", i);
            }
        });

        // indices of nested columns
        let nest_on: Vec<usize> = (0..number_of_regular_fields)
            .filter(|i| !group_on.contains(i))
            .collect();

        // Create the output [NestedSchema]
        let result_schema = child.schema().group_by(&group_on, &nest_on);
        let schema = Arc::new(result_schema);

        Self {
            child,
            group_on,
            nest_on,
            schema,
            metrics: ExecutionPlanMetricsSet::new(),
        }
    }

    /// Get the schema of the result after grouping,
    /// i.e, the schema of the key columns.
    pub fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    /// Get groupby input.
    pub fn child(&self) -> &MultiSemiJoin {
        &self.child
    }

    pub fn metrics(&self) -> MetricsSet {
        self.metrics.clone_inner()
    }

    /// Get a JSON representation of the GroupBy node and all its descendants ([MultiSemiJoin] & [GroupBy]), including their metrics.
    /// The JSON representation is a string, without newlines, and is appended to `output`.
    pub fn as_json(&self, output: &mut String) -> Result<(), std::fmt::Error> {
        use std::fmt::Write;

        write!(output, "{{ \"operator\": \"GROUPBY\"")?;
        write_metrics_as_json(&Some(self.metrics()), output)?;

        write!(output, ", \"children\": [")?;
        self.child.as_json(output)?;

        write!(output, "]}}")?;

        Ok(())
    }

    /// Collect metrics from this GroupBy node and all its descendants as a pretty-printed string.
    /// The string is appended to `output_buffer` with an indentation of `indent` spaces.
    pub fn collect_metrics(&self, output_buffer: &mut String, indent: usize) {
        use std::fmt::Write;

        (0..indent).for_each(|_| output_buffer.push(' '));

        writeln!(output_buffer, "[GROUPBY] {}", self.metrics())
            .expect("Failed to write groupby metrics to string.");

        self.child.collect_metrics(output_buffer, indent + 4);
    }

    /// Compute the result of the groupby operation.
    /// This is guaranteed to be linear in the size of the input MultiSemijoin relation.
    pub async fn materialize(
        &self,
        context: Arc<TaskContext>,
    ) -> Result<GroupedRelRef, DataFusionError> {
        // Init metrics and start timer
        let metrics = GroupByMetrics::new(0, &self.metrics);
        let materialize_timer = metrics.materialize_total_time.timer();

        let collect_timer = metrics.semijoin_collect_time.timer();

        // Execute child node
        let semijoin_stream = self.child.execute(0, context)?;

        // While collecting all batches from the semijoin stream:
        //      - Store all batches in a Vec
        //      - compute `total_rows`: the sum of all batch.num_rows()
        let (batches, total_rows) = semijoin_stream
            .try_fold((vec![], 0usize), |mut acc, batch| async move {
                acc.1 += batch.num_rows();
                acc.0.push(batch);
                Ok((acc.0, acc.1))
            })
            .await?;

        collect_timer.done();

        metrics.input_rows.add(total_rows);
        metrics.input_batches.add(batches.len());

        // Measure total time spent by grouping the input tuples
        let groupby_timer = metrics.groupby_time.timer();
        let mut grouped_rel_builder = init_grouped_rel_builder(
            &self.group_on,
            &self.schema,
            total_rows,
            RandomState::new(),
            false, //TODO: must be removed when flag is removed
        );
        grouped_rel_builder.build(&batches);
        //  end timer and save metrics
        groupby_timer.done();

        let nested_state_building_timer = metrics.nested_state_building_time.timer();
        let nested_column_schema = &self.schema.nested_fields[0]; // Guaranteed to be valid since the output schema has exactly one nested column
        let grouped_col_inner_data = if nested_column_schema.is_singular() {
            // When the resulting [GroupedRel] object is singular we do not need to concatenate
            // any of the non-group columns: those will never be needed.
            None
        } else if batches.len() == 0 {
            // Empty input, nothing needs to be concatenated
            Some(NestedRel::empty_no_next(nested_column_schema.clone()))
        } else {
            Some(create_nested_col_inner_data(
                &batches,
                &self.nest_on,
                nested_column_schema,
                total_rows,
                &metrics,
            ))
        };

        nested_state_building_timer.done();

        let result = grouped_rel_builder.finish(self.schema.clone(), grouped_col_inner_data, false);

        materialize_timer.done();

        Ok(result)
    }

    pub fn group_on(&self) -> &[usize] {
        &self.group_on
    }
}

/// The [GroupBy] operator creates a new [GroupedRel] object that has a single nested column.
/// This function creates the [NestedRel] that provides the data for this single nested column.
/// It does so by concatenating all the regular and non_regular columns that are being grouped
/// and makes a new [NestedRel] out of this.
///
/// Implementation note: the NestedRel that we return  does not yet have values for `next`. This is
/// intentional, as it will filled in by the GroupedRelBuilder::finish method.
fn create_nested_col_inner_data(
    batches: &[SemiJoinResultBatch],
    nest_on: &[usize],
    nested_column_schema: &NestedSchemaRef,
    total_rows: usize,
    metrics: &GroupByMetrics,
) -> NestedRel {
    let timer = metrics.concat_nested_columns_time.timer();

    // Implementation note: the old append implementation uses ArrayBuilders, in particular ArrayBuilder::append_slice.
    // As far as I can see, however, that is only valid if also the input data is non_null. (In other words, the old
    // implementation potentially turns NULLs into non-nulls).
    // In this new implementation, I have therefore reverted to arrow::compute::concat, which is what also the HashJoin uses.
    // This works for *any* kind of array (also string etc).

    // Regular columns that will now be nested need to be concatenated
    let mut regular_cols = Vec::with_capacity(nest_on.len());
    for i in 0..nest_on.len() {
        let array = datafusion::arrow::compute::concat(
            &batches
                .iter()
                .map(|batch| match batch {
                    SemiJoinResultBatch::Flat(record_batch) => {
                        record_batch.column(nest_on[i]).as_ref() // FIXED: nest_on[i] instead of i
                    }
                    SemiJoinResultBatch::Nested(nested_rel) => {
                        nested_rel.regular_column(nest_on[i]).as_ref() // FIXED: nest_on[i] instead of i
                    }
                })
                .collect::<Vec<_>>(),
        )
        .unwrap();
        regular_cols.push(array);
    }

    // The nested columns will be nested one level deeper; they also need to be concatenated
    let num_nested_cols = nested_column_schema.nested_fields.len();
    let mut nested_cols = Vec::with_capacity(num_nested_cols);
    for (i, nested_field_schema) in nested_column_schema.nested_fields.iter().enumerate() {
        let nested_col = if nested_field_schema.is_singular() {
            concat_singular_nested_columns(
                &batches
                    .iter()
                    .map(|batch| match batch {
                        SemiJoinResultBatch::Flat(_record_batch) => {
                            panic!("Expected input batch to have nested columns")
                        }
                        SemiJoinResultBatch::Nested(nested_batch) => {
                            nested_batch.nested_column(i).as_singular()
                        }
                    })
                    .collect::<Vec<_>>(),
                total_rows,
            )
        } else {
            // Non-singular nested columns need to be concatenated
            concat_non_singular_nested_columns(
                &batches
                    .iter()
                    .map(|batch| match batch {
                        SemiJoinResultBatch::Flat(_record_batch) => {
                            panic!("Expected input batch to have nested columns")
                        }
                        SemiJoinResultBatch::Nested(nested_rel) => {
                            nested_rel.nested_column(i).as_non_singular()
                        }
                    })
                    .collect::<Vec<_>>(),
                &nested_field_schema,
                total_rows,
            )
        };

        nested_cols.push(nested_col);
    }
    timer.done();

    // Create the NestedRel
    NestedRel::new_no_next(nested_column_schema.clone(), regular_cols, nested_cols)
}

/// Concatenate a slice of non-singular nested columns into one non-singular nested column
/// Assumes that all of the input [NonSingularNestedColumns] have the same inner [NestedRel]
/// `num_rows` is the total number of rows after concatenation
pub fn concat_non_singular_nested_columns(
    columns: &[&NonSingularNestedColumn],
    schema: &NestedSchemaRef,
    total_rows: usize,
) -> NestedColumn {
    if columns.is_empty() {
        // In the old implementation, we created a NonSingularNestedColumn without a next vector.
        // But I don't know why? It seems like it should have a next vector, because it is not top-level.
        return NestedColumn::NonSingular(NonSingularNestedColumn::empty_with_next(schema.clone()));
        // return NestedColumn::NonSingular(NonSingularNestedColumn::empty_old(schema.clone()));
    }

    // We may now assume it is non-empty therefore colums[0] is valid
    let data = columns[0].data.clone();
    let mut weights: Vec<Weight> = Vec::with_capacity(total_rows);
    for col in columns {
        weights.extend_from_slice(&col.weights);
    }
    let mut hols: Vec<Idx> = Vec::with_capacity(total_rows);
    for col in columns {
        hols.extend_from_slice(&col.hols);
    }

    NestedColumn::NonSingular(NonSingularNestedColumn {
        hols,
        weights,
        data,
    })
}

/// Concatenate a slice of singular nested columns into one singular nested column
pub fn concat_singular_nested_columns(
    columns: &[&SingularNestedColumn],
    total_rows: usize,
) -> NestedColumn {
    let mut weights: Vec<Weight> = Vec::with_capacity(total_rows);
    for col in columns {
        weights.extend_from_slice(&col.weights);
    }
    NestedColumn::Singular(SingularNestedColumn { weights })
}

/// Trait for building a [super::data::GroupedRel] object.
/// The [super::data::GroupedRel] object is the result of a [GroupBy] operator.
/// We have specialized implementations for single-key, double-key and more-than-double-key groupby columns.
pub trait GroupedRelBuilder {
    /// Group batches on key columns and update internal state.
    fn build(&mut self, batches: &[SemiJoinResultBatch]);

    /// Finish building: combine the build state in an actual [GroupedRel] object.
    /// `data` is Some(nested_data) if the GroupedRel to be constructed is non-singular;
    ///        in that case `nested_data` is the inner [NestedRel] of the NonSingularNestedColumn.
    ///        Initially, nested_data.next is None;  the builder is expected to fill in the correct values.
    /// `data` is None otherwise.
    /// TODO: remove use_alternative parameter is here for benchmarking purposes
    fn finish(
        &mut self,
        schema: NestedSchemaRef,
        grouped_col_inner_data: Option<NestedRel>,
        use_alternative: bool,
    ) -> GroupedRelRef;
}

pub type GroupedRelBuilderRef = Box<dyn GroupedRelBuilder>;

pub fn init_grouped_rel_builder(
    group_on: &[usize],
    grouped_schema: &NestedSchemaRef,
    capacity: usize,
    random_state: RandomState,
    flag: bool,
) -> GroupedRelBuilderRef {
    // we specialize the implementation based on the number of columns to group on.

    let is_singular = grouped_schema.nested_fields[0].is_singular();

    // Separate GroupedRelBuilders exist for the cases where the groupby columns are nullable.
    // (s.t. NullBuffers are only checked for nullable columns!)
    let nullable = grouped_schema
        .regular_fields
        .fields()
        .iter()
        .any(|f| f.is_nullable());

    if group_on.len() == 0 {
        return grouped_rel::none::make_builder(is_singular, flag);
    } else if group_on.len() == 1 {
        // Specialized implementation when there is only one key column
        // Faster than the generic (fallback) implementation

        let data_type = &grouped_schema.regular_fields.fields()[0].data_type();
        let group_on_col = group_on[0];
        if data_type.is_primitive() && !nullable {
            return grouped_rel::one::make_builder(
                data_type,
                group_on_col,
                is_singular,
                capacity,
                random_state,
                flag,
            );
        } else if data_type.is_primitive() && nullable {
            return grouped_rel::one_nullable::make_builder(
                data_type,
                group_on_col,
                is_singular,
                capacity,
                random_state,
                flag,
            );
        }
    } else if group_on.len() == 2 && !nullable {
        // Specialized implementation when there are two key columns
        // Faster than the generic (fallback) implementation
        let keys_schema = grouped_schema.regular_fields.fields();
        let (key1_datatype, key2_datatype) =
            (keys_schema[0].data_type(), keys_schema[1].data_type());
        let group_on_cols = (group_on[0], group_on[1]);
        if key1_datatype.is_primitive() && key2_datatype.is_primitive() {
            return grouped_rel::two::make_builder(
                key1_datatype,
                key2_datatype,
                group_on_cols,
                is_singular,
                capacity,
                random_state,
                flag,
            );
        }
    }

    // Fallback implementation for > 2 columns or non-primitive keys.

    if nullable {
        grouped_rel::default_nullable::make_builder(
            group_on.to_vec(),
            grouped_schema.regular_fields.clone(),
            is_singular,
            capacity,
            random_state,
            flag,
        )
    } else {
        grouped_rel::default::make_builder(
            group_on.to_vec(),
            grouped_schema.regular_fields.clone(),
            is_singular,
            capacity,
            random_state,
            flag,
        )
    }
}

#[cfg(test)]
mod tests {
    use std::error::Error;

    use datafusion::{
        arrow::{
            array::{RecordBatch, UInt8Array},
            datatypes::{DataType, Field, Schema, UInt8Type},
            error::ArrowError,
        },
        physical_plan::memory::MemoryExec,
    };
    use grouped_rel::{
        default::DefaultSingularGroupedRel, none::NoneNonSingularGroupedRel,
        one::OneKeyNonSingularGroupedRel, one_nullable::OneKeyNullableNonSingularGroupedRel,
        two::DoubleKeyNonSingularGroupedRel,
    };

    use crate::yannakakis::data::NestedSchema;

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
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
        ]));
        let a = UInt8Array::from(vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);
        let b = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
        let c = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
        RecordBatch::try_new(schema.clone(), vec![Arc::new(a), Arc::new(b), Arc::new(c)])
    }

    /// Single-batch MultiSemiJoin result
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
    fn example_input() -> Result<MultiSemiJoin, DataFusionError> {
        let batch = example_batch()?;
        let schema = batch.schema();
        let memoryexec = MemoryExec::try_new(&[vec![batch]], schema, None).unwrap();
        Ok(MultiSemiJoin::new(Arc::new(memoryexec), vec![], vec![]))
    }

    /// Test groupby::new() with valid group_columns
    #[test]
    fn test_groupby_new() -> Result<(), ArrowError> {
        let semijoin = example_input()?;
        let schema = semijoin.schema();

        let group_columns = vec![0];
        let nest_columns = vec![1, 2];
        let nest_schema = schema.regular_fields.project(&nest_columns)?;
        let nest_schema = NestedSchema::new(Arc::new(nest_schema), vec![]);
        let regular_fields = schema.regular_fields.project(&group_columns)?;

        // Groupby {a,b,c} on column "a"
        let groupby = GroupBy::new(semijoin, group_columns.clone());
        assert_eq!(groupby.group_on, group_columns);
        assert_eq!(groupby.nest_on, nest_columns);

        // Expected output schema: {a, {b,c}}
        let expected_schema =
            NestedSchema::new(Arc::new(regular_fields), vec![Arc::new(nest_schema)]);
        assert_eq!(groupby.schema().as_ref(), &expected_schema);

        Ok(())
    }

    /// Groupby on empty group_columns
    #[tokio::test]
    async fn test_groupby_empty_group_columns() -> Result<(), DataFusionError> {
        let semijoin = example_input()?;
        let schema = semijoin.schema();

        let group_columns = vec![];
        let nest_columns = vec![0, 1, 2];
        let nest_schema = schema.regular_fields.project(&nest_columns)?;
        let nest_schema = NestedSchema::new(Arc::new(nest_schema), vec![]);
        let regular_fields = schema.regular_fields.project(&group_columns)?;

        // Groupby {a,b,c} on {}
        let groupby = GroupBy::new(semijoin, group_columns.clone());
        assert_eq!(groupby.group_on, group_columns);
        assert_eq!(groupby.nest_on, nest_columns);

        // Expected output schema: {{ ,{a,b,c}}
        let expected_schema =
            NestedSchema::new(Arc::new(regular_fields), vec![Arc::new(nest_schema)]);
        assert_eq!(groupby.schema().as_ref(), &expected_schema);

        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<NoneNonSingularGroupedRel>()
            .unwrap();

        let expected_rows = example_batch()?.num_rows();
        assert_eq!(groupby_state.nrows as usize, expected_rows);
        assert_eq!(groupby_state.weight as usize, expected_rows); // Leaf: all rows have weight 1

        Ok(())
    }

    /// Groupby on column out of bounds
    #[test]
    #[should_panic]
    fn test_groupby_invalid_group_columns() {
        let semijoin = example_input().unwrap();

        // Groupby on column out of bounds
        GroupBy::new(semijoin, vec![4]); // should panic
    }

    /// Groupby on *all* columns.
    #[tokio::test]
    async fn test_groupby_all_columns() -> Result<(), DataFusionError> {
        let semijoin = example_input()?;
        let schema = semijoin.schema();

        let group_columns = vec![0, 1, 2];
        let nest_columns = vec![];
        let nest_schema = schema.regular_fields.project(&nest_columns)?;
        let nest_schema = NestedSchema::new(Arc::new(nest_schema), vec![]);
        let regular_fields = schema.regular_fields.project(&group_columns)?;

        // Groupby {a,b,c} on {a,b,c}
        let groupby = GroupBy::new(semijoin, group_columns.clone());
        assert_eq!(groupby.group_on, group_columns);
        assert_eq!(groupby.nest_on, nest_columns);

        // Expected output schema: {{a,b,c,{}}
        let expected_schema =
            NestedSchema::new(Arc::new(regular_fields), vec![Arc::new(nest_schema)]);
        assert_eq!(groupby.schema().as_ref(), &expected_schema);

        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<DefaultSingularGroupedRel>()
            .unwrap();

        let expected_groups = example_batch()?.num_rows();
        assert_eq!(groupby_state.map.len(), expected_groups);

        Ok(())
    }

    /// GroupBy 1 batch on 1 key column, where all rows end up in the same group.
    /// Groupby Keys are non-nullable!
    #[tokio::test]
    async fn test_groupby_single_key_single_group() -> Result<(), Box<dyn Error>> {
        let semijoin = example_input()?;

        // GroupBy on column "a" (a=1 for all rows)
        let groupby = GroupBy::new(semijoin, vec![0]);
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<OneKeyNonSingularGroupedRel<UInt8Type>>()
            .unwrap();

        // Test that all rows end up in the same group
        assert!(groupby_state.map.len() == 1);
        let next = groupby_state.data.next.as_deref();
        next.unwrap()
            .iter()
            .enumerate()
            .for_each(|(row_nr, next_ptr)| {
                assert_eq!(row_nr, *next_ptr as usize);
            });

        // Test that original columns are stored correctly
        let nested_cols = &groupby_state.data.regular_cols;
        assert!(nested_cols.len() == 2); // {b,c}
        assert_eq!(
            &nested_cols[1],
            example_batch()?.column(2),
            "c is not stored correctly"
        );
        assert_eq!(
            &nested_cols[0],
            example_batch()?.column(1),
            "b is not stored correctly"
        );

        Ok(())
    }

    /// GroupBy 1 batch on 1 key column, where all rows end up in the same group.
    /// Groupby key is nullable!
    #[tokio::test]
    async fn test_groupby_single_nullable_key_single_group() -> Result<(), Box<dyn Error>> {
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::UInt8, true),
            Field::new("b", DataType::UInt8, false),
            Field::new("c", DataType::UInt8, false),
        ]));
        let a = UInt8Array::from(vec![
            Some(1),
            Some(1),
            Some(1),
            Some(1),
            Some(1),
            None,
            None,
            None,
            None,
            None,
        ]);
        let b = UInt8Array::from(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
        let c = UInt8Array::from(vec![1, 2, 3, 4, 5, 1, 2, 3, 4, 5]);
        let batch =
            RecordBatch::try_new(schema.clone(), vec![Arc::new(a), Arc::new(b), Arc::new(c)])?;
        let memoryexec = MemoryExec::try_new(&[vec![batch.clone()]], schema, None)?;
        let semijoin = MultiSemiJoin::new(Arc::new(memoryexec), vec![], vec![]);

        // GroupBy on column "a" (a=1 for all rows)
        let groupby = GroupBy::new(semijoin, vec![0]);
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<OneKeyNullableNonSingularGroupedRel<UInt8Type>>()
            .unwrap();

        // Test that the first 5 rows are in the same group
        assert!(groupby_state.map.len() == 1);
        let next = groupby_state.data.next.as_deref();
        let next = &next.unwrap()[..5]; // Only the first 5 rows are in a group
        next.iter().enumerate().for_each(|(row_nr, next_ptr)| {
            assert_eq!(row_nr, *next_ptr as usize);
        });

        // Test that original columns are stored correctly
        let nested_cols = &groupby_state.data.regular_cols;
        assert!(nested_cols.len() == 2); // {b,c}
        assert_eq!(
            &nested_cols[1],
            batch.column(2),
            "c is not stored correctly"
        );
        assert_eq!(
            &nested_cols[0],
            batch.column(1),
            "b is not stored correctly"
        );

        Ok(())
    }

    /// GroupBy 1 batch on 1 column, where all rows end up in different groups.
    #[tokio::test]
    async fn test_groupby_single_key_multiple_groups() -> Result<(), Box<dyn Error>> {
        let semijoin = example_input()?;

        // GroupBy on column "a" (a=1 for all rows)
        let groupby = GroupBy::new(semijoin, vec![1]);
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<OneKeyNonSingularGroupedRel<UInt8Type>>()
            .unwrap();

        // Test that all rows end up in another group
        assert!(groupby_state.map.len() == 10);
        let next = groupby_state.data.next.as_deref().unwrap();
        assert_eq!(next.len(), 10);
        assert!(next.iter().all(|&next_ptr| next_ptr == 0));

        Ok(())
    }

    /// GroupBy 1 batch on two key columns
    #[tokio::test]
    async fn test_groupby_double_keys() -> Result<(), Box<dyn Error>> {
        let semijoin = example_input()?;

        // GroupBy on columns "a" and "b" (all (a,b) tuples are distinct)
        let groupby = GroupBy::new(semijoin, vec![0, 1]);
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<DoubleKeyNonSingularGroupedRel<UInt8Type, UInt8Type>>()
            .unwrap();

        // Test that all rows end up in another group
        assert!(groupby_state.map.len() == 10);
        let next = groupby_state.data.next.as_deref().unwrap();
        assert_eq!(next.len(), 10);
        assert!(next.iter().all(|&next_ptr| next_ptr == 0));

        Ok(())
    }

    /// GroupBy 1 batch on three (and ALL) key columns.
    /// Keys will be converted to rows (because >2 keys).
    /// Creates a singular nested field.
    #[tokio::test]
    async fn test_groupby_three_keys() -> Result<(), Box<dyn Error>> {
        let semijoin = example_input()?;

        // GroupBy on columns a,b,c (all (a,b,c) tuples are distinct)
        let groupby = GroupBy::new(semijoin, vec![0, 1, 2]);
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<DefaultSingularGroupedRel>()
            .unwrap();

        // Test that all rows end up in another group
        assert!(groupby_state.map.len() == 10);

        groupby_state
            .map
            .clone()
            .into_iter()
            .for_each(|(_key, group_id)| {
                let group = groupby_state.group_keys.row(group_id);
                let group_weight: Weight = group.get_extra(0);
                assert_eq!(group_weight, 1); // ... and that each group has weight 1
            });

        Ok(())
    }

    /// GroupBy multiple batches
    #[tokio::test]
    async fn test_groupby_multiple_batches() -> Result<(), Box<dyn Error>> {
        let n_batches = 5usize;
        let batches = (0..n_batches)
            .map(|_| example_batch().unwrap())
            .collect::<Vec<RecordBatch>>();
        let schema = batches[0].schema();

        let memoryexec = MemoryExec::try_new(&[batches], schema, None)?;
        let semijoin = MultiSemiJoin::new(Arc::new(memoryexec), vec![], vec![]);

        // GroupBy on column "a" (a=1 for all rows)
        let groupby = GroupBy::new(semijoin, vec![0]);
        let context: Arc<TaskContext> = Arc::new(TaskContext::default());
        let groupby_state_ref = groupby.materialize(context).await?;
        let groupby_state = groupby_state_ref
            .as_any()
            .downcast_ref::<OneKeyNonSingularGroupedRel<UInt8Type>>()
            .unwrap();

        // Test that all rows end up in the same group
        assert!(groupby_state.map.len() == 1);
        assert!(groupby_state
            .map
            .clone()
            .into_iter()
            .all(|(_key, weight, _ptr)| weight == (n_batches * 10) as Weight)); // ... and that the group has weight n_batches * 10
        let next = groupby_state.data.next.as_deref();
        next.unwrap()
            .iter()
            .enumerate()
            .for_each(|(row_nr, next_ptr)| {
                assert_eq!(row_nr, *next_ptr as usize);
            });

        Ok(())
    }
}
