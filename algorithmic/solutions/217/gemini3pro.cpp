#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global variables for problem dimensions
int N, M;

// Helper function to perform the interactive query
// indices: a list of dango indices (1-based) to include in the subset
// Returns: the maximum number of beautiful sticks that can be formed from the subset
int query(const vector<int>& indices) {
    if (indices.empty()) return 0;
    cout << "? " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Checks if the bucket at bucket_idx currently contains a dango of the same color as item_x.
// This works by querying the complement set U \ (B_k U {x}).
// In the full set U, every color appears M times.
// In U \ B_k, every color present in B_k appears M-1 times (others M times).
// If B_k contains color(x), then U \ B_k \ {x} removes another instance, so count becomes M-2.
// If B_k does not contain color(x), then we just remove x, so count becomes M-1.
// Returns: true if B_k contains color(x), false otherwise.
bool has_color(int bucket_idx, int item_x, const vector<vector<int>>& buckets) {
    // Static vector to avoid reallocation; marks excluded items
    static vector<bool> excluded(N * M + 1, false);
    
    // Mark items to exclude: all items currently in the bucket and the new item x
    excluded[item_x] = true;
    for (int item : buckets[bucket_idx]) {
        excluded[item] = true;
    }
    
    // Construct the query set (U \ Excluded)
    vector<int> q_set;
    q_set.reserve(N * M);
    for (int i = 1; i <= N * M; ++i) {
        if (!excluded[i]) {
            q_set.push_back(i);
        }
    }
    
    // Reset the excluded array for future calls
    excluded[item_x] = false;
    for (int item : buckets[bucket_idx]) {
        excluded[item] = false;
    }

    int res = query(q_set);
    
    // If res == M - 2, it means the minimum frequency of some color is M - 2.
    // This implies we removed 2 instances of color(x). So B_k has the color.
    return res == M - 2;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    // Buckets to store the partitioned dangos
    vector<vector<int>> buckets(M);
    // List of indices of buckets that are not yet full
    vector<int> active_buckets(M);
    iota(active_buckets.begin(), active_buckets.end(), 0);

    // Process each dango one by one
    for (int x = 1; x <= N * M; ++x) {
        int target_bucket = -1;
        
        if (active_buckets.size() == 1) {
            // If only one bucket is active, the item must go there
            target_bucket = active_buckets[0];
        } else {
            // Binary search to find the first bucket that does NOT contain color(x).
            // We rely on the invariant that items of the same color fill buckets sequentially.
            // Thus, for a given color, `has_color` will be True for a prefix of active buckets, and then False.
            
            int L = 0, R = active_buckets.size() - 1;
            int ans_idx = R; // Default to the last one if all checks logic falls through (though loop handles it)
            
            while (L <= R) {
                int mid = L + (R - L) / 2;
                
                // Optimization: If we are at the last active bucket, the item MUST fit there
                // because a solution is guaranteed to exist.
                if (mid == (int)active_buckets.size() - 1) {
                    ans_idx = mid;
                    break;
                }
                
                if (has_color(active_buckets[mid], x, buckets)) {
                    // True: bucket has color, so x must go to a later bucket
                    L = mid + 1;
                } else {
                    // False: bucket doesn't have color, could be this one or earlier?
                    // We want the FIRST bucket that doesn't have the color to maintain the filling order invariant.
                    ans_idx = mid;
                    R = mid - 1;
                }
            }
            target_bucket = active_buckets[ans_idx];
        }

        buckets[target_bucket].push_back(x);

        // If the bucket becomes full (size N), remove it from active list
        if ((int)buckets[target_bucket].size() == N) {
            for (size_t i = 0; i < active_buckets.size(); ++i) {
                if (active_buckets[i] == target_bucket) {
                    active_buckets.erase(active_buckets.begin() + i);
                    break;
                }
            }
        }
    }

    // Output the resulting partition
    for (int i = 0; i < M; ++i) {
        cout << "!";
        for (int item : buckets[i]) {
            cout << " " << item;
        }
        cout << endl;
    }

    return 0;
}