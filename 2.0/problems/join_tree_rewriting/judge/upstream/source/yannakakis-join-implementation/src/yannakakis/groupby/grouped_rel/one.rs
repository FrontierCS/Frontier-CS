//! Specialized [GroupedRel] implementations, and their builders for grouping on single-column primitive keys groupby columns.
//! The keys are assumed to be non-nullable.
//! Two variants exist: one for singular [GroupedRel] and one for non-singular [GroupedRel]

use ahash::RandomState;

use datafusion::arrow::array::downcast_primitive;
use datafusion::arrow::array::Array;
use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::array::PrimitiveArray;
use datafusion::arrow::array::RecordBatch;
use datafusion::arrow::datatypes::ArrowPrimitiveType;
use datafusion::arrow::datatypes::DataType;
use datafusion::common::hash_utils::HashValue;
use hashbrown::raw::RawTable;

use super::super::GroupedRelBuilder;

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

use std::sync::Arc;

/// A [GroupedRel] implementation that groups on a single key column of type T and where the unique nested column is non-singular.
pub struct OneKeyNonSingularGroupedRel<T>
where
    T: ArrowPrimitiveType,
{
    /// The scheme of the [GroupedRel]
    pub schema: NestedSchemaRef,
    /// Hashmap mapping keys of type T to (weight, hol_ptr) tuples.
    pub map: RawTable<(T::Native, WEIGHT, PTR)>,
    /// The data part of the nested column
    pub data: Arc<NestedRel>,
    /// The random state for hashing keys during lookup
    pub random_state: RandomState,
    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,
}

