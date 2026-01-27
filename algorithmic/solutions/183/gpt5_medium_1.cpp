#include <bits/stdc++.h>
using namespace std;

struct FastRand {
    uint64_t x;
    FastRand(uint64_t seed) : x(seed) {}
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint64_t operator()() { return next(); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    int M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<vector<int>> adj(N);
    adj.reserve(N);
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

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    // Initial greedy maximal independent set: order by static degree ascending with random tiebreak
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    FastRand rng(seed);

    vector<uint64_t> rkeys(N);
    for (int i = 0; i < N; ++i) rkeys[i] = rng();

    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return rkeys[a] < rkeys[b];
    });

    vector<char> inS(N, 0), blocked(N, 0);
    for (int v : order) {
        if (!blocked[v]) {
            inS[v] = 1;
            blocked[v] = 1;
            for (int u : adj[v]) blocked[u] = 1;
        }
    }

    // Local search with 0-additions and 1-swaps
    vector<int> conf(N, 0);
    vector<int> sup(N, -1); // unique neighbor in S when conf==1
    for (int v = 0; v < N; ++v) {
        if (inS[v]) {
            for (int u : adj[v]) {
                if (!inS[u]) {
                    int c = ++conf[u];
                    if (c == 1) sup[u] = v;
                    else sup[u] = -1;
                }
            }
        }
    }

    vector<int> q0, q1;
    q0.reserve(N);
    q1.reserve(N);
    for (int u = 0; u < N; ++u) {
        if (!inS[u]) {
            if (conf[u] == 0) q0.push_back(u);
            else if (conf[u] == 1) q1.push_back(u);
        }
    }

    auto time_start = chrono::steady_clock::now();
    auto time_limit = chrono::milliseconds(1900);

    auto now = [&](){ return chrono::steady_clock::now(); };
    auto elapsed = [&](){ return chrono::duration_cast<chrono::milliseconds>(now() - time_start); };

    auto addToS = [&](int u) {
        inS[u] = 1;
        for (int w : adj[u]) {
            if (!inS[w]) {
                int old = conf[w];
                conf[w] = old + 1;
                if (conf[w] == 1) {
                    sup[w] = u;
                    q1.push_back(w);
                } else if (conf[w] == 2) {
                    sup[w] = -1;
                }
            }
        }
    };
    auto removeFromS = [&](int v) {
        inS[v] = 0;
        for (int w : adj[v]) {
            if (!inS[w]) {
                int old = conf[w];
                conf[w] = old - 1;
                if (conf[w] == 0) {
                    sup[w] = -1;
                    q0.push_back(w);
                } else if (conf[w] == 1) {
                    int last = -1;
                    for (int t : adj[w]) {
                        if (inS[t]) { last = t; break; }
                    }
                    sup[w] = last;
                    q1.push_back(w);
                }
            }
        }
    };

    while (elapsed() < time_limit) {
        bool progressed = false;
        // Add all currently free vertices
        while (!q0.empty() && elapsed() < time_limit) {
            int u = q0.back(); q0.pop_back();
            if (u < 0 || u >= N) continue;
            if (inS[u]) continue;
            if (conf[u] != 0) continue;
            addToS(u);
            progressed = true;
        }
        if (progressed) continue;

        // Try a swap using a vertex with exactly one conflict
        bool swapped = false;
        while (!q1.empty() && elapsed() < time_limit) {
            int u = q1.back(); q1.pop_back();
            if (u < 0 || u >= N) continue;
            if (inS[u]) continue;

            if (conf[u] == 0) { q0.push_back(u); continue; }
            if (conf[u] != 1) continue;

            int v = sup[u];
            if (v == -1 || !inS[v]) {
                // recompute
                int cnt = 0, lastv = -1;
                for (int w : adj[u]) {
                    if (inS[w]) { cnt++; lastv = w; if (cnt > 1) break; }
                }
                if (cnt == 0) {
                    conf[u] = 0; sup[u] = -1; q0.push_back(u);
                    continue;
                } else if (cnt > 1) {
                    conf[u] = cnt; sup[u] = -1;
                    continue;
                } else {
                    conf[u] = 1; sup[u] = lastv; v = lastv;
                }
            }
            // Perform swap: remove v from S, add u
            removeFromS(v);
            addToS(u);
            swapped = true;
            progressed = true;
            break;
        }
        if (!swapped) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << (inS[i] ? 1 : 0) << '\n';
    }
    return 0;
}