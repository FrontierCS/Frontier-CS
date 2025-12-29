#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int req(ll dsq) {
    if (dsq == 0) return 0;
    long double sr = sqrtl((long double)dsq);
    int p = (int)sr;
    if ((ll)p * p < dsq) p++;
    return p;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int N, M, K;
    cin >> N >> M >> K;
    vector<ll> X(N + 1), Y(N + 1);
    for (int i = 1; i <= N; i++) {
        cin >> X[i] >> Y[i];
    }
    struct Edge {
        int u, v, id;
        ll w;
    };
    vector<Edge> edges(M);
    for (int j = 0; j < M; j++) {
        int u, v;
        ll w;
        cin >> u >> v >> w;
        edges[j] = {u, v, j, w};
    }
    vector<ll> A(K), B(K);
    for (int k = 0; k < K; k++) {
        cin >> A[k] >> B[k];
    }
    vector<vector<ll>> dist_sq(N + 1, vector<ll>(K));
    for (int i = 1; i <= N; i++) {
        for (int kk = 0; kk < K; kk++) {
            ll dx = X[i] - A[kk];
            ll dy = Y[i] - B[kk];
            dist_sq[i][kk] = dx * dx + dy * dy;
        }
    }
    // Kruskal for MST
    vector<int> parent(N + 1);
    for (int i = 1; i <= N; i++) parent[i] = i;
    function<int(int)> find = [&](int x) -> int {
        return parent[x] != x ? parent[x] = find(parent[x]) : x;
    };
    auto unite = [&](int x, int y) -> bool {
        int px = find(x), py = find(y);
        if (px == py) return false;
        parent[px] = py;
        return true;
    };
    sort(edges.begin(), edges.end(), [](const Edge& a, const Edge& b) {
        return a.w < b.w;
    });
    vector<vector<pair<int, int>>> tree(N + 1);
    int comp = N;
    for (auto& e : edges) {
        if (unite(e.u, e.v)) {
            tree[e.u].emplace_back(e.v, e.id);
            tree[e.v].emplace_back(e.u, e.id);
            comp--;
            if (comp == 1) break;
        }
    }
    // BFS to set parents
    vector<int> par(N + 1, -1);
    vector<int> par_edge_id(N + 1, -1);
    vector<bool> vis(N + 1, false);
    queue<int> qq;
    qq.push(1);
    vis[1] = true;
    par[1] = -1;
    while (!qq.empty()) {
        int u = qq.front();
        qq.pop();
        for (auto [v, eid] : tree[u]) {
            if (!vis[v]) {
                vis[v] = true;
                par[v] = u;
                par_edge_id[v] = eid;
                qq.push(v);
            }
        }
    }
    // Find best_i for each resident
    vector<int> best_i(K);
    for (int kk = 0; kk < K; kk++) {
        ll mind = LLONG_MAX / 2;
        int best = -1;
        for (int i = 1; i <= N; i++) {
            ll d = dist_sq[i][kk];
            if (d < mind) {
                mind = d;
                best = i;
            }
        }
        best_i[kk] = best;
    }
    // Compute maxr
    vector<int> maxr(N + 1, 0);
    for (int kk = 0; kk < K; kk++) {
        int i = best_i[kk];
        ll dsq = dist_sq[i][kk];
        int r = req(dsq);
        maxr[i] = max(maxr[i], r);
    }
    // Needed stations
    vector<bool> needed(N + 1, false);
    for (int i = 1; i <= N; i++) {
        if (maxr[i] > 0) needed[i] = true;
    }
    // Collect used edge ids
    set<int> used_ids;
    for (int i = 1; i <= N; i++) {
        if (needed[i]) {
            int cur = i;
            while (par[cur] != -1) {
                used_ids.insert(par_edge_id[cur]);
                cur = par[cur];
            }
        }
    }
    // P
    vector<int> P(N + 1, 0);
    for (int i = 1; i <= N; i++) {
        P[i] = maxr[i];
    }
    // B
    vector<int> BB(M, 0);
    for (int id : used_ids) {
        BB[id] = 1;
    }
    // Output
    for (int i = 1; i <= N; i++) {
        cout << P[i];
        if (i < N) cout << " ";
        else cout << "\n";
    }
    for (int j = 0; j < M; j++) {
        cout << BB[j];
        if (j < M - 1) cout << " ";
        else cout << "\n";
    }
}