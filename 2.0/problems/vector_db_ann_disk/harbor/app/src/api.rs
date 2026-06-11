use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
pub struct LoadRequest {
    pub graph_path: String,
    pub vector_path: String,
}

#[derive(Serialize)]
pub struct LoadResponse {
    pub status: String,
}

#[derive(Deserialize)]
pub struct SearchRequest {
    pub vector: Vec<f32>,
    pub top_k: u32,
}

#[derive(Serialize)]
pub struct SearchResult {
    pub id: u64,
    pub distance: f64,
}

#[derive(Serialize)]
pub struct SearchResponse {
    pub results: Vec<SearchResult>,
}
