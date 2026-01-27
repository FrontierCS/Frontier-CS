#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> parent, sz;
    DSU(int n = 0) { init(n); }
    void init(int n) {
        parent.resize(n);
        sz.assign(n, 1);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    void unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return;
        if (sz[a] < sz[b]) swap(a, b);
        parent[b] = a;
        sz[a] += sz[b];
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    DSU dsu(n + 1);
    vector<int> a(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << "? " << i << " 1 1 " << j << endl;
            cout.flush();
            int resp;
            if (!(cin >> resp)) return 0;
            if (resp == 1) {
                a[i] = j;
                dsu.unite(i, j);
                break;
            }
        }
    }

    int root1 = dsu.find(1);
    vector<int> ans;
    for (int i = 1; i <= n; ++i) {
        if (dsu.find(i) == root1) ans.push_back(i);
    }

    cout << "! " << ans.size();
    for (int x : ans) cout << ' ' << x;
    cout << endl;
    cout.flush();

    return 0;
}