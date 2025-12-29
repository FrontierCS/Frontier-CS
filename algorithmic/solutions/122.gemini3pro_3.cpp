#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

void solve() {
    // Strategy:
    // Query 1: Use an array of M ones. 
    // M is chosen to balance the worst-case size of the second query.
    // If M = 66666, the maximum range of candidates for W roughly matches the remaining
    // allowance for N in the second query (since max N = 10^5).
    int M = 66666;
    cout << "? " << M;
    for (int i = 0; i < M; ++i) {
        cout << " 1";
    }
    cout << endl;

    int L;
    cin >> L;
    if (L == -1) exit(0);
    // L=0 is impossible for word length 1 and W >= 1.
    if (L == 0) exit(0);

    // Calculate the range of possible values for W based on L.
    // L = ceil(M / W) <=> L-1 < M/W <= L.
    // Lower bound: M/W <= L => W >= M/L => W >= ceil(M/L).
    // Upper bound: M/W > L-1 => W < M/(L-1) => W <= floor((M-1)/(L-1)).
    // Note: If L=1, W can be up to 100000.
    
    long long min_W = (1LL * M + L - 1) / L;
    long long max_W;
    
    if (L == 1) {
        max_W = 100000;
    } else {
        max_W = (1LL * M - 1) / (L - 1);
        if (max_W > 100000) max_W = 100000;
    }

    // If the range contains only one value, we found W.
    if (min_W == max_W) {
        cout << "! " << min_W << endl;
        return;
    }

    // Query 2: Distinguish W in [min_W, max_W].
    // We construct a query using pairs (A, k) where A = min_W.
    // Since W >= min_W, A fits on a line. 
    // The pair (A, k) fits on one line if A + k <= W, otherwise it takes 2 lines.
    // We test for k in {1, ..., range_len}.
    // The number of pairs that fit will tell us W - A.
    
    int A = (int)min_W;
    int range_len = (int)(max_W - min_W);
    
    vector<int> q2;
    q2.reserve(2 * range_len);
    for (int k = 1; k <= range_len; ++k) {
        q2.push_back(A);
        q2.push_back(k);
    }

    cout << "? " << q2.size();
    for (int x : q2) {
        cout << " " << x;
    }
    cout << endl;

    int L2;
    cin >> L2;
    if (L2 == -1) exit(0);

    // Calculation:
    // Let N_pairs = range_len.
    // Let C be the count of k such that A + k <= W.
    // Lines = C * 1 + (N_pairs - C) * 2 = 2 * N_pairs - C.
    // Therefore C = 2 * N_pairs - Lines.
    // Since we check k=1..range_len, C is exactly W - A.
    // So W = A + C.

    long long C = 2LL * range_len - L2;
    long long W = A + C;
    cout << "! " << W << endl;
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