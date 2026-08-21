//! Defines take methods for [Array] that can handle weights.
//! The methods are inspired by the arrow take kernel.
//!
use std::sync::Arc;

use datafusion::arrow::{
    array::{Array, ArrayData, ArrayRef, AsArray, BooleanArray, GenericByteArray, PrimitiveArray},
    buffer::{BooleanBuffer, MutableBuffer, NullBuffer, ScalarBuffer},
    datatypes::{ArrowNativeType, ArrowPrimitiveType, ByteArrayType, DataType},
    downcast_primitive_array,
    error::ArrowError,
    util::bit_util,
};

use crate::take::non_weighted_u32::take;

/// Take values from an [Array] using the given `indices` and `weights`.
/// The `output_size` is used for preallocation and should be the sum of all `weights`.
///
/// # Panics
/// Panics if
/// - `indices.len() != weights.len()`, or
/// - the indices are out of bounds.
pub fn take_weighted(
    values: &dyn Array,
    indices: &[u32],
    weights: &[u32],
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

            DataType::Binary =>
                Ok(Arc::new(take_bytes(values.as_binary::<i32>(), indices, weights, output_size)?))

            DataType::LargeBinary =>
                Ok(Arc::new(take_bytes(values.as_binary::<i64>(), indices, weights, output_size)?))

            DataType::Utf8 =>
                Ok(Arc::new(take_bytes(values.as_string::<i32>(), indices, weights, output_size)?)),

            DataType::LargeUtf8 =>
                Ok(Arc::new(take_bytes(values.as_string::<i64>(), indices, weights, output_size)?))

            t => unimplemented!("Take_weighted_unchecked not supported for data type {:?}", t)
        )
    }
}

fn take_boolean(
    values: &BooleanArray,
    indices: &[u32],
    weights: &[u32],
    output_size: usize,
) -> BooleanArray {
    let values_buffer = take_bits(values.values(), indices, weights, output_size);
    let nulls_buffer = take_nulls(values.nulls(), indices, weights, output_size);
    BooleanArray::new(values_buffer, nulls_buffer)
}

fn take_primitive<T>(
    values: &PrimitiveArray<T>,
    indices: &[u32],
    weights: &[u32],
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
    indices: &[u32],
    weights: &[u32],
) -> ScalarBuffer<T> {
    indices
        .iter()
        .zip(weights)
        .flat_map(|(&idx, &weight)| {
            // unsafe variant does not seem to be faster
            let value = values[idx as usize];
            // let value = unsafe { *values.get_unchecked(idx) };
            std::iter::repeat(value).take(weight as usize)
        })
        .collect()
}

#[inline(never)]
fn take_nulls(
    values: Option<&NullBuffer>,
    indices: &[u32],
    weights: &[u32],
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
    indices: &[u32],
    weights: &[u32],
    output_size: usize, // used for pre-allocating the output buffer
) -> BooleanBuffer {
    let mut output_buffer = MutableBuffer::new_null(output_size);
    let output_slice = output_buffer.as_slice_mut();

    indices
        .iter()
        .zip(weights)
        .fold(0usize, |offset, (&index, &weight)| {
            if values.value(index as usize) {
                (0..weight).for_each(|w| {
                    bit_util::set_bit(output_slice, offset + w as usize);
                });
            }
            offset + weight as usize
        });

    BooleanBuffer::new(output_buffer.into(), 0, output_size)
}

fn take_bytes<T: ByteArrayType>(
    array: &GenericByteArray<T>,
    indices: &[u32],
    weights: &[u32],
    output_size: usize, // sum of weights, total number of items in output array
) -> Result<GenericByteArray<T>, ArrowError> {
    let data_len = output_size;

    let bytes_offset = (data_len + 1) * std::mem::size_of::<T::Offset>();
    let mut offsets = MutableBuffer::new(bytes_offset);
    offsets.push(T::Offset::default());

    let mut values = MutableBuffer::new(0);

    let nulls;

    if array.null_count() == 0 {
        indices.iter().zip(weights).for_each(|(index, weight)| {
            let s: &[u8] = array.value(index.as_usize()).as_ref();
            for _ in 0..*weight {
                values.extend_from_slice(s);
                offsets.push(T::Offset::usize_as(values.len()));
            }
        });
        nulls = None
    } else {
        let num_bytes = bit_util::ceil(data_len, 8);

        let mut null_buf = MutableBuffer::new(num_bytes).with_bitset(num_bytes, true);
        let null_slice = null_buf.as_slice_mut();

        indices
            .iter()
            .zip(weights)
            .fold(0_usize, |offset, (index, weight)| {
                let index = index.as_usize();
                let weight = weight.as_usize();
                if array.is_valid(index) {
                    let s: &[u8] = array.value(index).as_ref();
                    for _ in 0..weight {
                        values.extend_from_slice(s.as_ref());
                        offsets.push(T::Offset::usize_as(values.len()));
                    }
                } else {
                    for w in 0..weight {
                        bit_util::unset_bit(null_slice, offset + w);
                        offsets.push(T::Offset::usize_as(values.len()));
                    }
                }
                offset + weight
            });

        nulls = Some(null_buf.into());
    }

    T::Offset::from_usize(values.len()).expect("offset overflow");

    let array_data = ArrayData::builder(T::DATA_TYPE)
        .len(data_len)
        .add_buffer(offsets.into())
        .add_buffer(values.into())
        .null_bit_buffer(nulls);

    let array_data = unsafe { array_data.build_unchecked() };

    Ok(GenericByteArray::from(array_data))
}

#[cfg(test)]
mod tests {
    use datafusion::arrow::array::{StringArray, UInt32Array};

    use crate::yannakakis::data::Weight as WEIGHT;

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
        let output_size = weights.iter().sum::<WEIGHT>() as usize;

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
        let output_size = weights.iter().sum::<WEIGHT>() as usize;

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![0, 10, 10, 30, 30, 30]));

        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn take_weighted_u32_nulls() {
        let values = UInt32Array::from(vec![Some(0), None, Some(20), Some(30)]);
        let indices = vec![0, 1, 3];
        let weights = vec![1, 2, 3];
        let output_size = weights.iter().sum::<WEIGHT>() as usize;

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

    #[test]
    fn take_weighted_u32_string_no_nulls() {
        let values = StringArray::from(vec!["a", "b", "c", "d"]);
        let indices = vec![0, 1, 3];
        let weights = vec![1, 2, 3];
        let output_size = weights.iter().sum::<WEIGHT>() as usize;

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();
        let result = result.as_any().downcast_ref::<StringArray>().unwrap();
        let expected = StringArray::from(vec!["a", "b", "b", "d", "d", "d"]);

        assert_eq!(result, &expected);
    }

    #[test]
    fn take_weighted_u32_string_with_nulls() {
        let values = StringArray::from(vec![Some("a"), None, Some("c"), Some("d")]);
        let indices = vec![0, 1, 3];
        let weights = vec![1, 2, 3];
        let output_size = weights.iter().sum::<WEIGHT>() as usize;

        let result = take_weighted(&values, &indices, &weights, output_size).unwrap();
        let result = result.as_any().downcast_ref::<StringArray>().unwrap();
        let expected =
            StringArray::from(vec![Some("a"), None, None, Some("d"), Some("d"), Some("d")]);

        assert_eq!(result, &expected);
    }
}
