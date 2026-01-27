#include <bits/stdc++.h>
using namespace std;

struct Device {
    long long id;
    int x, y;
    char type; // 'R', 'S', 'C'
};

struct Robot {
    long long id;
    int x, y;
    bool isS;
};

struct Relay {
    long long id;
    int x, y;
};

static inline long long sqdist(int x1, int y1, int x2, int y2) {
    long long dx = (long long)x1 - x2;
    long long dy = (long long)y1 - y2;
    return dx*dx + dy*dy;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<Robot> robots;
    robots.reserve(N);
    vector<Relay> relays;
    relays.reserve(K);

    for (int i = 0; i < N + K; ++i) {
        long long id;
        int x, y;
        char t;
        cin >> id >> x >> y >> t;
        if (t == 'R' || t == 'S') {
            Robot r;
            r.id = id;
            r.x = x;
            r.y = y;
            r.isS = (t == 'S');
            robots.push_back(r);
        } else if (t == 'C') {
            Relay c;
            c.id = id;
            c.x = x;
            c.y = y;
            relays.push_back(c);
        }
    }

    // Ensure we have exactly N robots and K relays as per first line
    // If input mismatched, adjust N and K to sizes read
    if ((int)robots.size() != N) N = (int)robots.size();
    if ((int)relays.size() != K) K = (int)relays.size();

    const long long INF = (1LL<<62);

    // Precompute costs from robots to relays: cost = 5 * squared distance
    vector<long long> costRtoC; // size N*K, row-major [r*K + c]
    if (K > 0) {
        costRtoC.assign((size_t)N * (size_t)K, 0);
        for (int i = 0; i < N; ++i) {
            const Robot &ri = robots[i];
            for (int c = 0; c < K; ++c) {
                const Relay &rc = relays[c];
                long long d2 = sqdist(ri.x, ri.y, rc.x, rc.y);
                costRtoC[(size_t)i * (size_t)K + (size_t)c] = d2 * 5; // scaled by 5
            }
        }
    }

    // Build top T relays for each robot to approximate min over relays
    int T = 0;
    if (K > 0) {
        if (K <= 100) T = K;
        else if (K <= 600) T = 50;
        else T = 40;
    }
    vector<vector<int>> topCIdx(N);
    if (K > 0 && T > 0) {
        for (int i = 0; i < N; ++i) {
            // maintain a max-heap of size up to T by (cost, idx)
            struct Entry { long long cost; int idx; };
            auto cmp = [](const Entry& a, const Entry& b){ return a.cost < b.cost; }; // for max-heap using priority_queue default max
            // Actually default priority_queue is max-heap by comparator <. We need max by cost, so use custom struct with operator< reversed or comparator greater.
            // We'll use priority_queue<Entry, vector<Entry>, function<bool(const Entry&, const Entry&)>> with comparator that returns a.cost < b.cost means a has lower priority -> not desired
            // Better: use priority_queue with comparator that makes larger cost come first:
            struct Cmp {
                bool operator()(const Entry& a, const Entry& b) const {
                    return a.cost < b.cost; // larger cost has higher priority (top)
                }
            };
            priority_queue<Entry, vector<Entry>, Cmp> pq;
            for (int c = 0; c < K; ++c) {
                long long w = costRtoC[(size_t)i * (size_t)K + (size_t)c];
                if ((int)pq.size() < T) {
                    pq.push({w, c});
                } else if (!pq.empty() && w < pq.top().cost) {
                    pq.pop();
                    pq.push({w, c});
                }
            }
            topCIdx[i].reserve(pq.size());
            while (!pq.empty()) {
                topCIdx[i].push_back(pq.top().idx);
                pq.pop();
            }
            // order not necessary
        }
    }

    // Prim's algorithm on robots only with edge weights w'(i,j) = min(direct(i,j), min_c cost(i,c)+cost(j,c) over top relays)
    vector<long long> dist(N, INF);
    vector<int> parent(N, -1);
    vector<char> viaC(N, 0); // 1 if edge realized via relay
    vector<int> viaCidx(N, -1);
    vector<char> used(N, 0);

    auto direct_cost = [&](int i, int j)->long long {
        const Robot &a = robots[i];
        const Robot &b = robots[j];
        long long d2 = sqdist(a.x, a.y, b.x, b.y);
        int coeff = (a.isS || b.isS) ? 4 : 5;
        return d2 * coeff;
    };

    dist[0] = 0;
    for (int it = 0; it < N; ++it) {
        int u = -1;
        long long best = INF;
        for (int v = 0; v < N; ++v) {
            if (!used[v] && dist[v] < best) {
                best = dist[v];
                u = v;
            }
        }
        if (u == -1) break; // disconnected should not happen
        used[u] = 1;
        for (int v = 0; v < N; ++v) {
            if (used[v]) continue;
            long long dcost = direct_cost(u, v);
            long long minVia = INF;
            int bestC = -1;
            if (K > 0 && T > 0) {
                // scan union of topCIdx[u] and topCIdx[v]
                const auto &Lu = topCIdx[u];
                const auto &Lv = topCIdx[v];
                // scan Lu
                for (int idx = 0; idx < (int)Lu.size(); ++idx) {
                    int c = Lu[idx];
                    long long w = costRtoC[(size_t)u * (size_t)K + (size_t)c] + costRtoC[(size_t)v * (size_t)K + (size_t)c];
                    if (w < minVia) { minVia = w; bestC = c; }
                }
                // scan Lv
                for (int idx = 0; idx < (int)Lv.size(); ++idx) {
                    int c = Lv[idx];
                    long long w = costRtoC[(size_t)u * (size_t)K + (size_t)c] + costRtoC[(size_t)v * (size_t)K + (size_t)c];
                    if (w < minVia) { minVia = w; bestC = c; }
                }
            }
            long long newCost = dcost;
            char newVia = 0;
            int newCidx = -1;
            if (minVia < newCost) {
                newCost = minVia;
                newVia = 1;
                newCidx = bestC;
            }
            if (newCost < dist[v]) {
                dist[v] = newCost;
                parent[v] = u;
                viaC[v] = newVia;
                viaCidx[v] = newCidx;
            }
        }
    }

    // Build edges and selected relays
    vector<char> relayUsed(K, 0);
    vector<pair<long long, long long>> edges;
    edges.reserve(2 * max(0, N - 1));

    auto add_edge = [&](long long a, long long b) {
        if (a > b) swap(a, b);
        edges.emplace_back(a, b);
    };

    for (int v = 1; v < N; ++v) {
        int u = parent[v];
        if (u < 0) continue; // should not
        if (viaC[v] && viaCidx[v] >= 0) {
            int c = viaCidx[v];
            relayUsed[c] = 1;
            add_edge(robots[v].id, relays[c].id);
            add_edge(robots[u].id, relays[c].id);
        } else {
            add_edge(robots[v].id, robots[u].id);
        }
    }

    // Deduplicate edges
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());

    // Prepare selected relay IDs
    vector<long long> chosenRelays;
    for (int c = 0; c < K; ++c) if (relayUsed[c]) chosenRelays.push_back(relays[c].id);
    sort(chosenRelays.begin(), chosenRelays.end());

    // Output
    if (chosenRelays.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < chosenRelays.size(); ++i) {
            if (i) cout << "#";
            cout << chosenRelays[i];
        }
        cout << "\n";
    }

    if (edges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < edges.size(); ++i) {
            if (i) cout << "#";
            cout << edges[i].first << "-" << edges[i].second;
        }
        cout << "\n";
    }

    return 0;
}