//! Specialized [GroupedRel] implementations, and their builders for grouping on multi-column or non-primitive keys.
//! Keys are first converted to row a row store in this case.
//! Works when there are NULL values in the keys. They are handled as follows: NULL != NULL (they are simply ignored and hence never grouped/matched during lookups).
//! Two variants exist: one for singular [GroupedRel] and one for non-singular [GroupedRel]

use std::sync::Arc;

use ahash::RandomState;
use datafusion::arrow::array::{ArrayRef, RecordBatch};
use datafusion::arrow::datatypes::{Field, Schema, SchemaRef};
use hashbrown::raw::RawTable;
use parking_lot::RwLock;

use crate::row::RowLayout;
use crate::yannakakis::data::{IDX_TYPE as PTR_TYPE, WEIGHT_TYPE};

use super::super::GroupedRelBuilder;

use super::super::super::super::row::{Row, Rows};
use super::super::super::data::GroupedRel;
use super::super::super::data::GroupedRelRef;
use super::super::super::data::Idx as PTR;
use super::super::super::data::NestedBatch;
use super::super::super::data::NestedColumn;
use super::super::super::data::NestedRel;
use super::super::super::data::NestedSchemaRef;
use super::super::super::data::NonSingularNestedColumn;
use super::super::super::data::SemiJoinResultBatch;
use super::super::super::data::SingularNestedColumn;
use super::super::super::data::Weight as WEIGHT;
use super::super::super::sel::Sel;

/// A [GroupedRel] implementation for grouping on multi-column (> 2) or non-primitive keys,
/// and where the unique nested column is NOT singular.
pub struct DefaultNullableNonSingularGroupedRel {
    /// The scheme of the [GroupedRel]
    pub schema: NestedSchemaRef,

    /// Hashmap mapping keys of type [Row] to (key, weight, hol_ptr) tuples.
    /// The (key, weight, hol_ptr) is stored in a separate [Rows] object called `group_keys`.
    /// The hashmap then stores the index of the (key, weight, hol_ptr) tuple in the [Rows] object.
    pub map: RawTable<(u64, usize)>,

    /// Stores (key, weight, hol_ptr) for each group key.
    pub group_keys: Rows,

    /// The data part of the nested column
    pub data: Arc<NestedRel>,

    /// The random state for hashing keys during lookup
    pub random_state: RandomState,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,

    /// Buffer for keys that is reused across multiple calls of [Self::lookup_impl()].
    ///
    /// *Interior mutability pattern in multi-threaded context
    /// (RwLock is multi-threaded variant of RefCell).*
    batch_keys_buffer: RwLock<Rows>,
}

impl DefaultNullableNonSingularGroupedRel {
    /// Create a new [DefaultNonSingularGroupedRel] instance.
    pub fn new(
        schema: NestedSchemaRef,
        map: RawTable<(u64, usize)>,
        group_keys: Rows,
        data: Arc<NestedRel>,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        let layout = group_keys.layout().clone();
        Self {
            schema,
            map,
            group_keys,
            data,
            random_state,
            alternative_flag: use_alternative,
            batch_keys_buffer: RwLock::new(Rows::new(layout, 0)),
        }
    }

