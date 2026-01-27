#include <bits/stdc++.h>
using namespace std;

using Graph = vector<vector<int>>;

static inline int countSet(const vector<char>& inSet) {
    int cnt = 0;
    for (char c : inSet) if (c) ++cnt;
    return cnt;
}

static vector<int> degeneracy_order_minheap(const Graph& g) {
    int N = (int)g.size();
    vector<int> degAlive(N);
    vector<char> alive(N, 1);
    for (int i = 0; i < N; ++i) degAlive[i] = (int)g[i].size();
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;
    for (int i = 0; i < N; ++i) pq.emplace(degAlive[i], i);
    vector<int> order;
    order.reserve(N);
    while (!pq.empty()) {
        auto [d, v] = pq.top(); pq.pop();
        if (!alive[v] || d != degAlive[v]) continue;
        alive[v] = 0;
        order.push_back(v);
        for (int u : g[v]) {
            if (alive[u]) {
                --degAlive[u];
                pq.emplace(degAlive[u], u);
            }
        }
    }
    return order;
}

static vector<char> greedy_from_order(const Graph& g, const vector<int>& order, bool reverse = false) {
    int N = (int)g.size();
    vector<char> inSet(N, 0);
    if (!reverse) {
        for (int v : order) {
            bool ok = true;
            for (int u : g[v]) {
                if (inSet[u]) { ok = false; break; }
            }
            if (ok) inSet[v] = 1;
        }
    } else {
        for (int i = (int)order.size() - 1; i >= 0; --i) {
            int v = order[i];
            bool ok = true;
            for (int u : g[v]) {
                if (inSet[u]) { ok = false; break; }
            }
            if (ok) inSet[v] = 1;
        }
    }
    return inSet;
}

static vector<char> greedy_static_degree(const Graph& g, mt19937& rng) {
    int N = (int)g.size();
    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();
    vector<uint32_t> rv(N);
    for (int i = 0; i < N; ++i) rv[i] = rng();
    stable_sort(ord.begin(), ord.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return rv[a] < rv[b];
    });
    return greedy_from_order(g, ord, false);
}

static void improve_one_two_swap(vector<char>& inSet, const Graph& g, int time_ms, mt19937& rng) {
    int N = (int)g.size();
    vector<int> cs(N, 0);
    for (int v = 0; v < N; ++v) if (inSet[v]) {
        for (int u : g[v]) cs[u]++;
    }
    vector<int> cover(N, -1);
    deque<int> ones;
    for (int v = 0; v < N; ++v) if (!inSet[v] && cs[v] == 1) {
        for (int u : g[v]) if (inSet[u]) { cover[v] = u; break; }
        if (cover[v] != -1) ones.push_back(v);
    }
    vector<int> mark(N, 0);
    int stamp = 1;
    auto startClock = chrono::steady_clock::now();

    auto elapsed_ms = [&](){
        return (int)chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - startClock).count();
    };

    auto addToSet = [&](int x) {
        if (inSet[x]) return;
        // assume safe: cs[x] == 0
        inSet[x] = true;
        for (int t : g[x]) {
            int before = cs[t];
            cs[t]++;
            if (cs[t] == 1) {
                cover[t] = x;
                if (!inSet[t]) ones.push_back(t);
            } else if (cs[t] == 2) {
                cover[t] = -1;
            }
        }
    };

    auto removeFromSet = [&](int u) {
        if (!inSet[u]) return;
        inSet[u] = false;
        for (int t : g[u]) {
            cs[t]--;
            if (cs[t] == 1) {
                int newCover = -1;
                for (int y : g[t]) if (inSet[y]) { newCover = y; break; }
                cover[t] = newCover;
                if (!inSet[t] && newCover != -1) ones.push_back(t);
            } else if (cs[t] == 0) {
                cover[t] = -1;
            }
        }
    };

    while (elapsed_ms() < time_ms) {
        bool improved = false;

        if (ones.empty()) {
            for (int v = 0; v < N; ++v) {
                if (!inSet[v] && cs[v] == 1) {
                    if (cover[v] == -1) {
                        for (int y : g[v]) if (inSet[y]) { cover[v] = y; break; }
                    }
                    if (cover[v] != -1) ones.push_back(v);
                }
            }
        }

        while (!ones.empty() && elapsed_ms() < time_ms) {
            int v = ones.back(); ones.pop_back();
            if (inSet[v] || cs[v] != 1) continue;
            int u = cover[v];
            if (u == -1 || !inSet[u]) {
                u = -1;
                for (int y : g[v]) if (inSet[y]) { u = y; break; }
                cover[v] = u;
                if (u == -1) continue;
            }

            stamp++;
            for (int a : g[v]) mark[a] = stamp;

            int foundW = -1;
            if (!g[u].empty()) {
                int startIdx = (int)(rng() % g[u].size());
                for (int k = 0; k < (int)g[u].size(); ++k) {
                    int w = g[u][(startIdx + k) % g[u].size()];
                    if (w == v) continue;
                    if (inSet[w]) continue;
                    if (cs[w] != 1) continue;
                    if (mark[w] == stamp) continue; // adjacent to v
                    foundW = w;
                    break;
                }
            }

            if (foundW != -1) {
                int w = foundW;
                // Perform swap: remove u, add v and w
                removeFromSet(u);
                addToSet(v);
                addToSet(w);

                // Greedy augmentation: neighbors of u that now have cs==0
                deque<int> zeros;
                for (int t : g[u]) {
                    if (!inSet[t] && cs[t] == 0) zeros.push_back(t);
                }
                while (!zeros.empty()) {
                    int t = zeros.back(); zeros.pop_back();
                    if (!inSet[t] && cs[t] == 0) {
                        addToSet(t);
                    }
                }

                improved = true;
                break;
            }
        }

        if (!improved) break;
    }

    // Final augmentation to ensure maximality: add any vertex with cs==0
    for (int v = 0; v < N; ++v) {
        if (!inSet[v] && cs[v] == 0) {
            addToSet(v);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    Graph g(N);
    g.reserve(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    // Deduplicate adjacency lists
    for (int i = 0; i < N; ++i) {
        auto& vec = g[i];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    // Initial sets: degeneracy-based and degree-ascending randomized
    vector<int> order = degeneracy_order_minheap(g);
    vector<char> set1 = greedy_from_order(g, order, true);

    vector<char> set2 = greedy_static_degree(g, rng);

    // Choose best
    vector<char>* best = &set1;
    if (countSet(set2) > countSet(set1)) best = &set2;

    // Improve best with 1-2 swap heuristic under time budget
    // Allow around 1200 ms for improvement
    improve_one_two_swap(*best, g, 1200, rng);

    // Output solution
    for (int i = 0; i < N; ++i) {
        cout << (int)(*best)[i] << '\n';
    }
    return 0;
}