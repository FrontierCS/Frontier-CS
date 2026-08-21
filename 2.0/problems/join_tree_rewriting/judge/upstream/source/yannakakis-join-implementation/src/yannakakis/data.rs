//! The data model central to our Implementation of Yannakakis.
//!
//!

use super::sel::Sel;
use std::{any::Any, sync::Arc};

use datafusion::arrow::{
    array::{ArrayRef, RecordBatch},
    datatypes::{DataType, Field, FieldRef, Schema, SchemaRef},
};

/// A [NestedSchema] is like a traditional flat relational schema except that fields may be nested.
/// Formally, it is a sequence of the form (A1, ..., Am, N1, ..., Nn) where:
/// - each Ai is a non-nested field (i.e., a regular attribute), and
/// - each Nj is itself a nested schema.
/// Note that both m and n may be zero.
/// In particular, some or all of the Nj, when viewed as NestedSchema's may themselves be the empty sequence.
///
/// From a logical viewpoint, an instance of a [NestedSchema] is a bag (i.e., a multiset of tuples) where each tuple has the form
/// (a1, ..., am, n1, ..., nn) with a1, ..., am being the values of the regular fields and n1, ..., nn being the values of the nested fields
/// (these are themselves hence against bags). However, none of the nested field values ni may be empty.
///
/// Clearly, a [NestedSchema] can encode a regular flat, non-nested schema. This happens when  it does not have any nested
/// fields, i.e., when n = 0.
///
/// A [NestedSchema] can also encode the result of a [GroupBy] operator. This happens when it has exactly one nested field, i.e., when n = 1.
/// We call the schema **grouped** in that case.
///
/// Also (semi-)joining a flat relation with a grouped relation will logically result in a nested relation with a grouped schema.
///
/// When we join a flat relation with multiple grouped relations, the result is a nested relation with a nested schema with n > 1.
///
/// Note while in general in nested relational algebra the values of a nested field like { (C) } are sets of tuples of schema (C) with
/// these sets possibly empty, for our purposes (i.e., implementing yannakakis) a nested field always contains a *non*-empty set of
/// tuples (over the child schema).  This ensures that when an instance I of a nested schema S is unnested, all of the regular regular field
/// values in I also occur in the unnested instance. This is important to obtain the constant-delay enumeratation property of the yannakakis
/// algorithm.
///
/// A NestedSchema is called *singular* if it is empty, or if it has only nested fields (i.e., m=0)  all of which are themselves singular.
/// For example, the schema ( { () } ) is singular, as is the schema ( { () }, { ( {()}, {()} ) } ).
/// In a schema like ( A, B, { {()}}) ) where all the nested field are singular unnesting has only the effect multiplying the multiplicity of the  regular tuples.
/// For example, in the instance
///
/// ----------------------------------
/// | A | B | { {()} }               |
/// | a1| b1| { {(), () }, {(), ()}} |
/// ----------------------------------
///
/// The tuple a1, b1 will be repeated four times when unnesting the nested field.
///
/// Since Instances with schemas such as the one above can be created by grouping a relation on *all* of its regular fields.
/// (And then possibly semijoining and grouping again on all of the regular fields, and so on) we will take care to handle such relations efficiently:
/// instead of keeping the entire nested state singular nested field, we can simply summarize them as the weight of the tuple required during unnesting.
///
/// A [NestedSchema] is called *simple* if all of its nested fields are singular. We will hence apply the above optimization to instances of simple schemas.
///
#[derive(Debug, PartialEq, Eq)]
pub struct NestedSchema {
    /// The non-nested fields of the schema
    pub regular_fields: SchemaRef,
    /// The nested fields of the schema
    pub nested_fields: Vec<NestedSchemaRef>,
}

pub type NestedSchemaRef = Arc<NestedSchema>;

impl NestedSchema {
    pub fn new(regular_fields: SchemaRef, nested_fields: Vec<NestedSchemaRef>) -> Self {
        Self {
            regular_fields,
            nested_fields,
        }
    }

    /// A [NestedSchema] is *grouped* if it has exactly one nested field, i.e., if n = 1.    
    /// The result of the [GroupBy] operator is logically a nested relation that has a grouped schema.  
    pub fn is_grouped(&self) -> bool {
        self.nested_fields.len() == 1
    }

    /// A [NestedSchema] encodes a flat schema if it does not have any nested fields.
    #[inline]
    pub fn is_flat(&self) -> bool {
        self.nested_fields.is_empty()
    }

