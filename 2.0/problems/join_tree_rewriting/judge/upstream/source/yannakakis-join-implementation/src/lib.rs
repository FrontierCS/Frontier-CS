// Allow only during development
#![allow(dead_code)]
#![allow(unreachable_code)]

pub mod display;
pub mod row;
pub mod sel;
pub mod take;
pub mod yannakakis;

#[global_allocator]
static ALLOC: snmalloc_rs::SnMalloc = snmalloc_rs::SnMalloc;

#[cfg(test)]
mod tests {
    // use super::*;
}
