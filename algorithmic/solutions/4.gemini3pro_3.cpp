#include <iostream>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

// Global variables
int n;
long long k;
long long memo[2005][2005];
bool visited[2005][2005];

// Query function with caching
// Queries the value at A[r][c]
long long query(int r, int c) {
    if (visited[r][c]) return memo[r][c];
    cout << "QUERY " << r << " " << c << endl;
    long long val;
    cin >> val;
    visited[r][c] = true;
    memo[r][c] = val;
    return val;
}

// Function to output the answer and terminate
void done(long long ans) {
    cout << "DONE " << ans << endl;
    exit(0);
}

// Boundaries for the active region
// L[i]: column index of the rightmost element in row i known to be <= answer's lower bound range
// R[i]: column index of the leftmost element in row i known to be > answer's upper bound range
int L[2005];
int R[2005];

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> k)) return 0;

    // Initialize boundaries
    for (int i = 1; i <= n; ++i) {
        L[i] = 0;
        R[i] = n + 1;
    }

    long long count_L = 0; // Number of elements <= current L boundary
    mt19937 rng(1337); // Random number generator
    int stuck_cnt = 0; // Counter to detect lack of progress

    while (true) {
        long long S = 0;
        vector<int> active_rows;
        for (int i = 1; i <= n; ++i) {
            if (L[i] < R[i] - 1) {
                S += (R[i] - 1 - L[i]);
                active_rows.push_back(i);
            }
        }

        // If active space is empty (should not happen normally) or small enough, solve directly
        if (S <= 850) {
            vector<long long> vals;
            for (int r : active_rows) {
                for (int c = L[r] + 1; c < R[r]; ++c) {
                    vals.push_back(query(r, c));
                }
            }
            sort(vals.begin(), vals.end());
            // We need the (k - count_L)-th element from the sorted values
            long long idx = k - count_L - 1;
            if (idx >= 0 && idx < vals.size()) {
                done(vals[idx]);
            } else {
                // Fallback, though logic dictates idx should be valid
                if (!vals.empty()) done(vals.back());
                else break; // Should not exit here
            }
        }

        // Pick a random pivot from the active region
        long long rand_idx = uniform_int_distribution<long long>(0, S - 1)(rng);
        int r_pivot = -1, c_pivot = -1;
        long long current_s = 0;
        for (int r : active_rows) {
            long long width = R[r] - 1 - L[r];
            if (current_s + width > rand_idx) {
                r_pivot = r;
                c_pivot = L[r] + 1 + (rand_idx - current_s);
                break;
            }
            current_s += width;
        }

        long long pivot = query(r_pivot, c_pivot);
        
        // Count elements <= pivot and trace the path
        // path_c[i] stores the column index of the rightmost element <= pivot in row i
        vector<int> path_c(n + 1);
        long long cnt_le = 0;
        int c = 0; // Tracks column from row below
        for (int i = n; i >= 1; --i) {
            // Start search from max of (column from row below, L[i] + 1)
            int curr = max(c, L[i] + 1);
            while (curr < R[i]) {
                long long val = query(i, curr);
                if (val > pivot) break;
                curr++;
            }
            path_c[i] = curr - 1;
            c = path_c[i];
            cnt_le += path_c[i];
        }

        bool changed = false;
        
        if (cnt_le < k) {
            // Answer is > pivot
            // Update L to path_c
            for(int i = 1; i <= n; ++i) {
                if (L[i] != path_c[i]) changed = true;
                L[i] = path_c[i];
            }
            count_L = cnt_le;
            stuck_cnt = 0; // Progress made
        } else {
            // Answer is <= pivot
            // Update R to path_c + 1
            for(int i = 1; i <= n; ++i) {
                if (R[i] != path_c[i] + 1) changed = true;
                R[i] = path_c[i] + 1;
            }
            
            if (!changed) {
                // If R didn't change, it means all active elements in these rows are <= pivot
                // If this persists, it likely means all active candidates are equal to pivot
                stuck_cnt++;
                if (stuck_cnt > 10) done(pivot);
            } else {
                stuck_cnt = 0;
            }
        }
    }
    return 0;
}