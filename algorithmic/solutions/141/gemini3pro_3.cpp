#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

int N, K;

// Perform a query operation
bool query(int c) {
    cout << "? " << c << endl;
    char res;
    cin >> res;
    return res == 'Y';
}

// Output the answer
void answer(int d) {
    cout << "! " << d << endl;
    exit(0);
}

// Function to ensure the memory contains exactly the elements of the chunk.
// It performs exactly K queries using elements from the chunk cyclically.
void load_chunk(const vector<int>& chunk) {
    int m = chunk.size();
    if (m == 0) return;
    
    int count = 0;
    while (count < K) {
        for (int x : chunk) {
            query(x);
            count++;
            if (count == K) break;
        }
    }
}

// Filters 'target' against 'basis'. Returns elements of 'target' that are NOT present in 'basis'.
// 'basis' is known to contain distinct elements.
vector<int> filter(vector<int>& target, const vector<int>& basis) {
    if (target.empty() || basis.empty()) return target;
    
    vector<int> active_target = target;
    
    // Process basis in chunks of size K
    for (size_t i = 0; i < basis.size(); i += K) {
        if (active_target.empty()) break;
        
        vector<int> chunk;
        for (size_t j = i; j < min(basis.size(), i + K); ++j) {
            chunk.push_back(basis[j]);
        }
        
        vector<int> next_target;
        // Optimization: if chunk size is small, loading it repeatedly is cheap.
        // We must ensure that for EACH t in active_target, it is checked against the FULL chunk.
        // Since querying t modifies memory (pushes out one element), we technically need to reload
        // or maintain the chunk.
        // To be strictly correct and fit within standard complexity for this problem type,
        // we reload for each check if strictness is required, but that is O(N^2).
        // However, we can batch: load chunk, query 1 element.
        
        // Since K <= N <= 1024, and Ops limit 100,000. O(N^2) is risky (10^6).
        // We use the property that 'query' returns Y if element is in memory.
        // Strategy: load chunk, then check t.
        // Note: checking t1 removes 1 element of chunk. checking t2 removes another.
        // So we can only check a few targets before the chunk is significantly degraded.
        // BUT, we only have 100,000 ops.
        // Let's assume we need to reload for each target to be correct.
        
        for (int t : active_target) {
            load_chunk(chunk); 
            bool res = query(t);
            if (!res) {
                next_target.push_back(t);
            }
        }
        active_target = next_target;
    }
    
    return active_target;
}

// Recursive function to find distinct elements indices
vector<int> solve(vector<int> candidates) {
    if (candidates.size() <= 1) return candidates;
    
    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());
    
    vector<int> L = solve(left_part);
    vector<int> R = solve(right_part);
    
    // Merge: Filter R against L
    vector<int> R_filtered = filter(R, L);
    
    L.insert(L.end(), R_filtered.begin(), R_filtered.end());
    return L;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> K)) return 0;
    
    vector<int> initial_candidates(N);
    iota(initial_candidates.begin(), initial_candidates.end(), 1);
    
    vector<int> distinct_elements = solve(initial_candidates);
    
    answer(distinct_elements.size());
    
    return 0;
}