impl<T> GroupedRel for OneKeyNonSingularGroupedRel<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    fn lookup(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
        _row_count: usize,
    ) -> (Sel, NestedColumn) {
        let keys = validate_lookup_keys(keys);

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
        let keys = validate_lookup_keys(keys);
        let (weights, hols) = self.lookup_sel_impl(keys, sel, hashes_buffer);
        // Return a non-signular nested column
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

#[inline]
/// Validate that `keys` consist of a single column of primitive type, which is non-null.
/// Returns this unique column as a PrimitiveArray of the correct type
fn validate_lookup_keys<T>(keys: &[ArrayRef]) -> &PrimitiveArray<T>
where
    T: ArrowPrimitiveType,
{
    assert!(
        keys.len() == 1,
        "OneKey GroupedRel variants requires a single key column"
    );
    let keys = keys[0]
        .as_any()
        .downcast_ref::<PrimitiveArray<T>>()
        .expect("Key column should be a primitive array of type T");

    assert!(!keys.is_nullable(), "Lookup keys should be non-nullable");

    keys
}

impl<T> OneKeyNonSingularGroupedRel<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    /// Create a new [OneKeySingularGroupedRel] with the given map and random state.
    pub fn new(
        schema: NestedSchemaRef,
        map: RawTable<(T::Native, WEIGHT, PTR)>,
        data: Arc<NestedRel>,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        Self {
            schema,
            map,
            data,
            random_state,
            alternative_flag: use_alternative,
        }
    }

    #[inline(always)]
    pub fn lookup_impl(
        &self,
        keys: &PrimitiveArray<T>,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>, Vec<PTR>) {
        let mut sel_vector: Vec<PTR> = Vec::with_capacity(keys.len());
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(keys.len());
        let mut hols: Vec<PTR> = Vec::with_capacity(keys.len());

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // NOTE: in contrast to when building the hashmap, we do not store the key here, as this is impossible to do in a generic way (we don't know the type of the key in the Groups::lookup function)
        // and we cannot mutate the groups structure here, so we can't have a local keys_and_hashes buffer that stores the keys (at least, not in a performant way)
        hashes_buffer.resize(keys.len(), 0);
        for (hash, src_key) in hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *hash = src_key.hash_one(&self.random_state);
        }

        for (i, (hash, key)) in hashes_buffer.iter().zip(keys.values().iter()).enumerate() {
            let key = *key;
            let hash = *hash;
            let entry = self.map.get(hash, |(k, _, _)| *k == key);

            if let Some((_, weight, hol_ptr)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
                hols.push(*hol_ptr);
            }
        }

        (sel_vector, weights, hols)
    }

    /// Included for benchmarking purposes. Can be removed in final version.
    pub fn lookup_impl_alternative(
        &self,
        keys: &PrimitiveArray<T>,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>, Vec<PTR>) {
        let mut sel_vector: Vec<PTR> = Vec::new();
        let mut weights: Vec<WEIGHT> = Vec::new();
        let mut hols: Vec<PTR> = Vec::new();

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // NOTE: in contrast to when building the hashmap, we do not store the key here, as this is impossible to do in a generic way (we don't know the type of the key in the Groups::lookup function)
        // and we cannot mutate the groups structure here, so we can't have a local keys_and_hashes buffer that stores the keys (at least, not in a performant way)
        hashes_buffer.resize(keys.len(), 0);
        for (hash, src_key) in hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *hash = src_key.hash_one(&self.random_state);
        }

        for (i, (hash, key)) in hashes_buffer.iter().zip(keys.values().iter()).enumerate() {
            let key = *key;
            let hash = *hash;
            let entry = self.map.get(hash, |(k, _, _)| *k == key);

            if let Some((_, weight, hol_ptr)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
                hols.push(*hol_ptr);
            }
        }

        (sel_vector, weights, hols)
    }

    pub fn lookup_sel_impl(
        &self,
        keys: &PrimitiveArray<T>,
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<WEIGHT>, Vec<PTR>) {
        // Create result vectors with the same length as keys.len
        let mut weights: Vec<WEIGHT> = vec![0 as WEIGHT; keys.len()];
        let mut hols: Vec<PTR> = vec![0 as PTR; keys.len()];

        // this function uses a lot of unsafe code for performance
        // SAFETY:
        // The safety hinges on the fact that the sel vector is monotonically increasing, with the maximum value below keys.len()
        assert!(sel.max() <= keys.len(), "Selection vector out of bounds");

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        hashes_buffer.resize(sel.len(), 0);
        for (hash, row_nr) in hashes_buffer.iter_mut().zip(sel.iter()) {
            let key = unsafe { keys.value_unchecked(row_nr) };
            *hash = key.hash_one(&self.random_state);
        }

        // Iterate over the selection vector, and for each row, look up the key in the hashmap
        // when the inner closure returns true the row is retained in the selection vector
        // in the closure, `i` is the position in `sel` at which the element `row_nr` is found.
        sel.refine(|i, row_nr| {
            let key = unsafe { keys.value_unchecked(row_nr) };
            let hash = unsafe { *hashes_buffer.get_unchecked(i) };

            let entry = self.map.get(hash, |(k, _, _)| *k == key);

            match entry {
                Some((_, weight, hol_ptr)) => {
                    // Copy the found weight to the weights vector at index `row_idx`
                    // SAFETY: row_idx is guaranteed to be within bounds of the weights vector
                    let dest_weight = unsafe { weights.get_unchecked_mut(row_nr) };
                    *dest_weight = *weight;

                    // Copy the found hol_ptr to the hols vector at index `row_idx`
                    // SAFETY: row_idx is guaranteed to be within bounds of the weights vector
                    let dest_hol_ptr = unsafe { hols.get_unchecked_mut(row_nr) };
                    *dest_hol_ptr = *hol_ptr;

                    true
                }
                None => false,
            }
        });

        (weights, hols)
    }
}

