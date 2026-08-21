//! Row storage functionality.
//! This module contains code to translate columnar-based data (i.e., `struct of arrays`
//! in the form of a [RecordBatch]) back and forth to a row based format.
//!
//! The row based format is backed by raw bytes ([`[u8]`]).
//!
//! The row based format is useful because, as e.g. mentioned in [this paper],
//! some database operations, are inherently "row oriented" and less amenable
//! to vectorization. The "classics" are: hash table updates in joins
//! and hash aggregates, as well as comparing tuples in sort /
//! merging.
//!
//! [this paper]: https://db.in.tum.de/~kersten/vectorization_vs_compilation.pdf
//!
//! The row-based layout and the implementation of this module is inspired by:
//! Inspired by:
//! - the duckdb row format (https://github.com/duckdb/duckdb/blob/e5716b925d6f987c1a0dcb9d8657a61be9fe8d2a/src/common/types/row/row_layout.cpp,
//!   also description in https://duckdb.org/2021/08/27/external-sorting.html, )
//! - some aspects of the datafusion row format
//!   (https://docs.rs/datafusion-row/latest/datafusion_row/, support was removed in version 28.0.0)
//!

use std::hash::{Hash, Hasher};
use std::sync::Arc;

use datafusion::arrow;

use arrow::array::{Array, ArrayRef, AsArray};
use arrow::array::{ArrayAccessor, FixedSizeBinaryArray};
use arrow::array::{ArrayDataBuilder, BufferBuilder, PrimitiveBuilder};
use arrow::datatypes::DataType;
use arrow::downcast_primitive_array;
use arrow::util::bit_util::{get_bit_raw, set_bit_raw, unset_bit_raw};
use datafusion::arrow::array::PrimitiveArray;
use datafusion::arrow::datatypes::ArrowPrimitiveType;

use self::fixed::{FixedLengthEncoding, FromSlice};
pub use self::layout::RowLayout;

use crate::sel::Selection;

pub mod fixed;
mod layout;

#[derive(Debug, Default)]
pub struct Rows {
    /// The layout of each row.
    layout: Arc<RowLayout>,
    /// The actual data of the rows.
    data: Vec<u8>,
    // TODO For variable size rows:
    // heap: Vec<ArrayRef>,
}

impl Rows {
    /// Returns an empty [`Rows`] with capacity for `row_capacity` rows adhering to `layout` Rowlayout
    pub fn new(layout: Arc<RowLayout>, row_capacity: usize) -> Self {
        // The total capacity of the data buffer, in bytes, to hold row_capacity rows
        let data_capacity = row_capacity * layout.row_width();
        let data = Vec::with_capacity(data_capacity);
        Self { layout, data }
    }

    /// Reserve capacity for `additional` more rows to be appended to `self`.
    /// The underlying data buffer may reserve more space than requested to speculatively avoid frequent reallocations.
    /// Does nothing if the capacity is already sufficient.
    /// See [`Vec::reserve`] for more information.
    #[inline(always)]
    pub fn reserve(&mut self, additional: usize) {
        let row_width = self.layout.row_width();
        self.data.reserve(additional * row_width);
    }

    /// Clear all rows from `self`, but retain the allocated memory for future use.
    #[inline(always)]
    pub fn clear(&mut self) {
        self.data.clear();
    }

    /// Returns the layout of the rows in this [`Rows`] object
    #[inline(always)]
    pub fn layout(&self) -> &Arc<RowLayout> {
        &self.layout
    }

    /// Returns an (immutable) `Row` object for the row at `row_index`
    #[inline(always)]
    pub fn row(&self, row_index: usize) -> Row {
        let row_width = self.layout.row_width();
        let start = row_index * row_width;
        let end = start + row_width;

        Row {
            layout: &self.layout,
            data: &self.data[start..end],
        }
    }

    /// Returns a (mutable) `RowMut` object for the row at `row_index`
    #[inline(always)]
    pub fn row_mut(&mut self, row_index: usize) -> RowMut {
        let row_width = self.layout.row_width();
        let start = row_index * row_width;
        let end = start + row_width;

        RowMut {
            layout: &self.layout,
            data: &mut self.data[start..end],
        }
    }

    /// Append new row to `self`.
    ///
    /// Row is initialized with zeros (not NULL) by setting all bytes to 0x00.
    /// Returns a [`RowMut`] that can be used to set the actual row values.
    pub fn append_row(&mut self) -> RowMut {
        let existing_buffer_length = self.data.len();

        // Reserve space for one more row
        let to_reserve = self.layout.row_width();

        // We initialize all bytes in the new rows with 0x00.
        // This ensures that all null bits, if they are present, are set to 0 (valid, non-null).
        // All field values are hence initialized as zero.
        self.data
            .resize(existing_buffer_length + to_reserve, 0x00_u8);

        self.row_mut(self.num_rows() - 1)
    }

    /// Append the rows in `columns` to `self`.
    ///
    /// # Panics
    ///
    /// Panics if:
    /// - the schema of `columns` does not match that provided of [`Rows::layout()`]; or
    /// - one of the columns is shorter than the first column
    pub fn append(&mut self, columns: &[ArrayRef]) {
        // Get the length of the first column, and call append_sel on all columns with a selection of 0..len
        columns
            .first()
            .map(|x| self.append_sel(columns, 0..x.len()));
    }

    /// Append a selection of the rows in `columns` to `self`
    /// The selection is specified by `sel`, which is a [Selection] of row indices to be taken from `columns`.
    ///
    /// # Panics
    ///
    /// Panics if:
    /// - the schema of `columns` does not match that provided of [`Rows::layout()`]; or
    /// - the selection is invalid for one of the given colums (meaning the selection does not guarantee that elements are within the bounds of the column)
    pub fn append_sel<S: Selection>(&mut self, columns: &[ArrayRef], sel: S) {
        let schema = self.layout.schema();
        let row_width = self.layout.row_width();

        assert!(
            schema.fields().len() == columns.len(),
            "Number of columns in schema ({}) does not match number of columns to be appended ({})",
            schema.fields().len(),
            columns.len()
        );

        let existing_buffer_length = self.data.len();

        // The number of to-be-appended rows
        let num_new_rows = sel.len();

        // Reserve enough space for the to-be-appended rows
        let to_reserve = num_new_rows * row_width;

        // We initialize all bytes in the new rows with 0x00.
        // This ensures that all null bits, if they are present, are set to 0 (valid, non-null).
        // All field values are hence initialized as zero.
        // If a field value is later found to null, it will be correctly set by convert_column_sel.
        self.data
            .resize(existing_buffer_length + to_reserve, 0x00_u8);

        let buffer = &mut self.data[existing_buffer_length..];

        // Append each column to the data buffer
        for (idx, (column, field)) in columns.iter().zip(schema.fields().iter()).enumerate() {
            assert!(
                column.data_type().equals_datatype(&field.data_type()),
                "Schema mismatch while appending columns to rows: column {}, expected {} in layout got {}",
                idx,
                field.data_type(),
                column.data_type()
            );

            convert_column_sel(column.as_ref(), &sel, buffer, &self.layout, idx);
        }
    }

    /// The number of rows in this [`Rows`] object
    #[inline]
    pub fn num_rows(&self) -> usize {
        self.data.len() / self.layout.row_width()
    }

