//! Specialized implementation for flattening a [SemiJoinResultBatch] that only works when
//! - It is a flat batch ([SemiJoinResultBatch::Flat]), or
//! - it is a nested batch ([SemiJoinResultBatch::Nested]), and **ALL** [NestedSchema]s have max. 1 nested column, irrespective of the nesting depth.

use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::array::RecordBatch;
use datafusion::arrow::array::UInt32Array;
use datafusion::arrow::compute::TakeOptions;
use datafusion::arrow::error::ArrowError;
use datafusion::error::DataFusionError;
use datafusion::error::Result;
use metrics::FlattenMetrics;

use crate::take::weighted_u32::take_weighted;
use crate::yannakakis::data::Idx;

use super::super::data::{NestedSchema, NonSingularNestedColumn, SemiJoinResultBatch, Weight};
use super::super::schema::YannakakisSchema;
use super::metrics;
use super::take_all_weighted;

/// Flatten a [SemiJoinResultBatch].
/// Assumes that each [NestedSchema] has at most one nested field.
#[inline(always)]
pub(super) fn flatten_batch(
    batch: SemiJoinResultBatch,
    output_schema: &YannakakisSchema, // the *flat* output schema
    metrics: &FlattenMetrics,
) -> Result<RecordBatch, DataFusionError> {
    metrics.input_rows.add(batch.num_rows());
    let flatten_time = metrics.flatten_time.timer();

    let result = match batch {
        SemiJoinResultBatch::Flat(recordbatch) => recordbatch,
        SemiJoinResultBatch::Nested(nestedbatch) => {
            // Compute total number of rows in flat output batch,
            // which is the sum of the total weights in the nested batch
            let weights = nestedbatch.total_weights();
            let sum_of_weights = weights.iter().sum::<u32>() as usize;

            // Buffer for storing output arrays
            let n_cols = output_schema.n_unnest_fields();
            let mut output_buffer: Vec<ArrayRef> = Vec::with_capacity(n_cols);

            // Fill output with data from regular fields
            let guard_take_timer = metrics.guard_take_time.timer();
            let regular_fields = &nestedbatch.schema().regular_fields;
            for i in 0..regular_fields.fields().len() {
                let col = nestedbatch.regular_column(i);
                output_buffer.push(take_all_weighted(col, &weights, sum_of_weights)?);
            }
            guard_take_timer.done();

            let unnest_time = metrics.unnest_time.timer();

            // Unnest nested field if non-singular (max. 1 nested field)
            let batch_schema = nestedbatch.schema();
            if batch_schema.is_nested() {
                let nestedcol_schema = &batch_schema.nested_fields[0];
                if !nestedcol_schema.is_singular() {
                    let nestedcol = nestedbatch.nested_column(0).as_non_singular();
                    unnest_non_singular(
                        nestedcol,
                        nestedcol_schema,
                        &mut output_buffer,
                        sum_of_weights,
                        nestedcol.hols(), // pointers to be unnested,
                        &mut Vec::new(),
                        &mut Vec::new(),
                    )?;
                }
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

/// Recursively unnest a [NestedColumn::NonSingular] with the given `schema`.
/// For each output column, a new array with length = `output_size` will be appended to `output_buffer`.
fn unnest_non_singular(
    nested: &NonSingularNestedColumn,
    schema: &NestedSchema,
    output_buffer: &mut Vec<ArrayRef>,
    output_size: usize,
    ptrs: &[Idx], // pointers to be unnested
    row_ids: &mut Vec<Idx>,
    weights_buffer: &mut Vec<Weight>,
) -> Result<(), ArrowError> {
    if schema.nested_fields.len() == 0 {
        unnest_final_level(nested, schema, output_buffer, ptrs)
    } else {
        unnest_intermediate_level(
            nested,
            schema,
            output_buffer,
            output_size,
            ptrs,
            row_ids,
            weights_buffer,
        )
    }
}

/// Specialized code for unnesting a [NonSingularNestedColumn] when
/// - its [NestedSchema] still has nested fields (hence intermediate level), and
/// - this was the only nested field of its parent [NestedSchema].
///
/// e.g.
/// - parent schema was {a, {{b,{d}}}}
/// - and now we want to unnest {b,{d}}
fn unnest_intermediate_level(
    nestedcol: &NonSingularNestedColumn,
    schema: &NestedSchema,
    output_buffer: &mut Vec<ArrayRef>,
    output_size: usize,
    ptrs: &[Idx], // pointers to be unnested
    row_ids: &mut Vec<Idx>,
    weights_buffer: &mut Vec<Weight>,
) -> Result<(), ArrowError> {
    // Buffers. For each row that will be appended to the output, we store:
    // - the row id for indexing into the data arrays
    // - the weight, i.e., the number of times the row should be copied to the output
    row_ids.clear();
    row_ids.reserve(output_size);
    weights_buffer.clear();
    weights_buffer.reserve(output_size);

    // Follow hol_ptrs to collect row_ids.
    for ptr in ptrs {
        for row_id in nestedcol.iterate_linked_list(*ptr) {
            row_ids.push(row_id);
        }
    }

    // Collect row weights.
    let weights = nestedcol.data.total_weights();
    let weights_slice = weights.as_slice();
    for row in row_ids.iter() {
        let weight = unsafe { *weights_slice.get_unchecked(*row as usize) };
        weights_buffer.push(weight);
    }

    // for each regular field, compute output arrays
    for i in 0..schema.regular_fields.fields().len() {
        let col = nestedcol.regular_column(i);
        output_buffer.push(take_weighted(
            col.as_ref(),
            &row_ids,
            &weights_buffer,
            output_size,
        )?);
    }

    // Our NestedColumn `nested` may itself recursively have nested columns.
    // We will unnest the non-singular ones here.
    // NOTE: only valid when there is exactly one nested field in the schema!!!!
    let nested_cols = &nestedcol.data.nested_cols;
    let nested_schemas = &schema.nested_fields;
    for (nested_schema, nested_col) in nested_schemas.iter().zip(nested_cols.iter()) {
        if !nested_schema.is_singular() {
            let nested_col = nested_col.as_non_singular();
            let hols = nested_col.hols();
            let mut nested_ptrs = Vec::with_capacity(output_size);
            for row_id in row_ids.iter() {
                let ptr = unsafe { *hols.get_unchecked(*row_id as usize) };
                nested_ptrs.push(ptr);
            }
            // ... and unnest them.
            unnest_non_singular(
                nested_col,
                &nested_schema,
                output_buffer,
                output_size,
                &nested_ptrs,
                row_ids,
                weights_buffer,
            )?;
        }
    }

    Ok(())
}

/// Specialized code for unnesting a [NonSingularNestedColumn] when
/// - its [NestedSchema] has no nested fields anymore (hence final level), and
/// - this was the only nested field of its parent [NestedSchema].
///
/// e.g.
/// - parent schema was {a, {{b,{}}}}
/// - and now we want to unnest {b,{}}
fn unnest_final_level(
    nested: &NonSingularNestedColumn,
    schema: &NestedSchema, // schema of `nested`
    output_buffer: &mut Vec<ArrayRef>,
    ptrs: &[Idx], // pointers to be unnested
) -> Result<(), ArrowError> {
    // Follow hol_ptrs to collect row_ids
    let row_ids = UInt32Array::from_iter_values(
        ptrs.iter()
            .flat_map(|hol_ptr| nested.iterate_linked_list(*hol_ptr)),
    );

    // No weights need to be computed: all rows have weight 1.

    // For each regular attribute of the nested column, compute output array
    for i in 0..schema.regular_fields.fields().len() {
        let col = nested.regular_column(i);
        output_buffer.push(datafusion::arrow::compute::take(
            col.as_ref(),
            &row_ids,
            Some(TakeOptions {
                check_bounds: false,
            }),
        )?);
    }

    // No further unnesting is needed, as we have reached the final level.

    Ok(())
}
