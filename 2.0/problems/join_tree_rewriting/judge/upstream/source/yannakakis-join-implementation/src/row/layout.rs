use std::sync::Arc;

use datafusion::arrow::{
    self,
    array::ArrayRef,
    datatypes::{Field, Schema, SchemaRef},
};

use crate::sel::Selection;

use super::Rows;

/// A RowLayout specifies how records of a given [Schema] are stored as a fixed-width
/// sequence of u8 bytes (a Row).
///
/// *Limitation*: Schemas with variable-length fields are currently not supported.
/// In a later stage, variable-length fields can be supported by having these fields point into a separate
/// heap buffer (cf Duckdb). This implies that the row layout is always fixed-width, for all schemas, but with
/// an extra layer of indirection for variable-length fields.
///
/// Each row consists of two parts: a "`null bitmap`" and "`field values`".
///
/// ```plaintext
/// ┌─────────────────┬─────────────────────┐
/// │  Null Bitmask   │      Field values   │
/// └─────────────────┴─────────────────────┘
/// ```
///
/// When the RowLayout is created with "align=true", then the entire row will be aligned at 8-byte word
/// boundaries. In other words: the row-length is padded to be a multiple of 8-bytes.
///
/// The "`null bitmap`" is a sequence of bits, one bit per field in the schema which indicates
/// whether the value in that field is NULL or not: : the bit is 0 if the field is valid (non-null) and 1 otherwise.
/// If the [Schema] does not allow any fields to be null, then the null bitmap is omitted.
///
///
/// In the region of the "`field values", we store the fields in the order they are defined in the
/// schema. For primitive types, the value is encoded in the same number of bytes as the physical type.
/// (Variable-length types are TODO, as indicated above.)
///
///  For example, given the schema (Int8, Float32, Int64) with a null-free tuple
///
///  Encoding the tuple (1, 3.14, 42)
///
///  Requires 13 bytes (1 + 4 + 8 bytes for each field, respectively), assuming the row is not aligned:
///
/// ```plaintext
/// ┌──────────────────────┬──────────────────────┬──────────────────────┐
/// │         0x01         │      0x4048F5C3      │      0x0000002A      │
/// └──────────────────────┴──────────────────────┴──────────────────────┘
/// 0                      1                      5                     12
/// ```
///
///  If the row is algined, then the row length is padded to 16 bytes:
/// ```plaintext
/// ┌──────────────────────┬──────────────────────┬──────────────────────┐───────┐
/// │         0x01         │      0x4048F5C3      │      0x0000002A      │  pad  │
/// └──────────────────────┴──────────────────────┴──────────────────────┘───────┘
/// 0                      1                      5                     12      15
/// ```
///
///
///  If the schema allows null values and the tuple is (1, NULL, 42)
///
///  Encoding the tuple requires 13 bytes (1 byte for the null bit mask + 12 bytes data). Hence, the layout
///  when not-aligned, aligned is:
///
/// ```plaintext
/// ┌──────────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
/// │       0b00000010         │         0x01         │      0x00000000      │      0x0000002A      │
/// └──────────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
/// 0                          1                      2                      7                     13
/// ```
///
/// # Extra (special purpose) fields
///
/// In addition to the regular fields, a row can also contain special purpose fields, which we call extra fields.
/// These extra fields come with their own schema. The region of the "`field values`" is further subdivided into
/// the "`regular fields`" and the "`extra fields`". The regular fields precede the extra fields.
///
/// ```plaintext
/// ┌─────────────────┬─────────────────────┬────────────────────┐
/// │  Null Bitmask   │    Regular fields   │    Extra fields    │
/// └─────────────────┴─────────────────────┴────────────────────┘
/// ```
///
/// The "`extra fields`" come with their own schema, and are stored in the order they are defined in this schema.
///
/// For example, if the schema of the regular fields is (Int8,Int8) and the schema of the extra fields is
/// (UInt32, UInt32), then the layout of the tuple (1, NULL) with extra field values (42, 43) when not-aligned, is:
///
/// ```plaintext
/// ┌──────────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
/// │       0b00000010         │         0x01         │         0x00         │      0x0000002A      │      0x0000002B      │
/// └──────────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
/// 0                          1                      2                      3                      7                     11
/// ```
#[derive(Clone, Debug)]
pub struct RowLayout {
    /// The schema of the regular fields in the row
    schema: SchemaRef,
    /// The schema of the extra fields in the row
    extra_schema: SchemaRef,
    /// The width of the null bitmap in bytes
    null_bitmap_width: usize,
    /// The width in bytes of the data portion of the row, excluding the null bitmap and excluding alignment padding
    data_width: usize,
    /// The full width of the row (including null bitmap, data, and alignment padding)
    row_width: usize,
    /// The offsets of each regular field in the row
    offsets: Vec<usize>,
    /// The offsets of each extra field in the row
    extra_offsets: Vec<usize>,
    /// Whether all fields are of fixed size
    all_constant: bool,
}