    /// Returns an iterator over the [`Row`]s in this [`Rows`] object
    pub fn iter(&self) -> RowsIter<'_> {
        self.into_iter()
    }

    /// Returns an iterator over the [`RowMut`]s in this [`Rows`] object
    /// This iterator allows mutating the rows in place.
    pub fn iter_mut(&mut self) -> RowsIterMut<'_> {
        let chunk_iter = self.data.chunks_exact_mut(self.layout.row_width());
        RowsIterMut {
            chunk_iter,
            layout: &self.layout,
        }
    }

    /// Returns an iterator over the [`RowMut`]s in this [`Rows`] object,
    /// starting at the row at `offset`.
    /// This iterator allows mutating the rows in place.
    ///
    /// # Panics
    /// Panics if `offset` is larger than the number of rows in this [`Rows`] object
    pub fn iter_mut_from_offset(&mut self, offset: usize) -> RowsIterMut<'_> {
        let row_width = self.layout.row_width();
        let data = &mut self.data[offset * row_width..];
        let chunk_iter = data.chunks_exact_mut(row_width);
        RowsIterMut {
            chunk_iter,
            layout: &self.layout,
        }
    }
}

impl<'a> IntoIterator for &'a Rows {
    type Item = Row<'a>;
    type IntoIter = RowsIter<'a>;

    fn into_iter(self) -> Self::IntoIter {
        RowsIter {
            chunk_iter: self.data.chunks_exact(self.layout.row_width()),
            layout: &self.layout,
        }
    }
}

/// An iterator over [`Rows`]
#[derive(Debug)]
pub struct RowsIter<'a> {
    chunk_iter: std::slice::ChunksExact<'a, u8>,
    layout: &'a RowLayout,
}

impl<'a> Iterator for RowsIter<'a> {
    type Item = Row<'a>;

    #[inline]
    fn next(&mut self) -> Option<Self::Item> {
        self.chunk_iter.next().map(|data| Row {
            layout: self.layout,
            data,
        })
    }

    #[inline]
    fn size_hint(&self) -> (usize, Option<usize>) {
        self.chunk_iter.size_hint()
    }
}

impl<'a> ExactSizeIterator for RowsIter<'a> {
    #[inline]
    fn len(&self) -> usize {
        self.chunk_iter.len()
    }
}

impl<'a> DoubleEndedIterator for RowsIter<'a> {
    #[inline]
    fn next_back(&mut self) -> Option<Self::Item> {
        self.chunk_iter.next_back().map(|data| Row {
            layout: self.layout,
            data,
        })
    }
}

/// A iterator of [`RowMut`] over [`Rows`]
#[derive(Debug)]
pub struct RowsIterMut<'a> {
    chunk_iter: std::slice::ChunksExactMut<'a, u8>,
    layout: &'a RowLayout,
}

impl<'a> RowsIterMut<'a> {
    pub fn from_slice(slice: &'a mut [u8], layout: &'a RowLayout) -> Self {
        let chunk_iter = slice.chunks_exact_mut(layout.row_width());
        Self { chunk_iter, layout }
    }
}

impl<'a> Iterator for RowsIterMut<'a> {
    type Item = RowMut<'a>;

    #[inline]
    fn next(&mut self) -> Option<Self::Item> {
        self.chunk_iter.next().map(|data| RowMut {
            layout: self.layout,
            data,
        })
    }

    #[inline]
    fn size_hint(&self) -> (usize, Option<usize>) {
        self.chunk_iter.size_hint()
    }
}

impl<'a> ExactSizeIterator for RowsIterMut<'a> {
    #[inline]
    fn len(&self) -> usize {
        self.chunk_iter.len()
    }
}

impl<'a> DoubleEndedIterator for RowsIterMut<'a> {
    #[inline]
    fn next_back(&mut self) -> Option<Self::Item> {
        self.chunk_iter.next_back().map(|data| RowMut {
            layout: self.layout,
            data,
        })
    }
}

/// Converts a selection of a `&dyn Array` column into row format by scattering the column values across the rows.
/// The destination rows have the `layout` [RowLayout] and are encoded in the provided `rows` array.
///
/// ## Dealing with NULL values in array
/// For performance reasons, this method only sets the null bit in rows for values that are null in `column`.
/// Non-NULL values are encoded directly, without unsetting their null bit.
/// This implies that the caller needs to have set the null bit corresponding to this field to 0 for all rows
/// in `data` prior to calling.
///
/// ## Panics
/// Panics if:
/// - `layout.has_null_bitmap()` is false, but the array contains NULL values, as in this case the
///    column cannot be correctly encoded in rows that are valid w.r.t. the given [RowLayout]
/// - `sel` is not valid for `column` (i.e., the selection does not guarantee that elements are within the bounds of the column)
fn convert_column_sel<S: Selection>(
    column: &dyn Array,
    sel: S,
    rows: &mut [u8],
    layout: &RowLayout,
    field_idx: usize,
) {
    // Following use statement is required to make the downcast_primitive_array! macro work (otherwise error `arrow_schema unknown`)
    use arrow::datatypes as arrow_schema;

    downcast_primitive_array! {
        column => encode_primitive_array_sel(column, sel, rows, layout, field_idx),
        DataType::Null => {}
        DataType::Boolean => encode_primitive_array_sel(column.as_boolean(), sel, rows, layout, field_idx),
        DataType::Binary => unimplemented!()
        DataType::LargeBinary => unimplemented!(),
        DataType::Utf8 => unimplemented!(),
        DataType::LargeUtf8 => unimplemented!(),
        DataType::FixedSizeBinary(_) => encode_fixed_size_binary_array_sel(column.as_fixed_size_binary(), sel, rows, layout, field_idx),
        _ => unreachable!(),
    }
}

/// Converts a selection of a [PrimitiveArray] with [FixedLengthEncoding] type into row format by scattering the column values across the rows.
/// The destination rows have the `layout` [RowLayout] and are encoded in the provided `rows` array.
///
/// ## Dealing with NULL values in array
/// For performance reasons, this method only sets the null bit in rows for values that are null in `column`.
/// Non-NULL values are encoded directly, without unsetting their null bit.
/// This implies that the caller needs to have set the null bit corresponding to this field to 0 for all rows
/// in `data` prior to calling.
///
/// ## Panics
/// - Panics if `layout.has_null_bitmap()` is false, but the array contains NULL values, as in this case the
///   column cannot be correctly encoded in rows that are valid w.r.t. the given [RowLayout]
/// - `sel` is not valid for `column` (i.e., the selection does not guarantee that elements are within the bounds of the column)
fn encode_primitive_array_sel<T, A, S>(
    array: A,
    sel: S,
    rows: &mut [u8],
    layout: &RowLayout,
    field_idx: usize,
) where
    T: fixed::FixedLengthEncoding, // This is the native type, for which we know how to encode in a row
    A: ArrayAccessor<Item = T>, // This is any type that implements the ArrayAccessor trait that allows us to get values as T
    S: Selection,
{
    let field_offset = layout.field_offset(field_idx);
    let mut rows = RowsIterMut::from_slice(rows, layout);

    // Check that the selection is valid for this array. This is a precondition for unsafe array access methods that follow.
    // note: checking minimum >= 0 is trivially true because min is a usize.
    assert!(
        sel.max() as usize <= array.len() as usize,
        "Selection maximum index is larger than array length"
    );

    // If there are no NULL values in the array, we can just encode all values without checking for NULLs for each item that we iterate over
    if array.null_count() == 0 {
        for row_idx in sel.iter() {
            // SAFETY: we know that the index is valid because we are iterating unitl array.len()
            let value = unsafe { array.value_unchecked(row_idx as usize) };

            let mut row = rows.next().expect("Not enough rows to hold all values");
            row.set_at_offset(field_offset, value);
        }
    } else {
        // There are NULL values in the array, so we need to check for NULLs for each item that we iterate over
        // and set the corresponding null bit in the row if the value is NULL
        assert!(
            layout.has_null_bitmap(),
            "Array has NULL values, but no null bitmap is present in the row"
        );

        for row_idx in sel.iter() {
            let mut row = rows.next().expect("Not enough rows to hold all values");

            if array.is_null(row_idx as usize) {
                // SAFETY: we know that the field index is valid because calculating field_offset did not fail
                // moreover, we already checked that the null bitmap is present
                // therefore, the null bitmap is present and at least `field_idx` bits wide
                unsafe {
                    row.set_null_unchecked(field_idx);
                }
            } else {
                // SAFETY: we know that the index is valid
                let value = unsafe { array.value_unchecked(row_idx as usize) };
                row.set_at_offset(field_offset, value);
            }
        }
    }
}