    /// A [NestedSchema] is truely nested if it has at least one nested field.
    #[inline]
    pub fn is_nested(&self) -> bool {
        !self.is_flat()
    }

    /// A [NestedSchema] is singular if it is empty or if it has only nested fields, all of which are singular.
    #[inline]
    pub fn is_singular(&self) -> bool {
        self.regular_fields.fields().is_empty()
            && self.nested_fields.iter().all(|f| f.is_singular())
    }

    /// A [NestedSchema] is empty if it has no regular fields and no nested fields.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.regular_fields.fields().is_empty() && self.nested_fields.is_empty()
    }

    /// Create the emtpy nested schema.
    #[inline]
    pub fn empty() -> Self {
        let regular_fields: Vec<Field> = vec![];
        let regular_fields = Arc::new(Schema::new(regular_fields));
        let nested_fields = Vec::new();
        Self {
            regular_fields,
            nested_fields,
        }
    }

    /// Create a new [NestedSchema] that results from grouping on `group_on` and nesting the columns in `nest_on`.
    /// group_on and nest_on must be a partition of regular_fields.len()
    #[inline]
    pub fn group_by(&self, group_on: &[usize], nest_on: &[usize]) -> Self {
        let new_regular_fields = Arc::new(self.regular_fields.project(group_on).unwrap());
        // the regular fields that will now be nested
        let nested_regular_fields = Arc::new(self.regular_fields.project(nest_on).unwrap());
        let inner_nested_schema =
            NestedSchema::new(nested_regular_fields, self.nested_fields.clone());

        Self {
            regular_fields: new_regular_fields,
            nested_fields: vec![Arc::new(inner_nested_schema)],
        }
    }

    /// Create a new [NestedSchema] that results from taking the semijoin of a relation with `guard_schema` and multiple relations with `semijoin_rhs_schemas`.
    pub fn semijoin<'a>(
        guard_schema: &SchemaRef,
        semijoin_rhs_schemas: &[&NestedSchemaRef],
    ) -> Self {
        let regular_fields = guard_schema.clone();

        semijoin_rhs_schemas.iter().for_each(|s| {
            assert!(s.is_grouped());
        });

        let nested_fields = semijoin_rhs_schemas
            .iter()
            // nested_fields[0] is guaranteed to exist, as the reguls of a [GroupBy] always has a grouped schema
            .map(|c| c.nested_fields[0].clone())
            .collect();

        Self {
            regular_fields,
            nested_fields,
        }
    }

    /// Create a new [Schema] that results from recursively flattening all the nested fields.
    pub fn flatten(&self) -> Schema {
        fn flatten_recursive(schema: &NestedSchema, fields: &mut Vec<FieldRef>) {
            fields.extend(schema.regular_fields.fields().iter().cloned());
            schema
                .nested_fields
                .iter()
                .for_each(|f| flatten_recursive(f, fields));
        }

        let mut fields = Vec::new();
        flatten_recursive(self, &mut fields);
        Schema::new(fields)
    }
}

pub type Idx = u32; // native type
pub type Weight = u32; // native type

pub const IDX_TYPE: DataType = DataType::UInt32; // arrow datatype variant
pub const WEIGHT_TYPE: DataType = DataType::UInt32; // arrow datatype variant