    #[inline(always)]
    pub fn lookup_impl(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>, Vec<PTR>) {
        let n_rows = keys[0].len();

        let mut sel_vector: Vec<PTR> = Vec::with_capacity(n_rows);
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(n_rows);
        let mut hols: Vec<PTR> = Vec::with_capacity(n_rows);

        // Convert keys to rows.
        // Reuse the same rows buffer across different calls of this method.
        let mut batch_keys_buffer = self.batch_keys_buffer.write();
        batch_keys_buffer.clear();
        batch_keys_buffer.reserve(n_rows); // no-op if capacity is already enough
        batch_keys_buffer.append(keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(n_rows, 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(batch_keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        // Lookup the keys in the hashmap
        for (i, (hash, key)) in hashes_buffer
            .iter()
            .zip(batch_keys_buffer.iter())
            .enumerate()
        {
            if key.contains_null() {
                continue; // row with NULL will never match, no need to look it up
            }

            let entry = self.map.get(*hash, |(_, group_id)| {
                let group = self.group_keys.row(*group_id);
                key.prefix_eq_unchecked(&group)
            });

            if let Some((_, group_id)) = entry {
                let group = self.group_keys.row(*group_id);
                let weight = group.get_extra::<WEIGHT>(0);
                let hol_ptr = group.get_extra::<PTR>(1);

                sel_vector.push(i as PTR);
                weights.push(weight);
                hols.push(hol_ptr);
            }
        }

        (sel_vector, weights, hols)
    }

    /// Included for benchmarking purposes. Can be removed in final version.
    /// It currently does the same as [Self::lookup_impl()].
    #[inline(always)]
    pub fn lookup_impl_alternative(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>, Vec<PTR>) {
        let n_rows = keys[0].len();

        let mut sel_vector: Vec<PTR> = Vec::with_capacity(n_rows);
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(n_rows);
        let mut hols: Vec<PTR> = Vec::with_capacity(n_rows);

        // Convert keys to rows.
        // Reuse the same rows buffer across different calls of this method.
        let mut batch_keys_buffer = self.batch_keys_buffer.write();
        batch_keys_buffer.clear();
        batch_keys_buffer.reserve(n_rows); // no-op if capacity is already enough
        batch_keys_buffer.append(keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(n_rows, 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(batch_keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        // Lookup the keys in the hashmap
        for (i, (hash, key)) in hashes_buffer
            .iter()
            .zip(batch_keys_buffer.iter())
            .enumerate()
        {
            if key.contains_null() {
                continue; // row with NULL will never match, no need to look it up
            }

            let entry = self.map.get(*hash, |(_, group_id)| {
                let group = self.group_keys.row(*group_id);
                key.prefix_eq_unchecked(&group)
            });

            if let Some((_, group_id)) = entry {
                let group = self.group_keys.row(*group_id);
                let weight = group.get_extra::<WEIGHT>(0);
                let hol_ptr = group.get_extra::<PTR>(1);

                sel_vector.push(i as PTR);
                weights.push(weight);
                hols.push(hol_ptr);
            }
        }

        (sel_vector, weights, hols)
    }

    #[inline(always)]
    fn lookup_sel_impl(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<WEIGHT>, Vec<PTR>) {
        let n_rows = keys[0].len();

        let mut weights: Vec<WEIGHT> = vec![0 as WEIGHT; n_rows];
        let mut hols: Vec<PTR> = vec![0 as PTR; n_rows];

        // this function uses a lot of unsafe code for performance
        // SAFETY:
        // The safety hinges on the fact that the sel vector is monotonically increasing, with the maximum value below n_rows.
        assert!(sel.max() <= n_rows, "Selection vector out of bounds");

        // Convert keys to rows.
        // Reuse the same rows buffer across different calls of this method.
        let mut batch_keys_buffer = self.batch_keys_buffer.write();
        batch_keys_buffer.clear();
        batch_keys_buffer.reserve(n_rows); // no-op if capacity is already enough
        batch_keys_buffer.append(keys);

        // Iterate through these rows to compute hashes
        // Only do this for rows in `sel`
        hashes_buffer.resize(sel.len(), 0);
        for (hash, row_nr) in hashes_buffer.iter_mut().zip(sel.iter()) {
            let key = batch_keys_buffer.row(row_nr);
            *hash = self.random_state.hash_one(&key);
        }

        // Iterate over the selection vector, and for each row, look up the key in the hashmap
        // when the inner closure returns true the row is retained in the selection vector
        // in the closure, `i` is the position in `sel` at which the element `row_nr` is found.
        sel.refine(|i, row_nr| {
            let key = batch_keys_buffer.row(row_nr);

            if key.contains_null() {
                return false; // row with NULL will never match, no need to look it up
            }

            let hash = unsafe { hashes_buffer.get_unchecked(i) };

            let entry = self.map.get(*hash, |(_, group_id)| {
                let group = self.group_keys.row(*group_id);
                key.prefix_eq_unchecked(&group)
            });

            match entry {
                Some((_, group_id)) => {
                    let group = self.group_keys.row(*group_id);
                    let weight = group.get_extra::<WEIGHT>(0);
                    let hol_ptr = group.get_extra::<PTR>(1);

                    // Copy the found weight to the weights vector at index `row_idx`
                    // SAFETY: row_idx is guaranteed to be within bounds of the weights vector
                    let dest_weight = unsafe { weights.get_unchecked_mut(row_nr) };
                    *dest_weight = weight;

                    // Copy the found hol_ptr to the hols vector at index `row_idx`
                    // SAFETY: row_idx is guaranteed to be within bounds of the weights vector
                    let dest_hol_ptr = unsafe { hols.get_unchecked_mut(row_nr) };
                    *dest_hol_ptr = hol_ptr;

                    true
                }
                None => false,
            }
        });

        (weights, hols)
    }
}

impl GroupedRel for DefaultNullableNonSingularGroupedRel {
    fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }
    fn lookup(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
        _row_count: usize,
    ) -> (Sel, NestedColumn) {
        let (sel, weights, hols) = if !self.alternative_flag {
            self.lookup_impl(keys, hashes_buffer)
        } else {
            self.lookup_impl_alternative(keys, hashes_buffer)
        };

        // Return a non-singular nested column
        let ns_nested_col = NonSingularNestedColumn {
            hols,
            weights,
            data: self.data.clone(),
        };

        (
            Sel::new_unchecked(sel),
            NestedColumn::NonSingular(ns_nested_col),
        )
    }

    fn lookup_sel(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
        _row_count: usize,
    ) -> NestedColumn {
        let (weights, hols) = self.lookup_sel_impl(keys, sel, hashes_buffer);
        // Return a non-singular nested column
        let ns_nested_col = NonSingularNestedColumn {
            hols,
            weights,
            data: self.data.clone(),
        };

        NestedColumn::NonSingular(ns_nested_col)
    }

    fn as_any(&self) -> &dyn std::any::Any {
        self
    }

    fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

/// A [GroupedRelBuilder] implementation that produces a [DefaultNonSingularGroupedRel].
pub struct DefaultNullableNonSingularGroupedRelBuilder {
    /// The index of the columns in the [SemijoinResultBatch]s that will be used as the groupby-key.
    group_on_cols: Vec<usize>,

    /// Hashmap mapping keys of type [Row] to (key, weight, hol_ptr) tuples.
    /// The (key, weight, hol_ptr) is stored in a separate [Rows] object called `group_keys`.
    /// The hashmap then stores the index of the (key, weight, hol_ptr) tuple in the [Rows] object.
    pub map: RawTable<(u64, usize)>,

    /// Stores (key, weight, hol_ptr) for each group key.
    pub group_keys: Rows,

    /// Encodes a linked list of next_ptr, chaining together all tuples that belong to the same group
    next: Vec<PTR>,

    /// The random state for hashing keys during lookup
    pub random_state: RandomState,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl GroupedRelBuilder for DefaultNullableNonSingularGroupedRelBuilder {
    fn build(&mut self, batches: &[SemiJoinResultBatch]) {
        let mut offset = 0;

        // Rowlayout for keys (without extra fields like weight and hol_ptr)
        let keys_schema = self.group_keys.layout().schema();
        let keys_layout = RowLayout::new(Arc::new(keys_schema.clone()), true);

        // Buffer to store keys as rows
        let mut keys_buffer = Rows::new(Arc::new(keys_layout), 0);

        // Buffer to store hashes of keys
        let mut hashes_buffer = Vec::new();

        for batch in batches {
            self.ingest(batch, offset, &mut keys_buffer, &mut hashes_buffer);
            offset += batch.num_rows();
        }
    }

    fn finish(
        &mut self,
        schema: NestedSchemaRef,
        grouped_col_inner_data: Option<NestedRel>,
        use_alternative: bool,
    ) -> GroupedRelRef {
        // The grouped_inner_col data does not yet have the correct `next` vector; we set it here.
        let mut data = grouped_col_inner_data
            .expect("Non-singular nested column requires a valid inner NestedRel!");
        data.next = Some(std::mem::take(&mut self.next));
        let data = Arc::new(data);

        let grouped_rel: DefaultNullableNonSingularGroupedRel =
            DefaultNullableNonSingularGroupedRel::new(
                schema,
                std::mem::take(&mut self.map),
                std::mem::take(&mut self.group_keys),
                data,
                std::mem::take(&mut self.random_state),
                use_alternative,
            );

        Arc::new(grouped_rel)
    }
}

impl DefaultNullableNonSingularGroupedRelBuilder {
    /// Create a new [DefaultNonSingularGroupedRelBuilder] instance with the given capacity and random state.
    /// Grouping will be done on `group_on_cols` of the input. These columns must be non-nested.
    pub fn new(
        group_on_cols: Vec<usize>,
        keys_schema: SchemaRef,
        capacity: usize,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        let extra_fields = Arc::new(Schema::new(vec![
            Field::new("weight", WEIGHT_TYPE, false),
            Field::new("hol_ptr", PTR_TYPE, false),
        ]));

        let layout = RowLayout::with_extra_fields(keys_schema, extra_fields, true);
        let group_keys = Rows::new(Arc::new(layout), capacity);

        Self {
            group_on_cols,
            map: RawTable::with_capacity(capacity),
            group_keys,
            next: vec![0; capacity],
            random_state,
            use_alternative,
        }
    }

    /// Ingest a single [SemiJoinResultBatch] of tuples into the state.
    #[inline(always)]
    fn ingest(
        &mut self,
        batch: &SemiJoinResultBatch,
        offset: usize,
        keys_buffer: &mut Rows,
        hashes_buffer: &mut Vec<u64>,
    ) {
        match batch {
            SemiJoinResultBatch::Flat(batch) => {
                self.ingest_flat_batch(batch, offset, keys_buffer, hashes_buffer);
            }
            SemiJoinResultBatch::Nested(batch) => {
                self.ingest_nested_batch(batch, offset, keys_buffer, hashes_buffer);
            }
        }
    }

    /// Ingest a single Flat [RecordBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_flat_batch(
        &mut self,
        batch: &RecordBatch,
        offset: usize,
        keys_buffer: &mut Rows,
        hashes_buffer: &mut Vec<u64>,
    ) {
        // Get key columns from guard batch
        let keys = self
            .group_on_cols
            .iter()
            .map(|col| batch.column(*col).clone())
            .collect::<Vec<_>>();

        // Convert keys to rows
        keys_buffer.clear();
        keys_buffer.reserve(batch.num_rows()); // no-op if capacity is already enough
        keys_buffer.append(&keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(batch.num_rows(), 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        for (row, (hash, key)) in hashes_buffer.iter().zip(keys_buffer.iter()).enumerate() {
            // row with NULL will never match, no need to update the hashmap
            if !key.contains_null() {
                self.update_key(key, 1, row, offset, *hash);
            }
        }
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(
        &mut self,
        batch: &NestedBatch,
        offset: usize,
        keys_buffer: &mut Rows,
        hashes_buffer: &mut Vec<u64>,
    ) {
        // Get key columns from guard batch
        let keys = self
            .group_on_cols
            .iter()
            .map(|col| batch.regular_column(*col).clone())
            .collect::<Vec<_>>();

        // Convert keys to rows
        keys_buffer.clear();
        keys_buffer.reserve(batch.num_rows()); // no-op if capacity is already enough
        keys_buffer.append(&keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(batch.num_rows(), 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        // Get the total weight of each row in the batch
        let weights = batch.total_weights();

        for (row, (hash, (key, weight))) in hashes_buffer
            .iter()
            .zip(keys_buffer.iter().zip(weights))
            .enumerate()
        {
            // row with NULL will never match, no need to update the hashmap
            if !key.contains_null() {
                self.update_key(key, *weight, row, offset, *hash);
            }
        }
    }

    /// Update hashmap with info from new tuple.
    #[inline(always)]
    fn update_key(
        &mut self,
        key: Row,
        tuple_weight: WEIGHT,
        row: usize,
        offset: usize,
        hash: u64, // hash value of key
    ) {
        let entry = self.map.get_mut(hash, |(_, group_id)| {
            let group = self.group_keys.row(*group_id);
            key.prefix_eq_unchecked(&group)
        });

        match entry {
            // Group does not exist yet
            None => {
                let next_group_idx = self.map.len();

                // Insert new group (id) in map
                self.map.insert(hash, (hash, next_group_idx), |_| panic!("[ERROR!!!] rehash called on insert into RawTable (meaning pre-allocation was too small)!"));

                // Insert new group in group_keys
                let mut new_group = self.group_keys.append_row();
                new_group.copy_prefix_from(&key);
                new_group.set_extra(0, tuple_weight);
                new_group.set_extra(1, (offset + row + 1) as PTR); // update the hol pointer to the current tuple (+1 since 0 is reserved for "no next")

                // Update next
                self.next[offset + row] = 0; // no next since this is the first tuple in the group
            }

            // Group already exists
            Some((_, group_id)) => {
                let mut group = self.group_keys.row_mut(*group_id);

                // Add tuple weight to total group weight
                let group_weight = group.get_extra::<WEIGHT>(0);
                group.set_extra(0, group_weight + tuple_weight);

                // Update hol_ptr & next
                let old_hol_ptr = group.get_extra::<PTR>(1);
                group.set_extra(1, (offset + row + 1) as PTR); // update the hol pointer to the current tuple (+1 since 0 is reserved for "no next")
                self.next[offset + row] = old_hol_ptr; // store the previous head of list in the slot for the current tuple}
            }
        }
    }
}

// --------------------------------------------------------------------------
// NON-SINGULAR ABOVE -------------------------------------------------------
// SINGULAR BELOW -----------------------------------------------------------
// --------------------------------------------------------------------------

/// A [GroupedRel] implementation for grouping on multi-column (> 2) or non-primitive keys,
/// and where the unique nested column in singular.
pub struct DefaultNullableSingularGroupedRel {
    /// The scheme of the [GroupedRel]
    pub schema: NestedSchemaRef,

    /// Hashmap mapping keys of type [Row] to (key, weight) tuples.
    /// The (key, weight) is stored in a separate [Rows] object called `group_keys`.
    /// The hashmap then stores the index of the (key, weight) tuple in the [Rows] object.
    pub map: RawTable<(u64, usize)>,

    /// Stores (key, weight) for each group key.
    /// No hol_ptr is stored since the nested column is singular.
    pub group_keys: Rows,

    /// The random state for hashing keys during lookup
    pub random_state: RandomState,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,

    /// Buffer for keys that is reused across multiple calls of [Self::lookup_impl()].
    ///
    /// *Interior mutability pattern in multi-threaded context
    /// (RwLock is multi-threaded variant of RefCell).*
    batch_keys_buffer: RwLock<Rows>,
}

impl DefaultNullableSingularGroupedRel {
    /// Create a new [DefaultSingularGroupedRel] instance.
    pub fn new(
        schema: NestedSchemaRef,
        map: RawTable<(u64, usize)>,
        group_keys: Rows,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        let layout = group_keys.layout().clone();
        Self {
            schema,
            map,
            group_keys,
            random_state,
            alternative_flag: use_alternative,
            batch_keys_buffer: RwLock::new(Rows::new(layout, 0)),
        }
    }

    #[inline(always)]
    pub fn lookup_impl(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>) {
        let n_rows = keys[0].len();

        let mut sel_vector: Vec<PTR> = Vec::with_capacity(n_rows);
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(n_rows);

        // Convert keys to rows.
        // Reuse the same rows buffer across different calls of this method.
        let mut batch_keys_buffer = self.batch_keys_buffer.write();
        batch_keys_buffer.clear();
        batch_keys_buffer.reserve(n_rows); // no-op if capacity is already enough
        batch_keys_buffer.append(keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(n_rows, 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(batch_keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        // Lookup the keys in the hashmap
        for (i, (hash, key)) in hashes_buffer
            .iter()
            .zip(batch_keys_buffer.iter())
            .enumerate()
        {
            if key.contains_null() {
                continue; // row with NULL will never match, no need to look it up
            }

            let entry = self.map.get(*hash, |(_, group_id)| {
                let group = self.group_keys.row(*group_id);
                key.prefix_eq_unchecked(&group)
            });

            if let Some((_, group_id)) = entry {
                let group = self.group_keys.row(*group_id);
                let weight = group.get_extra::<WEIGHT>(0);

                sel_vector.push(i as PTR);
                weights.push(weight);
            }
        }

        (sel_vector, weights)
    }

    /// Included for benchmarking purposes. Can be removed in final version.
    /// It currently does the same as [Self::lookup_impl()].
    #[inline(always)]
    pub fn lookup_impl_alternative(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>) {
        let n_rows = keys[0].len();

        let mut sel_vector: Vec<PTR> = Vec::with_capacity(n_rows);
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(n_rows);

        // Convert keys to rows.
        // Reuse the same rows buffer across different calls of this method.
        let mut batch_keys_buffer = self.batch_keys_buffer.write();
        batch_keys_buffer.clear();
        batch_keys_buffer.reserve(n_rows); // no-op if capacity is already enough
        batch_keys_buffer.append(keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(n_rows, 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(batch_keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        // Lookup the keys in the hashmap
        for (i, (hash, key)) in hashes_buffer
            .iter()
            .zip(batch_keys_buffer.iter())
            .enumerate()
        {
            if key.contains_null() {
                continue; // row with NULL will never match, no need to look it up
            }

            let entry = self.map.get(*hash, |(_, group_id)| {
                let group = self.group_keys.row(*group_id);
                key.prefix_eq_unchecked(&group)
            });

            if let Some((_, group_id)) = entry {
                let group = self.group_keys.row(*group_id);
                let weight = group.get_extra::<WEIGHT>(0);

                sel_vector.push(i as PTR);
                weights.push(weight);
            }
        }

        (sel_vector, weights)
    }

    #[inline(always)]
    fn lookup_sel_impl(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
    ) -> Vec<WEIGHT> {
        let n_rows = keys[0].len();

        let mut weights: Vec<WEIGHT> = vec![0 as WEIGHT; n_rows];

        // this function uses a lot of unsafe code for performance
        // SAFETY:
        // The safety hinges on the fact that the sel vector is monotonically increasing, with the maximum value below n_rows.
        assert!(sel.max() <= n_rows, "Selection vector out of bounds");

        // Convert keys to rows.
        // Reuse the same rows buffer across different calls of this method.
        let mut batch_keys_buffer = self.batch_keys_buffer.write();
        batch_keys_buffer.clear();
        batch_keys_buffer.reserve(n_rows); // no-op if capacity is already enough
        batch_keys_buffer.append(keys);

        // Iterate through these rows to compute hashes
        // Only do this for rows in `sel`
        hashes_buffer.resize(sel.len(), 0);
        for (hash, row_nr) in hashes_buffer.iter_mut().zip(sel.iter()) {
            let key = batch_keys_buffer.row(row_nr);
            *hash = self.random_state.hash_one(&key);
        }

        // Iterate over the selection vector, and for each row, look up the key in the hashmap
        // when the inner closure returns true the row is retained in the selection vector
        // in the closure, `i` is the position in `sel` at which the element `row_nr` is found.
        sel.refine(|i, row_nr| {
            let key = batch_keys_buffer.row(row_nr);
            if key.contains_null() {
                return false; // row with NULL will never match, no need to look it up
            }

            let hash = unsafe { hashes_buffer.get_unchecked(i) };

            let entry = self.map.get(*hash, |(_, group_id)| {
                let group = self.group_keys.row(*group_id);
                key.prefix_eq_unchecked(&group)
            });

            match entry {
                Some((_, group_id)) => {
                    let group = self.group_keys.row(*group_id);
                    let weight = group.get_extra::<WEIGHT>(0);

                    // Copy the found weight to the weights vector at index `row_idx`
                    // SAFETY: row_idx is guaranteed to be within bounds of the weights vector
                    let dest_weight = unsafe { weights.get_unchecked_mut(row_nr) };
                    *dest_weight = weight;

                    true
                }
                None => false,
            }
        });

        weights
    }
}

impl GroupedRel for DefaultNullableSingularGroupedRel {
    fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    fn lookup(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
        _row_count: usize,
    ) -> (Sel, NestedColumn) {
        let (sel, weights) = if !self.alternative_flag {
            self.lookup_impl(keys, hashes_buffer)
        } else {
            self.lookup_impl_alternative(keys, hashes_buffer)
        };

        (
            Sel::new_unchecked(sel),
            NestedColumn::Singular(SingularNestedColumn { weights }),
        )
    }

    fn lookup_sel(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
        _row_count: usize,
    ) -> NestedColumn {
        let weights = self.lookup_sel_impl(keys, sel, hashes_buffer);

        NestedColumn::Singular(SingularNestedColumn { weights })
    }

    fn as_any(&self) -> &dyn std::any::Any {
        self
    }

    fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

/// A [GroupedRelBuilder] implementation that produces a [DefaultSingularGroupedRel].
pub struct DefaultNullableSingularGroupedRelBuilder {
    /// The index of the columns in the [SemijoinResultBatch]s that will be used as the groupby-key.
    group_on_cols: Vec<usize>,

    /// Hashmap mapping keys of type [Row] to (key, weight) tuples.
    /// The (key, weight) is stored in a separate [Rows] object called `group_keys`.
    /// The hashmap then stores the index of the (key, weight) tuple in the [Rows] object.
    pub map: RawTable<(u64, usize)>,

    /// Stores (key, weight) for each group key.
    pub group_keys: Rows,

    /// The random state for hashing keys during lookup
    pub random_state: RandomState,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl GroupedRelBuilder for DefaultNullableSingularGroupedRelBuilder {
    fn build(&mut self, batches: &[SemiJoinResultBatch]) {
        // Rowlayout for keys (without extra fields like weight)
        let keys_schema = self.group_keys.layout().schema();
        let keys_layout = RowLayout::new(Arc::new(keys_schema.clone()), true);

        // Buffer to store keys as rows
        let mut keys_buffer = Rows::new(Arc::new(keys_layout), 0);

        // Buffer to store hashes of keys
        let mut hashes_buffer = Vec::new();

        for batch in batches {
            self.ingest(batch, &mut keys_buffer, &mut hashes_buffer);
        }
    }

    fn finish(
        &mut self,
        schema: NestedSchemaRef,
        grouped_col_inner_data: Option<NestedRel>,
        use_alternative: bool,
    ) -> GroupedRelRef {
        assert!(
            grouped_col_inner_data.is_none(),
            "A singular [GroupedRel] should not have an inner NestedRel!"
        );

        let grouped_rel = DefaultNullableSingularGroupedRel::new(
            schema,
            std::mem::take(&mut self.map),
            std::mem::take(&mut self.group_keys),
            std::mem::take(&mut self.random_state),
            use_alternative,
        );

        Arc::new(grouped_rel)
    }
}

impl DefaultNullableSingularGroupedRelBuilder {
    /// Create a new [DefaultSingularGroupedRelBuilder] instance with the given capacity and random state.
    /// Grouping will be done on `group_on_cols` of the input. These columns must be non-nested.
    pub fn new(
        group_on_cols: Vec<usize>,
        keys_schema: SchemaRef,
        capacity: usize,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        let extra_fields = Arc::new(Schema::new(vec![
            Field::new("weight", WEIGHT_TYPE, false),
            // Field::new("hol_ptr", PTR_TYPE, false), // no hol_ptr for singular nested column
        ]));

        let layout = RowLayout::with_extra_fields(keys_schema, extra_fields, true);
        let group_keys = Rows::new(Arc::new(layout), capacity);

        Self {
            group_on_cols,
            map: RawTable::with_capacity(capacity),
            group_keys,
            random_state,
            use_alternative,
        }
    }

    /// Ingest a single [SemiJoinResultBatch] of tuples into the state.
    #[inline(always)]
    fn ingest(
        &mut self,
        batch: &SemiJoinResultBatch,
        keys_buffer: &mut Rows,
        hashes_buffer: &mut Vec<u64>,
    ) {
        match batch {
            SemiJoinResultBatch::Flat(batch) => {
                self.ingest_flat_batch(batch, keys_buffer, hashes_buffer);
            }
            SemiJoinResultBatch::Nested(batch) => {
                self.ingest_nested_batch(batch, keys_buffer, hashes_buffer);
            }
        }
    }

    /// Ingest a single Flat [RecordBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_flat_batch(
        &mut self,
        batch: &RecordBatch,
        keys_buffer: &mut Rows,
        hashes_buffer: &mut Vec<u64>,
    ) {
        // Get key columns from guard batch
        let keys = self
            .group_on_cols
            .iter()
            .map(|col| batch.column(*col).clone())
            .collect::<Vec<_>>();

        // Convert keys to rows
        keys_buffer.clear();
        keys_buffer.reserve(batch.num_rows()); // no-op if capacity is already enough
        keys_buffer.append(&keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(batch.num_rows(), 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        for (hash, key) in hashes_buffer.iter().zip(keys_buffer.iter()) {
            // row with NULL will never match, no need to update the hashmap
            if !key.contains_null() {
                self.update_key(key, 1, *hash);
            }
        }
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(
        &mut self,
        batch: &NestedBatch,
        keys_buffer: &mut Rows,
        hashes_buffer: &mut Vec<u64>,
    ) {
        // Get key columns from guard batch
        let keys = self
            .group_on_cols
            .iter()
            .map(|col| batch.regular_column(*col).clone())
            .collect::<Vec<_>>();

        // Convert keys to rows
        keys_buffer.clear();
        keys_buffer.reserve(batch.num_rows()); // no-op if capacity is already enough
        keys_buffer.append(&keys);

        // Iterate through these rows to compute hashes
        hashes_buffer.resize(batch.num_rows(), 0);
        for (hash, key) in hashes_buffer.iter_mut().zip(keys_buffer.iter()) {
            *hash = self.random_state.hash_one(&key);
        }

        // Get the total weight of each row in the batch
        let weights = batch.total_weights();

        for (hash, (key, weight)) in hashes_buffer.iter().zip(keys_buffer.iter().zip(weights)) {
            // row with NULL will never match, no need to update the hashmap
            if !key.contains_null() {
                self.update_key(key, *weight, *hash);
            }
        }
    }

    /// Update hashmap with info from new tuple.
    #[inline(always)]
    fn update_key(
        &mut self,
        key: Row,
        tuple_weight: WEIGHT,
        hash: u64, // hash value of key
    ) {
        let entry = self.map.get_mut(hash, |(_, group_id)| {
            let group = self.group_keys.row(*group_id);
            key.prefix_eq_unchecked(&group)
        });

        match entry {
            // Group does not exist yet
            None => {
                let next_group_idx = self.map.len();

                // Insert new group (id) in map
                self.map.insert(hash, (hash, next_group_idx), |_| panic!("[ERROR!!!] rehash called on insert into RawTable (meaning pre-allocation was too small)!"));

                // Insert new group in group_keys
                let mut new_group = self.group_keys.append_row();
                new_group.copy_prefix_from(&key);
                new_group.set_extra(0, tuple_weight);
            }

            // Group already exists
            Some((_, group_id)) => {
                let mut group = self.group_keys.row_mut(*group_id);

                // Add tuple weight to total group weight
                let group_weight = group.get_extra::<WEIGHT>(0);
                group.set_extra(0, group_weight + tuple_weight);
            }
        }
    }
}

/// Create a new [GroupedRelBuilder] that can group by any number of columns.
/// This is a fallback variant where keys will be converted to [Rows].
/// The singular flag indicates whether the nested column is singular or not.
pub fn make_builder(
    group_on_cols: Vec<usize>,
    keys_schema: SchemaRef,
    is_singular: bool,
    capacity: usize,
    random_state: RandomState,
    flag: bool,
) -> Box<dyn GroupedRelBuilder> {
    if is_singular {
        Box::new(DefaultNullableSingularGroupedRelBuilder::new(
            group_on_cols,
            keys_schema,
            capacity,
            random_state,
            flag,
        ))
    } else {
        Box::new(DefaultNullableNonSingularGroupedRelBuilder::new(
            group_on_cols,
            keys_schema,
            capacity,
            random_state,
            flag,
        ))
    }
}
