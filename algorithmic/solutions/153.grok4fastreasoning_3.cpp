#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int N = 400;
    int M = 1995;
    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) {
        cin >> x[i] >> y[i];
    }
    vector<pair<int, int>> ed(M);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        ed[i] = {u, v};
    }
    vector<int> par(N), rnk(N, 0);
    for (int i = 0; i < N; i++) par[i] = i;
    auto find = [&](auto&& self, int a) -> int {
        if (par[a] != a) par[a] = self(self, par[a]);
        return par[a];
    };
    auto unite = [&](int a, int b) -> bool {
        a = find(find, a);
        b = find(find, b);
        if (a == b) return false;
        if (rnk[a] < rnk[b]) swap(a, b);
        par[b] = a;
        if (rnk[a] == rnk[b]) rnk[a]++;
        return true;
    };
    for (int i = 0; i < M; i++) {
        int l;
        cin >> l;
        int u = ed[i].first, v = ed[i].second;
        if (unite(u, v)) {
            cout << 1 << '\n';
        } else {
            cout << 0 << '\n';
        }
        cout.flush();
    }
}