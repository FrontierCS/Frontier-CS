#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>

using namespace std;

// Global variables for problem constraints
int N, K;
mt19937 rng(1337);

// Wrapper for query operation
bool query(int c) {
    cout << "? " << c << endl;
    char res;
    cin >> res;
    return res == 'Y';
}

// Wrapper for reset operation (not used in optimal strategy but provided)
void reset_mem() {
    cout << "R" << endl;
}

// Heuristic filter: queries all elements in 'indices'.
// Retains elements that return 'N' (not seen in last K).
// To ensure correctness (not dropping a distinct value due to matching garbage),
// we unconditionally keep the first K elements.
vector<int> filter_stream(vector<int>& indices) {
    if (indices.empty()) return {};
    if (indices.size() <= (size_t)K) return indices; 
    
    vector<int> kept;
    kept.reserve(indices.size());
    
    // Shuffle to randomize which duplicates are caught
    shuffle(indices.begin(), indices.end(), rng);
    
    int safe_count = 0;
    for (int x : indices) {
        bool res = query(x);
        // Always keep the first K elements as they act as the initial fill
        // and could have matched "garbage" from previous operations.
        if (safe_count < K) {
            kept.push_back(x);
            safe_count++;
        } else {
            // For subsequent elements, if they return 'N', they are locally distinct.
            // If 'Y', they match something in the last K queries (which are in 'kept').
            if (!res) {
                kept.push_back(x);
            }
        }
    }
    return kept;
}

// Merges two sets of indices A and B, where A and B are each internally distinct sets.
// Returns the union of distinct values.
vector<int> merge_sets(const vector<int>& A, const vector<int>& B) {
    if (A.empty()) return B;
    if (B.empty()) return A;
    
    vector<int> unique_B;
    
    // Strategy depends on K
    if (K == 1) {
        // With capacity 1, we can only compare 1 vs 1.
        // We must check each element of B against A.
        unique_B = B;
        vector<int> next_B;
        for (int b_idx : unique_B) {
            bool found = false;
            // Check b against all elements of A
            for (int a_idx : A) {
                query(a_idx);       // Load a
                if (query(b_idx)) { // Check b against a
                    found = true;
                    break;
                }
            }
            if (!found) {
                next_B.push_back(b_idx);
            }
        }
        unique_B = next_B;
    } else {
        // Block strategy allows checking multiple elements at once
        // We load a chunk of A, then query a chunk of B.
        // block_A_size + block_B_size <= K
        // Optimal split is K/2 each.
        int block_A_size = K / 2;
        int block_B_size = K - block_A_size;
        
        unique_B = B;
        
        // Iterate through A in chunks
        for (size_t i = 0; i < A.size(); i += block_A_size) {
            if (unique_B.empty()) break;
            
            // Construct current block of A
            vector<int> chunk_A;
            for (size_t k = 0; k < (size_t)block_A_size && i + k < A.size(); ++k) {
                chunk_A.push_back(A[i + k]);
            }
            
            vector<int> next_unique_B;
            // Iterate through current survivors of B in chunks
            for (size_t j = 0; j < unique_B.size(); j += block_B_size) {
                vector<int> chunk_B;
                for (size_t k = 0; k < (size_t)block_B_size && j + k < unique_B.size(); ++k) {
                    chunk_B.push_back(unique_B[j + k]);
                }
                
                // Load chunk_A into memory
                for (int x : chunk_A) query(x);
                
                // Query chunk_B
                // Elements returning 'Y' match something in chunk_A (or previous elements of chunk_B).
                // Since chunk_B is from a distinct set, they don't match previous chunk_B elements.
                // Thus 'Y' implies match in chunk_A.
                for (int x : chunk_B) {
                    if (!query(x)) {
                        next_unique_B.push_back(x);
                    }
                }
            }
            unique_B = next_unique_B;
        }
    }
    
    vector<int> result = A;
    result.insert(result.end(), unique_B.begin(), unique_B.end());
    return result;
}

// Recursive function to solve for a set of indices
vector<int> solve(vector<int> indices) {
    if (indices.empty()) return {};
    if (indices.size() == 1) return indices;
    
    // Apply filter to reduce size if there are many duplicates
    // This uses O(N) queries but can save O(N^2/K) work.
    if (indices.size() > (size_t)K) {
        indices = filter_stream(indices);
    }
    
    if (indices.size() <= 1) return indices;
    
    // Divide and Conquer
    int mid = indices.size() / 2;
    vector<int> left_part(indices.begin(), indices.begin() + mid);
    vector<int> right_part(indices.begin() + mid, indices.end());
    
    vector<int> res_left = solve(left_part);
    vector<int> res_right = solve(right_part);
    
    return merge_sets(res_left, res_right);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> K)) return 0;
    
    vector<int> indices(N);
    iota(indices.begin(), indices.end(), 1);
    
    // Initial shuffle
    shuffle(indices.begin(), indices.end(), rng);
    
    vector<int> distinct = solve(indices);
    
    cout << "! " << distinct.size() << endl;
    
    return 0;
}