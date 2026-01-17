#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Maximum N is 2000. 
// We use a cache to store query results to avoid re-querying and minimize query count.
// -1 indicates a value has not been queried yet.
int cache_arr[2005][2005];
int n;

// Function to perform query: ? l r
// Returns (sum_{l <= i < j <= r} [p_i > p_j]) % 2
int query(int l, int r) {
    if (l >= r) return 0; // Range length < 2 implies 0 inversions
    if (cache_arr[l][r] != -1) return cache_arr[l][r];
    
    // Using ? and ! as per the example output format.
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return cache_arr[l][r] = res;
}

// Function to determine if p[k] > p[r]
// Returns 1 if p[k] > p[r], 0 otherwise.
// Derivation:
// Let Inv(l, r) be the parity of inversions in subarray p[l...r].
// We know Inv(l, r) = Inv(l, r-1) + sum_{i=l}^{r-1} [p[i] > p[r]]  (mod 2)
// Let S(l, r) = sum_{i=l}^{r-1} [p[i] > p[r]] (mod 2)
// S(l, r) = Inv(l, r) - Inv(l, r-1) (mod 2)
// Also S(l, r) = [p[l] > p[r]] + S(l+1, r) (mod 2)
// So [p[l] > p[r]] = S(l, r) - S(l+1, r) (mod 2)
// Substituting S terms:
// [p[k] > p[r]] = (Inv(k, r) - Inv(k, r-1)) - (Inv(k+1, r) - Inv(k+1, r-1)) (mod 2)
int compare(int k, int r) {
    int v1 = query(k, r);
    int v2 = query(k, r - 1);
    int term1 = (v1 - v2 + 2) % 2;

    int v3 = query(k + 1, r);
    int v4 = query(k + 1, r - 1);
    int term2 = (v3 - v4 + 2) % 2;

    return (term1 - term2 + 2) % 2;
}

int main() {
    // Initialize cache
    for (int i = 0; i <= 2000; ++i) {
        for (int j = 0; j <= 2000; ++j) {
            cache_arr[i][j] = -1;
        }
    }

    if (!(cin >> n)) return 0;

    // sorted_indices stores the indices of the permutation elements processed so far,
    // sorted by their values. 
    // Initially contains index 1.
    vector<int> sorted_indices;
    sorted_indices.push_back(1);

    // Iteratively insert 2, 3, ..., n into the sorted list
    for (int r = 2; r <= n; ++r) {
        int low = 0;
        int high = sorted_indices.size();

        // Binary search for the position of p[r]
        while (low < high) {
            int mid = low + (high - low) / 2;
            int k = sorted_indices[mid];
            
            // Check if p[k] > p[r]
            if (compare(k, r)) {
                // p[k] > p[r], so p[r] is smaller and should be to the left of p[k]
                high = mid;
            } else {
                // p[k] < p[r], so p[r] is larger and should be to the right of p[k]
                low = mid + 1;
            }
        }
        
        // Insert r at the correct position
        sorted_indices.insert(sorted_indices.begin() + low, r);
    }

    // Reconstruct the permutation values
    // sorted_indices[i] is the index in p that holds the (i+1)-th smallest value.
    // So p[sorted_indices[i]] = i + 1.
    vector<int> ans(n + 1);
    for (int i = 0; i < n; ++i) {
        ans[sorted_indices[i]] = i + 1;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}