/// A [NestedColumn] is the way that the values of a nested field are represented inside of a NestedSchema.
/// A [NestedBatch] is the way that we store a batch of records that have at least one nested column,
/// and which itself does not occur in an outer nested column
///
/// To illustrate, say that we have a nested schema (A, B, N) where N is a nested field, N = { (C, D) }.
/// Consider the following logical instance R of this schema:
///
/// =================
/// | A | B | { C , D } |
/// | a1| b1| ========  |
/// |   |   | |c1 | d1| |
/// |   |   | |c2 | d2| |
/// |   |   | ========  |
/// |   |   |           |
/// | a2| b2| ========  |
/// |   |   | |c3 | d1| |
/// |   |   | ========  |
/// |   |   |           |
/// | a3| b3| ========  |
/// |   |   | |c1 | d1| |
/// |   |   | |c2 | d2| |
/// |   |   | ========  |
/// | ...               |
/// ---------------------
///
/// We will represent this instance as a [NestedBatch] where we represent the nested field { (C, D) } as a
/// [NestedColumn] which is a struct that consists of three parts:
/// - a [NestedRel] object that contains the actual data in the nested field.
/// - a Vec<Idx> that refers, for each tupel in R, to the *non-empty* nested set encoded in the associated [NestedRel].
///   This vector is called the HOL vector of the nested column { (C, D) }.
/// - A Vec<Weight> that gives the total number of tuples that will be produced when completely unnesting the current multiset element of the nested column.
///
/// Hence, we conceptually store relation R as
/// -----------------
/// | A | B | CD_HOL | CD_WEIGHT |
/// | a1| b1| 1      | 2         |
/// | a2| b2| 2      | 1         |
/// | a3| b3| 1      | 2         |
/// ...
/// -----------------
///
/// Where the [NestedRel] of { (C,D) } is
/// -----------------
/// | next | C | D |
/// | 0    | c2| d2|
/// | 1    | c1| d1|
/// | 0    | c3| d1|
/// ----------------
///
/// (Note that wile CD_HOL and CD_WEIGHT is displayed as a vector belonging to R, it is stored inside the NestedColumn data structure, togeteher with the [NestedRel])
///
/// The `next` column in the [NestedRel] encodes a linked list, chaining all the records in the store that pertain to the same set (i.e., tuple) in the nested column N.
/// The CD_HOL values indicate the first tuple in this linked list.
/// For example, for tuple (a1,b1) the HOL is 1, which refers to (c1,d1) in the [NestedColumnStore], whose next element is 1,
/// referring to (c2,d2), which has no next element (0 = end of list). In other words, HOL=1 refers to the set {(c1,d1), (c2,d2)}.
///
/// A number of comments are important to make at this point:
///
/// 1) A [NestedBatch] may have more than one nested column.
///    In that case there will be multipe a [NestedColumn] objects , one for each nested field. The total weight of the a tuple in the [NestedBatch] (i.e., the total
///    number of tuples produced when completely unnesting) is then obtained by taking the product of the weights of the nested columns.
///
/// 2)
/// Note that a NestedColumn may (recursively) itself have nested fields. For example, assume that our nested field N = { (C, D, { (E) }) }. In that case
/// the [NestedRel] of N will itself behave as a [NestedBatch], and have itself a [NestedRel] object for the inner nested field { (E) }, giving the layout
/// -----------------
/// | next | C | D | E_WEIGHT | E_HOL |
/// | 0    | c2| d2| 1        | 3     |
/// | 1    | c1| d1| 1        | 2     |
/// | 0    | c3| d1| 1        | 1     |
/// ----------------
///
/// where the [NestedRel] of { (E) } will be
/// -------------
/// | next | E |
/// |  ....    |
/// ------------
///
/// 3) A [NestedColumn] may be singular. As explained in the module-level documentation, we optimize the storage of singular nested columns.
///    In particular, the data layout explained above pertains to Non-Singular Nested Columns. For singular nested columns there is only a weight vector,
///    no list of HOL vectors in the NestedBatch, and there is no NestedRel object.
///

/// A [NestedColumn] encodes a multiset of { x1, ..., xn }  where each xi is an instance (i.e. a multiset of tuples) over a [NestedSchema].
/// A [NestedColumn] is  is either singular or non-singular. It is singular if it's schema is singular.
/// We optimize the storage of singular nested columns: they do not occupy any space beyond stating the total number of tuples produced when completely unnesting.
/// (See module-level discussion)
#[derive(Clone)]
pub enum NestedColumn {
    Singular(SingularNestedColumn),
    NonSingular(NonSingularNestedColumn),
}

impl NestedColumn {
    /// The number of rows in the nested column (where each row is itself a multiset).
    #[inline]
    pub fn num_rows(&self) -> usize {
        match self {
            NestedColumn::Singular(s) => s.num_rows(),
            NestedColumn::NonSingular(n) => n.num_rows(),
        }
    }

    /// converts the [NestedColumn] to a [SingularNestedColumn]
    /// Panics if the [NestedColumn] is not singular.
    #[inline]
    pub fn as_singular(&self) -> &SingularNestedColumn {
        match self {
            NestedColumn::Singular(s) => s,
            _ => panic!("Expected a singular nested column"),
        }
    }

    /// converts the [NestedColumn] to a [NonSingularNestedColumn]
    /// Panics if the [NestedColumn] is singular.
    #[inline]
    pub fn as_non_singular(&self) -> &NonSingularNestedColumn {
        match self {
            NestedColumn::NonSingular(n) => n,
            _ => panic!("Expected a non-singular nested column"),
        }
    }

