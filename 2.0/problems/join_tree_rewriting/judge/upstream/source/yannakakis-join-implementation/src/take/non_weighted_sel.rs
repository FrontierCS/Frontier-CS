//! This module contains the implementation of the `take` operation for [Array]s with non-weighted indices.
//! This is inspired by the `take` operation in Apache Arrow.
//! The difference between this implementation and the one in Apache Arrow is
//! that this implementation accepts `indices` as a Selection instead of an `ArrayRef`.

use std::sync::Arc;

use datafusion::arrow::{
    array::{Array, ArrayRef, BooleanArray, PrimitiveArray},
    buffer::{BooleanBuffer, MutableBuffer, NullBuffer, ScalarBuffer},
    datatypes::{ArrowNativeType, ArrowPrimitiveType, DataType},
    downcast_primitive_array,
    error::ArrowError,
    util::bit_util,
};

use crate::{sel::Selection, yannakakis::data::Idx as PTR};

/// Take values from an [Array] using the given `indices`.
///
/// # Panics
/// Panics if any of the indices is out of bounds.
pub fn take<I>(array: &dyn Array, indices: I) -> Result<ArrayRef, ArrowError>
where
    I: Selection,
{
    // Following use statement is required to make the downcast_primitive_array! macro work (otherwise error `arrow_schema unknown`)
    use datafusion::arrow::datatypes as arrow_schema;

    downcast_primitive_array!(
        array => Ok(Arc::new(take_primitive(array, indices)?)),
        DataType::Boolean => {
            let array = array.as_any().downcast_ref::<BooleanArray>().unwrap();
            Ok(Arc::new(take_boolean(array, indices)))
        }
        t => unimplemented!("Take_unchecked not supported for data type {:?}", t)
    )
}

fn take_boolean<I>(values: &BooleanArray, indices: I) -> BooleanArray
where
    I: Selection,
{
    let val_buf = take_bits(values.values(), indices.iter());
    let null_buf = take_nulls(values.nulls(), indices);
    BooleanArray::new(val_buf, null_buf)
}

fn take_primitive<T, I>(
    values: &PrimitiveArray<T>,
    indices: I,
) -> Result<PrimitiveArray<T>, ArrowError>
where
    T: ArrowPrimitiveType,
    I: Selection,
{
    let values_buf = take_native(values.values(), indices.iter());
    let nulls = take_nulls(values.nulls(), indices);
    Ok(PrimitiveArray::new(values_buf, nulls).with_data_type(values.data_type().clone()))
}

#[inline(never)]
fn take_nulls<I>(values: Option<&NullBuffer>, indices: I) -> Option<NullBuffer>
where
    I: Selection,
{
    match values.filter(|n| n.null_count() > 0) {
        Some(n) => {
            let buffer = take_bits(n.inner(), indices.iter());
            Some(NullBuffer::new(buffer)).filter(|n| n.null_count() > 0)
        }
        None => None,
    }
}

#[inline(never)]
fn take_native<T: ArrowNativeType, I>(values: &[T], indices: I) -> ScalarBuffer<T>
where
    I: ExactSizeIterator<Item = PTR>,
{
    indices.map(|index| values[index as usize]).collect()
}

#[inline(never)]
fn take_bits<I>(values: &BooleanBuffer, indices: I) -> BooleanBuffer
where
    I: ExactSizeIterator<Item = PTR>,
{
    let len = indices.len();
    let mut output_buffer = MutableBuffer::new_null(len);
    let output_slice = output_buffer.as_slice_mut();

    indices.enumerate().for_each(|(i, index)| {
        if values.value(index as usize) {
            bit_util::set_bit(output_slice, i);
        }
    });

    BooleanBuffer::new(output_buffer.into(), 0, len)
}

#[cfg(test)]
mod tests {
    use datafusion::arrow::array::UInt32Array;

    use super::*;

    #[test]
    fn test_take_primitive() {
        let array = Arc::new(UInt32Array::from(vec![0, 10, 20, 30]));
        let result = take(array.as_ref(), (1..3).into_iter()).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![10, 20]));
        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn test_take_boolean() {
        let array = Arc::new(BooleanArray::from(vec![true, false, true, false]));
        let result = take(array.as_ref(), (1..3).into_iter()).unwrap();
        let expected = Arc::new(BooleanArray::from(vec![false, true]));
        assert_eq!(result.as_ref(), expected.as_ref());
    }

    #[test]
    fn test_take_primitive_nulls() {
        let array = Arc::new(UInt32Array::from(vec![Some(0), None, Some(20), Some(30)]));
        let result = take(array.as_ref(), (1..3).into_iter()).unwrap();
        let expected = Arc::new(UInt32Array::from(vec![None, Some(20)]));
        assert_eq!(result.as_ref(), expected.as_ref());
    }
}