/// A [GroupedRelBuilder] implementation that produces a [OneKeyNonSingularGroupedRel].
pub struct OneKeyNonSingularGroupedRelBuilder<T>
where
    T: ArrowPrimitiveType,
{
    /// The index of the column in the [SemijoinResultBatch]s that will be used as the groupby-key.
    group_on_col: usize,

    /// Hashmap mapping keys of type T to (weight, hol_ptr) tuples.
    /// `weight` is the total weight of input tuples that have this key (this is the sum of { t.weight | t in input, t.key ==key})
    ///  `hol_ptr` is the index of the first tuple in the group.
    pub map: RawTable<(T::Native, WEIGHT, PTR)>,
    /// Encodes a linked list of next_ptr, chaining together all tuples that belong to the same group
    next: Vec<PTR>,
    /// The random state for hashing keys
    pub random_state: RandomState,
    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl<T> GroupedRelBuilder for OneKeyNonSingularGroupedRelBuilder<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    fn build(&mut self, batches: &[SemiJoinResultBatch]) {
        let mut offset = 0;

        // The `filtered_keys_buffer` will be used to store (key, hash) pairs of values
        let mut keys_and_hashes_buffer = Vec::new();

        for batch in batches {
            self.ingest(batch, offset, &mut keys_and_hashes_buffer);
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

        //let map = std::mem::take(&mut self.map);
        let grouped_rel: OneKeyNonSingularGroupedRel<T> = OneKeyNonSingularGroupedRel::new(
            schema,
            std::mem::take(&mut self.map),
            data,
            std::mem::take(&mut self.random_state),
            use_alternative,
        );

        Arc::new(grouped_rel)
    }
}

impl<T> OneKeyNonSingularGroupedRelBuilder<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    /// Create a new builder with the given capacity and random state.
    /// Grouping will be done on `groupby_key_col` of the input. This column must be non-nested.
    pub fn new(
        group_on_col: usize,
        capacity: usize,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        Self {
            group_on_col,
            map: RawTable::with_capacity(capacity),
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
        keys_and_hashes_buffer: &mut Vec<(T::Native, u64)>,
    ) {
        match batch {
            SemiJoinResultBatch::Flat(batch) => {
                self.ingest_flat_batch(batch, offset, keys_and_hashes_buffer);
            }
            SemiJoinResultBatch::Nested(batch) => {
                self.ingest_nested_batch(batch, offset, keys_and_hashes_buffer);
            }
        }
    }

    /// Ingest a single Flat [RecordBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_flat_batch(
        &mut self,
        batch: &RecordBatch,
        offset: usize,
        keys_and_hashes_buffer: &mut Vec<(T::Native, u64)>,
    ) {
        // Get key column from guard batch and downcast it to a PrimitiveArray of type T
        let keys = batch.column(self.group_on_col);
        let keys = keys
            .as_any()
            .downcast_ref::<PrimitiveArray<T>>()
            .expect("Key column should be a primitive array of type T");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(!keys.is_nullable(), "Group-by keys should be non-nullable");

        // We will store (key, hash) pairs in the `keys_and_hashes` buffer
        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?
        keys_and_hashes_buffer.resize(keys.len(), (T::default_value(), 0));
        for ((key, hash), src_key) in keys_and_hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *key = *src_key;
            *hash = key.hash_one(&self.random_state);
        }

        for (row, (key, hash)) in keys_and_hashes_buffer.iter().enumerate() {
            self.update_key(*key, 1, row, offset, *hash);
        }
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(
        &mut self,
        batch: &NestedBatch,
        offset: usize,
        keys_and_hashes_buffer: &mut Vec<(T::Native, u64)>,
    ) {
        // Get key column from guard batch and downcast it to a PrimitiveArray of type T
        let keys = batch.regular_column(self.group_on_col);
        let keys = keys
            .as_any()
            .downcast_ref::<PrimitiveArray<T>>()
            .expect("Key column should be a primitive array of type T");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(!keys.is_nullable(), "Group-by keys should be non-nullable");

        //store (key, hash) pairs for all rows in the batch (ignoring the selection vector)
        // strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // It also means we have the same loop-code path for filtered and non-filtered batches
        keys_and_hashes_buffer.resize(keys.len(), (T::default_value(), 0));
        for ((key, hash), src_key) in keys_and_hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *key = *src_key;
            *hash = key.hash_one(&self.random_state);
        }

        // The total weight of each row in the batch
        let weights = batch.total_weights();

        for (row, ((key, hash), weight)) in keys_and_hashes_buffer.iter().zip(weights).enumerate() {
            self.update_key(*key, *weight, row, offset, *hash);
        }
    }

    #[inline(always)]
    fn update_key(
        &mut self,
        key: T::Native,
        tuple_weight: WEIGHT,
        row: usize,
        offset: usize,
        hash: u64, // the hash value of the key
    ) {
        let entry = self.map.get_mut(hash, |(k, _, _)| *k == key);

        match entry {
            // Group does not exist yet
            None => {
                self.map.insert(
                    hash,
                    (key, tuple_weight, (offset + row + 1) as PTR),
                    |(_k  , _, _)| {
                        panic!("[ERROR!!!] rehash called on insert into RawTable (meaning pre-allocation was too small)!");
                        //k.hash_one(&self.random_state)
                    },
                );
            }

            // Group already exists
            Some((_key, weight, hol_ptr)) => {
                *weight += tuple_weight;
                let old_hol_ptr = *hol_ptr;
                *hol_ptr = (offset + row + 1) as PTR; // update the hol pointer to the current tuple (+1 since 0 is reserved for "no next")
                self.next[offset + row] = old_hol_ptr; // store the previous head of list in the slot for the current tuple
            }
        }
    }
}