    /// returns a reference to the weights vector
    #[inline]
    pub fn weights(&self) -> &[Weight] {
        match self {
            NestedColumn::Singular(s) => &s.weights,
            NestedColumn::NonSingular(n) => &n.weights,
        }
    }
}

/// A singular nested column
#[derive(Clone, Default)]
pub struct SingularNestedColumn {
    /// The weight of each tuple in the nested column.
    pub weights: Vec<Weight>,
}

impl SingularNestedColumn {
    /// Creates a new Empty SingularNestedColumn
    pub fn empty() -> Self {
        Self {
            weights: Vec::new(),
        }
    }

    /// The number of rows in the nested column (where each row is itself a multiset).
    #[inline]
    pub fn num_rows(&self) -> usize {
        self.weights.len()
    }

    /// returns a reference to the weights vector
    #[inline]
    pub fn weights(&self) -> &[Weight] {
        &self.weights
    }
}

/// A [NonSingularNestedColumn] is non-singular Nested Column occurring as a nested field in an instance of some [NestedSchema].
//TODO: the clone should only be there in test mode, we should remove it in production.
#[derive(Clone)]
pub struct NonSingularNestedColumn {
    /// Head-Of-List indexes,  one for each tuple in the nested column, identifying the nested multisets in these tuples.
    /// Paired with the weights of the elements in the nested column.
    pub hols: Vec<Idx>,

    /// The weights vector, indicating for each element in the nested column the total number of tuples produced when completely unnesting.
    /// is of the same length as `hols`.
    pub weights: Vec<Weight>,

    /// The actual content of the nested column
    pub data: Arc<NestedRel>,
}

impl Default for NonSingularNestedColumn {
    fn default() -> Self {
        Self {
            hols: Vec::new(),
            weights: Vec::new(),
            data: Arc::new(NestedRel::empty_old(Arc::new(NestedSchema::empty()))),
        }
    }
}

impl NonSingularNestedColumn {
    pub fn empty_old(schema: NestedSchemaRef) -> Self {
        Self {
            hols: Vec::new(),
            weights: Vec::new(),
            data: Arc::new(NestedRel::empty_old(schema)),
        }
    }

    /// Creates a new Empty NonSingularNestedColumn with the given schema and with next vector of the inner data set to `Some(vec![])`
    pub fn empty_with_next(schema: NestedSchemaRef) -> Self {
        Self {
            hols: Vec::new(),
            weights: Vec::new(),
            data: Arc::new(NestedRel::empty_with_next(schema)),
        }
    }

    /// The number of rows in the nested column (where each element is itself a multiset).
    #[inline]
    pub fn num_rows(&self) -> usize {
        self.weights.len()
    }

    /// returns a reference to the weights vector
    #[inline]
    pub fn weights(&self) -> &[Weight] {
        &self.weights
    }

    /// returns a reference to the hols vector
    #[inline]
    pub fn hols(&self) -> &[Idx] {
        &self.hols
    }

    /// returns the regular column at index `i`
    #[inline]
    pub fn regular_column(&self, i: usize) -> &ArrayRef {
        self.data.regular_column(i)
    }

    /// Returns an iterator that iterates over the linked list starting at `hol_ptr`.
    /// The iterator yields row id's that can be used to index into the regular columns of this NestedRel.
    ///
    /// # Panics
    /// Panics if `hol_ptr` is not a valid.
    #[inline]
    pub fn iterate_linked_list(&self, hol_ptr: Idx) -> impl Iterator<Item = Idx> + '_ {
        self.data.iterate_linked_list(hol_ptr)
    }
}

/// The total weights of tuples in a [NestedRel].
pub enum TotalWeights<'a> {
    /// All tuples have weight 1.
    /// This is the case when there are no nested columns.
    Ones,
    /// The [NestedRel] has only one nested column.
    /// The total weights are the weights of that nested column.
    SingleNestedColumn(&'a [Weight]),
    /// The [NestedRel] has at least two nested columns.
    /// The total weights are the product of the weights of the nested columns (element-wise).
    MultipleNestedColumns(&'a [Weight]),
}

impl TotalWeights<'_> {
    /// Returns the total weights as a slice.
    ///
    /// # Panics
    /// Panics if `self` is of variant [TotalWeights::Ones] (meaning that all weights = 1), because then the total weights are not stored in a vector.
    /// This is the case when the [NestedRel] has no nested columns anymore.
    pub fn as_slice(&self) -> &[Weight] {
        match self {
            TotalWeights::Ones => {
                panic!("Total weights are not stored in a vector because all weights are 1")
            }
            TotalWeights::SingleNestedColumn(weights) => weights,
            TotalWeights::MultipleNestedColumns(weights) => weights,
        }
    }
}

