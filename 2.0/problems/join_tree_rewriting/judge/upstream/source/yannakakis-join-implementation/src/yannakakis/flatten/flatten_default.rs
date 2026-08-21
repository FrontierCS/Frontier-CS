//! Default implementation for flattening a [SemiJoinResultBatch], which works for all cases.

use std::ops::Range;
use std::sync::Arc;

use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::array::RecordBatch;
use datafusion::arrow::error::ArrowError;
use datafusion::error::DataFusionError;
use datafusion::error::Result;

use crate::yannakakis::data::Idx;
use crate::yannakakis::data::NestedColumn;
use crate::yannakakis::data::NestedRel;
use crate::yannakakis::data::SemiJoinResultBatch;
use crate::yannakakis::flatten::take_all_weighted;
use crate::yannakakis::schema::YannakakisSchema;

use super::super::data::{NestedSchema, NonSingularNestedColumn, Weight};
use super::metrics::FlattenMetrics;

/// The result of unnesting a non-singular [NestedColumn].
struct UnnestNestedColumnResult {
    inner: UnnestNestedRelResult,
}

impl UnnestNestedColumnResult {
    /// Update result by memcpying ranges of rows.
    fn memcpy(&mut self, ranges: &Vec<CopyRange>) {
        self.inner.memcpy(ranges);
    }

    /// For each regular column, append the result (as [ArrayRef]) to `output_buffer`,
    /// and do this recursively for each nested column.
    fn finish(self, output_buffer: &mut Vec<ArrayRef>) -> Result<(), ArrowError> {
        self.inner.finish(output_buffer)
    }
}

impl From<UnnestNestedRelResult> for UnnestNestedColumnResult {
    fn from(inner: UnnestNestedRelResult) -> Self {
        Self { inner }
    }
}

/// The result of unnesting a [NestedRel].
struct UnnestNestedRelResult {
    // For each regular column of the [NestedRel] that is fixed-width,
    // the result is an ArrayRef.
    // For each regular column of the [NestedRel] that is not fixed-width,
    // the result is a Vec<Idx> (this is the same vector for each non-fixed-width regular column).

    // As a first step, we store 1 Vec<Idx> for the whole nested rel.
    // After this is working, we can optimize by storing ArrayRefs for fixed-width regular columns.
    indices: Vec<Idx>,

    // The nested rel that was unnested.
    nestedrel: Arc<NestedRel>,

    /// The result of unnesting `self.nestedrel.nested_cols`
    nested_results: Vec<UnnestNestedColumnResult>,
}

impl UnnestNestedRelResult {
    fn new(indices: Vec<Idx>, nestedrel: Arc<NestedRel>) -> Self {
        let n_nested = nestedrel.schema().nested_fields.len();
        Self {
            indices,
            nestedrel,
            nested_results: Vec::with_capacity(n_nested),
        }
    }

    /// Update result by memcpying ranges of rows.
    #[inline(always)]
    fn memcpy(&mut self, ranges: &Vec<CopyRange>) {
        // Memcpy for regular fields of this nested rel
        for range in ranges {
            memcpy(range, &mut self.indices);
        }

        // Recursively memcpy for nested fields of this nested rel
        for nested in self.nested_results.iter_mut() {
            nested.inner.memcpy(ranges);
        }
    }

    /// For each regular column, append the result (as [ArrayRef]) to `output_buffer`,
    /// and do this recursively for each nested column.
    #[inline(always)]
    fn finish(self, output_buffer: &mut Vec<ArrayRef>) -> Result<(), ArrowError> {
        let n_regular_fields = self.nestedrel.schema().regular_fields.fields().len();

        for i in 0..n_regular_fields {
            let col = self.nestedrel.regular_column(i);
            output_buffer.push(crate::take::non_weighted_u32::take(col, &self.indices)?);
        }

        for nested in self.nested_results {
            nested.inner.finish(output_buffer)?;
        }

        Ok(())
    }
}

