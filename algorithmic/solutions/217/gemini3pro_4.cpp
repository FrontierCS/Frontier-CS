#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

int N, M;

// Global array to mark excluded items for query construction
bool is_excluded[10005];

int query(const vector<int>& indices) {
    if (indices.empty()) return 0;
    cout << "? " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl; // Flush is required
    int res;
    cin >> res;
    return res;
}

int main() {
    fast_io();
    if (!(cin >> N >> M)) return 0;

    // Trivial case M=1
    if (M == 1) {
        cout << "! ";
        for (int i = 1; i <= N; ++i) {
            cout << i << (i == N ? "" : " ");
        }
        cout << endl;
        return 0;
    }

    // Buckets to hold the indices of dangos for each stick
    vector<vector<int>> buckets(M);
    
    // Items to process
    vector<int> items(N * M);
    iota(items.begin(), items.end(), 1);

    // Shuffle items to avoid worst-case inputs and improve average performance of greedy
    mt19937 rng(1337);
    shuffle(items.begin(), items.end(), rng);

    // Pre-allocate query vector to avoid reallocations
    vector<int> q_set;
    q_set.reserve(N * M);

    for (int u : items) {
        // Try buckets in random order
        vector<int> candidates(M);
        iota(candidates.begin(), candidates.end(), 0);
        shuffle(candidates.begin(), candidates.end(), rng);
        
        bool placed = false;
        for (int b_idx : candidates) {
            // We want to check if u fits in buckets[b_idx].
            // A conflict occurs if buckets[b_idx] already contains a dango of color(u).
            // We can detect this by querying the complement of (buckets[b_idx] U {u}).
            // Let S = buckets[b_idx].
            // Query set Q = All_Items \ (S U {u}).
            // If u fits (color not in S), then in Q, we removed 1 copy of color(u) (u itself) 
            // and 1 copy of other colors in S. The min count of any color in Q will be M-1.
            // If u conflicts (color in S), then in Q, we removed 2 copies of color(u) (u and the one in S).
            // The min count will be M-2.
            // We check if result == M-1.

            // Construct query set efficiently
            // Mark items in current bucket and u as excluded
            for (int x : buckets[b_idx]) is_excluded[x] = true;
            is_excluded[u] = true;
            
            q_set.clear();
            for (int k = 1; k <= N * M; ++k) {
                if (!is_excluded[k]) {
                    q_set.push_back(k);
                }
            }
            
            // Reset excluded array
            for (int x : buckets[b_idx]) is_excluded[x] = false;
            is_excluded[u] = false;
            
            int res = query(q_set);
            
            if (res == M - 1) {
                buckets[b_idx].push_back(u);
                placed = true;
                break;
            }
        }
        // In a valid scenario, 'placed' should always be true eventually.
    }

    // Output the result
    for (int i = 0; i < M; ++i) {
        cout << "!";
        for (int x : buckets[i]) {
            cout << " " << x;
        }
        cout << endl;
    }

    return 0;
}