/// A [GroupedRel] implementation that groups on a single key column of type T and where the unique nested column is singular.
pub struct OneKeySingularGroupedRel<T>
where
    T: ArrowPrimitiveType,
{
    /// The schema of the [GroupedRel]
    pub schema: NestedSchemaRef,
    /// Hashmap mapping keys of type T to their weights.
    /// Because the nested column is singular, there is no need to create HOL pointers.
    pub map: RawTable<(T::Native, WEIGHT)>,
    /// The random state for hashing keys during lookup
    pub random_state: RandomState,
    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,
}

impl<T> GroupedRel for OneKeySingularGroupedRel<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    fn lookup(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
        _row_count: usize,
    ) -> (Sel, NestedColumn) {
        let keys = validate_lookup_keys(keys);

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
        let keys = validate_lookup_keys(keys);
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

impl<T> OneKeySingularGroupedRel<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    /// Create a new [OneKeySingularGroupedRel] with the given map and random state.
    pub fn new(
        schema: NestedSchemaRef,
        map: RawTable<(T::Native, WEIGHT)>,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        Self {
            schema,
            map,
            random_state,
            alternative_flag: use_alternative,
        }
    }

    #[inline(always)]
    pub fn lookup_impl(
        &self,
        keys: &PrimitiveArray<T>,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>) {
        // let mut sel_vector: Vec<PTR> = Vec::with_capacity(keys.len());
        // let mut weights: Vec<WEIGHT> = Vec::with_capacity(keys.len());

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // NOTE: in contrast to when building the hashmap, we do not store the key here, as this is impossible to do in a generic way (we don't know the type of the key in the Groups::lookup function)
        // and we cannot mutate the groups structure here, so we can't have a local keys_and_hashes buffer that stores the keys (at least, not in a performant way)
        hashes_buffer.resize(keys.len(), 0);
        for (hash, src_key) in hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *hash = src_key.hash_one(&self.random_state);
        }

        // let (sel_vector, weights) = hashes_buffer
        //     .iter()
        //     .zip(keys.values().iter())
        //     .enumerate()
        //     .filter_map(|(i, (&hash, &key))| {
        //         let entry = self.map.get(hash, |(k, _)| *k == key);
        //         entry.map(|(_, weight)| (i as PTR, *weight))
        //     })
        //     .unzip();

        let sel_vector: Vec<PTR> = hashes_buffer
            .iter()
            .zip(keys.values().iter())
            .enumerate()
            .filter_map(|(i, (&hash, &key))| {
                let entry = self.map.get(hash, |(k, _)| *k == key);
                entry.map(|_| i as PTR)
            })
            .collect();

        let weights = sel_vector
            .iter()
            .map(|&i| {
                let key = unsafe { keys.value_unchecked(i as usize) };
                let hash = unsafe { *hashes_buffer.get_unchecked(i as usize) };
                let entry = self.map.get(hash, |(k, _)| *k == key);

                match entry {
                    Some((_, weight)) => *weight,
                    None => unreachable!(),
                }
            })
            .collect();

        // for (i, (hash, key)) in hashes_buffer.iter().zip(keys.values().iter()).enumerate() {
        //     let key = *key;
        //     let hash = *hash;
        //     let entry = self.map.get(hash, |(k, _)| *k == key);

        //     if let Some((_, weight)) = entry {
        //         sel_vector.push(i as PTR);
        //         weights.push(*weight);
        //     }
        // }

        (sel_vector, weights)
    }

    /// Included for benchmarking purposes. Can be removed in final version.
    pub fn lookup_impl_alternative(
        &self,
        keys: &PrimitiveArray<T>,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>) {
        let mut sel_vector: Vec<PTR> = Vec::new();
        let mut weights: Vec<WEIGHT> = Vec::new();

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // NOTE: in contrast to when building the hashmap, we do not store the key here, as this is impossible to do in a generic way (we don't know the type of the key in the Groups::lookup function)
        // and we cannot mutate the groups structure here, so we can't have a local keys_and_hashes buffer that stores the keys (at least, not in a performant way)
        hashes_buffer.resize(keys.len(), 0);
        for (hash, src_key) in hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *hash = src_key.hash_one(&self.random_state);
        }

        for (i, (hash, key)) in hashes_buffer.iter().zip(keys.values().iter()).enumerate() {
            let key = *key;
            let hash = *hash;
            let entry = self.map.get(hash, |(k, _)| *k == key);

            if let Some((_, weight)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
            }
        }

        (sel_vector, weights)
    }

    pub fn lookup_sel_impl(
        &self,
        keys: &PrimitiveArray<T>,
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
    ) -> Vec<WEIGHT> {
        // Create result vectors with the same length as keys.len
        let mut weights: Vec<WEIGHT> = vec![0 as WEIGHT; keys.len()];

        // this function uses a lot of unsafe code for performance
        // SAFETY:
        // The safety hinges on the fact that the sel vector is monotonically increasing, with the maximum value below keys.len()
        assert!(sel.max() <= keys.len(), "Selection vector out of bounds");

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?
        hashes_buffer.resize(sel.len(), 0);
        for (hash, row_nr) in hashes_buffer.iter_mut().zip(sel.iter()) {
            let key = unsafe { keys.value_unchecked(row_nr) };
            *hash = key.hash_one(&self.random_state);
        }

        // Iterate over the selection vector, and for each row, look up the key in the hashmap
        // when the inner closure returns true the row is retained in the selection vector
        // in the closure, `i` is the position in `sel` at which the element `row_nr` is found.
        sel.refine(|i, row_nr| {
            let key = unsafe { keys.value_unchecked(row_nr) };
            let hash = unsafe { *hashes_buffer.get_unchecked(i) };

            let entry = self.map.get(hash, |(k, _)| *k == key);

            match entry {
                Some((_, weight)) => {
                    // Copy the found weight to the weights vector at index `row_idx`
                    // SAFETY: row_idx is guaranteed to be within bounds of the weights vector
                    let dest_weight = unsafe { weights.get_unchecked_mut(row_nr) };
                    *dest_weight = *weight;

                    true
                }
                None => false,
            }
        });

        weights
    }
}

