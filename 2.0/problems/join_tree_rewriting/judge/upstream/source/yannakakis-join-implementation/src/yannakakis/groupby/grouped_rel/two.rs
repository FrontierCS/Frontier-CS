//! Specialized [GroupedRel] implementations, and their builders for grouping on two-column primitive keys.
//! Two variants exist: one for singular [GroupedRel] and one for non-singular [GroupedRel]

// TO BE COMPLETED

use ahash::RandomState;

use datafusion::arrow::array::Array;
use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::array::PrimitiveArray;
use datafusion::arrow::array::RecordBatch;
use datafusion::arrow::datatypes::ArrowPrimitiveType;
use datafusion::arrow::datatypes::DataType;
use datafusion::arrow::datatypes::UInt8Type;
use datafusion::arrow::datatypes::*;
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

use DataType::*;

use std::sync::Arc;
use DurationMicrosecondType as duration_mus;
use DurationMillisecondType as duration_ms;
use DurationNanosecondType as duration_ns;
use DurationSecondType as duration_sec;

use Time32MillisecondType as time_ms;
use Time32SecondType as time_sec;
use Time64MicrosecondType as time_mus;
use Time64NanosecondType as time_ns;
use TimestampMicrosecondType as timestamp_mus;
use TimestampMillisecondType as timestamp_ms;
use TimestampNanosecondType as timestamp_ns;
use TimestampSecondType as timestamp_sec;

use IntervalDayTimeType as interval_dt;
use IntervalMonthDayNanoType as interval_md;
use IntervalYearMonthType as interval_ym;

// Combines two hashes into one hash
// Src: datafusion-common/src/common/hash_utils.rs
#[inline]
fn combine_hashes(l: u64, r: u64) -> u64 {
    let hash = (17 * 37u64).wrapping_add(l);
    hash.wrapping_mul(37).wrapping_add(r)
}

#[inline]
fn hash_pair<T1, T2>(key1: &T1::Native, key2: &T2::Native, state: &RandomState) -> u64
where
    T1: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2: ArrowPrimitiveType,
    T2::Native: HashValue,
{
    combine_hashes(key1.hash_one(state), key2.hash_one(state))
}

pub struct DoubleKeyNonSingularGroupedRel<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
{
    /// The scheme of the [GroupedRel]
    pub schema: NestedSchemaRef,
    /// Hashmap mapping keys of type (T1,T2) to (weight, hol_ptr) tuples.
    pub map: RawTable<(T1::Native, T2::Native, WEIGHT, PTR)>,
    /// The data part of the nested column
    pub data: Arc<NestedRel>,
    /// The random state for hashing keys during lookup
    pub random_state: RandomState,
    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,
}

impl<T1, T2> GroupedRel for DoubleKeyNonSingularGroupedRel<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2::Native: HashValue,
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
        let keys = validate_lookup_keys::<T1, T2>(keys);

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
        let keys = validate_lookup_keys::<T1, T2>(keys);
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

#[inline]
/// Validate that `keys` consist of two columns of primitive type, non-null, and that they are of the same length.
/// Returns these two columns as a [PrimitiveArray] of the correct type
fn validate_lookup_keys<T1, T2>(keys: &[ArrayRef]) -> (&PrimitiveArray<T1>, &PrimitiveArray<T2>)
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
{
    assert!(
        keys.len() == 2,
        "DoubleKey GroupedRel variants requires two key columns"
    );

    let keys = (
        keys[0]
            .as_any()
            .downcast_ref::<PrimitiveArray<T1>>()
            .expect("First key column should be a primitive array of type T1"),
        keys[1]
            .as_any()
            .downcast_ref::<PrimitiveArray<T2>>()
            .expect("Second key column should be a primitive array of type T2"),
    );

    assert!(
        keys.0.len() == keys.1.len(),
        "Lookup keys should be of the same length"
    );

    assert!(
        !keys.0.is_nullable() && !keys.1.is_nullable(),
        "Lookup keys should be non-nullable"
    );

    keys
}

