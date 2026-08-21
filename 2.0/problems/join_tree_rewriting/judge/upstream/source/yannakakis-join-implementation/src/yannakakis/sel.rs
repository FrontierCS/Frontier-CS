//! A selection vector: a sequence of monotonically increasing row_ids of a table, guaranteed to be between 0 and `max` - 1.

use super::data::Idx;

pub struct Sel {
    max: Idx,
    elems: Vec<Idx>,
}

impl Sel {
    /// Create a new selection vector out of the given elements.
    /// The elements must be strictly monotonically increasing.
    /// Caller is responsible for ensureing that elems is a sequence of strictly monotonically increasing numbers
    pub fn new_unchecked(elems: Vec<Idx>) -> Self {
        let max = elems.last().map_or(0, |&x| x + 1);
        Self { max, elems }
    }

    /// Create a new selection vector out of the given elements.
    /// Checks that they are strictly monotonically increasing
    pub fn new(elems: Vec<Idx>) -> Self {
        assert!(
            elems.windows(2).all(|w| w[0] < w[1]),
            "Selection vector must be strictly monotonically increasing"
        );
        Self::new_unchecked(elems)
    }

    /// Creates a new selection vector contain all elements between 0 and `max` - 1.
    pub fn all(max: Idx) -> Self {
        Sel {
            max,
            elems: (0..max).collect(),
        }
    }

    /// Returns the upper bound of the selection vector. All elements in the vector are strictly less than this value.
    /// We return it as a usize because that is what we typically need to index
    #[inline(always)]
    pub fn max(&self) -> usize {
        self.max as usize
    }

    /// Returns the elements in the selection vector.
    #[inline(always)]
    pub fn elems(&self) -> &[Idx] {
        &self.elems
    }

    /// The number of elements in the selection vector.
    #[inline(always)]
    pub fn len(&self) -> usize {
        self.elems.len()
    }

    /// Returns an iterator of usize elements in the selection vector.
    /// We convert to usize because that is what we typically need to index
    #[inline(always)]
    pub fn iter(&self) -> impl Iterator<Item = usize> + '_ {
        self.elems.iter().map(|x| *x as usize)
    }

    /// Refines the selection vector in-place to only contain the elements that pass a given predicate
    /// The predicate is given a pair (i, val) with i the index of the element in the selection vector and val the value of the element
    /// The selection vector remains valid: a sequence of strictly monotonically increasing row_ids strictly uppper bounded by `self.max`
    #[inline(always)]
    pub fn refine(&mut self, mut pred: impl FnMut(usize, usize) -> bool) {
        let mut head: usize = 0;
        // We cannot do iter_mut because we are modifying elems in place
        for i in 0..self.elems.len() {
            // SAFETY: i is always in bounds
            let row_idx = unsafe { *self.elems.get_unchecked(i) };
            if pred(i, row_idx as usize) {
                // SAFETY: head is at most self.elems.len()
                unsafe {
                    *self.elems.get_unchecked_mut(head) = row_idx;
                }
                head += 1;
            }
        }
        // Shorten the selection vector to contain only those elements that passed the filter
        self.elems.truncate(head);

        // TODO: is it useful to adjest the upper bound accordingly?
        //self.max = self.elems.last().map_or(0, |&x| x + 1);
    }

    /// Returns the inner vector of elements, consuming Self.
    #[inline(always)]
    pub fn into_vec(self) -> Vec<Idx> {
        self.elems
    }

    /// Clears the selection vector.
    #[inline(always)]
    pub fn clear(&mut self) {
        self.elems.clear();
        self.max = 0;
    }
}
