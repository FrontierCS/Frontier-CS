//! Specialized [GroupedRel] implementations, and their builders for grouping on no column.
//! This can happen when we need to take a cartesian product (i.e, a semijoin between two tables and no equi-join keys)
//! Two variants exist: one for singular [GroupedRel] and one for non-singular [GroupedRel]
//!
use crate::yannakakis::data::GroupedRelRef;
use crate::yannakakis::data::Idx;
use crate::yannakakis::data::NestedBatch;
use crate::yannakakis::data::NonSingularNestedColumn;
use crate::yannakakis::data::SemiJoinResultBatch;
use crate::yannakakis::data::SingularNestedColumn;
use crate::yannakakis::groupby::GroupedRelBuilder;

use super::super::super::data::GroupedRel;
use super::super::super::data::Idx as PTR;
use super::super::super::data::NestedColumn;
use super::super::super::data::NestedRel;
use super::super::super::data::NestedSchemaRef;
use super::super::super::data::Weight as WEIGHT;
use super::super::super::sel::Sel;
use datafusion::arrow::array::ArrayRef;
use datafusion::arrow::array::RecordBatch;

use std::sync::Arc;

/*
Special about this variant:
- All rows are together in a single group: need to store, HOL pointers, next vector or hashmap.
- Random state not needed (since no hashing)
- However, we still need to store the sum of the weights of all rows in the group.
*/

/*
From a logical viewpoint:
The next vector is always [0,1,...,nrows-1]. It encodes a single linked lists that contains all tuples.
Each hol_ptr will be `nrows` (refers to tuple at position `nrows-1`, which is the last tuple of the group)
*/

/// A [GroupedRel] implementation that groups on no column.
/// The result of the grouping is a single group that contains all input tuples.
pub struct NoneNonSingularGroupedRel {
    /// The scheme of the [GroupedRel]
    pub schema: NestedSchemaRef,

    /// Total weight of the grouped tuples.
    pub weight: WEIGHT,

    /// Total number of grouped tuples.
    pub nrows: Idx,

    /// The data part of the nested column.
    /// The data will be empty (since there are no columns to be nested at this level),
    /// except for the nested columns (if any) that are nested at a deeper level.
    pub data: Arc<NestedRel>,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,
}

impl GroupedRel for NoneNonSingularGroupedRel {
    fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    fn lookup(
        &self,
        keys: &[ArrayRef],
        _hashes_buffer: &mut Vec<u64>,
        row_count: usize,
    ) -> (Sel, NestedColumn) {
        assert_eq!(
            keys.len(),
            0,
            "No keys should be provided for NoneNonSingularGroupedRel"
        );

        let (sel, weights, hols) = if self.weight == 0 {
            // Groupby input was empty, no guard tuple passes the lookup
            (Sel::new_unchecked(vec![]), Vec::new(), Vec::new())
        } else {
            // Groupby input was non-empty, all tuples pass the lookup
            (
                Sel::all(row_count as Idx),
                vec![self.weight; row_count],
                vec![self.nrows as Idx; row_count],
            )
        };

        (
            sel,
            NestedColumn::NonSingular(NonSingularNestedColumn {
                hols,
                weights,
                data: self.data.clone(),
            }),
        )
    }

    fn lookup_sel(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        _hashes_buffer: &mut Vec<u64>,
        row_count: usize,
    ) -> NestedColumn {
        assert_eq!(
            keys.len(),
            0,
            "No keys should be provided for NoneNonSingularGroupedRel"
        );

        let (weights, hols) = if self.weight == 0 {
            // Groupby input was empty, no guard tuple passes the lookup
            sel.clear();
            (vec![0 as WEIGHT; row_count], vec![0 as PTR; row_count])
        } else {
            // Groupby input was non-empty, all tuples pass the lookup

            // `sel` remains the same
            (
                vec![self.weight; row_count],
                vec![self.nrows as Idx; row_count],
            )
        };

        NestedColumn::NonSingular(NonSingularNestedColumn {
            hols,
            weights,
            data: self.data.clone(),
        })
    }

    fn as_any(&self) -> &dyn std::any::Any {
        self
    }

    fn is_empty(&self) -> bool {
        self.nrows == 0
    }
}

/// A [GroupedRelBuilder] implementation that produces a [NoneNonSingularGroupedRel].
pub struct NoneNonSingularGroupedRelBuilder {
    /// Total weight of the grouped tuples.
    pub weight: WEIGHT,

    /// Total number of grouped tuples.
    pub nrows: Idx,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl NoneNonSingularGroupedRelBuilder {
    pub fn new(use_alternative: bool) -> Self {
        Self {
            weight: 0,
            nrows: 0,
            use_alternative: use_alternative,
        }
    }

    /// Ingest a single [SemiJoinResultBatch] of tuples into the state.
    #[inline(always)]
    fn ingest(&mut self, batch: &SemiJoinResultBatch) {
        match batch {
            SemiJoinResultBatch::Flat(batch) => self.ingest_flat_batch(batch),
            SemiJoinResultBatch::Nested(batch) => self.ingest_nested_batch(batch),
        }
    }

    /// Ingest a single Flat [RecordBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_flat_batch(&mut self, batch: &RecordBatch) {
        let input_rows = batch.num_rows() as Idx;
        self.nrows += input_rows;
        self.weight += input_rows; // weight = 1 for each row
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(&mut self, batch: &NestedBatch) {
        let input_rows = batch.num_rows() as Idx;
        self.nrows += input_rows;

        // Get the total weight of each row in the batch
        let weights = batch.total_weights();

        for weight in weights {
            self.weight += weight;
        }
    }
}

impl GroupedRelBuilder for NoneNonSingularGroupedRelBuilder {
    fn build(&mut self, batches: &[SemiJoinResultBatch]) {
        for batch in batches {
            self.ingest(batch);
        }
    }

