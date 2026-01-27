#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1024;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector< bitset<MAXN> > adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].count();

    // Build neighbor lists from adjacency bitsets (avoid duplicates)
    vector<vector<int>> g(N);
    for (int i = 0; i < N; ++i) {
        g[i].reserve(deg[i]);
        for (int j = 0; j < N; ++j) {
            if (adj[i].test(j)) g[i].push_back(j);
        }
    }

    auto greedyByOrder = [&](const vector<int>& order) {
        bitset<MAXN> F; // forbidden (selected and neighbors of selected)
        bitset<MAXN> S; // selected independent set
        for (int v : order) {
            if (!F.test(v)) {
                S.set(v);
                F |= adj[v];
                F.set(v);
            }
        }
        return S;
    };

    auto computeSize = [&](const bitset<MAXN>& S) -> int {
        return (int)S.count();
    };

    auto start = chrono::steady_clock::now();
    auto elapsed = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Initial orders and greedy runs
    vector<int> baseOrder(N);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    sort(baseOrder.begin(), baseOrder.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    bitset<MAXN> bestS = greedyByOrder(baseOrder);
    int bestSize = computeSize(bestS);

    double time_limit_total = 1.95;  // hard cap within 2s
    double time_limit_initial = 1.20; // time for multiple greedy attempts

    // Try random variations
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    // First, also try reversed degree order to diversify
    vector<int> revOrder = baseOrder;
    reverse(revOrder.begin(), revOrder.end());
    {
        bitset<MAXN> S = greedyByOrder(revOrder);
        int sz = computeSize(S);
        if (sz > bestSize) {
            bestSize = sz;
            bestS = S;
        }
    }

    while (elapsed() < time_limit_initial) {
        // Randomize order: with probability 1/2, sort by (deg, rand), else pure shuffle
        uniform_int_distribution<int> coin(0, 1);
        if (coin(rng) == 0) {
            vector<pair<pair<int, uint64_t>, int>> tmp;
            tmp.reserve(N);
            for (int i = 0; i < N; ++i) {
                uint64_t r = rng();
                tmp.push_back({{deg[i], r}, i});
            }
            sort(tmp.begin(), tmp.end(), [&](auto &x, auto &y){
                if (x.first.first != y.first.first) return x.first.first < y.first.first;
                return x.first.second < y.first.second;
            });
            for (int i = 0; i < N; ++i) order[i] = tmp[i].second;
        } else {
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
        }

        bitset<MAXN> S = greedyByOrder(order);
        int sz = computeSize(S);
        if (sz > bestSize) {
            bestSize = sz;
            bestS = S;
        }
    }

    // Improvement heuristic: 1-2 swap with greedy fill of zero-neighbor vertices
    auto improve_two_for_one = [&](bitset<MAXN>& S, double time_cap) {
        vector<int> cnt(N, 0);
        for (int v = 0; v < N; ++v) {
            cnt[v] = (int)(adj[v] & S).count();
        }

        vector<int> S_nodes;
        S_nodes.reserve(N);

        while (elapsed() < time_cap) {
            bool improved = false;
            S_nodes.clear();
            for (int i = 0; i < N; ++i) if (S.test(i)) S_nodes.push_back(i);
            shuffle(S_nodes.begin(), S_nodes.end(), rng);

            for (int u : S_nodes) {
                if (elapsed() >= time_cap) break;

                // Collect candidates v not in S with cnt[v]==1 and adj[u][v]==1
                vector<int> cand;
                cand.reserve(g[u].size());
                for (int v = 0; v < N; ++v) {
                    if (!S.test(v) && cnt[v] == 1 && adj[u].test(v)) {
                        cand.push_back(v);
                    }
                }
                if ((int)cand.size() < 2) continue;

                shuffle(cand.begin(), cand.end(), rng);

                bool found = false;
                int a = -1, b = -1;
                for (int i = 0; i < (int)cand.size() && !found; ++i) {
                    int x = cand[i];
                    for (int j = i + 1; j < (int)cand.size(); ++j) {
                        int y = cand[j];
                        if (!adj[x].test(y)) {
                            a = x; b = y; found = true; break;
                        }
                    }
                }
                if (!found) continue;

                // Perform swap: remove u, add a and b
                S.reset(u);
                S.set(a);
                S.set(b);

                // Update cnt for neighbors
                for (int w : g[u]) cnt[w]--;
                for (int w : g[a]) cnt[w]++;
                for (int w : g[b]) cnt[w]++;

                // Greedily add any now-free vertices (cnt==0)
                bool added = true;
                while (added && elapsed() < time_cap) {
                    added = false;
                    for (int v = 0; v < N; ++v) {
                        if (!S.test(v) && cnt[v] == 0) {
                            S.set(v);
                            for (int w : g[v]) cnt[w]++;
                            added = true;
                        }
                    }
                }

                improved = true;
                break; // restart while-loop to recompute order of S nodes
            }

            if (!improved) break;
        }
    };

    improve_two_for_one(bestS, time_limit_total);

    // Output result: one line per vertex: 1 if selected, 0 otherwise
    for (int i = 0; i < N; ++i) {
        cout << (bestS.test(i) ? 1 : 0) << '\n';
    }

    return 0;
}