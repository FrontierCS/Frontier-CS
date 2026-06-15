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

    pub fn load(
        &self,
        _index_path: &str,
        vector_path: &str,
        vector_dtype: Option<&str>,
        _pq_compressed_path: Option<&str>,
        _pq_pivots_path: Option<&str>,
    ) {
        let bytes = std::fs::read(vector_path).expect("read vector file");
        let row_bytes = DIM * std::mem::size_of::<f32>();
        let dtype = VectorDtype::from_hint(vector_dtype);
        let header = if bytes.len() >= 8 {
            let rows = u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]) as usize;
            let dim = u32::from_le_bytes([bytes[4], bytes[5], bytes[6], bytes[7]]) as usize;
            Some((rows, dim))
        } else {
            None
        };

        let mut vectors = Vec::new();
        if let Some((rows, dim)) = header {
            if dim == DIM {
                let payload = &bytes[8..];
                match dtype {
                    Some(dtype) => {
                        let row_width = DIM * dtype.item_size();
                        assert!(
                            payload.len() == rows * row_width,
                            "vector file size does not match vector_dtype"
                        );
                        vectors.reserve(rows);
                        for (id, row) in payload.chunks_exact(row_width).enumerate() {
                            vectors.push((id as u64, decode_row(row, dtype)));
                        }
                    }
                    None => {
                        if payload.len() == rows * row_bytes {
                            vectors.reserve(rows);
                            for (id, row) in payload.chunks_exact(row_bytes).enumerate() {
                                vectors.push((id as u64, decode_f32_row(row)));
                            }
                        } else if payload.len() == rows * DIM {
                            panic!("vector_dtype must be uint8 or int8 for one-byte vector data");
                        }
                    }
                }
            }
        }

        if vectors.is_empty() {
            if let Some(dtype) = dtype {
                let row_width = DIM * dtype.item_size();
                assert!(
                    bytes.len() % row_width == 0,
                    "vector file size does not match vector_dtype"
                );
                vectors.reserve(bytes.len() / row_width);
                for (id, row) in bytes.chunks_exact(row_width).enumerate() {
                    vectors.push((id as u64, decode_row(row, dtype)));
                }
            } else {
                vectors.reserve(bytes.len() / row_bytes);
                for (id, row) in bytes.chunks_exact(row_bytes).enumerate() {
                    vectors.push((id as u64, decode_f32_row(row)));
                }
            }
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

#[derive(Clone, Copy)]
enum VectorDtype {
    Float32,
    Uint8,
    Int8,
}

impl VectorDtype {
    fn from_hint(hint: Option<&str>) -> Option<Self> {
        hint.map(|hint| match hint.to_ascii_lowercase().as_str() {
            "f32" | "float" | "float32" => Self::Float32,
            "u8" | "uint8" => Self::Uint8,
            "i8" | "int8" => Self::Int8,
            other => panic!("unsupported vector_dtype: {other}"),
        })
    }

    fn item_size(self) -> usize {
        match self {
            Self::Float32 => std::mem::size_of::<f32>(),
            Self::Uint8 | Self::Int8 => 1,
        }
    }
}

fn decode_row(row: &[u8], dtype: VectorDtype) -> Vec<f32> {
    match dtype {
        VectorDtype::Float32 => decode_f32_row(row),
        one_byte_dtype => decode_one_byte_row(row, one_byte_dtype),
    }
}

fn decode_one_byte_row(row: &[u8], dtype: VectorDtype) -> Vec<f32> {
    match dtype {
        VectorDtype::Int8 => row
            .iter()
            .map(|value| i8::from_ne_bytes([*value]) as f32)
            .collect(),
        _ => row.iter().map(|value| *value as f32).collect(),
    }
}

fn decode_f32_row(row: &[u8]) -> Vec<f32> {
    let mut vector = Vec::with_capacity(DIM);
    for value in row.chunks_exact(4) {
        vector.push(f32::from_le_bytes([value[0], value[1], value[2], value[3]]));
    }
    vector
}