    fn finish(
        &mut self,
        schema: NestedSchemaRef,
        grouped_col_inner_data: Option<NestedRel>,
        use_alternative: bool,
    ) -> GroupedRelRef {
        // The grouped_inner_col data does not yet have the correct `next` vector; we set it here.
        // The `next` vector is always [0,1,...,nrows-1]. It encodes a single linked lists that contains all tuples.
        let mut data = grouped_col_inner_data
            .expect("Non-singular nested column requires a valid inner NestedRel!");
        data.next = Some((0..self.nrows as Idx).collect());
        let data = Arc::new(data);

        let grouped_rel = NoneNonSingularGroupedRel {
            schema,
            weight: self.weight,
            nrows: self.nrows,
            data,
            alternative_flag: use_alternative,
        };

        Arc::new(grouped_rel)
    }
}

// NON-SINGULAR ABOVE ------------------------------------------------------------
// SINGULAR BELOW ----------------------------------------------------------------

/// A [GroupedRel] implementation that groups on no column.
/// The result of the grouping is a single group that contains all input tuples.
pub struct NoneSingularGroupedRel {
    /// The scheme of the [GroupedRel]
    pub schema: NestedSchemaRef,

    /// Total weight of the grouped tuples.
    pub weight: WEIGHT,

    /// Total number of grouped tuples.
    pub nrows: Idx,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub alternative_flag: bool,
}

impl GroupedRel for NoneSingularGroupedRel {
    fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    fn lookup(
        &self,
        keys: &[ArrayRef],
        _hashes_buffer: &mut Vec<u64>,
        row_count: usize,
    ) -> (Sel, NestedColumn) {
        assert_eq!(
            keys.len(),
            0,
            "No keys should be provided for NoneSingularGroupedRel"
        );

        let (sel, weights) = if self.weight == 0 {
            // Groupby input was empty, no guard tuple passes the lookup
            (Sel::new_unchecked(vec![]), Vec::new())
        } else {
            // Groupby input was non-empty, all tuples pass the lookup
            (Sel::all(row_count as Idx), vec![self.weight; row_count])
        };

        (
            sel,
            NestedColumn::Singular(SingularNestedColumn { weights }),
        )
    }

    fn lookup_sel(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        _hashes_buffer: &mut Vec<u64>,
        row_count: usize,
    ) -> NestedColumn {
        assert_eq!(
            keys.len(),
            0,
            "No keys should be provided for NoneNonSingularGroupedRel"
        );

        let weights = if self.weight == 0 {
            // Groupby input was empty, no guard tuple passes the lookup
            sel.clear();
            vec![0 as WEIGHT; row_count]
        } else {
            // Groupby input was non-empty, all tuples pass the lookup

            // `sel` remains the same
            vec![self.weight; row_count]
        };

        NestedColumn::Singular(SingularNestedColumn { weights })
    }

    fn as_any(&self) -> &dyn std::any::Any {
        self
    }

    fn is_empty(&self) -> bool {
        self.nrows == 0
    }
}

/// A [GroupedRelBuilder] implementation that produces a [NoneSingularGroupedRel].
pub struct NoneSingularGroupedRelBuilder {
    /// Total weight of the grouped tuples.
    pub weight: WEIGHT,

    /// Total number of grouped tuples.
    pub nrows: Idx,

    /// TODO: this is for benching purpose only, remove when done.
    //#[cfg(test)]
    pub use_alternative: bool,
}

impl NoneSingularGroupedRelBuilder {
    pub fn new(use_alternative: bool) -> Self {
        Self {
            weight: 0,
            nrows: 0,
            use_alternative: use_alternative,
        }
    }

    /// Ingest a single [SemiJoinResultBatch] of tuples into the state.
    #[inline(always)]
    fn ingest(&mut self, batch: &SemiJoinResultBatch) {
        match batch {
            SemiJoinResultBatch::Flat(batch) => self.ingest_flat_batch(batch),
            SemiJoinResultBatch::Nested(batch) => self.ingest_nested_batch(batch),
        }
    }

    /// Ingest a single Flat [RecordBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_flat_batch(&mut self, batch: &RecordBatch) {
        let input_rows = batch.num_rows() as Idx;
        self.nrows += input_rows;
        self.weight += input_rows; // weight = 1 for each row
    }

    /// Ingest a single [NestedBatch] of tuples into the state.
    #[inline(always)]
    fn ingest_nested_batch(&mut self, batch: &NestedBatch) {
        let input_rows = batch.num_rows() as Idx;
        self.nrows += input_rows;

        // Compute the total weight of each row in the batch
        let weights = batch.total_weights();

        for weight in weights {
            self.weight += weight;
        }
    }
}

impl GroupedRelBuilder for NoneSingularGroupedRelBuilder {
    fn build(&mut self, batches: &[SemiJoinResultBatch]) {
        for batch in batches {
            self.ingest(batch);
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

        let grouped_rel = NoneSingularGroupedRel {
            schema,
            weight: self.weight,
            nrows: self.nrows,
            alternative_flag: use_alternative,
        };

        Arc::new(grouped_rel)
    }
}

/// Create a new [GroupedRelBuilder] for no grouping columns.
#[inline(always)]
pub fn make_builder(is_singular: bool, flag: bool) -> Box<dyn GroupedRelBuilder> {
    if is_singular {
        Box::new(NoneSingularGroupedRelBuilder::new(flag))
    } else {
        Box::new(NoneNonSingularGroupedRelBuilder::new(flag))
    }
}
