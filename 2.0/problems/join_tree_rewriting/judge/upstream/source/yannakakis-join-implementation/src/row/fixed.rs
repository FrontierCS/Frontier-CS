//! Encode() en decode() methods for fixed width types
//!
//! See https://arrow.apache.org/rust/arrow_row/fixed/index.html

use datafusion::arrow;
use arrow::datatypes::i256;
use half::f16;

/// Allows to create a value T::Encoded from a slice where T::FixedLenghtEncoding
/// needed for decoding.
pub trait FromSlice {
    fn from_slice(slice: &[u8]) -> Self;
}

impl<const N: usize> FromSlice for [u8; N] {
    #[inline]
    fn from_slice(slice: &[u8]) -> Self {
        slice.try_into().unwrap()
    }
}

pub trait FixedLengthEncoding: Copy {
    const ENCODED_LEN: usize = std::mem::size_of::<Self::Encoded>();

    type Encoded: Sized + Copy + FromSlice + AsRef<[u8]> + AsMut<[u8]>;

    fn encode(self) -> Self::Encoded;

    fn decode(encoded: Self::Encoded) -> Self;
}

impl FixedLengthEncoding for bool {
    type Encoded = [u8; 1];

    fn encode(self) -> [u8; 1] {
        [self as u8]
    }

    fn decode(encoded: Self::Encoded) -> Self {
        encoded[0] != 0
    }
}

////////////////////////////////////
// Encoding for unsigned integers //
////////////////////////////////////

macro_rules! encode_int {
    ($n:expr, $t:ty) => {
        impl FixedLengthEncoding for $t {
            type Encoded = [u8; $n];

            fn encode(self) -> [u8; $n] {
                self.to_ne_bytes()
            }

            fn decode(encoded: Self::Encoded) -> Self {
                Self::from_ne_bytes(encoded)
            }
        }
    };
}

encode_int!(1, u8);
encode_int!(2, u16);
encode_int!(4, u32);
encode_int!(8, u64);

//////////////////////////////////
// Encoding for signed integers //
//////////////////////////////////

encode_int!(1, i8);
encode_int!(2, i16);
encode_int!(4, i32);
encode_int!(8, i64);
encode_int!(16, i128);

// i256 does not have to/from_ne_bytes, so we use to/from_le_bytes instead
impl FixedLengthEncoding for i256 {
    type Encoded = [u8; 32];

    fn encode(self) -> [u8; 32] {
        self.to_le_bytes()
    }

    fn decode(encoded: Self::Encoded) -> Self {
        Self::from_le_bytes(encoded)
    }
}

//////////////////////////////////////
//      Encoding for floats         //
//////////////////////////////////////

// NOTE: macro for float is the same as for ints, but could become different in the future

macro_rules! encode_float {
    ($n:expr, $t:ty) => {
        impl FixedLengthEncoding for $t {
            type Encoded = [u8; $n];

            fn encode(self) -> [u8; $n] {
                self.to_ne_bytes()
            }

            fn decode(encoded: Self::Encoded) -> Self {
                Self::from_ne_bytes(encoded)
            }
        }
    };
}

encode_float!(2, f16);
encode_float!(4, f32);
encode_float!(8, f64);