impl Default for RowLayout {
    /// Creates an empty RowLayout
    fn default() -> Self {
        Self {
            schema: Arc::new(Schema::empty()),
            extra_schema: Arc::new(Schema::empty()),
            null_bitmap_width: 0,
            data_width: 0,
            row_width: 0,
            offsets: Vec::new(),
            extra_offsets: Vec::new(),
            all_constant: true,
        }
    }
}

/// Checks if `field` has a fixed-width datatype
#[inline]
fn is_fixed_width(field: &Field) -> bool {
    // See documentation of [arrow_schema::Datatype] to see that below are all fixed-width types
    use arrow::datatypes::DataType::*;
    // Note that we cannot simply use DataType::is_primitive because Boolean is not considered primitive
    matches!(
        field.data_type(),
        Boolean
            | Int8
            | UInt8
            | Int16
            | UInt16
            | Float16
            | Int32
            | UInt32
            | Float32
            | Int64
            | UInt64
            | Float64
            | Timestamp(_, _)
            | Date32
            | Time32(_)
            | Date64
            | Time64(_)
            | Duration(_)
            | Interval(_)
            | Decimal128(_, _)
            | Decimal256(_, _)
    )
}

/// Returns the number of bytes required to store values of `field` in a row.
#[inline]
fn field_width(field: &Field) -> usize {
    use arrow::datatypes::DataType;
    use arrow::datatypes::IntervalUnit;
    match field.data_type() {
        DataType::Null => todo!("Null type is not yet supported"),
        DataType::Boolean => 1,
        DataType::Int8 | DataType::UInt8 => 1,
        DataType::Int16 | DataType::UInt16 | DataType::Float16 => 2,
        DataType::Int32 | DataType::UInt32 | DataType::Float32 => 4,
        DataType::Int64 | DataType::UInt64 | DataType::Float64 => 8,
        DataType::Timestamp(_, _) => 8,
        DataType::Date32 | DataType::Time32(_) => 4,
        DataType::Date64 | DataType::Time64(_) => 8,
        DataType::Duration(_) => 8,
        DataType::Interval(IntervalUnit::YearMonth) => 4,
        DataType::Interval(IntervalUnit::DayTime) => 8,
        DataType::Interval(IntervalUnit::MonthDayNano) => 16,
        DataType::Decimal128(_, _) => 16,
        DataType::Decimal256(_, _) => 32,
        _ => unimplemented!("Encoding of non-fixed width types is not yet supported"),
        /* DataType::Utf8 | DataType::LargeUtf8 => None,
        DataType::Binary | DataType::LargeBinary => None,
        DataType::FixedSizeBinary(_) => None,
        DataType::List(_) | DataType::LargeList(_) | DataType::Map(_, _) => None,
        DataType::FixedSizeList(_, _) => None,
        DataType::Struct(_) => None,
        DataType::Union(_, _) => None,
        DataType::Dictionary(_, _) => None,
        DataType::RunEndEncoded(_, _) => None, */
    }
}

impl RowLayout {
    pub fn new(schema: SchemaRef, align: bool) -> Self {
        let mut has_nullable_fields = false;
        let mut data_width = 0;
        let mut offsets = Vec::with_capacity(schema.fields().len());
        let mut all_constant = true;
        for field in schema.fields() {
            offsets.push(data_width);
            has_nullable_fields |= field.is_nullable();
            all_constant &= is_fixed_width(&field);
            data_width += field_width(&field);
        }

        let nullbitmap_width = if has_nullable_fields {
            (schema.fields().len() + 7) / 8
        } else {
            0
        };

        let mut row_width = nullbitmap_width + data_width;
        if align {
            // Round up to multiple of 8 bytes
            row_width = (row_width + 7) / 8 * 8;
        }

        Self {
            schema,
            extra_schema: Arc::new(Schema::empty()),
            null_bitmap_width: nullbitmap_width,
            data_width,
            row_width,
            offsets,
            extra_offsets: Vec::new(),
            all_constant,
        }
    }

