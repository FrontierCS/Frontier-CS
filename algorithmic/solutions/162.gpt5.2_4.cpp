#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 30;
static constexpr int M = N * (N + 1) / 2;
static constexpr int OP_LIMIT = 10000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto idx = [&](int x, int y) -> int { return x * (x + 1) / 2 + y; };

    vector<int> xOf(M), yOf(M);
    for (int x = 0; x < N; x++) for (int y = 0; y <= x; y++) {
        int id = idx(x, y);
        xOf[id] = x;
        yOf[id] = y;
    }

    vector<vector<int>> adj(M);
    auto add_edge = [&](int a, int b) {
        adj[a].push_back(b);
    };
    for (int x = 0; x < N; x++) for (int y = 0; y <= x; y++) {
        int u = idx(x, y);
        if (y > 0) add_edge(u, idx(x, y - 1));
        if (y < x) add_edge(u, idx(x, y + 1));
        if (x > 0 && y > 0) add_edge(u, idx(x - 1, y - 1));
        if (x > 0 && y < x) add_edge(u, idx(x - 1, y));
        if (x + 1 < N) add_edge(u, idx(x + 1, y));
        if (x + 1 < N) add_edge(u, idx(x + 1, y + 1));
    }

    vector<int> S(N + 1, 0);
    for (int x = 0; x < N; x++) S[x + 1] = S[x] + (x + 1);

    vector<int> valTier(M);
    for (int x = 0; x < N; x++) {
        for (int v = S[x]; v < S[x + 1]; v++) valTier[v] = x;
    }

    vector<int> a(M), pos(M);
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            int v;
            cin >> v;
            int id = idx(x, y);
            a[id] = v;
            pos[v] = id;
        }
    }

    vector<array<int, 4>> ops;
    ops.reserve(OP_LIMIT);

    auto do_swap_idx = [&](int i, int j) {
        int vi = a[i], vj = a[j];
        a[i] = vj; a[j] = vi;
        pos[vi] = j;
        pos[vj] = i;
        ops.push_back({xOf[i], yOf[i], xOf[j], yOf[j]});
    };

    vector<char> fixed(M, 0);
    vector<int> dist(M), prv(M);
    deque<int> q;

    bool stop = false;

    for (int x = 0; x < N && !stop; x++) {
        for (int y = 0; y <= x && !stop; y++) {
            int t = idx(x, y);
            if (fixed[t]) continue;

            if (valTier[a[t]] == x) {
                fixed[t] = 1;
                continue;
            }

            fill(dist.begin(), dist.end(), -1);
            fill(prv.begin(), prv.end(), -1);
            q.clear();

            dist[t] = 0;
            q.push_back(t);

            int cand = -1;
            while (!q.empty()) {
                int u = q.front(); q.pop_front();
                if (valTier[a[u]] == x) {
                    cand = u;
                    break;
                }
                for (int v : adj[u]) {
                    if (fixed[v]) continue;
                    if (dist[v] != -1) continue;
                    dist[v] = dist[u] + 1;
                    prv[v] = u;
                    q.push_back(v);
                }
            }

            if (cand == -1) {
                fixed[t] = 1;
                continue;
            }

            int need = dist[cand];
            if ((int)ops.size() + need > OP_LIMIT) {
                stop = true;
                break;
            }

            int cur = cand;
            while (cur != t) {
                int nxt = prv[cur];
                do_swap_idx(cur, nxt);
                cur = nxt;
            }
            fixed[t] = 1;
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op[0] << " " << op[1] << " " << op[2] << " " << op[3] << "\n";
    }
    return 0;
}