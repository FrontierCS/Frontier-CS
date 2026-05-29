use crate::api::SearchResult;
use crate::distance::l2_distance;
use std::sync::RwLock;

pub struct VectorDB {
    vectors: RwLock<Vec<(u64, Vec<f32>)>>,
}

impl VectorDB {
    pub fn new() -> Self {
        Self {
            vectors: RwLock::new(Vec::new()),
        }
    }

    pub fn insert(&self, id: u64, vector: Vec<f32>) {
        self.vectors.write().unwrap().push((id, vector));
    }

    pub fn bulk_insert(&self, vectors: Vec<(u64, Vec<f32>)>) -> usize {
        let inserted = vectors.len();
        self.vectors.write().unwrap().extend(vectors);
        inserted
    }

    pub fn search(&self, vector: &[f32], top_k: u32) -> Vec<SearchResult> {
        let mut scored: Vec<SearchResult> = self
            .vectors
            .read()
            .unwrap()
            .iter()
            .map(|(id, candidate)| SearchResult {
                id: *id,
                distance: l2_distance(vector, candidate),
            })
            .collect();
        scored.sort_by(|a, b| a.distance.total_cmp(&b.distance));
        scored.truncate(top_k as usize);
        scored
    }
}