    pub fn with_extra_fields(schema: SchemaRef, extra_fields: SchemaRef, align: bool) -> Self {
        let n_regular_fields = schema.fields().len();
        let n_extra_fields = extra_fields.fields().len();
        let n_fields = n_regular_fields + n_extra_fields;

        let mut has_nullable_fields = false;
        let mut data_width = 0;
        let mut all_constant = true;
        let mut offsets = Vec::with_capacity(n_regular_fields);
        let mut extra_offsets = Vec::with_capacity(n_extra_fields);
        for field in schema.fields() {
            offsets.push(data_width);
            has_nullable_fields |= field.is_nullable();
            all_constant &= is_fixed_width(&field);
            data_width += field_width(&field);
        }
        for field in extra_fields.fields() {
            extra_offsets.push(data_width);
            has_nullable_fields |= field.is_nullable();
            all_constant &= is_fixed_width(&field);
            data_width += field_width(&field);
        }

        let nullbitmap_width = if has_nullable_fields {
            (n_fields + 7) / 8
        } else {
            0
        };

        let mut row_width = nullbitmap_width + data_width;
        if align {
            // Round up to multiple of 8 bytes
            row_width = (row_width + 7) / 8 * 8;
        }

        Self {
            schema,
            extra_schema: extra_fields,
            null_bitmap_width: nullbitmap_width,
            data_width,
            row_width,
            offsets,
            extra_offsets,
            all_constant,
        }
    }

    /// Convert [`ArrayRef`] columns into [`Rows`]
    /// Assumes that all arrays in `columns` have the same length.
    ///
    /// # Panics
    ///
    /// Panics if the schema of `columns` does not match that provided to [`RowLayout::new`]
    pub fn convert_columns(&self, columns: &[ArrayRef]) -> Rows {
        let len = columns.first().map(|c| c.len()).unwrap_or(0);
        let mut rows = self.empty_rows(len);
        rows.append(columns);
        rows
    }

    /// Convert a [`Selection`] of [`ArrayRef`] columns into [`Rows`]
    /// Assumes that all arrays in `columns` have the same length.
    ///
    /// # Panics
    ///
    /// Panics if the schema of `columns` does not match that provided to [`RowLayout::new`]
    pub fn convert_columns_sel<S>(&self, columns: &[ArrayRef], sel: S) -> Rows
    where
        S: Selection,
    {
        let len = columns.first().map(|c| c.len()).unwrap_or(0);
        let mut rows = self.empty_rows(len);
        rows.append_sel(columns, sel);
        rows
    }

    /// Returns an empty [`Rows`] with capacity for `row_capacity` rows adhering to `self` Rowlayout
    ///
    /// This can be used to buffer a selection of [`Row`]
    pub fn empty_rows(&self, row_capacity: usize) -> Rows {
        // The total capacity of the data buffer, in bytes, to hold row_capacity rows
        let data_capacity = row_capacity * self.row_width;
        let data = Vec::with_capacity(data_capacity);
        Rows {
            layout: Arc::new(self.clone()),
            data,
        }
    }

    /// Returns the [`Schema`] of the rows (excluding extra fields)
    pub fn schema(&self) -> &Schema {
        &self.schema
    }

    /// Returns
    /// - the [`Schema`] of the regular fields, and
    /// - the [`Schema`] of the extra fields.
    pub fn full_schema(&self) -> (&Schema, &Schema) {
        (&self.schema, &self.extra_schema)
    }

    /// Returns the number of bytes that this field occupies in the row.
    pub fn field_width(&self, field_index: usize) -> usize {
        field_width(self.schema.field(field_index))
    }

    /// Returns the number of bytes that this extra field occupies in the row.
    pub fn extra_field_width(&self, field_index: usize) -> usize {
        field_width(self.extra_schema.field(field_index))
    }

    /// Whether the row is null-free according to [RowLayout::full_schema].
    #[inline(always)]
    pub fn null_free(&self) -> bool {
        self.null_bitmap_width == 0
    }

    /// Whether each row has a null bitmap. Equivalent to !self.null_free()
    #[inline(always)]
    pub fn has_null_bitmap(&self) -> bool {
        !self.null_free()
    }

    /// Get the width of the null bitmap in bytes.
    #[inline]
    pub fn null_bitmap_width(&self) -> usize {
        self.null_bitmap_width
    }

    /// Get the width of the data portion of the row in bytes, excluding extra fields.
    /// This is equivalent to `self.data_width()` when there are no extra fields.
    #[inline]
    pub fn regular_data_width(&self) -> usize {
        if self.extra_offsets.is_empty() {
            self.data_width
        } else {
            self.extra_offsets[0]
        }
    }

