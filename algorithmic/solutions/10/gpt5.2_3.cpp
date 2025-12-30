#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

struct Solver {
    long long query(int u, int v) {
        cout << "? " << u << " " << v << "\n";
        cout.flush();
        long long d;
        if (!(cin >> d)) die();
        if (d == -1) die();
        return d;
    }

    void solve_one(int n) {
        if (n <= 1) {
            cout << "!\n";
            cout.flush();
            return;
        }

        vector<long long> depth(n + 1, 0);
        for (int i = 2; i <= n; i++) depth[i] = query(1, i);

        vector<int> order;
        order.reserve(max(0, n - 1));
        for (int i = 2; i <= n; i++) order.push_back(i);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (depth[a] != depth[b]) return depth[a] < depth[b];
            return a < b;
        });

        vector<vector<int>> children(n + 1);
        vector<int> parent(n + 1, 0);
        vector<long long> wpar(n + 1, 0);

        parent[1] = 0;
        wpar[1] = 0;

        for (int v : order) {
            int cur = 1;
            while (true) {
                int found = 0;
                int found_idx = -1;
                auto &ch = children[cur];

                for (int idx = 0; idx < (int)ch.size(); idx++) {
                    int c = ch[idx];
                    if (depth[c] >= depth[v]) continue;
                    long long d = query(c, v);
                    if (depth[c] + d == depth[v]) {
                        found = c;
                        found_idx = idx;
                        break;
                    }
                }

                if (!found) {
                    parent[v] = cur;
                    wpar[v] = depth[v] - depth[cur];
                    children[cur].push_back(v);
                    break;
                } else {
                    // Move-to-front heuristic to reduce scans on repeated usage
                    if (found_idx > 0) swap(children[cur][0], children[cur][found_idx]);
                    cur = found;
                }
            }
        }

        cout << "!";
        for (int i = 2; i <= n; i++) {
            cout << " " << parent[i] << " " << i << " " << wpar[i];
        }
        cout << "\n";
        cout.flush();
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        int T;
        if (!(cin >> T)) return;
        while (T--) {
            int n;
            if (!(cin >> n)) die();
            solve_one(n);
        }
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}