/// A [GroupedRelBuilder] implementation that produces a [OneKeySingularGroupedRel].
pub struct OneKeySingularGroupedRelBuilder<T>
where
    T: ArrowPrimitiveType,
{
    /// The index of the column in the [SemijoinResultBatch]s that will be used as the groupby-key.
    group_on_col: usize,

    /// Hashmap mapping keys of type T to weights.
    /// `weight` is the total weight of input tuples that have this key (this is the sum of { t.weight | t in input, t.key ==key})
    /// Since the [GroupedRel] that we are building is singular, there is no need to store HOL pointers, nor for creating a `next` vector.
    pub map: RawTable<(T::Native, WEIGHT)>,
    /// The random state for hashing keys
    pub random_state: RandomState,
    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl<T> GroupedRelBuilder for OneKeySingularGroupedRelBuilder<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    fn build(&mut self, batches: &[SemiJoinResultBatch]) {
        // The `filtered_keys_buffer` will be used to store (key, hash) pairs of values
        // we allocate the space once to re-use for every batch
        let mut keys_and_hashes_buffer = Vec::new();

        for batch in batches {
            self.ingest(batch, &mut keys_and_hashes_buffer);
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

        let grouped_rel: OneKeySingularGroupedRel<T> = OneKeySingularGroupedRel::new(
            schema,
            std::mem::take(&mut self.map),
            std::mem::take(&mut self.random_state),
            use_alternative,
        );

        Arc::new(grouped_rel)
    }
}

impl<T> OneKeySingularGroupedRelBuilder<T>
where
    T: ArrowPrimitiveType,
    T::Native: HashValue,
{
    /// Create a new builder with the given capacity and random state.
    /// Grouping will be done on `groupby_key_col` of the input. This column must be non-nested.
    pub fn new(
        group_on_col: usize,
        capacity: usize,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        Self {
            group_on_col,
            map: RawTable::with_capacity(capacity),
            random_state,
            use_alternative,
        }
    }

    /// Ingest a single [SemiJoinResultBatch] of tuples into the state.
    #[inline(always)]
    fn ingest(
        &mut self,
        batch: &SemiJoinResultBatch,
        keys_and_hashes_buffer: &mut Vec<(T::Native, u64)>,
    ) {
        match batch {
            SemiJoinResultBatch::Flat(batch) => {
                self.ingest_flat_batch(batch, keys_and_hashes_buffer);
            }
            SemiJoinResultBatch::Nested(batch) => {
                self.ingest_nested_batch(batch, keys_and_hashes_buffer);
            }
        }
    }

    /// Ingest a single Flat [RecordBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_flat_batch(
        &mut self,
        batch: &RecordBatch,
        keys_and_hashes_buffer: &mut Vec<(T::Native, u64)>,
    ) {
        // Get key column from guard batch and downcast it to a PrimitiveArray of type T
        let keys = batch.column(self.group_on_col);
        let keys = keys
            .as_any()
            .downcast_ref::<PrimitiveArray<T>>()
            .expect("Key column should be a primitive array of type T");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(!keys.is_nullable(), "Group-by keys should be non-nullable");

        // We will store (key, hash) pairs in the `keys_and_hashes` buffer
        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?
        keys_and_hashes_buffer.resize(keys.len(), (T::default_value(), 0));
        for ((key, hash), src_key) in keys_and_hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *key = *src_key;
            *hash = key.hash_one(&self.random_state);
        }

        for (key, hash) in keys_and_hashes_buffer.iter() {
            self.update_key(*key, 1, *hash);
        }
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(
        &mut self,
        batch: &NestedBatch,
        keys_and_hashes_buffer: &mut Vec<(T::Native, u64)>,
    ) {
        // Get key column from guard batch and downcast it to a PrimitiveArray of type T
        let keys = batch.regular_column(self.group_on_col);
        let keys = keys
            .as_any()
            .downcast_ref::<PrimitiveArray<T>>()
            .expect("Key column should be a primitive array of type T");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(!keys.is_nullable(), "Group-by keys should be non-nullable");

        // otherwise, store (key, hash) pairs for all rows in the batch (ignoring the selection vector)
        // strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // It also means we have the same loop-code path for filtered and non-filtered batches
        keys_and_hashes_buffer.resize(keys.len(), (T::default_value(), 0));
        for ((key, hash), src_key) in keys_and_hashes_buffer.iter_mut().zip(keys.values().iter()) {
            *key = *src_key;
            *hash = key.hash_one(&self.random_state);
        }

        // Compute the total weight of each row in the batch
        let weights = batch.total_weights();

        for ((key, hash), weight) in keys_and_hashes_buffer.iter().zip(weights) {
            self.update_key(*key, *weight, *hash);
        }
    }

    #[inline(always)]
    fn update_key(
        &mut self,
        key: T::Native,
        tuple_weight: WEIGHT,
        hash: u64, // the hash value of the key
    ) {
        let entry = self.map.get_mut(hash, |(k, _)| *k == key);

        match entry {
            // Group does not exist yet
            None => {
                self.map.insert(
                    hash,
                    (key, tuple_weight),
                    |(_k  , _)| {
                        panic!("[ERROR!!!] rehash called on insert into RawTable (meaning pre-allocation was too small)!");
                        //k.hash_one(&self.random_state)
                    },
                );
            }

            // Group already exists, just update the weight.
            Some((_key, weight)) => {
                *weight += tuple_weight;
            }
        }
    }
}

