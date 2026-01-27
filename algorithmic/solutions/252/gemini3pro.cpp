#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Helper to print query and get response
int query(int u, int k, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << u << " " << k << " " << S.size();
    for (int s : S) {
        cout << " " << s;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Step 1: Find Z = a^(n)(1)
    // Z is the node reached starting from 1 after n steps.
    // We binary search for Z in 1..n.
    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> S;
        S.reserve(mid - low + 1);
        for (int i = low; i <= mid; ++i) S.push_back(i);
        if (query(1, n, S)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    int Z = low;

    // Step 2: Find minimal period L of Z
    // Z is on a cycle. We find L such that a^(L)(Z) = Z.
    // We check sequentially L=1, 2, ...
    int L = 1;
    for (; L <= n; ++L) {
        if (query(Z, L, {Z})) break;
    }

    // Step 3: Find Cand = { u | a^(L)(u) = u }
    // These are nodes on cycles with length dividing L.
    // This set contains the cycle C_1 (which contains Z).
    vector<int> Cand;
    for (int u = 1; u <= n; ++u) {
        if (query(u, L, {u})) {
            Cand.push_back(u);
        }
    }

    // Step 4: Determine S = C_1
    // If Cand is small (specifically if it can't contain another cycle of length L),
    // we assume S = Cand. Otherwise, we trace C_1 explicitly.
    vector<int> S;
    // Heuristic: if |Cand| < 2*L, then Cand likely contains only C_1 (since any other cycle
    // must have length d|L, and if L is the minimal period of Z, the component of Z has cycle length L).
    // An overlapping cycle would imply more nodes.
    // Tracing is expensive, so avoid if possible.
    if ((int)Cand.size() < 2 * L) {
        S = Cand;
    } else {
        // Trace the cycle starting from Z within Cand
        // We know Z is in C_1. We find a(Z), a(a(Z))... until we have L nodes.
        vector<int> C1;
        C1.reserve(L);
        C1.push_back(Z);
        int curr = Z;
        for (int i = 0; i < L - 1; ++i) {
            // Find next node from curr: a(curr)
            // Binary search in Cand
            int l = 0, r = Cand.size() - 1;
            while (l < r) {
                int mid = l + (r - l) / 2;
                vector<int> subset;
                subset.reserve(mid - l + 1);
                for (int j = l; j <= mid; ++j) subset.push_back(Cand[j]);
                if (query(curr, 1, subset)) {
                    r = mid;
                } else {
                    l = mid + 1;
                }
            }
            curr = Cand[l];
            C1.push_back(curr);
        }
        S = C1;
    }

    // Step 5: Find A = { u | a^(N)(u) in S }
    // u is in the same component as 1 iff a^(N)(u) lands on C_1.
    // S contains C_1.
    vector<int> A;
    for (int u = 1; u <= n; ++u) {
        if (query(u, n, S)) {
            A.push_back(u);
        }
    }

    // Output answer
    cout << "! " << A.size();
    for (int u : A) {
        cout << " " << u;
    }
    cout << endl;

    return 0;
}