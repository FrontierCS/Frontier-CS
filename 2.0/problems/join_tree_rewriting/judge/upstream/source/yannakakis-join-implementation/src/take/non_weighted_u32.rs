//! This module contains the implementation of the `take` operation for [Array]s with non-weighted indices.
//! This is inspired by the `take` operation in Apache Arrow.
//! The difference between this implementation and the one in Apache Arrow is
//! that this implementation accepts `indices` as a `&[usize]` instead of an `ArrayRef`.

use std::sync::Arc;

use datafusion::arrow::{
    array::{
        Array, ArrayData, ArrayRef, AsArray, BooleanArray, GenericByteArray, PrimitiveArray,
        UInt32Array,
    },
    buffer::{BooleanBuffer, MutableBuffer, NullBuffer, ScalarBuffer},
    compute::TakeOptions,
    datatypes::{ArrowNativeType, ArrowPrimitiveType, ByteArrayType, DataType},
    downcast_primitive_array,
    error::ArrowError,
    util::bit_util,
};

/// Take values from an [Array] using the given `indices`.
///
/// # Panics
/// Panics if any of the indices is out of bounds.
pub fn take(array: &dyn Array, indices: &[u32]) -> Result<ArrayRef, ArrowError> {
    // Following use statement is required to make the downcast_primitive_array! macro work (otherwise error `arrow_schema unknown`)
    use datafusion::arrow::datatypes as arrow_schema;

    downcast_primitive_array!(
        array => Ok(Arc::new(take_primitive(array, indices)?)),
        DataType::Boolean => {
            let array = array.as_any().downcast_ref::<BooleanArray>().unwrap();
            Ok(Arc::new(take_boolean(array, indices)))
        }

        DataType::Binary =>
            Ok(Arc::new(take_bytes(array.as_binary::<i32>(), indices)?))

        DataType::LargeBinary =>
            Ok(Arc::new(take_bytes(array.as_binary::<i64>(), indices)?))

        DataType::Utf8 =>
            Ok(Arc::new(take_bytes(array.as_string::<i32>(), indices)?))

        DataType::LargeUtf8 =>
            Ok(Arc::new(take_bytes(array.as_string::<i64>(), indices)?))
        _ => {
            // Fallback to using the take implementation from Arrow
            let idx = UInt32Array::from(indices.to_vec());
            datafusion::arrow::compute::take(array, &idx, Some(TakeOptions{check_bounds: false}))
        }
    )
}

fn take_boolean(values: &BooleanArray, indices: &[u32]) -> BooleanArray {
    let val_buf = take_bits(values.values(), indices);
    let null_buf = take_nulls(values.nulls(), indices);
    BooleanArray::new(val_buf, null_buf)
}

fn take_primitive<T>(
    values: &PrimitiveArray<T>,
    indices: &[u32],
) -> Result<PrimitiveArray<T>, ArrowError>
where
    T: ArrowPrimitiveType,
{
    let values_buf = take_native(values.values(), indices);
    let nulls = take_nulls(values.nulls(), indices);
    Ok(PrimitiveArray::new(values_buf, nulls).with_data_type(values.data_type().clone()))
}

#[inline(never)]
fn take_nulls(values: Option<&NullBuffer>, indices: &[u32]) -> Option<NullBuffer> {
    match values.filter(|n| n.null_count() > 0) {
        Some(n) => {
            let buffer = take_bits(n.inner(), indices);
            Some(NullBuffer::new(buffer)).filter(|n| n.null_count() > 0)
        }
        None => None,
    }
}

#[inline(never)]
fn take_native<T: ArrowNativeType>(values: &[T], indices: &[u32]) -> ScalarBuffer<T> {
    indices
        .iter()
        .map(|&index| values[index as usize])
        .collect()
}

#[inline(never)]
fn take_bits(values: &BooleanBuffer, indices: &[u32]) -> BooleanBuffer {
    let len = indices.len();
    let mut output_buffer = MutableBuffer::new_null(len);
    let output_slice = output_buffer.as_slice_mut();

    indices.iter().enumerate().for_each(|(i, &index)| {
        if values.value(index as usize) {
            bit_util::set_bit(output_slice, i);
        }
    });

    BooleanBuffer::new(output_buffer.into(), 0, indices.len())
}

/// `take` implementation for string arrays
fn take_bytes<T: ByteArrayType>(
    array: &GenericByteArray<T>,
    indices: &[u32],
) -> Result<GenericByteArray<T>, ArrowError> {
    let data_len = indices.len();

    let bytes_offset = (data_len + 1) * std::mem::size_of::<T::Offset>();
    let mut offsets = MutableBuffer::new(bytes_offset);
    offsets.push(T::Offset::default());

    let mut values = MutableBuffer::new(0);

    let nulls;

    if array.null_count() == 0 {
        offsets.extend(indices.iter().map(|index| {
            let s: &[u8] = array.value(index.as_usize()).as_ref();
            values.extend_from_slice(s);
            T::Offset::usize_as(values.len())
        }));
        nulls = None
    } else {
        let num_bytes = bit_util::ceil(data_len, 8);

        let mut null_buf = MutableBuffer::new(num_bytes).with_bitset(num_bytes, true);
        let null_slice = null_buf.as_slice_mut();
        offsets.extend(indices.iter().enumerate().map(|(i, index)| {
            let index = index.as_usize();
            if array.is_valid(index) {
                let s: &[u8] = array.value(index).as_ref();
                values.extend_from_slice(s.as_ref());
            } else {
                bit_util::unset_bit(null_slice, i);
            }
            T::Offset::usize_as(values.len())
        }));
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

    use super::*;

    #[test]
    fn test_take_primitive() {
        let array = Arc::new(UInt32Array::from(vec![0, 10, 20, 30]));
        let indices = vec![0, 2];
        let result = take(array.as_ref(), &indices).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![0, 20]));
        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn test_take_boolean() {
        let array = Arc::new(BooleanArray::from(vec![true, false, true, false]));
        let indices = vec![0, 2];
        let result = take(array.as_ref(), &indices).unwrap();
        let expected = Arc::new(BooleanArray::from(vec![true, true]));
        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn test_take_primitive_nulls() {
        let array = Arc::new(UInt32Array::from(vec![Some(0), None, Some(20), Some(30)]));
        let indices = vec![1, 2];
        let result = take(array.as_ref(), &indices).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![None, Some(20)]));
        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn test_take_string_no_nulls() {
        let from = StringArray::from(vec!["a", "b", "c", "d"]);
        let indices = vec![0, 1, 3];

        let result = take(&from, &indices).unwrap();
        let result = result.as_any().downcast_ref::<StringArray>().unwrap();
        let expected = StringArray::from(vec!["a", "b", "d"]);
        assert_eq!(result, &expected);
    }

    #[test]
    fn test_take_string_nulls() {
        let from = StringArray::from(vec![Some("a"), None, Some("c"), Some("d")]);
        let indices = vec![0, 1, 3];

        let result = take(&from, &indices).unwrap();
        let result = result.as_any().downcast_ref::<StringArray>().unwrap();
        let expected = StringArray::from(vec![Some("a"), None, Some("d")]);
        assert_eq!(result, &expected);
    }
}
