#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> parent, rnk;
    DSU(int n = 0) { init(n); }
    void init(int n_) {
        n = n_;
        parent.assign(n + 1, 0);
        rnk.assign(n + 1, 0);
        for (int i = 0; i <= n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    void unite(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return;
        if (rnk[a] < rnk[b]) swap(a, b);
        parent[b] = a;
        if (rnk[a] == rnk[b]) ++rnk[a];
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) {
        return 0;
    }

    DSU dsu(n);

    auto query = [&](int idx) -> char {
        cout << "? " << idx << '\n';
        cout.flush();
        char ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    auto reset = [&]() {
        cout << "R\n";
        cout.flush();
    };

    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            reset();
            query(i); // ignore response
            char res = query(j);
            if (res == 'Y') {
                dsu.unite(i, j);
            }
        }
    }

    int d = 0;
    for (int i = 1; i <= n; ++i) {
        if (dsu.find(i) == i) ++d;
    }

    cout << "! " << d << '\n';
    cout.flush();
    return 0;
}