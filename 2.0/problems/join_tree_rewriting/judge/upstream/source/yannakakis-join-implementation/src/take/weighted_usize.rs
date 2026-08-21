//! Defines take methods for [Array] that can handle weights.
//! The methods are inspired by the arrow take kernel.
//! TODO: add more info

use std::sync::Arc;

use datafusion::arrow::{
    array::{Array, ArrayRef, BooleanArray, PrimitiveArray},
    buffer::{BooleanBuffer, MutableBuffer, NullBuffer, ScalarBuffer},
    datatypes::{ArrowNativeType, ArrowPrimitiveType, DataType},
    downcast_primitive_array,
    error::ArrowError,
    util::bit_util,
};

use super::non_weighted_usize::take;

/// Take values from an [Array] using the given `indices` and `weights`.
/// The `output_size` is used for preallocation and should be the sum of all `weights`.
///
/// # Panics
/// Panics if
/// - `indices.len() != weights.len()`, or
/// - the indices are out of bounds.
pub fn take_weighted(
    values: &dyn Array,
    indices: &[usize],
    weights: &[usize],
    output_size: usize,
) -> Result<ArrayRef, ArrowError> {
    // Following use statement is required to make the downcast_primitive_array! macro work (otherwise error `arrow_schema unknown`)
    use datafusion::arrow::datatypes as arrow_schema;

    debug_assert!(indices.len() == weights.len());

    // If all weights are 1, we can use the non-weighted take method
    // which is faster because it does not iterate over the weights.
    if indices.len() == output_size {
        take(values, indices)
    // If the weights are not all 1, we need to use the weighted take method
    } else {
        downcast_primitive_array! (
            values => Ok(Arc::new(take_primitive(values, indices, weights, output_size)?)),
            DataType::Boolean => {
                let values = values.as_any().downcast_ref::<BooleanArray>().unwrap();
                Ok(Arc::new(take_boolean(values, indices, weights, output_size)))
            }
            t => unimplemented!("Take_weighted_unchecked not supported for data type {:?}", t)
        )
    }
}

fn take_boolean(
    values: &BooleanArray,
    indices: &[usize],
    weights: &[usize],
    output_size: usize,
) -> BooleanArray {
    let values_buffer = take_bits(values.values(), indices, weights, output_size);
    let nulls_buffer = take_nulls(values.nulls(), indices, weights, output_size);
    BooleanArray::new(values_buffer, nulls_buffer)
}

fn take_primitive<T>(
    values: &PrimitiveArray<T>,
    indices: &[usize],
    weights: &[usize],
    output_size: usize,
) -> Result<PrimitiveArray<T>, ArrowError>
where
    T: ArrowPrimitiveType,
{
    let values_buffer = take_native(values.values(), indices, weights);
    let nulls_buffer = take_nulls(values.nulls(), indices, weights, output_size);
    Ok(PrimitiveArray::new(values_buffer, nulls_buffer))
}

#[inline(never)]
fn take_native<T: ArrowNativeType>(
    values: &[T],
    indices: &[usize],
    weights: &[usize],
) -> ScalarBuffer<T> {
    indices
        .iter()
        .zip(weights)
        .flat_map(|(&idx, &weight)| {
            // unsafe variant does not seem to be faster
            let value = values[idx];
            // let value = unsafe { *values.get_unchecked(idx) };
            std::iter::repeat(value).take(weight)
        })
        .collect()
}

#[inline(never)]
fn take_nulls(
    values: Option<&NullBuffer>,
    indices: &[usize],
    weights: &[usize],
    output_size: usize,
) -> Option<NullBuffer> {
    match values.filter(|n| n.null_count() > 0) {
        Some(n) => {
            let buffer = take_bits(n.inner(), indices, weights, output_size);
            Some(NullBuffer::new(buffer)).filter(|n| n.null_count() > 0)
        }
        None => None,
    }
}

#[inline(never)]
fn take_bits(
    values: &BooleanBuffer,
    indices: &[usize],
    weights: &[usize],
    output_size: usize, // used for pre-allocating the output buffer
) -> BooleanBuffer {
    let mut output_buffer = MutableBuffer::new_null(output_size);
    let output_slice = output_buffer.as_slice_mut();

    indices
        .iter()
        .zip(weights)
        .fold(0usize, |offset, (&index, &weight)| {
            if values.value(index) {
                (0..weight).for_each(|w| {
                    bit_util::set_bit(output_slice, offset + w);
                });
            }
            offset + weight
        });

    BooleanBuffer::new(output_buffer.into(), 0, output_size)
}

#[cfg(test)]
mod tests {
    use datafusion::arrow::array::UInt32Array;

    use super::*;

    #[test]
    fn take_no_indices() {
        let values = UInt32Array::from(vec![0, 10, 20, 30]);
        let indices = vec![];
        let weights = vec![];
        let output_size = 0;

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();

        assert!(result.is_empty());
    }

    #[test]
    fn take_weighted_boolean() {
        let values = BooleanArray::from(vec![true, true, false, false]);
        let indices = vec![0, 1, 3];
        let weights = vec![1, 2, 3];
        let output_size = weights.iter().sum();

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();
        let expected = Arc::new(BooleanArray::from(vec![
            true, true, true, false, false, false,
        ]));

        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn take_weighted_u32() {
        let values = UInt32Array::from(vec![0, 10, 20, 30]);
        let indices = vec![0, 1, 3];
        let weights = vec![1, 2, 3];
        let output_size = weights.iter().sum();

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![0, 10, 10, 30, 30, 30]));

        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn take_weighted_u32_nulls() {
        let values = UInt32Array::from(vec![Some(0), None, Some(20), Some(30)]);
        let indices = vec![0, 1, 3];
        let weights = vec![1, 2, 3];
        let output_size = weights.iter().sum();

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![
            Some(0),
            None,
            None,
            Some(30),
            Some(30),
            Some(30),
        ]));

        assert_eq!(result.as_ref(), expected.as_ref());
    }
}