impl<T1, T2> DoubleKeyNonSingularGroupedRel<T1, T2>
where
    T1: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2: ArrowPrimitiveType,
    T2::Native: HashValue,
{
    /// Create a new [DoubleKeyNonSingularGroupedRel] with the given map and random state.
    pub fn new(
        schema: NestedSchemaRef,
        map: RawTable<(T1::Native, T2::Native, WEIGHT, PTR)>,
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
    fn lookup_impl(
        &self,
        keys: (&PrimitiveArray<T1>, &PrimitiveArray<T2>),
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>, Vec<PTR>) {
        // keys.0.len() == keys.1.len() is guaranteed by the caller
        let mut sel_vector: Vec<PTR> = Vec::with_capacity(keys.0.len());
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(keys.0.len());
        let mut hols: Vec<PTR> = Vec::with_capacity(keys.0.len());

        hashes_buffer.resize(keys.0.len(), 0);

        // Hash `keys` and store them in hashes_buffer
        for (hash, (key1, key2)) in hashes_buffer
            .iter_mut()
            .zip(keys.0.values().iter().zip(keys.1.values()))
        {
            *hash = hash_pair::<T1, T2>(key1, key2, &self.random_state);
        }

        // Lookup the keys in the hashmap
        for (i, (hash, (key1, key2))) in hashes_buffer
            .iter()
            .zip(keys.0.values().iter().zip(keys.1.values()))
            .enumerate()
        {
            let entry = self
                .map
                .get(*hash, |(k1, k2, _, _)| *k1 == *key1 && *k2 == *key2);

            if let Some((_, _, weight, hol_ptr)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
                hols.push(*hol_ptr);
            }
        }

        (sel_vector, weights, hols)
    }

    /// Included for benchmarking purposes. Can be removed in final version.
    /// (Currently the same as `lookup_impl`)
    #[inline(always)]
    fn lookup_impl_alternative(
        &self,
        keys: (&PrimitiveArray<T1>, &PrimitiveArray<T2>),
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>, Vec<PTR>) {
        // keys.0.len() == keys.1.len() is guaranteed by the caller
        let mut sel_vector: Vec<PTR> = Vec::with_capacity(keys.0.len());
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(keys.0.len());
        let mut hols: Vec<PTR> = Vec::with_capacity(keys.0.len());

        hashes_buffer.resize(keys.0.len(), 0);

        // Hash `keys` and store them in hashes_buffer
        for (hash, (key1, key2)) in hashes_buffer
            .iter_mut()
            .zip(keys.0.values().iter().zip(keys.1.values()))
        {
            *hash = hash_pair::<T1, T2>(key1, key2, &self.random_state);
        }

        // Lookup the keys in the hashmap
        for (i, (hash, (key1, key2))) in hashes_buffer
            .iter()
            .zip(keys.0.values().iter().zip(keys.1.values()))
            .enumerate()
        {
            let entry = self
                .map
                .get(*hash, |(k1, k2, _, _)| *k1 == *key1 && *k2 == *key2);

            if let Some((_, _, weight, hol_ptr)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
                hols.push(*hol_ptr);
            }
        }

        (sel_vector, weights, hols)
    }

    fn lookup_sel_impl(
        &self,
        keys: (&PrimitiveArray<T1>, &PrimitiveArray<T2>),
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<WEIGHT>, Vec<PTR>) {
        // keys.0.len() == keys.1.len() is guaranteed by the caller
        // Create result vectors with the same length as keys.0.len (== keys.1.len())
        let mut weights: Vec<WEIGHT> = vec![0 as WEIGHT; keys.0.len()];
        let mut hols: Vec<PTR> = vec![0 as PTR; keys.0.len()];

        // this function uses a lot of unsafe code for performance
        // SAFETY:
        // The safety hinges on the fact that the sel vector is monotonically increasing, with the maximum value below keys.len()
        assert!(sel.max() <= keys.0.len(), "Selection vector out of bounds");

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // Store hashes in separate buffer
        hashes_buffer.resize(sel.len(), 0);
        for (hash, row_nr) in hashes_buffer.iter_mut().zip(sel.iter()) {
            let (key1, key2) = unsafe {
                (
                    keys.0.value_unchecked(row_nr),
                    keys.1.value_unchecked(row_nr),
                )
            };
            *hash = hash_pair::<T1, T2>(&key1, &key2, &self.random_state);
        }

        // Iterate over the selection vector, and for each row, look up the key in the hashmap
        // when the inner closure returns true the row is retained in the selection vector
        // in the closure, `i` is the position in `sel` at which the element `row_nr` is found.
        sel.refine(|i, row_nr| {
            let key = unsafe {
                (
                    keys.0.value_unchecked(row_nr),
                    keys.1.value_unchecked(row_nr),
                )
            };
            let hash = unsafe { *hashes_buffer.get_unchecked(i) };

            let entry = self
                .map
                .get(hash, |(k1, k2, _, _)| *k1 == key.0 && *k2 == key.1);

            match entry {
                Some((_, _, weight, hol_ptr)) => {
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

/// A [GroupedRelBuilder] implementation that produces a [DoubleKeyNonSingularGroupedRel].
pub struct DoubleKeyNonSingularGroupedRelBuilder<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
{
    /// The indices of the column in the [SemijoinResultBatch]s that will be used as the groupby-key.
    group_on_cols: (usize, usize),

    /// Hashmap mapping keys of type (T1,T2) to (weight, hol_ptr) tuples.
    /// `weight` is the total weight of input tuples that have this key (this is the sum of { t.weight | t in input, t.key ==key})
    ///  `hol_ptr` is the index of the first tuple in the group.
    pub map: RawTable<(T1::Native, T2::Native, WEIGHT, PTR)>,

    /// Encodes a linked list of next_ptr, chaining together all tuples that belong to the same group
    next: Vec<PTR>,

    /// The random state for hashing keys
    pub random_state: RandomState,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl<T1, T2> GroupedRelBuilder for DoubleKeyNonSingularGroupedRelBuilder<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2::Native: HashValue,
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

        let grouped_rel: DoubleKeyNonSingularGroupedRel<T1, T2> =
            DoubleKeyNonSingularGroupedRel::new(
                schema,
                std::mem::take(&mut self.map),
                data,
                std::mem::take(&mut self.random_state),
                use_alternative,
            );

        Arc::new(grouped_rel)
    }
}

impl<T1, T2> DoubleKeyNonSingularGroupedRelBuilder<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2::Native: HashValue,
{
    /// Create a new builder with the given capacity and random state.
    /// Grouping will be done on `group_on_cols` of the input. These columns must be non-nested.
    pub fn new(
        group_on_cols: (usize, usize),
        capacity: usize,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        Self {
            group_on_cols,
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
        keys_and_hashes_buffer: &mut Vec<(T1::Native, T2::Native, u64)>,
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
        keys_and_hashes_buffer: &mut Vec<(T1::Native, T2::Native, u64)>,
    ) {
        // Get key columns from guard batch and downcast them to PrimitiveArrays of type T1 and T2
        let key1 = batch
            .column(self.group_on_cols.0)
            .as_any()
            .downcast_ref::<PrimitiveArray<T1>>()
            .expect("1st key column should be a primitive array of type T1");
        let key2 = batch
            .column(self.group_on_cols.1)
            .as_any()
            .downcast_ref::<PrimitiveArray<T2>>()
            .expect("2nd key column should be a primitive array of type T2");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(
            !key1.is_nullable() && !key2.is_nullable(),
            "Group-by keys should be non-nullable"
        );

        // We will store (key, hash) pairs in the `keys_and_hashes` buffer
        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?
        keys_and_hashes_buffer.resize(key1.len(), (T1::default_value(), T2::default_value(), 0));
        for ((k1, k2, hash), (src_key1, src_key2)) in keys_and_hashes_buffer
            .iter_mut()
            .zip(key1.values().iter().zip(key2.values()))
        {
            *k1 = *src_key1;
            *k2 = *src_key2;
            *hash = hash_pair::<T1, T2>(k1, k2, &self.random_state);
        }

        for (row, (key1, key2, hash)) in keys_and_hashes_buffer.iter().enumerate() {
            self.update_key(*key1, *key2, 1, row, offset, *hash);
        }
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(
        &mut self,
        batch: &NestedBatch,
        offset: usize,
        keys_and_hashes_buffer: &mut Vec<(T1::Native, T2::Native, u64)>,
    ) {
        // Get key columns from guard batch and downcast them to PrimitiveArrays of type T1 and T2
        let key1 = batch
            .regular_column(self.group_on_cols.0)
            .as_any()
            .downcast_ref::<PrimitiveArray<T1>>()
            .expect("1st key column should be a primitive array of type T1");
        let key2 = batch
            .regular_column(self.group_on_cols.1)
            .as_any()
            .downcast_ref::<PrimitiveArray<T2>>()
            .expect("2nd key column should be a primitive array of type T2");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(
            !key1.is_nullable() && !key2.is_nullable(),
            "Group-by keys should be non-nullable"
        );

        //store (key, hash) pairs for all rows in the batch (ignoring the selection vector)
        // strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // It also means we have the same loop-code path for filtered and non-filtered batches
        keys_and_hashes_buffer.resize(key1.len(), (T1::default_value(), T2::default_value(), 0));
        for ((k1, k2, hash), (src_key1, src_key2)) in keys_and_hashes_buffer
            .iter_mut()
            .zip(key1.values().iter().zip(key2.values()))
        {
            *k1 = *src_key1;
            *k2 = *src_key2;
            *hash = hash_pair::<T1, T2>(k1, k2, &self.random_state);
        }

        // Compute the total weight of each row in the batch
        let weights = batch.total_weights();

        for (row, ((key1, key2, hash), weight)) in
            keys_and_hashes_buffer.iter().zip(weights).enumerate()
        {
            self.update_key(*key1, *key2, *weight, row, offset, *hash);
        }
    }

    /// Update hashmap with info from new tuple.
    #[inline(always)]
    fn update_key(
        &mut self,
        key1: T1::Native, // first part of key
        key2: T2::Native, // second part of key
        tuple_weight: WEIGHT,
        row: usize,
        offset: usize,
        hash: u64, // the hash value of (key1, key2)
    ) {
        let entry = self
            .map
            .get_mut(hash, |(k1, k2, _, _)| *k1 == key1 && *k2 == key2);

        match entry {
            // Group does not exist yet
            None => {
                self.map.insert(
                    hash,
                    (key1, key2, tuple_weight, (offset + row + 1) as PTR),
                    |(_k1, _k2  , _, _)| {
                        panic!("[ERROR!!!] rehash called on insert into RawTable (meaning pre-allocation was too small)!");
                    },
                );
            }

            // Group already exists
            Some((_, _, weight, hol_ptr)) => {
                *weight += tuple_weight;
                let old_hol_ptr = *hol_ptr;
                *hol_ptr = (offset + row + 1) as PTR; // update the hol pointer to the current tuple (+1 since 0 is reserved for "no next")
                self.next[offset + row] = old_hol_ptr; // store the previous head of list in the slot for the current tuple
            }
        }
    }
}

/// A [GroupedRel] implementation that groups on two key columns of type T1 and T2 respectively, and where the unique nested column is singular.
pub struct DoubleKeySingularGroupedRel<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
{
    /// The schema of the [GroupedRel]
    pub schema: NestedSchemaRef,
    /// Hashmap mapping keys of type T to their weights.
    /// Because the nested column is singular, there is no need to create HOL pointers.
    pub map: RawTable<(T1::Native, T2::Native, WEIGHT)>,
    /// The random state for hashing keys during lookup
    pub random_state: RandomState,
    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,
}

impl<T1, T2> GroupedRel for DoubleKeySingularGroupedRel<T1, T2>
where
    T1: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2: ArrowPrimitiveType,
    T2::Native: HashValue,
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

impl<T1, T2> DoubleKeySingularGroupedRel<T1, T2>
where
    T1: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2: ArrowPrimitiveType,
    T2::Native: HashValue,
{
    /// Create a new [OneKeySingularGroupedRel] with the given map and random state.
    pub fn new(
        schema: NestedSchemaRef,
        map: RawTable<(T1::Native, T2::Native, WEIGHT)>,
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
        keys: (&PrimitiveArray<T1>, &PrimitiveArray<T2>),
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>) {
        // keys.0.len() == keys.1.len() is guaranteed by the caller
        let mut sel_vector: Vec<PTR> = Vec::with_capacity(keys.0.len());
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(keys.0.len());

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // NOTE: in contrast to when building the hashmap, we do not store the key here, as this is impossible to do in a generic way (we don't know the type of the key in the Groups::lookup function)
        // and we cannot mutate the groups structure here, so we can't have a local keys_and_hashes buffer that stores the keys (at least, not in a performant way)
        hashes_buffer.resize(keys.0.len(), 0);
        for (hash, (src_key1, src_key2)) in hashes_buffer
            .iter_mut()
            .zip(keys.0.values().iter().zip(keys.1.values()))
        {
            *hash = hash_pair::<T1, T2>(src_key1, src_key2, &self.random_state);
        }

        for (i, (hash, (key1, key2))) in hashes_buffer
            .iter()
            .zip(keys.0.values().iter().zip(keys.1.values()))
            .enumerate()
        {
            let key1 = *key1;
            let key2 = *key2;
            let hash = *hash;
            let entry = self.map.get(hash, |(k1, k2, _)| *k1 == key1 && *k2 == key2);

            if let Some((_, _, weight)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
            }
        }

        (sel_vector, weights)
    }

    /// Included for benchmarking purposes. Can be removed in final version.
    /// (Currently the same as `lookup_impl`)
    pub fn lookup_impl_alternative(
        &self,
        keys: (&PrimitiveArray<T1>, &PrimitiveArray<T2>),
        hashes_buffer: &mut Vec<u64>,
    ) -> (Vec<PTR>, Vec<WEIGHT>) {
        // keys.0.len() == keys.1.len() is guaranteed by the caller
        let mut sel_vector: Vec<PTR> = Vec::with_capacity(keys.0.len());
        let mut weights: Vec<WEIGHT> = Vec::with_capacity(keys.0.len());

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // NOTE: in contrast to when building the hashmap, we do not store the key here, as this is impossible to do in a generic way (we don't know the type of the key in the Groups::lookup function)
        // and we cannot mutate the groups structure here, so we can't have a local keys_and_hashes buffer that stores the keys (at least, not in a performant way)
        hashes_buffer.resize(keys.0.len(), 0);
        for (hash, (src_key1, src_key2)) in hashes_buffer
            .iter_mut()
            .zip(keys.0.values().iter().zip(keys.1.values()))
        {
            *hash = hash_pair::<T1, T2>(src_key1, src_key2, &self.random_state);
        }

        for (i, (hash, (key1, key2))) in hashes_buffer
            .iter()
            .zip(keys.0.values().iter().zip(keys.1.values()))
            .enumerate()
        {
            let key1 = *key1;
            let key2 = *key2;
            let hash = *hash;
            let entry = self.map.get(hash, |(k1, k2, _)| *k1 == key1 && *k2 == key2);

            if let Some((_, _, weight)) = entry {
                sel_vector.push(i as PTR);
                weights.push(*weight);
            }
        }

        (sel_vector, weights)
    }

    pub fn lookup_sel_impl(
        &self,
        keys: (&PrimitiveArray<T1>, &PrimitiveArray<T2>),
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
    ) -> Vec<WEIGHT> {
        // keys.0.len() == keys.1.len() is guaranteed by the caller
        // Create result vectors with the same length as keys.len
        let mut weights: Vec<WEIGHT> = vec![0 as WEIGHT; keys.0.len()];

        // this function uses a lot of unsafe code for performance
        // SAFETY:
        // The safety hinges on the fact that the sel vector is monotonically increasing, with the maximum value below keys.len()
        assert!(sel.max() <= keys.0.len(), "Selection vector out of bounds");

        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop (about 10% faster)
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?

        // Store hashes in separate buffer
        hashes_buffer.resize(sel.len(), 0);
        for (hash, row_nr) in hashes_buffer.iter_mut().zip(sel.iter()) {
            let (key1, key2) = unsafe {
                (
                    keys.0.value_unchecked(row_nr),
                    keys.1.value_unchecked(row_nr),
                )
            };
            *hash = hash_pair::<T1, T2>(&key1, &key2, &self.random_state);
        }

        // Iterate over the selection vector, and for each row, look up the key in the hashmap
        // when the inner closure returns true the row is retained in the selection vector
        // in the closure, `i` is the position in `sel` at which the element `row_nr` is found.
        sel.refine(|i, row_nr| {
            let key = unsafe {
                (
                    keys.0.value_unchecked(row_nr),
                    keys.1.value_unchecked(row_nr),
                )
            };
            let hash = unsafe { *hashes_buffer.get_unchecked(i) };

            let entry = self
                .map
                .get(hash, |(k1, k2, _)| *k1 == key.0 && *k2 == key.1);

            match entry {
                Some((_, _, weight)) => {
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

/// A [GroupedRelBuilder] implementation that produces a [DoubleKeySingularGroupedRel].
pub struct DoubleKeySingularGroupedRelBuilder<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
{
    /// The indices of the column in the [SemijoinResultBatch]s that will be used as the groupby-key.
    group_on_cols: (usize, usize),

    /// Hashmap mapping keys of type (T1,T2) to weights.
    /// `weight` is the total weight of input tuples that have this key (this is the sum of { t.weight | t in input, t.key ==key})
    /// Since the [GroupedRel] that we are building is singular, there is no need to store HOL pointers, nor for creating a `next` vector.
    pub map: RawTable<(T1::Native, T2::Native, WEIGHT)>,

    /// The random state for hashing keys
    pub random_state: RandomState,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl<T1, T2> GroupedRelBuilder for DoubleKeySingularGroupedRelBuilder<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2::Native: HashValue,
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

        let grouped_rel: DoubleKeySingularGroupedRel<T1, T2> = DoubleKeySingularGroupedRel::new(
            schema,
            std::mem::take(&mut self.map),
            std::mem::take(&mut self.random_state),
            use_alternative,
        );

        Arc::new(grouped_rel)
    }
}

impl<T1, T2> DoubleKeySingularGroupedRelBuilder<T1, T2>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2::Native: HashValue,
{
    /// Create a new builder with the given capacity and random state.
    /// Grouping will be done on `group_on_cols` of the input. These columns must be non-nested.
    pub fn new(
        group_on_cols: (usize, usize),
        capacity: usize,
        random_state: RandomState,
        use_alternative: bool,
    ) -> Self {
        Self {
            group_on_cols,
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
        keys_and_hashes_buffer: &mut Vec<(T1::Native, T2::Native, u64)>,
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
        keys_and_hashes_buffer: &mut Vec<(T1::Native, T2::Native, u64)>,
    ) {
        // Get key columns from guard batch and downcast them to PrimitiveArrays of type T1 and T2
        let key1 = batch
            .column(self.group_on_cols.0)
            .as_any()
            .downcast_ref::<PrimitiveArray<T1>>()
            .expect("1st key column should be a primitive array of type T1");
        let key2 = batch
            .column(self.group_on_cols.1)
            .as_any()
            .downcast_ref::<PrimitiveArray<T2>>()
            .expect("2nd key column should be a primitive array of type T2");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(
            !key1.is_nullable() && !key2.is_nullable(),
            "Group-by keys should be non-nullable"
        );

        // We will store (key, hash) pairs in the `keys_and_hashes` buffer
        // Strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // may have something to do with the fact that each individual loop becomes simpler, and therefore easier to optimize / execute?
        keys_and_hashes_buffer.resize(key1.len(), (T1::default_value(), T2::default_value(), 0));
        for ((k1, k2, hash), (src_key1, src_key2)) in keys_and_hashes_buffer
            .iter_mut()
            .zip(key1.values().iter().zip(key2.values()))
        {
            *k1 = *src_key1;
            *k2 = *src_key2;
            *hash = hash_pair::<T1, T2>(k1, k2, &self.random_state);
        }

        for (key1, key2, hash) in keys_and_hashes_buffer.iter() {
            self.update_key(*key1, *key2, 1, *hash);
        }
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(
        &mut self,
        batch: &NestedBatch,
        keys_and_hashes_buffer: &mut Vec<(T1::Native, T2::Native, u64)>,
    ) {
        // Get key columns from guard batch and downcast them to PrimitiveArrays of type T1 and T2
        let key1 = batch
            .regular_column(self.group_on_cols.0)
            .as_any()
            .downcast_ref::<PrimitiveArray<T1>>()
            .expect("1st key column should be a primitive array of type T1");
        let key2 = batch
            .regular_column(self.group_on_cols.1)
            .as_any()
            .downcast_ref::<PrimitiveArray<T2>>()
            .expect("2nd key column should be a primitive array of type T2");

        // NOTE: this code assumes that the group-by keys are always non-null.
        assert!(
            !key1.is_nullable() && !key2.is_nullable(),
            "Group-by keys should be non-nullable"
        );

        //store (key, hash) pairs for all rows in the batch (ignoring the selection vector)
        // strangely enough, storing the hash value in a separate buffer and then using it in the loop below is faster
        // than computing the hash in the loop
        // It also means we have the same loop-code path for filtered and non-filtered batches
        keys_and_hashes_buffer.resize(key1.len(), (T1::default_value(), T2::default_value(), 0));
        for ((k1, k2, hash), (src_key1, src_key2)) in keys_and_hashes_buffer
            .iter_mut()
            .zip(key1.values().iter().zip(key2.values()))
        {
            *k1 = *src_key1;
            *k2 = *src_key2;
            *hash = hash_pair::<T1, T2>(k1, k2, &self.random_state);
        }

        // Compute the total weight of each row in the batch
        let weights = batch.total_weights();
        for ((key1, key2, hash), weight) in keys_and_hashes_buffer.iter().zip(weights) {
            self.update_key(*key1, *key2, *weight, *hash);
        }
    }

    #[inline(always)]
    fn update_key(
        &mut self,
        key1: T1::Native,
        key2: T2::Native,
        tuple_weight: WEIGHT,
        hash: u64, // the hash value of the key
    ) {
        let entry = self
            .map
            .get_mut(hash, |(k1, k2, _)| *k1 == key1 && *k2 == key2);

        match entry {
            // Group does not exist yet
            None => {
                self.map.insert(
                    hash,
                    (key1, key2, tuple_weight),
                    |(_, _ , _)| {
                        panic!("[ERROR!!!] rehash called on insert into RawTable (meaning pre-allocation was too small)!");
                        //k.hash_one(&self.random_state)
                    },
                );
            }

            // Group already exists, just update the weight.
            Some((_, _, weight)) => {
                *weight += tuple_weight;
            }
        }
    }
}

/// Create [GroupedRelBuilder] for primitive key types T1 & T2.
fn mkbuilder<T1, T2>(
    group_on_cols: (usize, usize),
    is_singular: bool,
    capacity: usize,
    random_state: RandomState,
    flag: bool,
) -> Box<dyn GroupedRelBuilder>
where
    T1: ArrowPrimitiveType,
    T2: ArrowPrimitiveType,
    T1::Native: HashValue,
    T2::Native: HashValue,
{
    if is_singular {
        Box::new(DoubleKeySingularGroupedRelBuilder::<T1, T2>::new(
            group_on_cols,
            capacity,
            random_state,
            flag,
        ))
    } else {
        Box::new(DoubleKeyNonSingularGroupedRelBuilder::<T1, T2>::new(
            group_on_cols,
            capacity,
            random_state,
            flag,
        ))
    }
}

fn downcast_t2<T1>(
    t2: &DataType,
    group_on_cols: (usize, usize),
    is_singular: bool,
    capacity: usize,
    state: RandomState,
    flag: bool,
) -> Box<dyn GroupedRelBuilder>
where
    T1: ArrowPrimitiveType,
    T1::Native: HashValue,
{
    use IntervalUnit::*;
    use TimeUnit::*;

    match t2 {
        Int8 => mkbuilder::<T1, Int8Type>(group_on_cols, is_singular, capacity, state, flag),
        Int16 => mkbuilder::<T1, Int16Type>(group_on_cols, is_singular, capacity, state, flag),
        Int32 => mkbuilder::<T1, Int32Type>(group_on_cols, is_singular, capacity, state, flag),
        Int64 => mkbuilder::<T1, Int64Type>(group_on_cols, is_singular, capacity, state, flag),
        UInt8 => mkbuilder::<T1, UInt8Type>(group_on_cols, is_singular, capacity, state, flag),
        UInt16 => mkbuilder::<T1, UInt16Type>(group_on_cols, is_singular, capacity, state, flag),
        UInt32 => mkbuilder::<T1, UInt32Type>(group_on_cols, is_singular, capacity, state, flag),
        UInt64 => mkbuilder::<T1, UInt64Type>(group_on_cols, is_singular, capacity, state, flag),
        Float16 => mkbuilder::<T1, Float16Type>(group_on_cols, is_singular, capacity, state, flag),
        Float32 => mkbuilder::<T1, Float32Type>(group_on_cols, is_singular, capacity, state, flag),
        Float64 => mkbuilder::<T1, Float64Type>(group_on_cols, is_singular, capacity, state, flag),
        Timestamp(Nanosecond, _) => {
            mkbuilder::<T1, timestamp_ns>(group_on_cols, is_singular, capacity, state, flag)
        }
        Timestamp(Microsecond, _) => {
            mkbuilder::<T1, timestamp_mus>(group_on_cols, is_singular, capacity, state, flag)
        }
        Timestamp(Millisecond, _) => {
            mkbuilder::<T1, timestamp_ms>(group_on_cols, is_singular, capacity, state, flag)
        }
        Timestamp(Second, _) => {
            mkbuilder::<T1, timestamp_sec>(group_on_cols, is_singular, capacity, state, flag)
        }
        Date32 => mkbuilder::<T1, Date32Type>(group_on_cols, is_singular, capacity, state, flag),
        Date64 => mkbuilder::<T1, Date64Type>(group_on_cols, is_singular, capacity, state, flag),
        Time32(Second) => {
            mkbuilder::<T1, time_sec>(group_on_cols, is_singular, capacity, state, flag)
        }
        Time32(Millisecond) => {
            mkbuilder::<T1, time_ms>(group_on_cols, is_singular, capacity, state, flag)
        }
        Time64(Microsecond) => {
            mkbuilder::<T1, time_mus>(group_on_cols, is_singular, capacity, state, flag)
        }
        Time64(Nanosecond) => {
            mkbuilder::<T1, time_ns>(group_on_cols, is_singular, capacity, state, flag)
        }
        Duration(Second) => {
            mkbuilder::<T1, duration_sec>(group_on_cols, is_singular, capacity, state, flag)
        }
        Duration(Millisecond) => {
            mkbuilder::<T1, duration_ms>(group_on_cols, is_singular, capacity, state, flag)
        }
        Duration(Microsecond) => {
            mkbuilder::<T1, duration_mus>(group_on_cols, is_singular, capacity, state, flag)
        }
        Duration(Nanosecond) => {
            mkbuilder::<T1, duration_ns>(group_on_cols, is_singular, capacity, state, flag)
        }
        Interval(YearMonth) => {
            mkbuilder::<T1, interval_ym>(group_on_cols, is_singular, capacity, state, flag)
        }
        Interval(DayTime) => {
            mkbuilder::<T1, interval_dt>(group_on_cols, is_singular, capacity, state, flag)
        }
        Interval(MonthDayNano) => {
            mkbuilder::<T1, interval_md>(group_on_cols, is_singular, capacity, state, flag)
        }
        Decimal128(_, _) => {
            mkbuilder::<T1, Decimal128Type>(group_on_cols, is_singular, capacity, state, flag)
        }
        Decimal256(_, _) => {
            mkbuilder::<T1, Decimal256Type>(group_on_cols, is_singular, capacity, state, flag)
        }
        _ => panic!(
            "GroupedRelBuilder specialisation for two keys can only be done for primitive types"
        ),
    }
}

/// Create a new [GroupedRelBuilder] for a double primitive-typed key column.
pub fn make_builder(
    t1: &DataType,
    t2: &DataType,
    group_on_cols: (usize, usize),
    is_singular: bool,
    capacity: usize,
    random_state: RandomState,
    flag: bool,
) -> Box<dyn GroupedRelBuilder> {
    // Arrow's downcast_primitive! macro only works for a single primitive datatype.
    // However, we want to downcast two possibly different primitive datatypes (t1&t2).
    // One strategy would be to use downcast_primitive! to downcast t1, and in that macro, call downcast_primitive! to downcast t2.
    // For some reason, it is invalid to call the downcast_primitive! macro in another custom macro.
    //
    // Cleaner solutions than the one below are welcome!

    use IntervalUnit::*;
    use TimeUnit::*;

    match t1 {
        Int8 => {
            downcast_t2::<Int8Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Int16 => {
            downcast_t2::<Int16Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Int32 => {
            downcast_t2::<Int32Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Int64 => {
            downcast_t2::<Int64Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        UInt8 => {
            downcast_t2::<UInt8Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        UInt16 => {
            downcast_t2::<UInt16Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        UInt32 => {
            downcast_t2::<UInt32Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        UInt64 => {
            downcast_t2::<UInt64Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Float16 => {
            downcast_t2::<Float16Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Float32 => {
            downcast_t2::<Float32Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Float64 => {
            downcast_t2::<Float64Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Timestamp(_, _) => todo!(),
        Date32 => {
            downcast_t2::<Date32Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Date64 => {
            downcast_t2::<Date64Type>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Time32(Second) => {
            downcast_t2::<time_sec>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Time32(Millisecond) => {
            downcast_t2::<time_ms>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Time64(Microsecond) => {
            downcast_t2::<time_mus>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Time64(Nanosecond) => {
            downcast_t2::<time_ns>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Duration(Nanosecond) => {
            downcast_t2::<duration_ns>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Duration(Microsecond) => downcast_t2::<duration_mus>(
            t2,
            group_on_cols,
            is_singular,
            capacity,
            random_state,
            flag,
        ),
        Duration(Millisecond) => {
            downcast_t2::<duration_ms>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Duration(Second) => downcast_t2::<duration_sec>(
            t2,
            group_on_cols,
            is_singular,
            capacity,
            random_state,
            flag,
        ),
        Interval(YearMonth) => {
            downcast_t2::<interval_ym>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Interval(DayTime) => {
            downcast_t2::<interval_dt>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Interval(MonthDayNano) => {
            downcast_t2::<interval_md>(t2, group_on_cols, is_singular, capacity, random_state, flag)
        }
        Decimal128(_, _) => downcast_t2::<Decimal128Type>(
            t2,
            group_on_cols,
            is_singular,
            capacity,
            random_state,
            flag,
        ),
        Decimal256(_, _) => downcast_t2::<Decimal256Type>(
            t2,
            group_on_cols,
            is_singular,
            capacity,
            random_state,
            flag,
        ),
        _ => panic!(
            "GroupedRelBuilder specialisation for two keys can only be done for primitive types"
        ),
    }
}