/// Flatten a [SemiJoinResultBatch].
#[inline(always)]
pub(super) fn flatten_batch(
    batch: SemiJoinResultBatch,
    output_schema: &YannakakisSchema, // the *flat* output schema
    metrics: &FlattenMetrics,
) -> Result<RecordBatch, DataFusionError> {
    metrics.input_rows.add(batch.num_rows());
    let flatten_time = metrics.flatten_time.timer();

    let result: RecordBatch = match batch {
        SemiJoinResultBatch::Flat(recordbatch) => recordbatch,
        SemiJoinResultBatch::Nested(nestedbatch) => {
            // Compute total number of rows in flat output batch,
            // which is the sum of the total weights in the nested batch.
            // Simultaneously, we also compute the offsets for each nested row in the flat output batch.
            let weights = nestedbatch.total_weights();
            let mut offsets = Vec::with_capacity(nestedbatch.num_rows()); // [0, weights[0], weights[0] + weights[1], ...]
            let sum_of_weights = weights.iter().fold(0, |acc, weight| {
                offsets.push(acc);
                acc + weight
            });

            // Buffer for storing output arrays
            let n_cols = output_schema.n_unnest_fields();
            let mut output_buffer: Vec<ArrayRef> = Vec::with_capacity(n_cols);

            // Fill output with data from regular fields
            let guard_take_timer = metrics.guard_take_time.timer();
            let regular_fields = &nestedbatch.schema().regular_fields;
            for i in 0..regular_fields.fields().len() {
                let col = nestedbatch.regular_column(i);
                output_buffer.push(take_all_weighted(col, &weights, sum_of_weights as usize)?);
            }
            guard_take_timer.done();

            // Unnest nested columns.
            let unnest_time = metrics.unnest_time.timer();
            let row_ids = (0..nestedbatch.num_rows() as u32).collect::<Vec<_>>();
            let mut repeat_buffer = vec![1; nestedbatch.num_rows()];
            let n_nested_cols = nestedbatch.schema().nested_fields.len();
            let mut unnesting_result = Vec::with_capacity(n_nested_cols);
            unnest_nestedcols(
                &nestedbatch.inner,
                &row_ids,
                &mut repeat_buffer,
                &offsets,
                weights,
                sum_of_weights as usize,
                &mut unnesting_result,
            )?;

            // For each unnested column, we now have a vector of indices.
            // We need to do arrow::take on each column with these indices.
            for unnested_col in unnesting_result {
                unnested_col.finish(&mut output_buffer)?;
            }

            unnest_time.done();

            // Duplicate output columns for join columns
            let timer = metrics.clone_join_columns_time.timer();
            let batch = output_schema.build_batch(&mut output_buffer)?;
            timer.done();
            batch
        }
    };

    flatten_time.done();
    metrics.output_rows.add(result.num_rows());
    Ok(result)
}

/// Unnest a [NonSingularNestedColumn].
fn unnest_nestedcol(
    col: &NonSingularNestedColumn,
    row_ids: &[Idx], // ids of tuples in `col` to be unnested
    repeat: &[u32],
    offsets: &[Idx],
    output_size: usize,
) -> Result<UnnestNestedColumnResult, ArrowError> {
    // Map row_ids to hol-ptrs.
    let hols = col.hols();
    let ptrs = row_ids
        .iter()
        .map(|row_id| unsafe { *hols.get_unchecked(*row_id as usize) })
        .collect::<Vec<_>>();

    let result = unnest_nestedrel(&col.data, &ptrs, repeat, offsets, output_size)?;
    Ok(result.into())
}

/// Specifies a range of rows to be copied: (range, number_of_copies)
type CopyRange = (Range<usize>, usize);

/// Unnest a [NestedRel].
#[inline(always)]
fn unnest_nestedrel(
    rel: &Arc<NestedRel>,
    ptrs: &[Idx],
    repeat: &[u32],
    offsets: &[Idx], // for each ptr, from which index in the output array we should start writing
    output_size: usize,
) -> Result<UnnestNestedRelResult, ArrowError> {
    debug_assert!(ptrs.len() == repeat.len());
    debug_assert!(ptrs.len() == offsets.len());

    if rel.schema().is_flat() {
        return unnest_flat_nestedrel(rel, ptrs, repeat, offsets, output_size);
    }

    let mut indices: Vec<Idx> = vec![0; output_size]; // indices of the rows in `rel` to be added to the output
                                                      // weighted: each index is repeated the number of times it should be copied to the output
    let total_weights = rel.total_weights(); // total weight of each row in `rel`
    let total_weights_slice = total_weights.as_slice();

    let mut offsets_buffer: Vec<Idx> = Vec::with_capacity(output_size); // offsets for recursive calls
    let mut repeat_buffer: Vec<u32> = Vec::with_capacity(output_size); // `repeat` values for recursive calls
    let mut row_ids_buffer: Vec<Idx> = Vec::with_capacity(output_size); // ids of the rows to be added to the output (non_weighted)
                                                                        // this will be used to index into the hols() and weights() of the nested fields

    for ((ptr, rep), offset) in ptrs.iter().zip(repeat).zip(offsets) {
        // `ptr` can write to `indices` starting from `offset`
        let to = &mut indices[*offset as usize..];

        // follow linked list to collect row_ids
        let mut sum_weights: Weight = 0;
        let row_ids = rel.iterate_linked_list(*ptr).flat_map(|row_id| {
            offsets_buffer.push(*offset + sum_weights);
            repeat_buffer.push(*rep);
            row_ids_buffer.push(row_id);
            let weight = total_weights_slice[row_id as usize];
            sum_weights += weight * *rep;
            std::iter::repeat(row_id).take((weight * rep) as usize)
        });

        // write row_ids to `indices`
        for (t, row_id) in to.iter_mut().zip(row_ids) {
            *t = row_id;
        }
    }

    // Unnest nested columns
    let mut result = UnnestNestedRelResult::new(indices, rel.clone());

    unnest_nestedcols(
        rel,
        &row_ids_buffer,
        &mut repeat_buffer,
        &offsets_buffer,
        total_weights_slice,
        output_size,
        &mut result.nested_results,
    )?;

    Ok(result)
}