    /// Get the width of the data portion of the row in bytes.
    /// This excludes the null bitmap and alignment padding.
    #[inline]
    pub fn data_width(&self) -> usize {
        self.data_width
    }

    /// Get the full width of the row in bytes. This includes the null bitmap, the data, and alignment padding.
    #[inline]
    pub fn row_width(&self) -> usize {
        self.row_width
    }

    /// Get offset of regular field in the row.
    /// Panics if field_index is out of bounds.
    #[inline]
    pub fn field_offset(&self, field_index: usize) -> usize {
        self.null_bitmap_width + self.offsets[field_index]
    }

    /// Get offset of extra field in the row.
    /// Panics if field_index is out of bounds.
    #[inline]
    pub fn extra_field_offset(&self, field_index: usize) -> usize {
        self.null_bitmap_width + self.extra_offsets[field_index]
    }

    /// Get the number of fields in the row.
    ///
    /// This is equivalent to `self.num_regular_fields() + self.num_extra_fields()`.
    #[inline]
    pub fn num_fields(&self) -> usize {
        self.offsets.len() + self.extra_offsets.len()
    }

    /// Get the number of regular fields in the row.
    #[inline]
    pub fn num_regular_fields(&self) -> usize {
        self.offsets.len()
    }

    /// Get the number of extra fields in the row.
    #[inline]
    pub fn num_extra_fields(&self) -> usize {
        self.extra_offsets.len()
    }

    #[inline]
    fn assert_field_index_valid(&self, idx: usize) {
        assert!(idx < self.offsets.len(), "Invalid field index {}", idx);
    }
}

#[cfg(test)]
mod tests {
    use datafusion::arrow::datatypes::DataType;

    use super::*;

    /// Example schema with `n_fields` fields, of which `n_nullable_fields` are nullable.
    /// All fields are of type UInt8.
    fn example_schema_regular(n_fields: usize, n_nullable_fields: usize) -> SchemaRef {
        let mut fields = Vec::with_capacity(n_fields);
        for i in 0..n_fields {
            fields.push(Field::new(
                format!("field_{}", i).as_str(),
                DataType::UInt8,
                i < n_nullable_fields,
            ));
        }
        Arc::new(Schema::new(fields))
    }

    /// Example schema {u32, u32}
    fn example_schema_with_extra_fields() -> SchemaRef {
        Arc::new(Schema::new(vec![
            Field::new("weight", DataType::UInt32, false), // 4 bytes
            Field::new("hol_ptr", DataType::UInt32, false), // 4 bytes
        ]))
    }

    #[test]
    /// Test that the null bitmap is omitted when the schema does not allow nulls
    fn test_null_bitmap_omitted() {
        let schema = example_schema_regular(4, 0);
        let layout = RowLayout::new(schema.clone(), false);
        assert!(!layout.has_null_bitmap());
        assert!(layout.null_free());
        assert_eq!(layout.null_bitmap_width(), 0);

        let extra_schema = example_schema_with_extra_fields();
        let layout = RowLayout::with_extra_fields(schema, extra_schema, false);
        assert!(!layout.has_null_bitmap());
        assert!(layout.null_free());
        assert_eq!(layout.null_bitmap_width(), 0);
    }

    #[test]
    /// Test that the null bitmap is included when the schema allows nulls
    /// and that the null bitmap is the correct size
    fn test_null_bitmap_width() {
        let schema = example_schema_regular(1, 1);
        let layout = RowLayout::new(schema, false);
        assert!(!layout.null_free());
        assert!(layout.has_null_bitmap());
        assert_eq!(layout.null_bitmap_width(), 1);

        // One bit per field
        // One byte stores the null bitmap for 8 fields
        let schema = example_schema_regular(8, 8);
        let layout = RowLayout::new(schema, false);
        assert!(!layout.null_free());
        assert!(layout.has_null_bitmap());
        assert_eq!(layout.null_bitmap_width(), 1);

        // Two bits needed to store the null bitmap for 9 fields
        let schema = example_schema_regular(9, 9);
        let layout = RowLayout::new(schema, false);
        assert!(!layout.null_free());
        assert!(layout.has_null_bitmap());
        assert_eq!(layout.null_bitmap_width(), 2);

        // At least one field has to be nullable
        let schema = example_schema_regular(9, 1);
        let layout = RowLayout::new(schema, false);
        assert!(!layout.null_free());
        assert!(layout.has_null_bitmap());
        assert_eq!(layout.null_bitmap_width(), 2);

        // No difference between regular and extra fields for null bitmap width
        let schema = example_schema_regular(7, 1);
        let extra_schema = example_schema_with_extra_fields(); // 2 fields
        let layout = RowLayout::with_extra_fields(schema, extra_schema, false);
        assert!(!layout.null_free());
        assert!(layout.has_null_bitmap());
        assert_eq!(layout.null_bitmap_width(), 2);
    }

