#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to represent a range [L, R] that contains 'k' candidates.
// 'offset' is the number of candidates strictly to the left of L (in the range 0...L-1).
struct Gap {
    int L, R;
    int k; 
    int offset; 
};

// Helper to print answer and exit
void answer(int i) {
    cout << "! " << i << endl;
    exit(0);
}

// Helper to perform a query
pair<int, int> query(int i) {
    cout << "? " << i << endl;
    int a0, a1;
    if (!(cin >> a0 >> a1)) exit(0);
    if (a0 == -1) exit(0); // Should not happen given constraints
    return {a0, a1};
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    int best_sum = 2e9; 
    vector<Gap> gaps;

    // Initial query at the center
    int mid = (n - 1) / 2;
    pair<int, int> res = query(mid);
    int s = res.first + res.second;

    if (s == 0) answer(mid);

    best_sum = s;
    
    // Initialize gaps based on the first query
    // res.first is the count of candidates in [0, mid-1]
    // res.second is the count of candidates in [mid+1, n-1]
    if (res.first > 0) gaps.push_back({0, mid - 1, res.first, 0});
    if (res.second > 0) gaps.push_back({mid + 1, n - 1, res.second, res.first});

    while (!gaps.empty()) {
        Gap current = gaps.back();
        gaps.pop_back();

        if (current.L > current.R) continue;

        int m = (current.L + current.R) / 2;
        pair<int, int> q = query(m);
        int current_s = q.first + q.second;

        if (current_s == 0) answer(m);

        if (current_s < best_sum) {
            // Found a strictly better item. This becomes the new reference.
            best_sum = current_s;
            gaps.clear();
            
            // The candidates are now the items better than m.
            // q.first items are to the left, q.second items are to the right.
            if (q.first > 0) gaps.push_back({0, m - 1, q.first, 0});
            if (q.second > 0) gaps.push_back({m + 1, n - 1, q.second, q.first});
        } else {
            // The item at m is not better than the current best.
            // We use the query result to split the current gap.
            
            // Calculate candidates in the left part [L, m-1].
            // q.first is total candidates in [0, m-1].
            // current.offset is total candidates in [0, L-1].
            int left_cands = q.first - current.offset;
            
            // Calculate candidates in the right part [m+1, R].
            // current.k is total candidates in [L, R].
            // m is not a candidate.
            int right_cands = current.k - left_cands; 
            
            // Add valid sub-intervals to the queue
            if (left_cands > 0) {
                gaps.push_back({current.L, m - 1, left_cands, current.offset});
            }
            if (right_cands > 0) {
                // The new offset for the right gap is current.offset + left_cands + (is m candidate?).
                // Since m is not a candidate, it is just current.offset + left_cands = q.first.
                gaps.push_back({m + 1, current.R, right_cands, q.first});
            }
        }
    }
    
    // Fallback, though logical flow guarantees finding the diamond.
    return 0;
}