/// Unnest all [NestedColumn]s of a [NestedRel].
fn unnest_nestedcols(
    nestedrel: &NestedRel,
    row_ids: &[Idx],
    repeat_buffer: &mut [u32],
    offsets: &[Idx],
    total_weights: &[Weight], // total weight of each row in `rel`
    output_size: usize,
    result: &mut Vec<UnnestNestedColumnResult>,
) -> Result<(), ArrowError> {
    let schemas = &nestedrel.schema().nested_fields; // schema of each nested column

    if schemas.len() > 1 {
        // Multiple nested columns.
        let nested_cols = (0..schemas.len())
            .map(|i| nestedrel.nested_column(i))
            .collect::<Vec<_>>();
        unnest_multiple_nested_cols(
            &nested_cols,
            schemas,
            &row_ids,
            repeat_buffer,
            &offsets,
            total_weights,
            output_size,
            result,
        )?;
    } else if schemas.len() == 1 && !schemas[0].is_singular() {
        // One non-singular nested column. Unnest it.
        result.push(unnest_nestedcol(
            nestedrel.nested_column(0).as_non_singular(),
            &row_ids,
            &repeat_buffer,
            &offsets,
            output_size,
        )?);
    }

    Ok(())
}

/// Unnest a [NestedRel] that has no nested columns anymore,
/// i.e., `rel.schema().is_flat() == true`.
#[inline(always)]
fn unnest_flat_nestedrel(
    rel: &Arc<NestedRel>,
    ptrs: &[Idx],
    repeat: &[u32],
    offsets: &[Idx], // for each ptr, from which index in the output array we should start writing
    output_size: usize,
) -> Result<UnnestNestedRelResult, ArrowError> {
    // No weight buffer needed, as all rows have weight 1
    // No new copy & repeat buffers needed for recursive calls, because there are no more recursive calls.

    let mut indices: Vec<Idx> = vec![0; output_size]; // ids of the rows to be added to the output

    for ((ptr, rep), offset) in ptrs.iter().zip(repeat).zip(offsets) {
        // `ptr` can write to `indices` starting from `offset`
        let to = &mut indices[*offset as usize..];

        // follow linked list to collect row_ids
        let row_ids = rel
            .iterate_linked_list(*ptr)
            .flat_map(|row_id| std::iter::repeat(row_id).take(*rep as usize)); // `rep` * `weight`, but `weight` is always 1

        // write row_ids to `indices`
        for (t, row_id) in to.iter_mut().zip(row_ids) {
            *t = row_id;
        }
    }

    Ok(UnnestNestedRelResult::new(indices, rel.clone()))
}

/// A [NestedRel] can have multiple [NestedColumn]s.
/// This method unnests these nested columns in case there are at least 2 of them.
fn unnest_multiple_nested_cols(
    nested_cols: &[&NestedColumn],
    schemas: &[Arc<NestedSchema>], // schema of each nested column
    row_ids_buffer: &[Idx],
    repeat_buffer: &mut [u32],
    offsets_buffer: &[Idx],
    total_weights: &[Weight], // total weight of each row in the [NestedRel] that `nested_cols` are part of
    output_size: usize,       // total number of rows in flat output batch
    result: &mut Vec<UnnestNestedColumnResult>,
) -> Result<(), ArrowError> {
    debug_assert!(nested_cols.len() >= 2);
    debug_assert!(nested_cols.len() == schemas.len());

    let mut copy_buffer: Vec<u32> = vec![1; row_ids_buffer.len()]; // copy value per row (if 1, no copying needed)
                                                                   // we'll update this buffer by iterating though the nested cols and multiplying pointer weights per row
    let mut copy: Vec<CopyRange> = Vec::new(); // ranges that need to be copied in the current iteration

    for (i, (nested_schema, nested_field)) in schemas.iter().zip(nested_cols).enumerate() {
        // COMPUTE REPEAT & COPY VALUES
        update_repeat_copy(
            &mut copy_buffer,
            repeat_buffer,
            row_ids_buffer,
            i,
            nested_field,
            total_weights,
            &mut copy,
        );

        // RECURSIVELY UNNEST NESTED COLUMN IF NON-SINGULAR
        if !nested_schema.is_singular() {
            let ns_nested = nested_field.as_non_singular();

            let mut nested_result = unnest_nestedcol(
                ns_nested,
                row_ids_buffer,
                &repeat_buffer,
                &offsets_buffer,
                output_size,
            )?;

            // Memcpy ranges of rows if needed
            nested_result.memcpy(&copy);

            result.push(nested_result);
        }

        copy.clear();
    }

    Ok(())
}