    #[test]
    /// Test that the "`field values" portion of the row is the correct size
    fn test_field_values_width() {
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, false),  // 1 byte
            Field::new("b", DataType::Int16, false), // 2 bytes
            Field::new("c", DataType::Int32, false), // 4 bytes
            Field::new("d", DataType::Int64, false), // 8 bytes
        ]));
        let layout = RowLayout::new(schema.clone(), false);
        assert_eq!(layout.regular_data_width(), 15);
        assert_eq!(layout.data_width(), 15);

        let extra_fields = example_schema_with_extra_fields(); // 8 bytes
        let layout = RowLayout::with_extra_fields(schema, extra_fields, false);
        assert_eq!(layout.regular_data_width(), 15);
        assert_eq!(layout.data_width(), 15 + 8);
    }

    #[test]
    /// Test that the row is aligned to 8-byte word boundaries
    /// when align=true
    fn test_alignment() {
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, false), // 1 byte
        ]));
        let layout = RowLayout::new(schema, true);
        assert_eq!(layout.data_width(), 1);
        assert_eq!(layout.row_width(), 8);

        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int64, false), // 8 bytes
        ]));
        let layout = RowLayout::new(schema, true);
        assert_eq!(layout.data_width(), 8);
        assert_eq!(layout.row_width(), 8);

        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, false),  // 1 byte
            Field::new("b", DataType::Int16, false), // 2 bytes
            Field::new("c", DataType::Int32, false), // 4 bytes
            Field::new("d", DataType::Int64, false), // 8 bytes
        ]));
        let layout = RowLayout::new(schema, true);
        assert_eq!(layout.data_width(), 15);
        assert_eq!(layout.row_width(), 16);
    }

    #[test]
    /// Test that the offsets of the regular fields are correct
    fn test_offsets_regular() {
        // Without null bitmap
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, false),  // 1 byte
            Field::new("b", DataType::Int16, false), // 2 bytes
            Field::new("c", DataType::Int32, false), // 4 bytes
            Field::new("d", DataType::Int64, false), // 8 bytes
        ]));
        let layout = RowLayout::new(schema, false);
        assert_eq!(layout.field_offset(0), 0);
        assert_eq!(layout.field_offset(1), 1);
        assert_eq!(layout.field_offset(2), 3);
        assert_eq!(layout.field_offset(3), 7);

        // With null bitmap (one byte)
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, true),  // 1 byte
            Field::new("b", DataType::Int16, true), // 2 bytes
            Field::new("c", DataType::Int32, true), // 4 bytes
            Field::new("d", DataType::Int64, true), // 8 bytes
        ]));
        let layout = RowLayout::new(schema, false);
        assert_eq!(layout.field_offset(0), 1);
        assert_eq!(layout.field_offset(1), 2);
        assert_eq!(layout.field_offset(2), 4);
        assert_eq!(layout.field_offset(3), 8);
    }

    #[test]
    /// Test that the offsets of the extra fields are correct
    fn test_offsets_extra() {
        // Without null bitmap
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, false),  // 1 byte
            Field::new("b", DataType::Int16, false), // 2 bytes
            Field::new("c", DataType::Int32, false), // 4 bytes
            Field::new("d", DataType::Int64, false), // 8 bytes
        ]));
        let extra_schema = example_schema_with_extra_fields();
        let layout = RowLayout::with_extra_fields(schema, extra_schema, false);
        assert_eq!(layout.extra_field_offset(0), 15);
        assert_eq!(layout.extra_field_offset(1), 15 + 4);

        // With null bitmap (one byte)
        let schema = Arc::new(Schema::new(vec![
            Field::new("a", DataType::Int8, true),  // 1 byte
            Field::new("b", DataType::Int16, true), // 2 bytes
            Field::new("c", DataType::Int32, true), // 4 bytes
            Field::new("d", DataType::Int64, true), // 8 bytes
        ]));
        let extra_schema = example_schema_with_extra_fields();
        let layout = RowLayout::with_extra_fields(schema, extra_schema, false);
        assert_eq!(layout.extra_field_offset(0), 16);
        assert_eq!(layout.extra_field_offset(1), 16 + 4);
    }
}