/// Converts a selection of a [FixedSizeBinaryArray] column into row format by scattering the column values across the rows.
/// The destination rows have the `layout` [RowLayout] and are encoded in the provided `rows` array.
///
/// ## Dealing with NULL values in array
/// For performance reasons, this method only sets the null bit in rows for values that are null in `column`.
/// Non-NULL values are encoded directly, without unsetting their null bit.
/// This implies that the caller needs to have set the null bit corresponding to this field to 0 for all rows
/// in `data` prior to calling.
///
/// ## Panics
/// Panics if
/// - `layout.has_null_bitmap()` is false, but the array contains NULL values, as in this case the
/// column cannot be correctly encoded in rows that are valid w.r.t. the given [RowLayout]
/// - `sel` is not valid for `column` (i.e., the selection does not guarantee that elements are within the bounds of the column)
/// - the values in the FixedSizeBinaryArray are not of the correct size (i.e., the size that was specified in the layout)
fn encode_fixed_size_binary_array_sel<S>(
    array: &FixedSizeBinaryArray,
    sel: S,
    rows: &mut [u8],
    layout: &RowLayout,
    field_idx: usize,
) where
    S: Selection,
{
    let field_width = layout.field_width(field_idx);

    assert!(
        array.value_length() as usize == field_width,
        "FixedSizeBinaryArray value length does not match width of field {} in layout: expected {}, got {}",
        field_idx,
        field_width,
        array.value_length()
    );

    let field_offset = layout.field_offset(field_idx);
    let mut rows = RowsIterMut::from_slice(rows, layout);

    // Check that the selection is valid for this array. This is a precondition for unsafe array access methods that follow.
    // note: checking minimum >= 0 is trivially true because min is a usize.
    assert!(
        sel.max() as usize <= array.len() as usize,
        "Selection maximum index is larger than array length"
    );

    // If there are no NULL values in the array, we can just encode all values without checking for NULLs for each item that we iterate over
    if array.null_count() == 0 {
        // No NULL values in array, so we can just encode all values without checking
        // for NULLs for each item that we iterate over
        for row_idx in sel.iter() {
            // SAFETY: we know that the index is valid
            let value = unsafe { array.value_unchecked(row_idx as usize) };
            let mut row = rows.next().expect("Not enough rows to hold all values");
            row.set_slice_at_offset(field_offset, value);
        }
    } else {
        // There are NULL values in the array, so we need to check for NULLs for each item that we iterate over
        // and set the corresponding null bit in the row if the value is NULL
        assert!(
            layout.has_null_bitmap(),
            "Array has NULL values, but no null bitmap is present in the row"
        );

        for row_idx in sel.iter() {
            let mut row = rows.next().expect("Not enough rows to hold all values");
            if array.is_null(row_idx as usize) {
                // SAFETY: we know that the field index is valid because calculating field_offset did not fail
                // moreover, we already checked that the null bitmap is present
                // therefore, the null bitmap is present and at least `field_idx` bits wide
                unsafe {
                    row.set_null_unchecked(field_idx);
                }
            } else {
                // SAFETY: we know that the index is valid
                let value = unsafe { array.value_unchecked(row_idx as usize) };
                row.set_slice_at_offset(field_offset, value);
            }
        }
    }
}

// TODO
fn encode_var_length_array(
    _array: &dyn Array,
    _rows: &mut [u8],
    _layout: &RowLayout,
    _field_idx: usize,
) {
    unimplemented!()
}

/// Decodes a `PrimitiveArray` from rows based on the provided `FixedLengthEncoding` `T`
/// TODO: change code to use the RowIter and Row functionality internally (cf convert_primitive_column)
fn decode_primitive<T: ArrowPrimitiveType>(
    rows: &[u8],
    layout: &RowLayout,
    field_idx: usize,
) -> PrimitiveArray<T>
where
    T::Native: FixedLengthEncoding,
{
    let row_width = layout.row_width();
    let field = layout.schema().field(field_idx);
    let field_offset = layout.field_offset(field_idx);
    let len = rows.len() / row_width;

    assert!(PrimitiveArray::<T>::is_compatible(field.data_type()));

    let mut rows = rows;

    if !field.is_nullable() {
        // No need to allocate a null buffer or decode NULL values
        let mut values = BufferBuilder::<T::Native>::new(len);
        for _idx in 0..len {
            let start = field_offset;
            let end = start + T::Native::ENCODED_LEN;
            let value = <T::Native as FixedLengthEncoding>::Encoded::from_slice(&rows[start..end]);
            values.append(T::Native::decode(value));
            rows = &rows[row_width..];
        }
        let builder = ArrayDataBuilder::new(field.data_type().clone())
            .len(len)
            .null_count(0)
            .add_buffer(values.finish())
            .null_bit_buffer(None);

        // SAFETY: Buffers correct length
        unsafe { builder.build_unchecked() }.into()
    } else {
        // NOTE: I would like to use NullBufferBuilder here, as PrimitiveBuilder does internally.
        // However, for some reason this is not accessible from the DataFusion version of Arrow?

        let mut builder = PrimitiveBuilder::<T>::with_capacity(len);
        for _idx in 0..len {
            let field_is_valid = unsafe { get_bit_raw(rows.as_ptr(), field_idx) };
            if field_is_valid {
                let start = field_offset;
                let end = start + <T::Native as FixedLengthEncoding>::ENCODED_LEN;
                let value =
                    <T::Native as FixedLengthEncoding>::Encoded::from_slice(&rows[start..end]);
                builder.append_value(T::Native::decode(value));
            } else {
                builder.append_null();
            }
            rows = &rows[row_width..];
        }
        builder.finish()
    }
}

/// An immutable representation of a row.
#[derive(Debug)]
pub struct Row<'a> {
    /// The layout of the row
    layout: &'a RowLayout,
    /// The actual data of the row
    data: &'a [u8],
}

impl<'a> Row<'a> {
    /// Get the null bitmap of the row.
    fn null_bitmap(&self) -> &[u8] {
        let null_bitmap_width = self.layout.null_bitmap_width();
        &self.data[..null_bitmap_width]
    }