/// Update `copy` and `repeat` vectors with a new [NestedColumn].
fn update_repeat_copy(
    copy_buffer: &mut [u32],
    repeat_buffer: &mut [u32],
    row_ids_buffer: &[Idx],
    i: usize, // id of nestedcol
    nestedcol: &NestedColumn,
    total_weights: &[Weight], // total_weights of the rows in the [NestedRel] that `nestedcol` is part of
    copy: &mut Vec<CopyRange>, // ranges that need to be copied for the current nestedcol (i)
) {
    let nested_weights = nestedcol.weights();
    copy_buffer
        .iter_mut()
        .zip(repeat_buffer.iter_mut())
        .zip(row_ids_buffer)
        .fold(0, |sum_weights, ((cpy, rep), row_id)| {
            let total_row_weight = *unsafe { total_weights.get_unchecked(*row_id as usize) };
            let nested_row_weight = *unsafe { nested_weights.get_unchecked(*row_id as usize) };

            let curr_copy = *cpy; // copy value for the current nested column
            *cpy *= nested_row_weight; // update copy value for next nested column

            // compute repeat value for current nested column
            if i == 0 {
                *rep *= total_row_weight / *cpy;
            } else {
                *rep /= nested_row_weight;
            }

            if curr_copy > 1 {
                let start = sum_weights as usize;
                let end = start + (nested_row_weight * *rep) as usize;

                copy.push((start..end, curr_copy as usize));
            }

            sum_weights + total_row_weight
        });
}

////////////////////////////////////////////////////////////////////////////////////////////////////
//                                              UTIL                                              //
////////////////////////////////////////////////////////////////////////////////////////////////////

/// Memcpy a range of elements multiple times.
///
/// e.g: `memcpy_range(&(1..4, 2), &mut vec![0,1,2,3,4,5,6,7,8,9]) => vec![0,1,2,3,1,2,3,7,8,9]`
///
/// # Panics
/// Panics if the range is out of bounds.
#[inline(always)]
fn memcpy<T: std::marker::Copy>(range: &CopyRange, output: &mut Vec<T>) {
    let start = range.0.start;
    let n_copies = range.1;
    let len = range.0.len();

    // see documentation of copy_from_slice for why to use split_at_mut
    let (chunk_to_copy, rest) = output[start..].split_at_mut(len);

    (1..n_copies).fold(0, |offset, _| {
        let end = offset + len;
        let to = &mut rest[offset..end];
        to.copy_from_slice(chunk_to_copy);
        end
    });
}

#[cfg(test)]
mod tests {
    use datafusion::{
        arrow::{
            array::{Int32Array, StringArray},
            datatypes::{DataType, Field, Schema},
            util::pretty::pretty_format_batches,
        },
        execution::TaskContext,
        physical_plan::{collect, memory::MemoryExec, ExecutionPlan},
    };

    use crate::yannakakis::{flatten::Flatten, groupby::GroupBy, multisemijoin::MultiSemiJoin};

    use super::*;

    fn binary_semijoin(
        guard: Arc<dyn ExecutionPlan>,
        child1: Arc<dyn ExecutionPlan>,
        child1_groupby: Vec<usize>,
        child1_join_cols: Vec<(usize, usize)>,
    ) -> Result<MultiSemiJoin, DataFusionError> {
        // Binary semijoin between R, S (guard=R, children=[S])

        let s = MultiSemiJoin::new(child1, vec![], vec![]);
        let s_grouped = Arc::new(GroupBy::new(s, child1_groupby));

        let binary_semijoin = MultiSemiJoin::new(guard, vec![s_grouped], vec![child1_join_cols]);

        Ok(binary_semijoin)
    }

    fn ternary_semijoin(
        guard: Arc<dyn ExecutionPlan>,
        child1: Arc<dyn ExecutionPlan>,
        child1_groupby: Vec<usize>,
        child1_join_cols: Vec<(usize, usize)>,
        child2: Arc<dyn ExecutionPlan>,
        child2_groupby: Vec<usize>,
        child2_join_cols: Vec<(usize, usize)>,
    ) -> Result<MultiSemiJoin, DataFusionError> {
        // Ternary semijoin between R, S, and T (guard=R, children=[S,T])

        let s = MultiSemiJoin::new(child1, vec![], vec![]);
        let s_grouped = Arc::new(GroupBy::new(s, child1_groupby));
        let t = MultiSemiJoin::new(child2, vec![], vec![]);
        let t_grouped = Arc::new(GroupBy::new(t, child2_groupby));

        let ternary_semijoin = MultiSemiJoin::new(
            guard,
            vec![s_grouped, t_grouped],
            vec![child1_join_cols, child2_join_cols],
        );

        Ok(ternary_semijoin)
    }

