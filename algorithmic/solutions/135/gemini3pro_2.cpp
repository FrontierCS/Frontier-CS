#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Struct to hold query result
struct QueryResult {
    int r;
    vector<pair<int, int>> pairs;
};

// Function to perform query
// Returns the pairs with minimal distance among {x, y}, {y, z}, {z, x}
QueryResult ask(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    vector<pair<int, int>> pairs(r);
    for (int i = 0; i < r; ++i) {
        cin >> pairs[i].first >> pairs[i].second;
        // Ensure pairs are stored with smaller index first for consistency
        if (pairs[i].first > pairs[i].second) swap(pairs[i].first, pairs[i].second);
    }
    return {r, pairs};
}

// Check if a specific pair exists in the query result
bool contains_pair(const QueryResult& res, int u, int v) {
    if (u > v) swap(u, v);
    for (const auto& p : res.pairs) {
        if (p.first == u && p.second == v) return true;
    }
    return false;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int K, N;
    if (!(cin >> K >> N)) return 0;

    // We maintain a chain of doors representing the current cyclic order found.
    // Start with a small random subset. Since input labels 0..N-1 correspond to 
    // a random permutation of positions, using 0..m-1 is equivalent to a random subset.
    // We use a small initial size to establish a coarse cycle, then use binary search.
    // m=6 is sufficient to ensure gaps are small enough (< N/2) with high probability.
    int m = 6; 
    vector<int> chain;
    
    // Initialize with first 2 doors
    chain.push_back(0);
    if (N > 1) chain.push_back(1);

    // Incrementally build the initial small cycle by checking all edges
    // This takes O(m^2) queries.
    for (int i = 2; i < m && i < N; ++i) {
        bool inserted = false;
        // Try to insert door 'i' into existing edges of the cycle
        for (int j = 0; j < chain.size(); ++j) {
            int u = chain[j];
            int v = chain[(j + 1) % chain.size()]; // Wrap around for cycle
            
            // Query the triangle u, i, v.
            // If u and v are neighbors in the cycle, the arc u-v should be the shortest path.
            // If inserting i between them makes u-i or i-v shorter, or simply if i lies on the arc u-v,
            // then the distance d(u, v) will likely not be the unique minimum or minimum at all 
            // compared to d(u, i) and d(i, v).
            // Specifically, if {u, v} is NOT in the closest pairs returned, it strongly suggests 
            // i is 'between' u and v on the short arc.
            QueryResult res = ask(u, i, v);
            
            if (!contains_pair(res, u, v)) {
                chain.insert(chain.begin() + j + 1, i);
                inserted = true;
                break;
            }
        }
        // If not inserted between any pair, append (should logically fit at end/beginning boundary)
        if (!inserted) {
            chain.push_back(i); 
        }
    }

    // Insert remaining doors using binary search on the cycle
    // This takes O(N log N) queries.
    for (int u = m; u < N; ++u) {
        int left_idx = 0;
        int cur_len = chain.size();
        
        // Binary search to find the correct edge to insert u
        while (cur_len > 1) {
            int mid_offset = cur_len / 2;
            int mid_idx = (left_idx + mid_offset) % chain.size();
            
            int A = chain[left_idx];
            int B = chain[mid_idx];
            
            QueryResult res = ask(A, u, B);
            
            // We check if u lies in the arc from chain[left_idx] to chain[mid_idx].
            // If {A, B} is NOT returned as a closest pair, it implies u is closer to A and B 
            // than A is to B, suggesting u is on the segment A-B.
            // This is our "Is Left" condition.
            if (!contains_pair(res, A, B)) {
                // u is in the left half (A...B)
                cur_len = mid_offset;
            } else {
                // u is in the right half (B...End)
                left_idx = mid_idx;
                cur_len = cur_len - mid_offset;
            }
        }
        
        // Insert u into the chain
        chain.insert(chain.begin() + left_idx + 1, u);
    }

    // Output the result
    cout << "!";
    for (int x : chain) cout << " " << x;
    cout << endl;

    return 0;
}