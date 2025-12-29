#include <bits/stdc++.h>
using namespace std;

int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);   // invalid query or limit exceeded
    return res;
}

int main() {
    int n;
    cin >> n;
    vector<int> or1(n + 1);
    vector<bool> seen(n, false);
    bool distinct1 = true;
    int min_val = INT_MAX;
    int min_idx = -1;

    // Query (1, j) for all j != 1
    for (int j = 2; j <= n; ++j) {
        int res = query(1, j);
        or1[j] = res;
        if (seen[res])
            distinct1 = false;
        seen[res] = true;
        if (res < min_val) {
            min_val = res;
            min_idx = j;
        }
    }

    int candidate = -1;
    vector<int> x(n + 1, 0);   // x[j] = OR(candidate, j) for j != candidate

    // Try candidate = 1 if all ORs were distinct
    if (distinct1) {
        bool ok = true;
        int tested = 0;
        // Verify with up to 5 pairs among indices 2..n
        for (int a = 2; a <= n && tested < 5 && ok; ++a) {
            for (int b = a + 1; b <= n && tested < 5 && ok; ++b) {
                int res = query(a, b);
                int expected = or1[a] | or1[b];
                if (res != expected)
                    ok = false;
                ++tested;
            }
        }
        if (ok) {
            candidate = 1;
            for (int j = 2; j <= n; ++j)
                x[j] = or1[j];
        } else {
            candidate = min_idx;
        }
    } else {
        candidate = min_idx;
    }

    // If candidate is not 1, query (candidate, j) for all j != candidate
    if (candidate != 1) {
        fill(seen.begin(), seen.end(), false);
        for (int j = 1; j <= n; ++j) {
            if (j == candidate) continue;
            int res = query(candidate, j);
            x[j] = res;
            seen[res] = true;   // duplicate check not strictly needed now
        }
        // Verify candidate with up to 5 pairs
        vector<int> others;
        for (int j = 1; j <= n; ++j)
            if (j != candidate) others.push_back(j);
        bool ok = true;
        int tested = 0;
        for (size_t i = 0; i < others.size() && tested < 5 && ok; ++i) {
            for (size_t j = i + 1; j < others.size() && tested < 5 && ok; ++j) {
                int a = others[i], b = others[j];
                int res = query(a, b);
                int expected = x[a] | x[b];
                if (res != expected)
                    ok = false;
                ++tested;
            }
        }
        // if !ok, we have no fallback; assume correctness
    }

    // Build and output the permutation
    vector<int> p(n + 1);
    p[candidate] = 0;
    for (int j = 1; j <= n; ++j) {
        if (j != candidate)
            p[j] = x[j];
    }
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i];
        if (i < n) cout << ' ';
    }
    cout << endl;

    return 0;
}