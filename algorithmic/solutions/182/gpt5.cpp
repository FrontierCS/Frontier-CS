#include <bits/stdc++.h>
using namespace std;

static inline uint64_t now_ms() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

vector<char> greedy_edge_cover(int N, const vector<int>& eu, const vector<int>& ev,
                               const vector<vector<int>>& incEdges, mt19937& rng) {
    int M = (int)eu.size();
    vector<int> deg(N + 1, 0);
    for (int v = 1; v <= N; ++v) deg[v] = (int)incEdges[v].size();
    vector<char> covered(M, 0);
    vector<char> inS(N + 1, 0);

    for (int e = 0; e < M; ++e) {
        if (covered[e]) continue;
        int u = eu[e], v = ev[e];
        int du = deg[u], dv = deg[v];
        int w;
        if (du > dv) w = u;
        else if (dv > du) w = v;
        else w = (rng() & 1) ? u : v;

        if (!inS[w]) inS[w] = 1;
        for (int f : incEdges[w]) {
            if (!covered[f]) {
                covered[f] = 1;
                int other = eu[f] ^ ev[f] ^ w;
                if (deg[other] > 0) --deg[other];
            }
        }
        deg[w] = 0;
    }
    return inS;
}

vector<char> mis_cover_from_order(int N, const vector<int>& eu, const vector<int>& ev,
                                  const vector<vector<int>>& incEdges, const vector<int>& order) {
    vector<char> blocked(N + 1, 0), inI(N + 1, 0);
    for (int v : order) {
        if (!blocked[v]) {
            inI[v] = 1;
            blocked[v] = 1;
            for (int e : incEdges[v]) {
                int other = eu[e] ^ ev[e] ^ v;
                blocked[other] = 1;
            }
        }
    }
    vector<char> inS(N + 1, 0);
    for (int v = 1; v <= N; ++v) inS[v] = !inI[v];
    return inS;
}

int cover_size(const vector<char>& inS) {
    int K = 0;
    for (size_t i = 1; i < inS.size(); ++i) if (inS[i]) ++K;
    return K;
}

bool is_valid_cover(const vector<char>& inS, const vector<int>& eu, const vector<int>& ev) {
    int M = (int)eu.size();
    for (int i = 0; i < M; ++i) {
        if (!(inS[eu[i]] || inS[ev[i]])) return false;
    }
    return true;
}

void prune_cover(vector<char>& inS, const vector<int>& eu, const vector<int>& ev,
                 const vector<vector<int>>& incEdges) {
    int N = (int)inS.size() - 1;
    for (int v = 1; v <= N; ++v) {
        if (!inS[v]) continue;
        bool removable = true;
        for (int e : incEdges[v]) {
            int other = eu[e] ^ ev[e] ^ v;
            if (!inS[other]) { removable = false; break; }
        }
        if (removable) inS[v] = 0;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N; int M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<pair<int,int>> edges;
    edges.reserve(M);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        edges.emplace_back(u, v);
    }

    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    M = (int)edges.size();

    vector<int> eu(M), ev(M);
    for (int i = 0; i < M; ++i) {
        eu[i] = edges[i].first;
        ev[i] = edges[i].second;
    }

    vector<vector<int>> incEdges(N + 1);
    for (int i = 0; i < M; ++i) {
        incEdges[eu[i]].push_back(i);
        incEdges[ev[i]].push_back(i);
    }

    vector<int> deg0(N + 1, 0);
    for (int v = 1; v <= N; ++v) deg0[v] = (int)incEdges[v].size();

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    uint64_t start_ms = now_ms();
    uint64_t time_limit_ms = 1800; // time budget
    uint64_t deadline = start_ms + time_limit_ms;

    vector<char> best(N + 1, 1);
    int bestK = N;

    // Heuristic 1: Greedy edge-based
    {
        vector<char> sol = greedy_edge_cover(N, eu, ev, incEdges, rng);
        int K = cover_size(sol);
        if (K < bestK) {
            bestK = K;
            best = move(sol);
        }
    }

    // Heuristic 2: MIS with ascending initial degree order
    {
        vector<int> order(N);
        iota(order.begin(), order.end(), 1);
        vector<uint32_t> key(N + 1);
        for (int v = 1; v <= N; ++v) key[v] = rng();
        sort(order.begin(), order.end(), [&](int a, int b){
            if (deg0[a] != deg0[b]) return deg0[a] < deg0[b];
            return key[a] < key[b];
        });
        vector<char> sol = mis_cover_from_order(N, eu, ev, incEdges, order);
        int K = cover_size(sol);
        if (K < bestK) {
            bestK = K;
            best = move(sol);
        }
    }

    // Heuristic 3: Multiple MIS random restarts within time budget
    while (now_ms() + 30 < deadline) {
        vector<int> order(N);
        iota(order.begin(), order.end(), 1);
        shuffle(order.begin(), order.end(), rng);
        vector<char> sol = mis_cover_from_order(N, eu, ev, incEdges, order);
        int K = cover_size(sol);
        if (K < bestK) {
            bestK = K;
            best = move(sol);
        }
    }

    // Final prune
    prune_cover(best, eu, ev, incEdges);
    // Safety check: if (somehow invalid) fix by adding endpoints of uncovered edges
    if (!is_valid_cover(best, eu, ev)) {
        for (int i = 0; i < M; ++i) {
            int u = eu[i], v = ev[i];
            if (!(best[u] || best[v])) {
                // add the higher degree endpoint
                if (deg0[u] >= deg0[v]) best[u] = 1; else best[v] = 1;
            }
        }
    }

    // Output
    for (int i = 1; i <= N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}