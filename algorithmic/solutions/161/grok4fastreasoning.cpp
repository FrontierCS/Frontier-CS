#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    int N, M, K;
    cin >> N >> M >> K;
    vector<double> X(N + 1), Y(N + 1);
    for (int i = 1; i <= N; i++) {
        cin >> X[i] >> Y[i];
    }
    vector<int> eu(M + 1), ev(M + 1);
    vector<ll> edge_w(M + 1);
    vector<vector<tuple<int, int, ll>>> g(N + 1);
    for (int j = 1; j <= M; j++) {
        int u, v;
        ll w;
        cin >> u >> v >> w;
        eu[j] = u;
        ev[j] = v;
        edge_w[j] = w;
        g[u].emplace_back(v, j, w);
        g[v].emplace_back(u, j, w);
    }
    vector<pair<double, double>> res(K);
    for (int k = 0; k < K; k++) {
        double a, b;
        cin >> a >> b;
        res[k] = {a, b};
    }
    vector<vector<double>> dist_res_to_stat(K, vector<double>(N + 1));
    for (int k = 0; k < K; k++) {
        auto [a, b] = res[k];
        for (int i = 1; i <= N; i++) {
            double dx = a - X[i];
            double dy = b - Y[i];
            dist_res_to_stat[k][i] = hypot(dx, dy);
        }
    }
    // Floyd-Warshall for shortest paths
    vector<vector<ll>> sp(N + 1, vector<ll>(N + 1, 1LL << 60));
    vector<vector<int>> nxt(N + 1, vector<int>(N + 1, -1));
    for (int i = 1; i <= N; i++) sp[i][i] = 0;
    for (int j = 1; j <= M; j++) {
        int u = eu[j], v = ev[j];
        ll w = edge_w[j];
        sp[u][v] = w;
        sp[v][u] = w;
        nxt[u][v] = v;
        nxt[v][u] = u;
    }
    for (int k = 1; k <= N; k++) {
        for (int i = 1; i <= N; i++) {
            for (int jj = 1; jj <= N; jj++) {
                if (sp[i][k] + sp[k][jj] < sp[i][jj]) {
                    sp[i][jj] = sp[i][k] + sp[k][jj];
                    nxt[i][jj] = nxt[i][k];
                }
            }
        }
    }
    // Compute initial Power using all stations
    vector<int> Power(N + 1, 0);
    for (int k = 0; k < K; k++) {
        double mind = 1e100;
        int best = -1;
        for (int i = 1; i <= N; i++) {
            double d = dist_res_to_stat[k][i];
            if (d < mind) {
                mind = d;
                best = i;
            }
        }
        int need = (int)ceil(mind);
        Power[best] = max(Power[best], need);
    }
    // Collect U
    vector<int> U;
    for (int i = 1; i <= N; i++) {
        if (Power[i] > 0 || i == 1) {
            U.push_back(i);
        }
    }
    int nu = U.size();
    if (nu == 1) {
        // Only 1, no edges
        for (int i = 1; i <= N; i++) {
            if (i > 1) cout << " ";
            cout << Power[i];
        }
        cout << endl;
        for (int j = 1; j <= M; j++) {
            if (j > 1) cout << " ";
            cout << 0;
        }
        cout << endl;
        return 0;
    }
    // MST on U using sp
    struct Edge {
        int u, v, idx;
        ll w;
        bool operator<(const Edge& o) const {
            return w < o.w;
        }
    };
    vector<Edge> subedgs;
    map<int, int> local_id;
    for (int ii = 0; ii < nu; ii++) {
        local_id[U[ii]] = ii;
    }
    for (int aa = 0; aa < nu; aa++) {
        for (int bb = aa + 1; bb < nu; bb++) {
            int u = U[aa], v = U[bb];
            ll ww = sp[u][v];
            if (ww < (1LL << 60)) {
                subedgs.push_back({u, v, -1, ww});
            }
        }
    }
    sort(subedgs.begin(), subedgs.end());
    vector<int> upar(nu);
    iota(upar.begin(), upar.end(), 0);
    auto ufind = [&](auto&& self, int x) -> int {
        return upar[x] == x ? x : upar[x] = self(self, upar[x]);
    };
    vector<pair<int, int>> mst_pairs;
    for (auto& e : subedgs) {
        int a = local_id[e.u];
        int b = local_id[e.v];
        int pa = ufind(ufind, a);
        int pb = ufind(ufind, b);
        if (pa != pb) {
            upar[pa] = pb;
            mst_pairs.push_back({e.u, e.v});
        }
    }
    // Now, for each mst_pair, get path edges
    auto get_path_edges = [&](int start, int goal) -> set<int> {
        if (start == goal) return {};
        vector<ll> dis(N + 1, 1LL << 60);
        dis[start] = 0;
        vector<int> par(N + 1, -1);
        vector<int> par_edge(N + 1, -1);
        priority_queue<pair<ll, int>, vector<pair<ll, int>>, greater<pair<ll, int>>> pq;
        pq.push({0, start});
        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d > dis[u]) continue;
            for (auto [to, jdx, ew] : g[u]) {
                ll nd = dis[u] + ew;
                if (nd < dis[to]) {
                    dis[to] = nd;
                    par[to] = u;
                    par_edge[to] = jdx;
                    pq.push({nd, to});
                }
            }
        }
        if (dis[goal] >= (1LL << 60)) return {};
        set<int> path_edges;
        int cur = goal;
        while (cur != start) {
            int e = par_edge[cur];
            if (e == -1) break;
            path_edges.insert(e);
            cur = par[cur];
        }
        return path_edges;
    };
    set<int> used_B;
    for (auto [s, t] : mst_pairs) {
        auto ped = get_path_edges(s, t);
        for (int e : ped) {
            used_B.insert(e);
        }
    }
    // Output
    for (int i = 1; i <= N; i++) {
        if (i > 1) cout << " ";
        cout << Power[i];
    }
    cout << endl;
    for (int j = 1; j <= M; j++) {
        if (j > 1) cout << " ";
        cout << (used_B.count(j) ? 1 : 0);
    }
    cout << endl;
    return 0;
}