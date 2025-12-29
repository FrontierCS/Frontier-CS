#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <cmath>

using namespace std;

// Function to simulate the editor process locally
// Returns number of lines needed to display article a with width W.
// Returns 0 if max(a) > W.
int solve_lines(const vector<int>& a, int W) {
    int lines = 1;
    long long current_s = 0;
    for (int x : a) {
        if (x > W) return 0;
        if (current_s + x <= W) {
            current_s += x;
        } else {
            lines++;
            current_s = x;
        }
    }
    return lines;
}

void solve() {
    int N = 100000; 

    // Query 1: N words of length 1.
    // This provides a range of candidate values for W.
    cout << "? " << N;
    for (int i = 0; i < N; ++i) cout << " 1";
    cout << endl;
    
    int k1;
    cin >> k1;
    // Check for invalid input or termination signal
    if (k1 == 0 || k1 == -1) exit(0);

    // Derive range [L, R] from k1
    // Relation: k1 = ceil(N / W)
    // Inequalities: k1 - 1 < N / W <= k1
    // Lower bound: W >= N / k1  => L = ceil(N / k1)
    // Upper bound: W < N / (k1 - 1)  (for k1 > 1) => W <= floor((N - 1) / (k1 - 1))
    
    int L = (N + k1 - 1) / k1;
    int R;
    if (k1 == 1) {
        R = 100000;
    } else {
        R = (N - 1) / (k1 - 1);
    }
    
    // Clamp R to the problem constraint
    if (R > 100000) R = 100000;
    if (L > R) L = R; 
    
    if (L == R) {
        cout << "! " << L << endl;
        return;
    }
    
    // Query 2: Random sequence to distinguish W within [L, R]
    // We generate numbers in [1, L]. Since L <= W_true, these words are always valid.
    // Using N=100000 and random values provides a high "slope" for the lines(W) function,
    // minimizing the chance of collisions (different W producing same line count).
    mt19937 rng(1337); 
    vector<int> a(N);
    for (int i = 0; i < N; ++i) {
        // Generate random length in [1, L]
        a[i] = (int)(rng() % L) + 1;
    }
    
    cout << "? " << N;
    for (int i = 0; i < N; ++i) {
        cout << " " << a[i];
    }
    cout << endl;
    
    int k2;
    cin >> k2;
    if (k2 == -1) exit(0);
    
    // Binary search for W in [L, R]
    // The number of lines is non-increasing with respect to W.
    // We search for W such that solve_lines(a, W) == k2.
    
    int ans = R;
    int low = L, high = R;
    
    while (low <= high) {
        int mid = low + (high - low) / 2;
        int sim = solve_lines(a, mid);
        
        if (sim == k2) {
            ans = mid;
            // Assuming uniqueness or finding any consistent W.
            // In case of a small plateau, the problem constraints and strategy 
            // usually imply we should find the consistent value. 
            // Since simulate is monotonic, we can break or try to find boundaries.
            // Given the high variance of the query, a match is likely unique.
            break; 
        } else if (sim < k2) {
            // Observed k2 lines, but mid gives fewer lines.
            // Fewer lines implies mid is too large (capacity too high).
            // We need a smaller W to get more lines.
            high = mid - 1;
        } else {
            // sim > k2
            // Mid gives too many lines. Capacity too low.
            // We need a larger W to reduce line count.
            low = mid + 1;
        }
    }
    
    cout << "! " << ans << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}