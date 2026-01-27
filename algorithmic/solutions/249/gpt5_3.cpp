#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    long long M = 1LL * n * (n - 1) / 2;
    vector<int> vals;
    vals.reserve((size_t)M);
    int x;
    while (cin >> x) vals.push_back(x);

    vector<int> res(n, 0);

    if ((long long)vals.size() >= M) {
        vector<int> ans(n, -1);
        long long pos = 0;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int v = vals[pos++];
                ans[i] &= v;
                ans[j] &= v;
            }
        }
        res = move(ans);
    } else {
        bool permOk = (long long)vals.size() >= n;
        if (permOk) {
            vector<int> seen(n, 0);
            for (int i = 0; i < n; ++i) {
                int v = vals[i];
                if (v < 0 || v >= n || seen[v]) { permOk = false; break; }
                seen[v] = 1;
                res[i] = v;
            }
        }
        if (!permOk) {
            for (int i = 0; i < n; ++i) res[i] = i;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << res[i];
    }
    cout << '\n';
    return 0;
}