    fn quaternary_semijoin(
        guard: Arc<dyn ExecutionPlan>,
        child1: Arc<dyn ExecutionPlan>,
        child1_groupby: Vec<usize>,
        child1_join_cols: Vec<(usize, usize)>,
        child2: Arc<dyn ExecutionPlan>,
        child2_groupby: Vec<usize>,
        child2_join_cols: Vec<(usize, usize)>,
        child3: Arc<dyn ExecutionPlan>,
        child3_groupby: Vec<usize>,
        child3_join_cols: Vec<(usize, usize)>,
    ) -> Result<MultiSemiJoin, DataFusionError> {
        // Quaternary semijoin between R, S, T, and U (guard=R, children=[S,T,U])

        let s = MultiSemiJoin::new(child1, vec![], vec![]);
        let s_grouped = Arc::new(GroupBy::new(s, child1_groupby));
        let t = MultiSemiJoin::new(child2, vec![], vec![]);
        let t_grouped = Arc::new(GroupBy::new(t, child2_groupby));
        let u = MultiSemiJoin::new(child3, vec![], vec![]);
        let u_grouped = Arc::new(GroupBy::new(u, child3_groupby));

        let quaternary_semijoin = MultiSemiJoin::new(
            guard,
            vec![s_grouped, t_grouped, u_grouped],
            vec![child1_join_cols, child2_join_cols, child3_join_cols],
        );

        Ok(quaternary_semijoin)
    }

    /// Create Arrow schema from column names and types.
    /// If `nullable` is `Some`, then it should be a vector of booleans indicating whether each column is nullable.
    /// If `nullable` is `None`, then all columns are non-nullable.
    fn create_schema(names: &[&str], types: &[DataType], nullable: Option<&[bool]>) -> Arc<Schema> {
        match nullable {
            Some(nullable) => Arc::new(Schema::new(
                names
                    .iter()
                    .zip(types.iter())
                    .zip(nullable.iter())
                    .map(|((name, data_type), nullable)| {
                        Field::new(name.to_string(), data_type.clone(), *nullable)
                    })
                    .collect::<Vec<_>>(),
            )),
            None => Arc::new(Schema::new(
                names
                    .iter()
                    .zip(types.iter())
                    .map(|(name, data_type)| Field::new(name.to_string(), data_type.clone(), false))
                    .collect::<Vec<_>>(),
            )),
        }
    }

