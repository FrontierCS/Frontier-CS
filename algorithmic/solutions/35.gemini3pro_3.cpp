#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>

using namespace std;

// Global variables
int N;
mt19937 rng(1337);

// Function to query the interactor
// Format: ? x |S| s1 s2 ...
// Returns 1 if yes, 0 if no, -1 if error
int query(int x, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << x << " " << S.size();
    for (int s : S) {
        cout << " " << s;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Invalid query or verdict from interactor
    return res;
}

// Function to verify if a candidate is the single element
// Returns true if x appears likely to be the single element
// Returns false if x is proven to be a double element
// We perform several checks. A double element appearing at indices u and v
// will be identified if we pick a set S such that u is in S and v is in S^c (or vice versa).
// In that case, Query(x, S) = 1 and Query(x, S^c) = 1.
// A single element will always have one 1 and one 0.
bool verify(int x) {
    // 18 checks give a false positive probability of 0.5^18 < 4e-6
    int checks = 18;
    for (int k = 0; k < checks; ++k) {
        vector<int> S;
        vector<int> Sc;
        S.reserve(2 * N);
        Sc.reserve(2 * N);
        for (int i = 1; i <= 2 * N - 1; ++i) {
            if (rng() % 2) S.push_back(i);
            else Sc.push_back(i);
        }
        
        // Ensure sets are valid (should be extremely likely for N=300)
        if (S.empty() || Sc.empty()) {
            k--; continue;
        }

        int q1 = query(x, S);
        if (q1 == 0) {
            // x is fully in Sc.
            // If x is double, both positions are in Sc (prob 0.25).
            // If x is single, position is in Sc (prob 0.5).
            // This result is consistent with single, so we continue verifying.
            // Note: We don't need to query Sc, because if q1=0, q2 MUST be 1
            // (since every number appears at least once).
            continue;
        } else {
            // q1 == 1. x intersects S.
            // Check intersection with Sc.
            int q2 = query(x, Sc);
            if (q2 == 1) {
                // x intersects both S and Sc. 
                // Since single element has only 1 position, it cannot be in both disjoint sets.
                // Therefore x is double.
                return false; 
            }
            // q2 == 0. x fully in S. Consistent with single.
        }
    }
    // If passed all checks, it's very likely single.
    return true;
}

// Recursive solver
// Repeatedly partitions candidates based on query result with a random set.
// The single element is equally likely to be in the '0' or '1' partition,
// but double elements are biased towards the '1' partition (prob 0.75).
// Thus we prioritize exploring the '0' partition.
int solve_recursive(vector<int>& candidates) {
    if (candidates.empty()) return -1;
    
    if (candidates.size() == 1) {
        // Verify the last standing candidate
        if (verify(candidates[0])) return candidates[0];
        else return -1;
    }

    // Create a random subset S
    vector<int> S;
    S.reserve(2 * N);
    for (int i = 1; i <= 2 * N - 1; ++i) {
        if (rng() % 2) S.push_back(i);
    }
    
    // Ensure S is non-trivial to avoid wasted queries
    if (S.empty()) S.push_back(1);
    if (S.size() == (size_t)(2 * N - 1)) S.pop_back();

    vector<int> c0, c1;
    c0.reserve(candidates.size());
    c1.reserve(candidates.size());

    // Filter candidates based on the random set
    for (int x : candidates) {
        int r = query(x, S);
        if (r == 0) c0.push_back(x);
        else c1.push_back(x);
    }

    // Heuristic: Try c0 first because it's expected to be smaller and 
    // has a higher concentration of the single element if it is there.
    int res = solve_recursive(c0);
    if (res != -1) return res;

    // If not found in c0 (i.e., filtered out as doubles), try c1
    return solve_recursive(c1);
}

void solve() {
    cin >> N;
    // Check for exit signal
    if (N == -1) exit(0);

    vector<int> candidates(N);
    iota(candidates.begin(), candidates.end(), 1);

    int ans = solve_recursive(candidates);
    cout << "! " << ans << endl;
}

int main() {
    // Optimize IO, but maintain safety with interactive problems
    ios_base::sync_with_stdio(false);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}