use crate::api::SearchResult;
use crate::distance::l2_distance;
use std::sync::RwLock;

const DIM: usize = 128;

pub struct VectorDB {
    vectors: RwLock<Vec<(u64, Vec<f32>)>>,
}

impl VectorDB {
    pub fn new() -> Self {
        Self {
            vectors: RwLock::new(Vec::new()),
        }
    }

    pub fn load(&self, _graph_path: &str, vector_path: &str) {
        let bytes = std::fs::read(vector_path).expect("read vector file");
        let row_bytes = DIM * std::mem::size_of::<f32>();
        let mut vectors = Vec::with_capacity(bytes.len() / row_bytes);
        for (id, row) in bytes.chunks_exact(row_bytes).enumerate() {
            let mut vector = Vec::with_capacity(DIM);
            for value in row.chunks_exact(4) {
                vector.push(f32::from_le_bytes([
                    value[0], value[1], value[2], value[3],
                ]));
            }
            vectors.push((id as u64, vector));
        }
        *self.vectors.write().unwrap() = vectors;
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