//TODO: remove clone (only for testing purposes)
#[derive(Clone)]
pub struct NestedRel {
    /// The schema of the nested column. This is guaranteed non-singular.
    pub schema: NestedSchemaRef,

    /// A vector that encodes a linked list, chaining the row_id's of values in `regular_cols` and `nested_cols` that belong to the same tuple in the nested column.
    /// This vector is of the same length as each array in `regular_cols` and each array in `nested_cols` if present.
    /// This vector is absent if the NestedRel is a top-level relation, i.e., if it does not occur as a nested field in another NestedRel.
    pub next: Option<Vec<Idx>>,

    /// We have one array for each regular, non_nested field in `schema`
    /// Each of these arrays is of the same length a `next`
    pub regular_cols: Vec<ArrayRef>,

    /// Our NestedColumn may itself recursively have nested columns in `schema.nested_fields`
    /// Each of these nestedcolumns has the same length as `next`
    pub nested_cols: Vec<NestedColumn>,

    /// The total weights of the tuples in the nested column.
    /// Only stored when there are >= 2 nested columns (to avoid recomputation).
    total_weights: Option<Vec<Weight>>,
}

impl NestedRel {
    /// Old implementation of creating an empty [NestedRel] with the given schema.
    /// Next is set to None, meaning that the NestedRel is a top-level relation.
    #[inline]
    pub fn empty_old(schema: Arc<NestedSchema>) -> Self {
        Self {
            schema,
            next: None,
            regular_cols: Vec::new(), // FIXME: number of regular cols should be equal to the number of regular fields in the schema
            nested_cols: Vec::new(), // FIXME: number of nested cols should be equal to the number of nested fields in the schema
            total_weights: None,
        }
    }

    /// Create a new empty [NestedRel] with the given schema, with `next` set to `Some(vec![])`, meaning that the NestedRel is NOT a top-level relation.
    #[inline]
    pub fn empty_with_next(schema: Arc<NestedSchema>) -> Self {
        let mut result = Self::empty_no_next(schema);
        result.next = Some(vec![]);
        result
    }

    /// Create a new empty [NestedRel] with the given schema, with `next` set to `None`, meaning that the NestedRel is a top-level relation.
    /// In contrast, the recursively nested columns will have a next vector (Some(vec![])).
    #[inline]
    pub fn empty_no_next(schema: Arc<NestedSchema>) -> Self {
        let regular_cols = schema
            .regular_fields
            .fields()
            .iter()
            .map(|f| datafusion::arrow::array::new_empty_array(f.data_type()))
            .collect::<Vec<_>>();

        let nested_cols = schema
            .nested_fields
            .iter()
            .map(|f| {
                if f.is_singular() {
                    NestedColumn::Singular(SingularNestedColumn::empty())
                } else {
                    NestedColumn::NonSingular(NonSingularNestedColumn::empty_with_next(f.clone()))
                }
            })
            .collect::<Vec<_>>();

        let total_weights = Self::compute_total_weights(&nested_cols);

        Self {
            schema,
            next: None,
            regular_cols,
            nested_cols,
            total_weights,
        }
    }

    /// Create a new [NestedRel] with the given schema and columns
    /// Implementation note: at current no validation is being done that the schema corresponds to the columns,
    /// nor that each column is of the same length
    #[inline]
    pub fn new(
        schema: Arc<NestedSchema>,
        next: Option<Vec<Idx>>,
        regular_cols: Vec<ArrayRef>,
        nested_cols: Vec<NestedColumn>,
    ) -> Self {
        let total_weights = Self::compute_total_weights(&nested_cols);
        Self {
            schema,
            next,
            regular_cols,
            nested_cols,
            total_weights,
        }
    }