    /// Whether the field at `field_index` is valid (non-null).
    /// Equivalent to `!is_null(field_index)`.
    #[inline(always)]
    pub fn is_valid(&self, field_index: usize) -> bool {
        self.layout.null_free() || unsafe { !get_bit_raw(self.null_bitmap().as_ptr(), field_index) }
    }

    /// Whether the field at `field_index` is null.
    /// Equivalent to `!is_valid(field_index)`.
    #[inline(always)]
    pub fn is_null(&self, field_index: usize) -> bool {
        !self.is_valid(field_index)
    }

    /// Whether any of the regular fields is null.
    #[inline(always)]
    pub fn contains_null(&self) -> bool {
        if self.layout.null_free() {
            false
        } else {
            let n_fields = self.layout.num_regular_fields();
            let null_bitmap = self.null_bitmap().as_ptr();
            (0..n_fields).any(|i| unsafe { get_bit_raw(null_bitmap, i) })
        }
    }

    /// Get the value at the field at `field_index`, assuming it is valid (non-null) and of type T.
    /// If the field is actually invalid (null), the returned value is undefined. Use get_opt if you want to handle nulls.
    /// This method is particularly useful if one knows that the field can never be null.
    ///
    /// Note that for performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, false)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![1u32]);
    /// # let b = PrimitiveArray::from(vec![f16::from_f32(3.0)]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32, b: f16}
    /// let row = rows.row(0);
    /// let value1: u32 = row.get(0);
    /// let value2      = row.get::<f16>(1);
    /// ```
    #[inline(always)]
    pub fn get<T>(&self, field_index: usize) -> T
    where
        T: FixedLengthEncoding,
    {
        self.get_at_offset(self.layout.field_offset(field_index))
    }

    /// Same as [`Row::get`] but for extra fields.
    #[inline(always)]
    pub fn get_extra<T>(&self, field_index: usize) -> T
    where
        T: FixedLengthEncoding,
    {
        self.get_at_offset(self.layout.extra_field_offset(field_index))
    }

    /// Get the value at the at byte offset `field_offset` in the row, assuming it is valid (non-null) and of type T.
    /// If the field is actually invalid (null), the returned value is undefined. Use get_opt_at_offset if you want to handle nulls.
    /// This method is particularly useful if one knows that the field can never be null.
    ///
    /// Note that for performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, false)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![1u32]);
    /// # let b = PrimitiveArray::from(vec![f16::from_f32(3.0)]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32, b: f16} without null bitmap
    /// let row = rows.row(0);
    /// let value1: u32 = row.get_at_offset(0);
    /// let value2      = row.get_at_offset::<f16>(4);
    /// ```
    #[inline(always)]
    pub fn get_at_offset<T>(&self, field_offset: usize) -> T
    where
        T: FixedLengthEncoding,
    {
        let end = field_offset + T::ENCODED_LEN;
        let encoded = T::Encoded::from_slice(&self.data[field_offset..end]);
        T::decode(encoded)
    }

    /// Get the value at the field at `field_index`, assuming it is of type T.
    /// Returns an Option<T> where None indicates that the field is invalid (null).
    ///
    /// Note that for performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, true),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, false)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![Some(1u32)]);
    /// # let b = PrimitiveArray::from(vec![f16::from_f32(3.0)]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32?, b: f16}
    /// let row = rows.row(0);
    /// let value1: Option<u32> = row.get_opt(0);
    /// let value2             = row.get_opt::<f16>(1);
    /// ```
    #[inline(always)]
    pub fn get_opt<T>(&self, field_index: usize) -> Option<T>
    where
        T: FixedLengthEncoding,
    {
        self.get_opt_at_offset(field_index, self.layout.field_offset(field_index))
    }

    /// Same as [`Row::get_opt`] but for extra fields.
    #[inline(always)]
    pub fn get_opt_extra<T>(&self, field_index: usize) -> Option<T>
    where
        T: FixedLengthEncoding,
    {
        self.get_opt_at_offset(field_index, self.layout.extra_field_offset(field_index))
    }

    /// Get the value at the field at byte offset `field_offset`, assuming it is of type T.
    /// Checks the null bit at `field_index` to determine whether the field is valid (non-null).
    /// Returns an Option<T> where None indicates that the field is invalid (null).
    ///
    /// This is a low-level API and may panic if the offset is incorrectly given.
    /// Users should prefer get_opt<T> instead, which takes a field index instead of an offset.
    ///
    /// Note that for performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, true),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, true)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![Some(1u32)]);
    /// # let b = PrimitiveArray::from(vec![Some(f16::from_f32(3.0))]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32?, b: f16?} and a 1-byte null bitmap
    /// let row = rows.row(0);
    /// let value1: Option<u32> = row.get_opt_at_offset(0, 1);
    /// let value2              = row.get_opt_at_offset::<f16>(1, 5);
    /// ```
    #[inline(always)]
    pub fn get_opt_at_offset<T>(&self, field_index: usize, field_offset: usize) -> Option<T>
    where
        T: FixedLengthEncoding,
    {
        if self.is_valid(field_index) {
            Some(self.get_at_offset(field_offset))
        } else {
            None
        }
    }

    /// Check if `self` is equal to `other`.
    ///
    /// Two rows are equal if they have
    /// - the same schema, and
    /// - the same underlying data buffer
    ///
    /// If two rows are equal except for their padding, they are also considered equal.
    #[inline(always)]
    pub fn eq(&self, other: &Self) -> bool {
        self.layout.full_schema() == other.layout.full_schema() && self.eq_unchecked(other)
    }

    // Check if `self` is equal to `other`, assuming that `self` and `other` have the same schema.
    #[inline(always)]
    pub fn eq_unchecked(&self, other: &Self) -> bool {
        self.data[..self.layout.null_bitmap_width() + self.layout.data_width()]
            == other.data[..other.layout.null_bitmap_width() + other.layout.data_width()]
    }

    /// Same as [`Row::eq`], but ignores extra fields.
    #[inline(always)]
    pub fn prefix_eq(&self, other: &Self) -> bool {
        self.layout.schema() == other.layout.schema() && self.prefix_eq_unchecked(other)
    }

    /// Same as [`Row::eq_unchecked`], but ignores extra fields.
    #[inline(always)]
    pub fn prefix_eq_unchecked(&self, other: &Self) -> bool {
        self.data[..self.layout.null_bitmap_width() + self.layout.regular_data_width()]
            == other.data[..other.layout.null_bitmap_width() + other.layout.regular_data_width()]
    }
}

impl<'a> Hash for Row<'a> {
    #[inline]
    fn hash<H: Hasher>(&self, state: &mut H) {
        // Hash only the regular fields, not the extra fields
        let prefix =
            &self.data[..self.layout.null_bitmap_width() + self.layout.regular_data_width()];
        prefix.hash(state)
    }
}

/// A mutable representation of a row. In contrast to `Row`, this struct allows setting values.
pub struct RowMut<'a> {
    /// The layout of the row
    layout: &'a RowLayout,
    /// The actual data of the row
    data: &'a mut [u8],
}