macro_rules! builder_one_key_helper_singular {
    ($key_type:ty, $group_col:expr, $capacity:expr, $random_state:expr, $flag:expr) => {
        Box::new(OneKeySingularGroupedRelBuilder::<$key_type>::new(
            $group_col,
            $capacity,
            $random_state,
            $flag,
        ))
    };
}

macro_rules! builder_one_key_helper_non_singular {
    ($key_type:ty, $group_col:expr, $capacity:expr, $random_state:expr, $flag:expr) => {
        Box::new(OneKeyNonSingularGroupedRelBuilder::<$key_type>::new(
            $group_col,
            $capacity,
            $random_state,
            $flag,
        ))
    };
}

/// Create a new [GroupedRelBuilder] for a single primitive-typed, **non-nullable** key column.
pub fn make_builder(
    t: &DataType,
    group_on_col: usize,
    is_singular: bool,
    capacity: usize,
    random_state: RandomState,
    flag: bool,
) -> Box<dyn GroupedRelBuilder> {
    // Following use statement is required to make the downcast_primitive! macro work (otherwise error `arrow_schema unknown`)
    use datafusion::arrow::datatypes as arrow_schema;

    if is_singular {
        downcast_primitive! {
            t => (builder_one_key_helper_singular, group_on_col, capacity, random_state, flag),
            _ => panic!("make_grouped_rel_builder_single_primitive_key expects primitive keys")
        }
    } else {
        downcast_primitive! {
            t => (builder_one_key_helper_non_singular,  group_on_col, capacity, random_state, flag),
            _ => panic!("make_grouped_rel_builder_single_primitive_key expects primitive keys")
        }
    }
}
