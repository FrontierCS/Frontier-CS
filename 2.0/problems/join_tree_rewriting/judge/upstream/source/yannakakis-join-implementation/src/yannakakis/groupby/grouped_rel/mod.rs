//! specialized [GroupedRel] implementations for different kinds of keys, as well as their builders
pub mod default; // default implementation for multi-column keys or non-primitive keys
pub mod default_nullable; // default implementation for multi-column keys or non-primitive keys, support NULLS
pub mod none; // nullary-column keys
pub mod one; // single-columns primitive keys (non-nullable)
pub mod one_nullable; // single-columns primitive keys (nullable)
pub mod two; // two-columns primitive keys