impl<'a> RowMut<'a> {
    /// Get an immutable version of this Mutable Row.
    /// Note: compiler should be able to optimize this away fully
    #[inline]
    fn as_row(&self) -> Row<'_> {
        Row {
            layout: self.layout,
            data: self.data,
        }
    }

    /// Whether the field at `field_index` is valid (non-null).
    /// Equivalent to `!is_null(field_index)`.
    #[inline(always)]
    pub fn is_valid(&self, field_index: usize) -> bool {
        self.as_row().is_valid(field_index)
    }

    /// Whether the field at `field_index` is null.
    /// Equivalent to `!is_valid(field_index)`.
    #[inline(always)]
    pub fn is_null(&self, field_index: usize) -> bool {
        self.as_row().is_null(field_index)
    }

    /// Get the value at the field at `field_index`, assuming it is valid (non-null) and of type T.
    /// See [Row::get] for more details.
    #[inline(always)]
    pub fn get<T>(&self, field_index: usize) -> T
    where
        T: FixedLengthEncoding,
    {
        self.as_row().get(field_index)
    }

    /// Same as [`RowMut::get`] but for extra fields.
    #[inline(always)]
    pub fn get_extra<T>(&self, field_index: usize) -> T
    where
        T: FixedLengthEncoding,
    {
        self.as_row().get_extra(field_index)
    }

    /// Get the value at the field at `field_index`, assuming it is of type T.
    /// Returns an Option<T> where None indicates that the field is invalid (null).
    /// See [Row::get] for more details.
    #[inline(always)]
    pub fn get_opt<T>(&self, field_index: usize) -> Option<T>
    where
        T: FixedLengthEncoding,
    {
        self.as_row().get_opt(field_index)
    }

    /// Same as [`RowMut::get_opt`] but for extra fields.
    #[inline(always)]
    pub fn get_opt_extra<T>(&self, field_index: usize) -> Option<T>
    where
        T: FixedLengthEncoding,
    {
        self.as_row().get_opt_extra(field_index)
    }

    /// Store `value` in the field at `field_index`.
    ///
    /// Note that this method does *not* alter the null bit of the field in any way.
    /// Use set_opt to ensure that the null bit is correctly set.
    ///
    /// Also note that for performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, false)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![1u32]);
    /// # let b = PrimitiveArray::from(vec![f16::from_f32(3.0)]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32, b: f16}
    /// let mut row = rows.row_mut(0);
    /// row.set(0, 42u32);
    /// row.set(1, f16::from_f32(3.14));
    /// ```
    #[inline(always)]
    pub fn set<T>(&mut self, field_index: usize, value: T)
    where
        T: FixedLengthEncoding,
    {
        self.set_at_offset(self.layout.field_offset(field_index), value);
    }

    /// Same as [`RowMut::set`] but for extra fields.
    #[inline(always)]
    pub fn set_extra<T>(&mut self, field_index: usize, value: T)
    where
        T: FixedLengthEncoding,
    {
        self.set_at_offset(self.layout.extra_field_offset(field_index), value);
    }

    /// Store `value` in the field that begins at byte `field_offset` in the row.
    /// This is a low-level API and may panic if the offset is incorrectly given.
    /// Users should prefer set<T> instead, which takes a field index instead of an offset.
    ///
    /// Note that this method does *not* alter the null bit of the field in any way.
    /// Use set_opt_at_offset to ensure that the null bit is correctly set.
    ///
    /// Also note that for performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    /// # Panics
    /// Panics if field_offset does not leave enough bytes to encode the field
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, false)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![1u32]);
    /// # let b = PrimitiveArray::from(vec![f16::from_f32(3.0)]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// //assume rows is a Rows object storing rows of Schema {a: u32, b: f16} and no bull bitmap is present
    /// let mut row = rows.row_mut(0);
    /// row.set_at_offset(0, 42u32);
    /// row.set_at_offset(4, f16::from_f32(3.14));
    /// ```
    #[inline(always)]
    pub fn set_at_offset<T>(&mut self, field_offset: usize, value: T)
    where
        T: FixedLengthEncoding,
    {
        let end = field_offset + T::ENCODED_LEN;

        // Types that implement FixedLengthEncoding allow encoded values to be byte slices by means of as_ref()
        // because of the bound FixedLengthEncoding::Encoded: AsRef<[u8]>.
        self.data[field_offset..end].copy_from_slice(value.encode().as_ref());
    }

    /// Store `value` in the field at `field_index`:
    /// If `value == Some(v)` then unset the null bit and store v in the field, otherwise set the null bit.
    ///
    /// For performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, true),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, false)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![Some(1u32)]);
    /// # let b = PrimitiveArray::from(vec![f16::from_f32(3.0)]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32?, b: f16}
    /// let mut row = rows.row_mut(0);
    /// row.set_opt(0, Some(42u32));
    /// ```
    #[inline(always)]
    pub fn set_opt<T>(&mut self, field_index: usize, value: Option<T>)
    where
        T: FixedLengthEncoding,
    {
        self.set_opt_at_offset(field_index, self.layout.field_offset(field_index), value);
    }

    /// Same as [`RowMut::set_opt`] but for extra fields.
    #[inline(always)]
    pub fn set_opt_extra<T>(&mut self, field_index: usize, value: Option<T>)
    where
        T: FixedLengthEncoding,
    {
        self.set_opt_at_offset(
            field_index,
            self.layout.extra_field_offset(field_index),
            value,
        );
    }

    /// Store `value` in the field that starts at byte offset `field_offset` in the row.
    /// If `value == Some(v)` then unset the null bit at `field_idx` and store v at the given offset, otherwise set the null bit.
    ///
    /// For performance reasons, we do not check that the field is of type T in the layout schema.
    /// This is the responsibility of the caller.
    ///
    /// # Example:
    /// ```
    /// # use std::sync::Arc;
    /// # use yannakakis_join_implementation::row::Rows;
    /// # use yannakakis_join_implementation::row::Row;
    /// # use yannakakis_join_implementation::row::RowLayout;
    /// # use half::f16;
    /// # use datafusion::arrow;
    /// # use arrow::array::PrimitiveArray;
    /// # let schema = Arc::new(arrow::datatypes::Schema::new(vec![
    /// #     arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, true),
    /// #     arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float16, true)]));
    /// # let layout = RowLayout::new(schema, true);
    /// # let mut rows = Rows::new(Arc::new(layout), 2);
    /// # let a = PrimitiveArray::from(vec![Some(1u32)]);
    /// # let b = PrimitiveArray::from(vec![Some(f16::from_f32(3.0))]);
    /// # rows.append(&[Arc::new(a), Arc::new(b)]);
    /// #
    /// // assume rows is a Rows object storing rows of Schema {a: u32?, b: f16?} and a null bitmap of 1 byte
    /// let mut row = rows.row_mut(0);
    /// row.set_opt_at_offset(0, 1, Some(42u32));
    /// row.set_opt_at_offset(1, 5, Some(f16::from_f32(3.14)));
    /// ```
    #[inline(always)]
    pub fn set_opt_at_offset<T>(
        &mut self,
        field_index: usize,
        field_offset: usize,
        value: Option<T>,
    ) where
        T: FixedLengthEncoding,
    {
        match value {
            Some(v) => {
                self.set_valid(field_index);
                self.set_at_offset(field_offset, v);
            }
            None => self.set_null(field_index),
        }
    }

    /// Store a slice of u8 in the field at `field_index`
    /// This is intended for those fields whose datatype is [DataType::FixedSizeBinary(_)]
    ///
    /// Note that this method does *not* alter the null bit of the field in any way.
    /// Use set_slice_opt_at_offset to ensure that the null bit is correctly set.
    ///
    /// Also note that for performance reasons, we do not check that the field is is indeed of
    /// datatype [DataType::FixedSizeBinary(l)]  with `l == value.len()`
    /// This is the responsibility of the caller.
    ///
    /// # Panics
    /// Panics if field_offset does not leave enough bytes to encode the field
    #[inline(always)]
    pub fn set_slice(&mut self, field_index: usize, value: &[u8]) {
        self.set_slice_at_offset(self.layout.field_offset(field_index), value)
    }

    /// Store a slice of u8 in the field that begins at byte `field_offset` in the row.
    /// This is intended for those fields whose datatype is [DataType::FixedSizeBinary(_)]
    /// This is a low-level API and may panic if the offset is incorrectly given.
    /// Users should prefer set_slice instead, which takes a field index instead of an offset.
    ///
    /// Note that this method does *not* alter the null bit of the field in any way.
    /// Use set_slice_opt_at_offset to ensure that the null bit is correctly set.
    ///
    /// Also note that for performance reasons, we do not check that the field is is indeed of
    /// datatype [DataType::FixedSizeBinary(l)]  with `l == value.len()`
    /// This is the responsibility of the caller.
    ///
    /// # Panics
    /// Panics if field_offset does not leave enough bytes to encode the field
    #[inline(always)]
    pub fn set_slice_at_offset(&mut self, field_offset: usize, value: &[u8]) {
        let end = field_offset + value.len();
        self.data[field_offset..end].copy_from_slice(value);
    }

    /// Store a slice of u8 in `value` in the field at `field_index`
    /// If `value == Some(v)` then set the null bit at `field_idx` and store v at the given offset, otherwise clear the null bit.
    /// This is intended for those fields whose datatype is [DataType::FixedSizeBinary(_)]
    ///
    /// For performance reasons, we do not check that the field is is indeed of
    /// datatype [DataType::FixedSizeBinary(l)]  with `l == value.len()`
    /// This is the responsibility of the caller.
    ///
    /// # Panics
    /// Panics if field_offset does not leave enough bytes to encode the field
    #[inline(always)]
    pub fn set_slice_opt(&mut self, field_index: usize, value: Option<&[u8]>) {
        self.set_slice_at_offset_opt(field_index, self.layout.field_offset(field_index), value)
    }

    /// Store a slice of u8 in the field that begins at byte `field_offset` in the row.
    /// If `value == Some(v)` then set the null bit at `field_idx` and store v at the given offset, otherwise clear the null bit.
    /// This is intended for those fields whose datatype is [DataType::FixedSizeBinary(_)]
    ///
    /// For performance reasons, we do not check that the field is is indeed of
    /// datatype [DataType::FixedSizeBinary(l)]  with `l == value.len()`
    /// This is the responsibility of the caller.
    ///
    /// # Panics
    /// Panics if field_offset does not leave enough bytes to encode the field
    #[inline(always)]
    pub fn set_slice_at_offset_opt(
        &mut self,
        field_index: usize,
        field_offset: usize,
        value: Option<&[u8]>,
    ) {
        match value {
            Some(v) => {
                self.set_valid(field_index);
                self.set_slice_at_offset(field_offset, v);
            }
            None => self.set_null(field_index),
        }
    }

    /// Copy prefix of `other` into this row.
    /// The prefix is the part of the row that corresponds to the regular fields of the schema (including the null bitmap).
    ///
    /// For performance reasons, we do not check that the prefix schemas of `other` and `self` are equal.
    /// This is the responsibility of the caller.
    ///
    /// # Panics
    /// Panics if the prefix of `other` and the prefix of `self` have unequal lengths.
    #[inline(always)]
    pub fn copy_prefix_from(&mut self, other: &Row<'_>) {
        let prefix =
            &mut self.data[..self.layout.null_bitmap_width() + self.layout.regular_data_width()];

        let other_prefix =
            &other.data[..self.layout.null_bitmap_width() + self.layout.regular_data_width()];

        prefix.copy_from_slice(other_prefix);
    }

    #[inline(always)]
    /// Set the null bit of field at `field_index` to 0 (valid, non-null).
    pub fn set_valid(&mut self, field_index: usize) {
        if !self.layout.null_free() {
            assert!(field_index < self.layout.num_fields());
            unsafe { self.set_valid_unchecked(field_index) }
        }
    }

    #[inline(always)]
    /// Set the null bit of field at `field_index` to 0 (valid, non-null).
    /// Assumes that null bitmap is present (i.e., self.layout.all_null() is false).
    /// Does not check that field_index is valid.
    pub unsafe fn set_valid_unchecked(&mut self, field_index: usize) {
        // the null bitmap is at the beginning of the slice, so modify that directly
        unset_bit_raw(self.data.as_mut_ptr(), field_index)
    }

    #[inline(always)]
    /// Set the null bit of field at `field_index` to 1.
    pub fn set_null(&mut self, field_index: usize) {
        if !self.layout.null_free() {
            assert!(field_index < self.layout.num_fields());
            unsafe { self.set_null_unchecked(field_index) }
        }
    }

    #[inline(always)]
    /// Set the null bit of field at `field_index` to 1.
    /// Assumes that null bitmap is present (i.e., self.layout.all_null() is false).
    /// Does not check that field_index is valid.
    pub unsafe fn set_null_unchecked(&mut self, field_index: usize) {
        // the null bitmap is at the beginning of the slice, so modify that directly
        set_bit_raw(self.data.as_mut_ptr(), field_index)
    }

    /// Check if `self` is equal to `other`.
    ///
    /// Two rows are equal if they have
    /// - the same schema, and
    /// - the same underlying data buffer
    ///
    /// If two rows are equal except for their padding, they are also considered equal.
    #[inline(always)]
    pub fn eq(&self, other: &Self) -> bool {
        self.as_row().eq(&other.as_row())
    }

    /// Check if `self` is equal to `other`, assuming that `self` and `other` have the same schema.
    #[inline(always)]
    pub fn eq_unchecked(&self, other: &Self) -> bool {
        self.as_row().eq_unchecked(&other.as_row())
    }

    /// Same as [`RowMut::eq`], but ignores extra fields.
    #[inline(always)]
    pub fn prefix_eq(&self, other: &Self) -> bool {
        self.as_row().prefix_eq(&other.as_row())
    }

    /// Same as [`RowMut::eq_unchecked`], but ignores extra fields.
    #[inline(always)]
    pub fn prefix_eq_unchecked(&self, other: &Self) -> bool {
        self.as_row().prefix_eq_unchecked(&other.as_row())
    }
}

