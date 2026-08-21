//! Various compute kernels:
//! - for multiplying vector of weights.
//! - take operation on nested columns.

use super::data::NestedColumn;
use super::data::NonSingularNestedColumn;
use super::data::SingularNestedColumn;
use super::data::Weight;
use super::sel::Sel;

/// Multiply two slices of u32s elementwise, returning the result as a newly-allocated vector
#[inline]
pub fn multiply_two_weight_slices(a: &[Weight], b: &[Weight]) -> Vec<Weight> {
    assert!(a.len() == b.len(), "Vectors must have the same length");
    a.iter().zip(b.iter()).map(|(x, y)| *x * y).collect()
}

/// Multiply two slices of u32s elementwise where the result is stored in the first mutable slice
#[inline]
pub fn multiply_weights_by(a: &mut [Weight], b: &[Weight]) {
    assert!(a.len() == b.len(), "Vectors must have the same length");
    a.iter_mut().zip(b.iter()).for_each(|(x, y)| *x *= y);
}

/// Multiply a collection of u32 slices elementwise, returning the result a a newly-allocated Vector
#[inline]
pub fn multiply_weights<'a>(
    mut weights: impl ExactSizeIterator<Item = &'a [Weight]>,
) -> Vec<Weight> {
    if weights.len() == 0 {
        return vec![];
    } else if weights.len() == 1 {
        return weights.next().unwrap().to_vec();
    } else
    // weights.len > 2
    {
        let first = weights.next().unwrap();
        let second = weights.next().unwrap();
        let mut result = multiply_two_weight_slices(first, second);
        for slice in weights {
            multiply_weights_by(&mut result, slice);
        }
        result
    }
}

/// multiply two slices of u32s elementwise where the result is stored in a mutable buffer
#[inline]
pub fn multiply_two_weight_slices_into_buffer(
    dest_buffer: &mut [Weight],
    a: &[Weight],
    b: &[Weight],
) {
    assert!(
        a.len() == b.len() && dest_buffer.len() == a.len(),
        "Vectors must have the same length"
    );
    for (i, w) in dest_buffer.iter_mut().enumerate() {
        *w = unsafe { a.get_unchecked(i) } * unsafe { b.get_unchecked(i) };
    }
}

/// multiply a collection of slices of u32s elementwise where the result is stored in a mutable buffer
#[inline]
pub fn multiply_weights_buffered<'a, 'b, 'c>(
    mut weights: impl ExactSizeIterator<Item = &'a [Weight]>,
    mut buffer: &'b mut [Weight],
) -> &'c [Weight]
where
    'a: 'c,
    'b: 'c,
{
    if weights.len() == 0 {
        return buffer;
    } else if weights.len() == 1 {
        return weights.next().unwrap();
    } else
    // weights.len > 2
    {
        let first = weights.next().unwrap();
        let second = weights.next().unwrap();
        multiply_two_weight_slices_into_buffer(&mut buffer, first, second);
        // Now multiply the rest
        for slice in weights {
            multiply_weights_by(&mut buffer, slice);
        }
        buffer
    }
}

/// Take rows of a NestedColumn by index from a selection vector, mutating the NestedColumn in place
/// Assumes that the indices in the selection vector are monotonically increasing, and valid for the nested column.
#[inline]
pub fn take_nested_column_inplace(nested_column: &mut NestedColumn, selection: &Sel) {
    match nested_column {
        NestedColumn::Singular(c) => take_singular_nested_column_inplace(c, selection),
        NestedColumn::NonSingular(c) => take_non_singular_nested_column_inplace(c, selection),
    }
}

#[inline]
fn take_singular_nested_column_inplace(nested_column: &mut SingularNestedColumn, selection: &Sel) {
    let weights = &mut nested_column.weights;
    assert!(selection.max() <= weights.len(), "Selection out of bounds");
    // SAFETY: selection is valid for weights
    take_vector_by_index_inplace(weights, selection);
}

#[inline]
fn take_non_singular_nested_column_inplace(
    nested_column: &mut NonSingularNestedColumn,
    selection: &Sel,
) {
    let weights = &mut nested_column.weights;
    assert!(selection.max() <= weights.len(), "Selection out of bounds");
    take_vector_by_index_inplace(weights, selection);
    let hols = &mut nested_column.hols;
    assert!(selection.max() <= hols.len(), "Selection out of bounds");
    take_vector_by_index_inplace(hols, selection);
}

/// Take rows of a vector by index from a selection vector, mutating the vector in place
/// Assumes that the indices in the selection vector are monotonically increasing, and valid for the vector.
/// It is undefined behavior if this is not the case.
#[inline]
fn take_vector_by_index_inplace<T>(vec: &mut Vec<T>, selection: &Sel)
where
    T: Copy,
{
    assert!(vec.len() >= selection.max(), "Selection out of bounds");
    let mut head: usize = 0;
    for idx in selection.iter() {
        // SAFETY: idx is always in bounds
        let src = unsafe { *vec.get_unchecked(idx) };
        // SAFETY: head is always in bounds  ?
        let dst = unsafe { vec.get_unchecked_mut(head) };
        *dst = src;
        head += 1;
    }
    vec.truncate(selection.len());
}

#[cfg(test)]
pub mod test {
    use super::*;

    #[test]
    fn test_multiply_two_weight_slices() {
        let a = vec![1, 2, 3];
        let b = vec![4, 5, 6];
        let result = multiply_two_weight_slices(&a, &b);
        assert_eq!(result, vec![4, 10, 18]);
    }

    #[test]
    fn test_multiply_weights_by() {
        let mut a = vec![1, 2, 3];
        let b = vec![4, 5, 6];
        multiply_weights_by(&mut a, &b);
        assert_eq!(a, vec![4, 10, 18]);
    }

    #[test]
    fn test_multiply_weights_three() {
        let a = vec![vec![1, 2, 3], vec![4, 5, 6], vec![7, 8, 9]];
        let result = multiply_weights(a.iter().map(|x| x.as_slice()));
        assert_eq!(result, vec![28, 80, 162]);
    }

    #[test]
    fn test_multiply_weights_two() {
        let a = vec![vec![1, 2, 3], vec![4, 5, 6]];
        let result = multiply_weights(a.iter().map(|x| x.as_slice()));
        assert_eq!(result, vec![4, 10, 18]);
    }

    #[test]
    fn test_multiply_weights_one() {
        let a = vec![vec![1, 2, 3]];
        let result = multiply_weights(a.iter().map(|x| x.as_slice()));
        assert_eq!(result, vec![1, 2, 3]);
    }

    #[test]
    fn test_multiply_weights_none() {
        let a: Vec<Vec<Weight>> = vec![];
        let result = multiply_weights(a.iter().map(|x| x.as_slice()));
        assert!(result.is_empty());
    }
}