    #[tokio::test]
    async fn flatten_ternary_semijoin_empty_result() -> Result<(), DataFusionError> {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c"], &[Int32, Int32, Int32], None);
        let s_schema = create_schema(&["d", "e", "f"], &[Int32, Int32, Int32], None);
        let t_schema = create_schema(&["g", "h", "i"], &[Int32, Int32, Int32], None);

        let data1 = vec![1, 1];
        let data2 = vec![2, 2];
        let columns1: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(data1.clone())),
            Arc::new(Int32Array::from(data1.clone())),
            Arc::new(Int32Array::from(data1.clone())),
        ];
        let columns2: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(data2.clone())),
            Arc::new(Int32Array::from(data2.clone())),
            Arc::new(Int32Array::from(data2.clone())),
        ];

        let r = vec![
            RecordBatch::try_new(r_schema.clone(), columns1)?,
            RecordBatch::try_new(r_schema.clone(), columns2.clone())?,
        ];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns2.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns2)?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);

        let plan = ternary_semijoin(
            r.clone(),
            s.clone(),
            vec![0],
            vec![(0, 0)],
            t.clone(),
            vec![0],
            vec![(1, 0)],
        )?;
        let plan = Arc::new(Flatten::new(Arc::new(plan)));
        let results = collect(plan, Arc::new(TaskContext::default())).await?;
        // single batch with 0 rows

        assert!(results.len() == 2);
        let batch1 = &results[0];
        let batch2 = &results[1];
        assert!(batch1.num_rows() == 0);
        assert!(batch2.num_rows() > 0);

        Ok(())
    }

    #[tokio::test]
    /// Test flattening a binary semijoin.
    /// R(a,b,c), S(d,e,f)
    /// The data is chosen such that R-S are one-to-one semijoins.
    async fn flatten_binary_semijoin_one_to_one_with_nullable_keys() -> Result<(), DataFusionError>
    {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c"], &[Int32, Int32, Int32], Some(&[true; 3]));
        let s_schema = create_schema(&["d", "e", "f"], &[Int32, Int32, Int32], Some(&[true; 3]));

        let data = vec![Some(1), Some(2), None, Some(4), Some(5)];

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(data.clone())),
            Arc::new(Int32Array::from(data.clone())),
            Arc::new(Int32Array::from(data.clone())),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);

        // Join on 1, 2, and all (3) columns.
        // For each case, the result is the same.
        for i in 1..=3 {
            let plan = binary_semijoin(
                r.clone(),
                s.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
            )?;
            let plan = Arc::new(Flatten::new(Arc::new(plan)));
            let results = collect(plan, Arc::new(TaskContext::default())).await?;
            assert!(results.len() == 1);
            let batch = &results[0];

            assert!(batch.num_columns() == 6);
            assert!(batch
                .columns()
                .iter()
                .all(|col| col.as_ref() == &Int32Array::from(vec![1, 2, 4, 5])));
        }

        Ok(())
    }

    #[tokio::test]
    /// Test flattening a ternary semijoin between R, S, and T.
    /// R(a,b,c), S(d,e,f), T(g,h,i)
    /// The data is chosen such that R-S and R-T are one-to-one semijoins.
    async fn flatten_ternary_semijoin_one_to_one() -> Result<(), DataFusionError> {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c"], &[Int32, Int32, Int32], None);
        let s_schema = create_schema(&["d", "e", "f"], &[Int32, Int32, Int32], None);
        let t_schema = create_schema(&["g", "h", "i"], &[Int32, Int32, Int32], None);

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(vec![1, 2, 3, 4, 5])),
            Arc::new(Int32Array::from(vec![1, 2, 3, 4, 5])),
            Arc::new(Int32Array::from(vec![1, 2, 3, 4, 5])),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns)?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);

        // Join on 1, 2, and all (3) columns.
        // For each case, the result is the same.
        for i in 1..=1 {
            let plan = ternary_semijoin(
                r.clone(),
                s.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
                t.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
            )?;
            let plan = Arc::new(Flatten::new(Arc::new(plan)));
            let results = collect(plan, Arc::new(TaskContext::default())).await?;
            assert!(results.len() == 1);
            let batch = &results[0];

            assert!(batch.num_columns() == 9);
            assert!(batch
                .columns()
                .iter()
                .all(|col| col.as_ref() == &Int32Array::from(vec![1, 2, 3, 4, 5])));
        }

        Ok(())
    }

    #[tokio::test]
    /// Test flattening a ternary semijoin between R, S, and T.
    /// R(a,b,c), S(d,e,f), T(g,h,i)
    /// The data is chosen such that R-S and R-T are one-to-one semijoins.
    async fn flatten_ternary_semijoin_one_to_one_with_nullable_keys() -> Result<(), DataFusionError>
    {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c"], &[Int32, Int32, Int32], Some(&[true; 3]));
        let s_schema = create_schema(&["d", "e", "f"], &[Int32, Int32, Int32], Some(&[true; 3]));
        let t_schema = create_schema(&["g", "h", "i"], &[Int32, Int32, Int32], Some(&[true; 3]));

        let data = vec![Some(1), Some(2), None, Some(4), Some(5)];

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(data.clone())),
            Arc::new(Int32Array::from(data.clone())),
            Arc::new(Int32Array::from(data.clone())),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns)?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);

        // Join on 1, 2, and all (3) columns.
        // For each case, the result is the same.
        for i in 1..=3 {
            let plan = ternary_semijoin(
                r.clone(),
                s.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
                t.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
            )?;
            let plan = Arc::new(Flatten::new(Arc::new(plan)));
            let results = collect(plan, Arc::new(TaskContext::default())).await?;
            assert!(results.len() == 1);
            let batch = &results[0];

            assert!(batch.num_columns() == 9);
            assert!(batch
                .columns()
                .iter()
                .all(|col| col.as_ref() == &Int32Array::from(vec![1, 2, 4, 5])));
        }

        Ok(())
    }

    #[tokio::test]
    /// Test flattening a ternary semijoin between R, S, and T.
    /// R(a,b,c), S(d,e,f), T(g,h,i)
    /// The data is chosen such that R-S and R-T are all_to_all joins (cartesian product).
    async fn flatten_ternary_semijoin_all_to_all() -> Result<(), DataFusionError> {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c"], &[Int32, Int32, Int32], None);
        let s_schema = create_schema(&["d", "e", "f"], &[Int32, Int32, Int32], None);
        let t_schema = create_schema(&["g", "h", "i"], &[Int32, Int32, Int32], None);

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(Int32Array::from(vec![1, 1])),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns)?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);

        // Join on 1, 2, and all (3) columns.
        // For each case, the result is the same.
        for i in 1..=3 {
            let plan = ternary_semijoin(
                r.clone(),
                s.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
                t.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
            )?;
            let plan = Arc::new(Flatten::new(Arc::new(plan)));
            let results = collect(plan, Arc::new(TaskContext::default())).await?;
            assert!(results.len() == 1);
            let batch = &results[0];

            assert!(batch.num_columns() == 9);
            assert!(batch
                .columns()
                .iter()
                .all(|col| col.as_ref() == &Int32Array::from(vec![1; 8])));
        }

        Ok(())
    }

    #[tokio::test]
    /// Test flattening a quaternary semijoin between R, S, T, and U.
    /// Each relation has 4 columns.
    /// The data is chosen such that R-S, R-T, and R-U are all_to_all joins (cartesian product).
    async fn flatten_quaternary_semijoin_all_to_all() -> Result<(), DataFusionError> {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c", "d"], &[Int32, Int32, Int32, Int32], None);
        let s_schema = create_schema(&["e", "f", "g", "h"], &[Int32, Int32, Int32, Int32], None);
        let t_schema = create_schema(&["i", "j", "k", "l"], &[Int32, Int32, Int32, Int32], None);
        let u_schema = create_schema(&["m", "n", "o", "p"], &[Int32, Int32, Int32, Int32], None);

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(Int32Array::from(vec![1, 1])),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns.clone())?];
        let u = vec![RecordBatch::try_new(u_schema.clone(), columns)?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);
        let u = Arc::new(MemoryExec::try_new(&[u], u_schema, None)?);

        // Join on 1, 2, 3, and all (4) columns.
        // For each case, the result is the same.
        for i in 0..=4 {
            let plan = quaternary_semijoin(
                r.clone(),
                s.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
                t.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
                u.clone(),
                (0..i).collect(),
                (0..i).map(|j| (j, j)).collect(),
            )?;
            let plan = Arc::new(Flatten::new(Arc::new(plan)));
            let results = collect(plan, Arc::new(TaskContext::default())).await?;
            assert!(results.len() == 1);
            let batch = &results[0];
            assert!(batch.num_columns() == 16); // 4 columns * 4 tables
            assert!(batch.num_rows() == 16);
            assert!(batch
                .columns()
                .iter()
                .all(|col| col.as_ref() == &Int32Array::from(vec![1; 16])));
        }

        Ok(())
    }

    #[tokio::test]
    /// Test flattening a ternary semijoin between R, S, and T.
    /// R(a,b,c), S(d,e,f), T(g,h,i)
    /// The data is chosen such that R-S and R-T are all_to_all joins (cartesian product).
    ///
    /// --------------------------------------------------------------------------------------
    /// Difference with `flatten_ternary_semijoin_all_to_all`:
    /// the regular columns of the nested relations are Utf-8.
    async fn flatten_utf8() -> Result<(), DataFusionError> {
        use DataType::*;

        let r_schema = create_schema(&["a", "b", "c"], &[Int32, Utf8, Utf8], None);
        let s_schema = create_schema(&["d", "e", "f"], &[Int32, Utf8, Utf8], None);
        let t_schema = create_schema(&["g", "h", "i"], &[Int32, Utf8, Utf8], None);

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(StringArray::from(vec!["1", "3"])),
            Arc::new(StringArray::from(vec!["2", "4"])),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns)?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);

        // Join on 1, 2, and all (3) columns.
        // For each case, the result is the same.
        let plan = ternary_semijoin(
            r.clone(),
            s.clone(),
            vec![0],
            vec![(0, 0)],
            t.clone(),
            vec![0],
            vec![(0, 0)],
        )?;
        let plan = Arc::new(Flatten::new(Arc::new(plan)));
        let results = collect(plan, Arc::new(TaskContext::default())).await?;
        assert!(results.len() == 1);
        let batch = &results[0];

        assert!(batch.num_columns() == 9);

        let expected = "+---+---+---+---+---+---+---+---+---+
