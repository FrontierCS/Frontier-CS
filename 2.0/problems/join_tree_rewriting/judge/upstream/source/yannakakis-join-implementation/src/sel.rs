use std::ops::Range;

use crate::yannakakis::data::Idx as PTR;

///! Trait and implementations for representing a selection (=subset) of elements of an array.

/// Struct to represent a set of `usize` elements, all guaranteed to be between `min` and `max`.
/// The struct allows to retrieve the elements multiple times by returning an iterator over it.
pub trait Selection {
    /// Returns the minimum element index that can be returned by this selection
    fn min(&self) -> PTR;

    /// Returns the maximum element index that can be returned by this selection
    fn max(&self) -> PTR;

    /// Returns an interator over the elements of this selection
    fn iter(&self) -> Box<dyn ExactSizeIterator<Item = PTR> + '_>;

    /// Returns the number of elements in this selection
    #[inline]
    fn len(&self) -> usize {
        self.iter().len()
    }
}

/// We implement Selection for Range<usize> to allow for easy creation of selections
impl Selection for Range<usize> {
    #[inline]
    fn min(&self) -> PTR {
        self.start as PTR
    }

    #[inline]
    fn max(&self) -> PTR {
        self.end as PTR
    }

    #[inline]
    fn iter(&self) -> Box<dyn ExactSizeIterator<Item = PTR> + '_> {
        Box::new(self.min()..self.max()).into_iter()
    }
}

/// Struct to represent a selection of elements of an Arrow Array
#[derive(Debug)]
pub struct ArraySelection {
    /// Some(Vec<usize>) is used to represent a selection of elements,
    /// None is used to represent the full array (i.e., no selection).
    /// This way, we can represent the full array without allocating a Vec
    elems: Option<Vec<PTR>>,
    min: PTR,
    max: PTR,
}

impl Selection for ArraySelection {
    #[inline]
    fn min(&self) -> PTR {
        self.min
    }

    #[inline]
    fn max(&self) -> PTR {
        self.max
    }

    #[inline]
    fn iter(&self) -> Box<dyn ExactSizeIterator<Item = PTR> + '_> {
        match &self.elems {
            Some(elems) => Box::new(elems.iter().cloned()),
            None => Box::new((self.min..self.max).into_iter()),
        }
    }
}

/// Implements Selection for &S if S implements Selection
impl<S: Selection> Selection for &S {
    #[inline]
    fn min(&self) -> PTR {
        (*self).min()
    }

    #[inline]
    fn max(&self) -> PTR {
        (*self).max()
    }

    #[inline]
    fn iter(&self) -> Box<dyn ExactSizeIterator<Item = PTR> + '_> {
        (*self).iter()
    }
}

impl ArraySelection {
    /// Create a new ArraySelection
    #[inline]
    pub fn new<P>(min: PTR, max: PTR, predicate: P) -> Self
    where
        P: FnMut(&PTR) -> bool,
    {
        let elems: Vec<PTR> = (min..max).into_iter().filter(predicate).collect();
        Self {
            min,
            max,
            elems: Some(elems),
        }
    }

    /// Create new ArraySelection from a Vec<usize>
    #[inline]
    pub fn from_vec(min: PTR, max: PTR, elems: Vec<PTR>) -> Self {
        Self {
            min,
            max,
            elems: Some(elems),
        }
    }

    /// Create a new ArraySelection that represents the full array (i.e., no selection)
    #[inline]
    pub fn full_array(min: PTR, max: PTR) -> Self {
        Self {
            min,
            max,
            elems: None,
        }
    }
}