    /// Create a new [NestedRel] with the given schema and columns, and with `next` set to None
    /// The nestedrel is hence a top-level relation, i.e., it does not occur as a nested field in another NestedRel.
    /// Implementation note: at current no validation is being done that the schema corresponds to the columns,
    /// nor that each column is of the same length
    #[inline]
    pub fn new_no_next(
        schema: Arc<NestedSchema>,
        regular_cols: Vec<ArrayRef>,
        nested_cols: Vec<NestedColumn>,
    ) -> Self {
        let total_weights = Self::compute_total_weights(&nested_cols);
        Self {
            schema,
            next: None,
            regular_cols,
            nested_cols,
            total_weights,
        }
    }

    /// Returns a reference to the NestedSchema of the NestedRel
    #[inline]
    pub fn schema(&self) -> &NestedSchemaRef {
        &self.schema
    }

    /// Retrieves the i-th regular column of the relation
    #[inline]
    pub fn regular_column(&self, i: usize) -> &ArrayRef {
        &self.regular_cols[i]
    }

    /// Retrieves the i-th nested column of the relation
    #[inline]
    pub fn nested_column(&self, i: usize) -> &NestedColumn {
        &self.nested_cols[i]
    }

    /// Returns an iterator that iterates over the linked list starting at `hol_ptr`.
    /// The iterator yields row id's that can be used to index into the regular columns of this [NestedRel].
    ///
    /// # Panics
    /// Panics if `hol_ptr` is not a valid or if there is no next vector (i.e., the NestedRel is a top-level relation).
    #[inline]
    pub fn iterate_linked_list(&self, hol_ptr: Idx) -> impl Iterator<Item = Idx> + '_ {
        let next = self
            .next
            .as_ref()
            .expect("Unable to iterate through linked list: next vector is None");

        std::iter::successors(Some(hol_ptr), move |&ptr| {
            if ptr == 0 {
                None
            } else {
                Some(next[(ptr - 1) as usize]) // -1 because pointer is the actual position + 1 (0 is reserved for EOL)
            }
        })
        .filter(|ptr| *ptr != 0) // skip final ptr (0 = EOL)
        .map(|ptr| ptr - 1) // map pointers to positions
    }

    /// Compute the total weights of the tuples in the nested column
    /// if there are at least two nested columns.
    /// Returns None if there is max. 1 nested column.
    #[inline]
    fn compute_total_weights(nested_cols: &Vec<NestedColumn>) -> Option<Vec<Weight>> {
        if nested_cols.len() <= 1 {
            None
        } else {
            Some(super::kernel::multiply_weights(
                nested_cols.iter().map(|c| c.weights()),
            ))
        }
    }

    /// Get the total weights of tuples in the nested column.
    #[inline]
    pub fn total_weights(&self) -> TotalWeights {
        match (&self.total_weights, self.nested_cols.len()) {
            (Some(weights), _) => TotalWeights::MultipleNestedColumns(weights.as_slice()),
            (None, 0) => TotalWeights::Ones,
            (None, 1) => TotalWeights::SingleNestedColumn(self.nested_cols[0].weights()),
            _ => unreachable!(),
        }
    }

    /// Returns true if all regular fields are primitive.
    #[inline]
    pub fn regular_fields_all_primitive(&self) -> bool {
        self.schema
            .regular_fields
            .fields()
            .iter()
            .all(|f| f.data_type().is_primitive())
    }
}

pub type NestedRelRef = Arc<NestedRel>;

/// A [NestedBatch] is a batch of records that have at *least one nested column* (possibly singular).
//TODO: the clone should only be there in test mode. We should remove it in production.
#[derive(Clone)]
pub struct NestedBatch {
    /// The [NestedSchema] of the nested batch.
    pub inner: NestedRel,
}

impl NestedBatch {
    /// Create a new [NestedBatch] with the given schema.
    /// The schema is guaranteed to be truely nested
    #[inline]
    pub fn new(
        schema: Arc<NestedSchema>,
        regular_cols: Vec<ArrayRef>,
        nested_cols: Vec<NestedColumn>,
    ) -> Self {
        assert!(schema.is_nested());
        let inner = NestedRel::new_no_next(schema, regular_cols, nested_cols);
        Self { inner }
    }

    /// Create a new [NestedBatch] with the given schema.
    /// The schema is guaranteed to be truely nested
    #[inline]
    pub fn empty(schema: Arc<NestedSchema>) -> Self {
        assert!(schema.is_nested());
        let inner = NestedRel::empty_no_next(schema);
        Self { inner }
    }

    /// This batch' NestedSchema. Guaranteed to be truely nested.
    #[inline]
    pub fn schema(&self) -> &NestedSchemaRef {
        self.inner.schema()
    }

