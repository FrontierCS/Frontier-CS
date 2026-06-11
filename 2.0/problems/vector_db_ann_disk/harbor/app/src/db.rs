use crate::api::SearchResult;

pub struct VectorDB {
    // Implement your index here.
}

impl VectorDB {
    pub fn new() -> Self {
        todo!("initialize your vector database")
    }

    pub fn load(&self, graph_path: &str, vector_path: &str) {
        let _ = (graph_path, vector_path);
        todo!("load the disk graph and vector data")
    }

    pub fn search(&self, vector: &[f32], top_k: u32) -> Vec<SearchResult> {
        let _ = (vector, top_k);
        todo!("return approximate nearest neighbors")
    }
}