| a | b | c | d | e | f | g | h | i |
+---+---+---+---+---+---+---+---+---+
| 1 | 1 | 2 | 1 | 3 | 4 | 1 | 3 | 4 |
| 1 | 1 | 2 | 1 | 3 | 4 | 1 | 1 | 2 |
| 1 | 1 | 2 | 1 | 1 | 2 | 1 | 3 | 4 |
| 1 | 1 | 2 | 1 | 1 | 2 | 1 | 1 | 2 |
| 1 | 3 | 4 | 1 | 3 | 4 | 1 | 3 | 4 |
| 1 | 3 | 4 | 1 | 3 | 4 | 1 | 1 | 2 |
| 1 | 3 | 4 | 1 | 1 | 2 | 1 | 3 | 4 |
| 1 | 3 | 4 | 1 | 1 | 2 | 1 | 1 | 2 |
+---+---+---+---+---+---+---+---+---+";

        assert_eq!(
            pretty_format_batches(&[batch.clone()])?.to_string(),
            expected
        );

        Ok(())
    }

    #[tokio::test]
    async fn flatten_deep_nesting() -> Result<(), DataFusionError> {
        use DataType::*;

        let r_schema = create_schema(&["r1", "r2"], &[Int32, Int32, Int32, Int32], None);
        let s_schema = create_schema(&["s1", "s2"], &[Int32, Int32, Int32, Int32], None);
        let t_schema = create_schema(&["t1", "t2"], &[Int32, Int32, Int32, Int32], None);
        let u_schema = create_schema(&["u1", "u2"], &[Int32, Int32, Int32, Int32], None);
        let v_schema = create_schema(&["v1", "v2"], &[Int32, Int32, Int32, Int32], None);
        let w_schema = create_schema(&["w1", "w2"], &[Int32, Int32, Int32, Int32], None);
        let x_schema = create_schema(&["x1", "x2"], &[Int32, Int32, Int32, Int32], None);
        let y_schema = create_schema(&["y1", "y2"], &[Int32, Int32, Int32, Int32], None);
        let z_schema = create_schema(&["z1", "z2"], &[Int32, Int32, Int32, Int32], None);

        let columns: Vec<ArrayRef> = vec![
            Arc::new(Int32Array::from(vec![1, 1])),
            Arc::new(Int32Array::from(vec![1, 1])),
        ];

        let r = vec![RecordBatch::try_new(r_schema.clone(), columns.clone())?];
        let s = vec![RecordBatch::try_new(s_schema.clone(), columns.clone())?];
        let t = vec![RecordBatch::try_new(t_schema.clone(), columns.clone())?];
        let u = vec![RecordBatch::try_new(u_schema.clone(), columns.clone())?];
        let v = vec![RecordBatch::try_new(v_schema.clone(), columns.clone())?];
        let w = vec![RecordBatch::try_new(w_schema.clone(), columns.clone())?];
        let x = vec![RecordBatch::try_new(x_schema.clone(), columns.clone())?];
        let y = vec![RecordBatch::try_new(y_schema.clone(), columns.clone())?];
        let z = vec![RecordBatch::try_new(z_schema.clone(), columns.clone())?];

        let r = Arc::new(MemoryExec::try_new(&[r], r_schema, None)?);
        let s = Arc::new(MemoryExec::try_new(&[s], s_schema, None)?);
        let t = Arc::new(MemoryExec::try_new(&[t], t_schema, None)?);
        let u = Arc::new(MemoryExec::try_new(&[u], u_schema, None)?);
        let v = Arc::new(MemoryExec::try_new(&[v], v_schema, None)?);
        let w = Arc::new(MemoryExec::try_new(&[w], w_schema, None)?);
        let x = Arc::new(MemoryExec::try_new(&[x], x_schema, None)?);
        let y = Arc::new(MemoryExec::try_new(&[y], y_schema, None)?);
        let z = Arc::new(MemoryExec::try_new(&[z], z_schema, None)?);

        // // W ⋉ (Y ⋉ Z)  (guard=W, children=[Y,Z])
        let y = MultiSemiJoin::new(y, vec![], vec![]);
        let y_grouped = Arc::new(GroupBy::new(y, vec![0]));
        let z = MultiSemiJoin::new(z, vec![], vec![]);
        let z_grouped = Arc::new(GroupBy::new(z, vec![0]));
        let w = MultiSemiJoin::new(
            w,
            vec![y_grouped, z_grouped],
            vec![vec![(0, 0)], vec![(0, 0)]],
        );

        // T ⋉ (V ⋉ W ⋉ X)   (guard=T, children=[V,W,X])
        let v = MultiSemiJoin::new(v, vec![], vec![]);
        let v_grouped = Arc::new(GroupBy::new(v, vec![0]));
        let w_grouped = Arc::new(GroupBy::new(w, vec![0]));
        let x = MultiSemiJoin::new(x, vec![], vec![]);
        let x_grouped = Arc::new(GroupBy::new(x, vec![0]));
        let t = MultiSemiJoin::new(
            t,
            vec![v_grouped, w_grouped, x_grouped],
            vec![vec![(0, 0)], vec![(0, 0)], vec![(0, 0)]],
        );

        // R ⋉ (S ⋉ T ⋉ U)   (guard=R, children=[S,T,U])
        let s = MultiSemiJoin::new(s, vec![], vec![]);
        let s_grouped = Arc::new(GroupBy::new(s, vec![0]));
        let t_grouped = Arc::new(GroupBy::new(t, vec![0]));
        let u = MultiSemiJoin::new(u, vec![], vec![]);
        let u_grouped = Arc::new(GroupBy::new(u, vec![0]));

        let root = MultiSemiJoin::new(
            r,
            vec![s_grouped, t_grouped, u_grouped],
            vec![vec![(0, 0)]; 3],
        );
        let flatten = Arc::new(Flatten::new(Arc::new(root)));

        let results = collect(flatten.clone(), Arc::new(TaskContext::default())).await?;
        assert!(results.len() == 1);
        let batch = &results[0];

        assert!(batch.num_columns() == 18); // 2*9 (9 tables with 2 columns each)
        assert!(batch.num_rows() == 512); // 2^9  (9 tables with two rows each & ajoins are cartesian products)

        assert!(batch
            .columns()
            .iter()
            .all(|col| col.as_ref() == &Int32Array::from(vec![1; 512])));

        Ok(())
    }
}