impl<'a> Hash for RowMut<'a> {
    #[inline]
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.data.hash(state)
    }
}

#[cfg(test)]
mod test {
    use datafusion::arrow;

    use arrow::array::PrimitiveArray;
    use std::sync::Arc;

    use crate::sel::ArraySelection;

    use super::*;

    /// Example schema: {a: u32, b: f64?}
    ///
    /// Data:
    ///     - a: [1, 2]
    ///     - b: [3.0, NULL]
    fn example_data() -> Rows {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));

        let layout = RowLayout::new(schema, true);

        let mut rows = Rows::new(Arc::new(layout), 2);

        let a = PrimitiveArray::from(vec![1u32, 2u32]);
        let b = PrimitiveArray::from(vec![Some(3.0), None]);

        rows.append(&[Arc::new(a), Arc::new(b)]);
        rows
    }

    /// Regular fields schema: {a: u32, b: f64?}
    /// Extra fields schema: {c: u32, d: u32?}
    ///
    /// Data:
    ///     - a: [1, 2]
    ///     - b: [3.0, NULL]
    /// Extra fields are initialized zero (non-null).
    fn example_data_with_extra() -> Rows {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));
        let extra_fields = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("c", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("d", arrow::datatypes::DataType::UInt32, true),
        ]));

        let layout = RowLayout::with_extra_fields(schema, extra_fields, false);
        let mut rows = Rows::new(Arc::new(layout), 2);

        let a = PrimitiveArray::from(vec![1u32, 2u32]);
        let b = PrimitiveArray::from(vec![Some(3.0), None]);
        rows.append(&[Arc::new(a), Arc::new(b)]);
        rows
    }

    #[test]
    fn test_append_row() {
        let mut rows = example_data();

        let mut new_row = rows.append_row();
        new_row.set(0, 100u32);
        new_row.set_opt(1, Some(200.0f64));

        assert_eq!(rows.num_rows(), 3);
        let new_row = rows.row(2);
        assert_eq!(new_row.get::<u32>(0), 100u32);
        assert_eq!(new_row.get_opt::<f64>(1), Some(200.0f64));
    }

    #[test]
    fn test_append() {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));

        let layout = RowLayout::new(schema, true);

        let mut rows = Rows::new(Arc::new(layout), 2);

        let a = PrimitiveArray::from(vec![1u32, 2u32]);
        let b = PrimitiveArray::from(vec![Some(3.0), None]);

        rows.append(&[Arc::new(a), Arc::new(b)]);

        assert_eq!(rows.num_rows(), 2);

        let row0 = rows.row(0);
        assert_eq!(row0.get::<u32>(0), 1u32);
        assert_eq!(row0.get::<f64>(1), 3.0);

        let row1 = rows.row(1);
        assert_eq!(row1.get::<u32>(0), 2u32);
        assert_eq!(row1.get_opt::<f64>(1), None);
    }

    #[test]
    /// Test append_sel
    fn test_append_sel() {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));

        let layout = RowLayout::new(schema, true);

        let mut rows = Rows::new(Arc::new(layout), 5);

        let a = PrimitiveArray::from(vec![1u32, 2u32, 3u32, 4u32, 5u32]);
        let b = PrimitiveArray::from(vec![Some(1.0), None, Some(3.0), None, Some(5.0)]);

        rows.append_sel(
            &[Arc::new(a), Arc::new(b)],
            ArraySelection::new(0, 5, |x| x % 2 == 0),
        );

        assert_eq!(rows.num_rows(), 3);

        let row0 = rows.row(0);
        assert_eq!(row0.get::<u32>(0), 1u32);
        assert_eq!(row0.get_opt::<f64>(1), Some(1.0));

        let row1 = rows.row(1);
        assert_eq!(row1.get::<u32>(0), 3u32);
        assert_eq!(row1.get_opt::<f64>(1), Some(3.0));

        let row2 = rows.row(2);
        assert_eq!(row2.get::<u32>(0), 5u32);
        assert_eq!(row2.get_opt::<f64>(1), Some(5.0));
    }

    #[test]
    /// Test the is_valid(), is_null() and contains_null() functions
    fn test_isvalid_isnull_containsnull() {
        let rows = example_data();

        let row0 = rows.row(0);
        assert!(row0.is_valid(0) & !row0.is_null(0));
        assert!(row0.is_valid(1) & !row0.is_null(1));
        assert!(!row0.contains_null());
        let row1 = rows.row(1);
        assert!(row1.is_valid(0) & !row1.is_null(0));
        assert!(!row1.is_valid(1) & row1.is_null(1));
        assert!(row1.contains_null());
    }

    #[test]
    /// Test getters and setters for optional values
    fn test_get_set_opt() {
        let mut rows = example_data();

        let mut row0 = rows.row_mut(0);
        assert!(row0.is_valid(1));
        assert_eq!(row0.get_opt::<f64>(1), Some(3.0));

        row0.set_opt::<f64>(1, None);
        assert!(!row0.is_valid(1));
        assert_eq!(row0.get_opt::<f64>(1), None);

        row0.set_opt::<f64>(1, Some(4.0));
        assert!(row0.is_valid(1));
        assert_eq!(row0.get_opt::<f64>(1), Some(4.0));

        // Previous code uses getters of RowMut
        // We will now test getters of Row

        let row0 = rows.row(0);
        assert_eq!(row0.get_opt::<f64>(1), Some(4.0));
        let row1 = rows.row(1);
        assert_eq!(row1.get_opt::<f64>(1), None);
    }

    #[test]
    /// Test getters and setters for non-nullable fields
    fn test_get_set() {
        let mut rows = example_data();

        {
            let mut row0 = rows.row_mut(0);
            row0.set::<u32>(0, 100);
            assert!(row0.is_valid(0));
            assert_eq!(row0.get::<u32>(0), 100);
        }

        {
            let mut row1 = rows.row_mut(1);
            row1.set::<u32>(0, 200);
            assert!(row1.is_valid(0));
            assert_eq!(row1.get::<u32>(0), 200);
        }

        // Previous code uses getters of RowMut
        // We will now test getters of Row

        let row0 = rows.row(0);
        assert!(row0.is_valid(0));
        assert_eq!(row0.get::<u32>(0), 100);
        let row1 = rows.row(1);
        assert!(row1.is_valid(0));
        assert_eq!(row1.get::<u32>(0), 200);
    }

    #[test]
    /// Test getters and setters for extra fields
    fn test_get_set_opt_extra() {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));
        let extra_fields = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("c", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("d", arrow::datatypes::DataType::UInt32, true),
        ]));

        let layout = RowLayout::with_extra_fields(schema, extra_fields, false);
        let mut rows = Rows::new(Arc::new(layout), 2);

        let a = PrimitiveArray::from(vec![1u32, 2u32]);
        let b = PrimitiveArray::from(vec![Some(3.0), None]);
        rows.append(&[Arc::new(a), Arc::new(b)]);

        let mut row0 = rows.row_mut(0);
        row0.set_extra(0, 100u32);
        assert_eq!(row0.get_extra::<u32>(0), 100u32);
        row0.set_opt_extra(1, Some(200u32));
        assert_eq!(row0.get_opt_extra::<u32>(1), Some(200u32));
        row0.set_opt_extra::<u32>(1, None);
        assert_eq!(row0.get_opt_extra::<u32>(1), None);
    }

    #[test]
    /// Test RowsIter
    fn test_rows_iter() {
        let rows = example_data();

        let mut iter = rows.iter();

        let row0 = iter.next().unwrap();
        assert_eq!(row0.get::<u32>(0), 1u32);
        assert_eq!(row0.get_opt::<f64>(1), Some(3.0));

        let row1 = iter.next().unwrap();
        assert_eq!(row1.get::<u32>(0), 2u32);
        assert_eq!(row1.get_opt::<f64>(1), None);

        assert!(iter.next().is_none());
    }

    #[test]
    /// Test RowsIterMut
    fn test_rows_iter_mut() {
        let mut rows = example_data();

        let mut iter = rows.iter_mut();
        let mut row0 = iter.next().unwrap();
        row0.set(0, 3u32);
        row0.set_opt(1, Some(4.0));
        assert_eq!(row0.get::<u32>(0), 3u32);
        assert_eq!(row0.get_opt::<f64>(1), Some(4.0));

        let row1 = iter.next().unwrap();
        assert_eq!(row1.get::<u32>(0), 2u32);
        assert_eq!(row1.get_opt::<f64>(1), None);
        assert!(iter.next().is_none())
    }

    #[test]
    /// Test RowsIterMut starting from a given row
    fn test_rows_iter_mut_from_offset() {
        let mut rows = example_data();

        let mut iter = rows.iter_mut_from_offset(1);
        let row1 = iter.next().unwrap();
        assert_eq!(row1.get::<u32>(0), 2u32);
        assert_eq!(row1.get_opt::<f64>(1), None);
        assert!(iter.next().is_none())
    }

    #[test]
    /// Test copy_prefix
    fn test_copy_prefix() {
        let mut rows = example_data();
        let rows2 = example_data();

        // we want to copy rows2[0] into rows[1]
        let row0 = rows2.row(0);
        let mut row1 = rows.row_mut(1);

        // prefixes are unequal before copying
        assert!(!row0.prefix_eq(&row1.as_row()));

        // prefixes should be equal after copying
        row1.copy_prefix_from(&row0);
        assert!(row0.prefix_eq(&rows.row(1)));
    }

    #[test]
    /// Test that copy_prefix ignores extra fields
    fn test_copy_prefix_ignore_extra_fields() {
        let mut rows = example_data_with_extra();
        let rows2 = example_data_with_extra();

        // we want to copy rows2[0] into rows[1]
        let row0 = rows2.row(0);
        {
            let mut row1 = rows.row_mut(1);
            row1.set_extra(0, 10u32);

            // prefixes should be equal after copying
            row1.copy_prefix_from(&row0);
        }
        let row1 = rows.row(1);
        assert!(row0.prefix_eq(&rows.row(1)));

        // extra fields should be unchanged
        assert_eq!(row1.get_extra::<u32>(0), 10u32);
    }

    #[test]
    /// Test row equality, assuming equal schemas
    fn test_row_eq_unchecked() {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));

        let layout = RowLayout::new(schema.clone(), true);
        let mut rows1 = Rows::new(Arc::new(layout), 5);

        let a = PrimitiveArray::from(vec![1u32, 1u32, 1u32, 1u32]);
        let b = PrimitiveArray::from(vec![Some(3.0), Some(3.0), Some(3.0), Some(3.0)]);
        rows1.append(&[Arc::new(a), Arc::new(b)]);

        {
            // Set the last row of b to None
            // The data portion of the row still equals the encoding of 3.0, but the null bit is set to 1
            // This way, we can check that `eq` compares the null bits!
            let mut row3 = rows1.row_mut(3);
            row3.set_opt::<f64>(1, None);
        }

        let row0 = rows1.row(0);
        let row1 = rows1.row(1);
        let row2 = rows1.row(2);
        let row3 = rows1.row(3);

        assert!(row0.eq_unchecked(&row0));
        assert!(row0.eq_unchecked(&row1));
        assert!(row0.eq_unchecked(&row2));
        assert!(row1.eq_unchecked(&row2));
        assert!(!row0.eq_unchecked(&row3));

        let layout = RowLayout::new(schema, false); // Same layout but without word-alignment
        let mut rows2 = Rows::new(Arc::new(layout), 1);
        let a = PrimitiveArray::from(vec![1u32]);
        let b = PrimitiveArray::from(vec![Some(3.0)]);
        rows2.append(&[Arc::new(a), Arc::new(b)]);

        assert!(row0.eq_unchecked(&rows2.row(0))); // Padding should not matter
    }

    #[test]
    /// Test row equality, including schema check
    fn test_row_eq() {
        // Create two different schemas
        let schema1 = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, true),
        ]));
        let schema2 = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
        ]));

        let layout1 = RowLayout::new(schema1, true);
        let layout2 = RowLayout::new(schema2.clone(), true);
        let layout3 = RowLayout::new(schema2, true);

        let mut rows1 = Rows::new(Arc::new(layout1), 1);
        let mut rows2 = Rows::new(Arc::new(layout2), 1);
        let mut rows3 = Rows::new(Arc::new(layout3), 1);

        let mut row1 = rows1.append_row();
        row1.set_opt(0, Some(100u32));
        let mut row2 = rows2.append_row();
        row2.set(0, 100u32);
        let mut row3 = rows3.append_row();
        row3.set(0, 100u32);

        assert!(!rows1.row(0).eq(&rows2.row(0))); // must differ because of schema
        assert!(rows2.row(0).eq(&rows3.row(0))); // same schema, resolves to equals_unchecked
    }

    #[test]
    /// Test row equality, ignoring extra fields
    fn test_row_prefix_eq() {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));
        let extra_fields = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("c", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("d", arrow::datatypes::DataType::UInt32, true),
        ]));

        let layout = Arc::new(RowLayout::with_extra_fields(schema, extra_fields, false));
        let mut rows = Rows::new(layout, 2);

        let a = PrimitiveArray::from(vec![1u32, 1u32]);
        let b = PrimitiveArray::from(vec![Some(3.0), Some(3.0)]);
        rows.append(&[Arc::new(a.clone()), Arc::new(b.clone())]);

        {
            let mut row0 = rows.row_mut(0);
            row0.set_extra(0, 100u32); // change extra field of first row
        }
        let row0 = rows.row(0);
        let row1 = rows.row(1);
        assert!(row0.prefix_eq(&row1)); // rows still match on their prefix
        assert!(!row0.eq(&row1)); // but not on their full schema
    }

    #[test]
    /// Test that rows are prefilled with 0x00.
    fn test_rows_prefilled_with_zero() {
        let schema = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("a", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("b", arrow::datatypes::DataType::Float64, true),
        ]));

        let layout = RowLayout::new(schema.clone(), false);
        let mut rows = Rows::new(Arc::new(layout), 1);
        let row0 = rows.append_row();
        assert_eq!(row0.get::<u32>(0), 0u32);
        assert_eq!(row0.get_opt::<f64>(1), Some(0.0f64));

        // Rows::append() overwrites only the regular fields,
        // the extra fields are still prefilled with 0x00.
        let extra_fields = Arc::new(arrow::datatypes::Schema::new(vec![
            arrow::datatypes::Field::new("c", arrow::datatypes::DataType::UInt32, false),
            arrow::datatypes::Field::new("d", arrow::datatypes::DataType::UInt32, true),
        ]));
        let layout = RowLayout::with_extra_fields(schema, extra_fields, false);
        let mut rows = Rows::new(Arc::new(layout), 1);
        let a = PrimitiveArray::from(vec![1u32]);
        let b = PrimitiveArray::from(vec![Some(3.0)]);
        rows.append(&[Arc::new(a), Arc::new(b)]);
        let row0 = rows.row(0);
        assert_eq!(row0.get_extra::<u32>(0), 0u32);
        assert_eq!(row0.get_opt_extra::<u32>(1), Some(0u32));
    }
}
