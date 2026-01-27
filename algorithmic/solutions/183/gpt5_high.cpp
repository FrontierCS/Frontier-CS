#include <bits/stdc++.h>
using namespace std;

static inline uint64_t time_now_ns() {
    using namespace std::chrono;
    return duration_cast<nanoseconds>(steady_clock::now().time_since_epoch()).count();
}

vector<char> greedy_min_degree(const vector<vector<int>>& adj, mt19937 &rng) {
    int N = (int)adj.size();
    vector<int> deg(N);
    int maxDeg = 0;
    for (int i = 0; i < N; ++i) {
        deg[i] = (int)adj[i].size();
        if (deg[i] > maxDeg) maxDeg = deg[i];
    }
    vector<vector<int>> bucket(maxDeg + 1);
    vector<int> pos(N, -1);
    vector<char> alive(N, 1), in_set(N, 0);
    for (int i = 0; i < N; ++i) {
        pos[i] = (int)bucket[deg[i]].size();
        bucket[deg[i]].push_back(i);
    }
    int curMin = 0;
    int aliveCount = N;

    auto removeVertex = [&](int x) {
        if (!alive[x]) return;
        alive[x] = 0;
        --aliveCount;
        int bx = deg[x];
        if (bx < 0) bx = 0; // safety
        if (pos[x] != -1) {
            int p = pos[x];
            int last = bucket[bx].back();
            bucket[bx][p] = last;
            pos[last] = p;
            bucket[bx].pop_back();
            pos[x] = -1;
        }
        for (int y : adj[x]) {
            if (alive[y]) {
                int oldd = deg[y];
                if (oldd < 1) continue; // safety for any anomalies
                int py = pos[y];
                int last2 = bucket[oldd].back();
                bucket[oldd][py] = last2;
                pos[last2] = py;
                bucket[oldd].pop_back();
                deg[y] = oldd - 1;
                pos[y] = (int)bucket[oldd - 1].size();
                bucket[oldd - 1].push_back(y);
                if (oldd - 1 < curMin) curMin = oldd - 1;
            }
        }
    };

    while (aliveCount > 0) {
        while (curMin <= maxDeg && bucket[curMin].empty()) ++curMin;
        if (curMin > maxDeg) break;
        int sz = (int)bucket[curMin].size();
        if (sz == 0) continue;
        int idx = (int)(rng() % sz);
        int u = bucket[curMin][idx];
        if (!alive[u]) continue;
        in_set[u] = 1;
        removeVertex(u);
        for (int v : adj[u]) if (alive[v]) removeVertex(v);
    }
    return in_set;
}

vector<char> greedy_random_order(const vector<vector<int>>& adj, mt19937 &rng) {
    int N = (int)adj.size();
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
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

bool improve_12_swap(vector<char>& selected, const vector<vector<int>>& adj, mt19937& rng, const chrono::steady_clock::time_point& deadline) {
    int N = (int)adj.size();
    if (chrono::steady_clock::now() > deadline) return false;

    vector<int> cc(N, 0);
    vector<int> owner(N, -2);
    vector<vector<int>> priv(N);
    vector<int> selList;
    selList.reserve(N);

    for (int i = 0; i < N; ++i) if (selected[i]) selList.push_back(i);

    for (int s : selList) {
        for (int t : adj[s]) {
            if (!selected[t]) {
                int c = ++cc[t];
                if (c == 1) owner[t] = s;
                else owner[t] = -1;
            }
        }
    }

    for (int t = 0; t < N; ++t) {
        if (!selected[t] && cc[t] == 1) {
            int o = owner[t];
            if (o >= 0) priv[o].push_back(t);
        }
    }

    static vector<int> mark;
    static int token = 1;
    if ((int)mark.size() != N) mark.assign(N, 0);

    shuffle(selList.begin(), selList.end(), rng);

    for (int w : selList) {
        if (chrono::steady_clock::now() > deadline) return false;
        auto &L = priv[w];
        if ((int)L.size() < 2) continue;

        // Choose u1 with minimal degree for faster check
        int u1 = -1, mind = INT_MAX;
        for (int x : L) {
            int d = (int)adj[x].size();
            if (d < mind) {
                mind = d;
                u1 = x;
            }
        }
        if (u1 == -1) continue;

        ++token;
        if (token == 0) { // handle overflow
            token = 1;
            fill(mark.begin(), mark.end(), 0);
        }
        for (int x : adj[u1]) mark[x] = token;
        mark[u1] = token;

        int u2 = -1;
        for (int x : L) {
            if (x != u1 && mark[x] != token) {
                u2 = x;
                break;
            }
        }
        if (u2 == -1) continue;

        // Perform 1-2 swap: remove w, add u1 and u2, then fill zeros
        auto removeFromSel = [&](int v) {
            if (!selected[v]) return;
            selected[v] = 0;
            for (int x : adj[v]) {
                if (!selected[x]) {
                    cc[x]--;
                }
            }
        };
        auto addToSel = [&](int u) {
            if (selected[u]) return;
            if (cc[u] != 0) return; // safety
            selected[u] = 1;
            for (int x : adj[u]) {
                if (!selected[x]) {
                    cc[x]++;
                }
            }
        };

        removeFromSel(w);
        // Now u1 and u2 should have cc == 0 (they had owner w)
        addToSel(u1);
        addToSel(u2);

        // Fill all zero-conflict vertices to reach maximality
        vector<int> q;
        q.reserve(N);
        for (int i = 0; i < N; ++i) {
            if (!selected[i] && cc[i] == 0) q.push_back(i);
        }
        for (size_t i = 0; i < q.size(); ++i) {
            int a = q[i];
            if (selected[a] || cc[a] != 0) continue;
            selected[a] = 1;
            for (int t : adj[a]) {
                if (!selected[t]) {
                    int prev = cc[t];
                    cc[t] = prev + 1;
                }
            }
        }

        return true; // improved
    }

    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
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
        auto &v = adj[i];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
    }

    uint64_t seed = time_now_ns() ^ (uint64_t)(uintptr_t)&seed;
    mt19937 rng((uint32_t)seed);

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1900);

    vector<char> bestSel(N, 0);
    int bestK = 0;

    int iter = 0;
    while (chrono::steady_clock::now() < deadline) {
        vector<char> curr;
        if ((rng() & 1u) == 0u) {
            curr = greedy_min_degree(adj, rng);
        } else {
            curr = greedy_random_order(adj, rng);
        }

        // Try a few 1-2 swap improvements
        int tries = 0;
        while (tries < 3 && chrono::steady_clock::now() < deadline) {
            bool improved = improve_12_swap(curr, adj, rng, deadline);
            if (!improved) break;
            ++tries;
        }

        int k = 0;
        for (char c : curr) if (c) ++k;
        if (k > bestK) {
            bestK = k;
            bestSel = move(curr);
        }
        ++iter;
        if (iter > 1000) break; // safety upper bound
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }
    return 0;
}