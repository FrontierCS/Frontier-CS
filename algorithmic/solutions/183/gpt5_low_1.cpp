#include <bits/stdc++.h>
using namespace std;

static vector<vector<int>> adj;
int N, M;

vector<char> mis_min_degree() {
    vector<int> remdeg(N, 0);
    for (int i = 0; i < N; ++i) remdeg[i] = (int)adj[i].size();

    vector<vector<int>> buckets(N + 1);
    for (int i = 0; i < N; ++i) buckets[remdeg[i]].push_back(i);

    vector<char> active(N, 1), inMIS(N, 0);
    int cur = 0;

    auto deactivate = [&](int u, auto&& deactivate_ref) -> void {
        if (!active[u]) return;
        active[u] = 0;
        for (int v : adj[u]) {
            if (active[v]) {
                int d = --remdeg[v];
                if (d < 0) d = 0; // safety against any unexpected issues
                buckets[d].push_back(v);
            }
        }
    };

    int remaining = N;
    while (remaining > 0) {
        while (cur <= N && (cur == N || buckets[cur].empty())) ++cur;
        if (cur > N) break;
        int u = buckets[cur].back();
        buckets[cur].pop_back();
        if (!active[u] || remdeg[u] != cur) continue;

        inMIS[u] = 1;
        deactivate(u, deactivate);
        --remaining;
        for (int v : adj[u]) {
            if (active[v]) {
                // deactivate neighbor v
                for (int w : adj[v]) {
                    if (active[w]) {
                        int d = --remdeg[w];
                        if (d < 0) d = 0;
                        buckets[d].push_back(w);
                    }
                }
                active[v] = 0;
                --remaining;
            }
        }
    }
    return inMIS;
}

vector<char> mis_random_order(uint64_t seed) {
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    std::mt19937_64 rng(seed);
    shuffle(order.begin(), order.end(), rng);

    vector<char> selected(N, 0), blocked(N, 0);
    for (int u : order) {
        if (!blocked[u]) {
            selected[u] = 1;
            for (int v : adj[u]) blocked[v] = 1;
        }
    }
    return selected;
}

vector<char> mis_degree_ascending() {
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (adj[a].size() != adj[b].size()) return adj[a].size() < adj[b].size();
        return a < b;
    });

    vector<char> selected(N, 0), blocked(N, 0);
    for (int u : order) {
        if (!blocked[u]) {
            selected[u] = 1;
            for (int v : adj[u]) blocked[v] = 1;
        }
    }
    return selected;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;
    adj.assign(N, {});
    adj.shrink_to_fit();
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 0; i < N; ++i) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
    }

    vector<char> best(N, 0);
    int bestK = -1;

    auto consider = [&](const vector<char>& sol) {
        int k = 0;
        for (char c : sol) if (c) ++k;
        if (k > bestK) {
            bestK = k;
            best = sol;
        }
    };

    consider(mis_min_degree());
    consider(mis_degree_ascending());

    uint64_t base_seed = chrono::steady_clock::now().time_since_epoch().count();
    int R = 5;
    for (int i = 0; i < R; ++i) {
        consider(mis_random_order(base_seed + i * 0x9e3779b97f4a7c15ULL));
    }

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}