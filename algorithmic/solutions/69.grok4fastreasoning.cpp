#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    int off = 2000;
    vector<int> A(n + 1), B(n + 1);
    for (int i = 1; i <= n; ++i) {
        A[i] = i;
        B[i] = off + i;
    }
    for (int i = 1; i <= n; ++i) {
        string s(A[i], 'X');
        s += string(B[i], 'O');
        cout << s << '\n';
    }
    cout.flush();
    unordered_map<long long, pair<int, int>> ans_map;
    for (int u = 1; u <= n; ++u) {
        for (int v = 1; v <= n; ++v) {
            int au = A[u], bu = B[u], av = A[v], bv = B[v];
            int max_a = max(au, av);
            int max_b = max(bu, bv);
            long long cr = 1LL * bu * av;
            long long abu = 1LL * au * bu;
            long long avb = 1LL * av * bv;
            int min_a = min(au, av);
            int min_b = min(bu, bv);
            long long mt = 1LL * min_a * min_b;
            long long pp = max_a + max_b + cr + abu + avb - mt;
            ans_map[pp] = {u, v};
        }
    }
    int q;
    cin >> q;
    for (int i = 0; i < q; ++i) {
        long long p;
        cin >> p;
        auto [u, v] = ans_map[p];
        cout << u << " " << v << '\n';
        cout.flush();
    }
    return 0;
}