    /// Retrieves the i-th regular column of the relation
    #[inline]
    pub fn regular_column(&self, i: usize) -> &ArrayRef {
        self.inner.regular_column(i)
    }

    /// Retrieves the i-th nested column of the relation
    #[inline]
    pub fn nested_column(&self, i: usize) -> &NestedColumn {
        self.inner.nested_column(i)
    }

    /// The number of rows in the nested batch
    #[inline]
    pub fn num_rows(&self) -> usize {
        // We have at least one nested column
        self.inner.nested_cols[0].num_rows()
    }

    // /// The total weights of the rows in the nested batch
    // /// For each row i, the total weight of i is the product of the weights of the nested columns.
    // pub fn total_weights_buffered<'a, 'b, 'c>(&'a self, buffer: &'b mut Vec<Weight>) -> &'c [Weight]
    // where
    //     'a: 'c,
    //     'b: 'c,
    // {
    //     // Ensure that the buffer is of the correct size
    //     buffer.resize(self.num_rows(), 0);
    //     super::kernel::multiply_weights_buffered(
    //         self.inner.nested_cols.iter().map(|c| c.weights()),
    //         buffer,
    //     )
    // }

    // /// The total weights of the rows in the nested batch
    // /// Returned as a freshly-allocated vector
    // /// For each row i, the total weight of i is the product of the weights of the nested columns.
    // pub fn total_weights(&self) -> Vec<Weight> {
    //     super::kernel::multiply_weights(self.inner.nested_cols.iter().map(|c| c.weights()))
    // }

    /// The total weights of the rows in the nested batch.
    /// For each row i, the total weight of i is the product of the weights of the nested columns.
    pub fn total_weights(&self) -> &[Weight] {
        match self.inner.total_weights() {
            TotalWeights::Ones => panic!("A nested batch always has >= 1 nested column"),
            TotalWeights::SingleNestedColumn(weights) => weights,
            TotalWeights::MultipleNestedColumns(weights) => weights,
        }
    }
}
/// Convert NestedBatch to a NestedRel
impl From<NestedBatch> for NestedRel {
    fn from(value: NestedBatch) -> Self {
        value.inner
    }
}

/// Represents a Grouped Relation.
/// A [GroupedRel] is the result of a [GroupBy] operator.
/// Logically, it is very similar to a [NestedBatch], but with two important differences:
/// (1) The schema of the [GroupedRel] is always grouped, i.e., it has exactly one nested field. By contrast, a [NestedBatch] may have n >= 1 nested fields.
/// (2) Given a tuple of the regular columns, the [GroupedRel] can efficiently lookup the corresponding tuple consisting of the nested columns in the relation.
/// There are various specialized implementations of [GroupedRel], depending on the exact nature of the non-nested fields and nested field (singular or not).
pub trait GroupedRel: Send + Sync {
    /// Returns a reference to the [NestedSchema] of the [GroupedRel].
    /// This schema is always grouped, i.e., schema.is_grouped() == true.
    fn schema(&self) -> &NestedSchemaRef;

    /// Given a slice `&[ArrayRef]` of N arrays that represent a (multi)set of N-ary keys (i.e., corresponding to the regular columns in `self.schema()`)
    /// searches for the keys contained in [GroupedRel] and returns
    /// - a `sel` selection vector that contains the row numbers of the keys found in the grouped relation.
    /// - a [NestedColumn] is returned that contains the selection of rows in `sel` in the [NestedColumn] in the grouped relation.
    ///
    /// `row_count` is the length of each array in `keys`, i.e, the number of rows in the probe batch.
    fn lookup(
        &self,
        keys: &[ArrayRef],
        hashes_buffer: &mut Vec<u64>,
        row_count: usize,
    ) -> (Sel, NestedColumn);

    /// A variant of `lookup` to be used when semijoining 2 or more relations.
    /// Given a slice `&[ArrayRef]` of N arrays that represent a (multi)set of N-ary keys (i.e., corresponding to the regular columns in `self.schema()`)
    /// searches for the keys contained in [GroupedRel] *but only for those row numbers contained in `sel`*.
    ///
    /// `row_count` is the length of each array in `keys`.
    ///
    /// In the lookup process, it updates `sel` to contain only the subset of input row numbers that were found in the grouped relation.
    ///
    /// The returned NestedColumn has as many rows as keys.len() but only those in `sel` will be valid in the sense that row_ids not in `sel`
    /// contain an empty set.
    /// The caller is responsible for doing a take_nested_column operation on the returned NestedColumn by (a subset) of `sel` to get the actual result.
    fn lookup_sel(
        &self,
        keys: &[ArrayRef],
        sel: &mut Sel,
        hashes_buffer: &mut Vec<u64>,
        row_count: usize,
    ) -> NestedColumn;

