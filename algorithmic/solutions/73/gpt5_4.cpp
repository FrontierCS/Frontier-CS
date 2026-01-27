#include <bits/stdc++.h>
using namespace std;

int n;

struct InversionOracle {
    int n;
    vector<vector<signed char>> cache; // -1 unknown, 0 or 1 known
    InversionOracle(int n): n(n), cache(n+2, vector<signed char>(n+2, -1)) {
        for (int i = 1; i <= n; ++i) cache[i][i] = 0;
    }
    int query(int l, int r) {
        if (l >= r) return 0;
        signed char &c = cache[l][r];
        if (c != -1) return (int)c;
        cout << "0 " << l << " " << r << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) {
            // If input fails, set default (should not happen in correct interactive environment)
            res = 0;
        }
        res &= 1;
        c = (signed char)res;
        return res;
    }
} *oracle;

inline int compGreater(int i, int j) {
    if (i == j) return 0;
    if (i < j) {
        int a = oracle->query(i, j);
        int b = oracle->query(i+1, j);
        int c = oracle->query(i, j-1);
        int d = oracle->query(i+1, j-1);
        return (a ^ b ^ c ^ d);
    } else {
        // i > j
        int a = oracle->query(j, i);
        int b = oracle->query(j+1, i);
        int c = oracle->query(j, i-1);
        int d = oracle->query(j+1, i-1);
        int x = (a ^ b ^ c ^ d); // [pj > pi]
        return x ^ 1; // [pi > pj] = not [pj > pi]
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    oracle = new InversionOracle(n);

    vector<int> idx(n);
    for (int i = 0; i < n; ++i) idx[i] = i + 1;

    stable_sort(idx.begin(), idx.end(), [](int a, int b){
        // return true if pa < pb
        return compGreater(a, b) == 0;
    });

    vector<int> ans(n+1);
    for (int rank = 0; rank < n; ++rank) {
        int pos = idx[rank];
        ans[pos] = rank + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) cout << " " << ans[i];
    cout << endl;
    cout.flush();

    return 0;
}