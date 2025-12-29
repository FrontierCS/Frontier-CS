#include <bits/stdc++.h>
using namespace std;

const int MAX_N = 1024;
const int M = 20; // number of signature bits

int main() {
    int n, k;
    cin >> n >> k;

    // Precompute signature sets S_b for b = 0..M-1
    // Each set has size = min(k, n/2) to fit in memory
    int sz = min(k, n/2);
    if (sz == 0) sz = 1; // at least one element
    vector<vector<int>> S(M);
    for (int b = 0; b < M; ++b) {
        int start = (b * 997) % n; // deterministic starting point
        for (int i = 0; i < sz; ++i) {
            int idx = (start + i) % n + 1; // convert to 1-indexed
            S[b].push_back(idx);
        }
        sort(S[b].begin(), S[b].end());
    }

    vector<bitset<M>> sig(n+1); // signatures for indices 1..n

    // Compute signatures
    for (int b = 0; b < M; ++b) {
        // Reset memory
        cout << "R" << endl;
        cout.flush();

        // Query all indices in S_b
        for (int idx : S[b]) {
            cout << "? " << idx << endl;
            cout.flush();
            char resp;
            cin >> resp;
            // we ignore the response for now
        }

        // Now query every index to get the b-th signature bit
        for (int i = 1; i <= n; ++i) {
            cout << "? " << i << endl;
            cout.flush();
            char resp;
            cin >> resp;
            if (resp == 'Y')
                sig[i].set(b);
            // else bit remains 0
        }
    }

    // Group indices by signature
    map<bitset<M>, vector<int>> groups;
    for (int i = 1; i <= n; ++i) {
        groups[sig[i]].push_back(i);
    }

    // Output answer
    int d = groups.size();
    cout << "! " << d << endl;
    cout.flush();

    return 0;
}