    fn as_any(&self) -> &dyn Any;

    /// Returns the number of rows in the [GroupedRel].
    fn is_empty(&self) -> bool;
}

pub type GroupedRelRef = Arc<dyn GroupedRel>;

/// A [SemiJoinResultBatch] is the result of a semijoin operation.
#[derive(Clone)]
pub enum SemiJoinResultBatch {
    /// A flat batch.
    ///
    /// A semijoinresult batch is flat if no actual semijoin was performed: the
    /// guard batch is returned as is. Every record has weight 1 by definition, and there
    /// there are no nested columns.
    Flat(RecordBatch),

    /// A nested batch
    Nested(NestedBatch),
}

impl SemiJoinResultBatch {
    /// Returns the number records that pass the semijoin
    #[inline]
    pub fn num_rows(&self) -> usize {
        match self {
            SemiJoinResultBatch::Flat(batch) => batch.num_rows(),
            SemiJoinResultBatch::Nested(nested) => nested.num_rows(),
        }
    }
}

#[cfg(test)]
pub mod test {
    use super::*;

    use datafusion::arrow::datatypes::DataType;

    #[test]
    fn test_nested_schema() {
        let schema = Arc::new(NestedSchema {
            regular_fields: Arc::new(Schema::new(vec![Field::new("A", DataType::Int32, false)])),
            nested_fields: vec![],
        });

        assert!(schema.is_flat());
        assert!(!schema.is_grouped());
        assert!(!schema.is_nested());
        assert!(!schema.is_singular());
        assert!(!schema.is_empty());

        let schema = Arc::new(NestedSchema {
            regular_fields: Arc::new(Schema::new(vec![Field::new("A", DataType::Int32, false)])),
            nested_fields: vec![schema],
        });

        assert!(!schema.is_flat());
        assert!(schema.is_grouped());
        assert!(schema.is_nested());
        assert!(!schema.is_singular());
        assert!(!schema.is_empty());
    }

    #[test]
    fn test_nested_column() {
        let singular = SingularNestedColumn {
            weights: vec![1, 2, 3],
        };
        let non_singular = NonSingularNestedColumn {
            hols: vec![1, 2, 3],
            weights: vec![1, 2, 3],
            data: Arc::new(NestedRel::empty_no_next(Arc::new(NestedSchema {
                regular_fields: Arc::new(Schema::new(vec![Field::new(
                    "A",
                    DataType::Int32,
                    false,
                )])),
                nested_fields: vec![],
            }))),
        };

        let singular_column = NestedColumn::Singular(singular.clone());
        let non_singular_column = NestedColumn::NonSingular(non_singular.clone());

        assert_eq!(singular_column.num_rows(), 3);
        assert_eq!(non_singular_column.num_rows(), 3);

        //assert_eq!(singular_column.as_singular(), &singular);
        //assert_eq!(non_singular_column.as_non_singular(), &non_singular);

        assert_eq!(singular_column.weights(), vec![1, 2, 3].as_slice());
        assert_eq!(non_singular_column.weights(), vec![1, 2, 3].as_slice());
    }

    #[test]
    fn test_total_weights() {
        // Create three singular columns with four rows each, having weight 1,2,3,4 respectively.
        let cols = vec![
            SingularNestedColumn {
                weights: vec![1, 2, 3, 4],
            },
            SingularNestedColumn {
                weights: vec![1, 2, 3, 4],
            },
            SingularNestedColumn {
                weights: vec![1, 2, 3, 4],
            },
        ];

        // create a singular NestedBatch with the columns
        let inner_schema = NestedSchema::empty();

        let batch = NestedBatch::new(
            Arc::new(NestedSchema {
                regular_fields: Arc::new(Schema::empty()),
                nested_fields: vec![Arc::new(inner_schema)],
            }),
            vec![],
            cols.into_iter()
                .map(|c| NestedColumn::Singular(c))
                .collect(),
        );

        let total_weights = batch.total_weights();
        assert_eq!(total_weights, vec![1, 8, 27, 64].as_slice());
    }
}
