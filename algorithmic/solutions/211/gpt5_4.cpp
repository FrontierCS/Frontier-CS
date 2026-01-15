#include <bits/stdc++.h>
using namespace std;

struct Device {
    int id;
    int x, y;
    char t;
};

static inline long long sqDist(int x1, int y1, int x2, int y2) {
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

    vector<Device> robots;
    robots.reserve(N);
    vector<Device> relays;
    relays.reserve(K);

    for (int i = 0; i < N + K; ++i) {
        int id, x, y;
        string ts;
        cin >> id >> x >> y >> ts;
        char t = ts.empty() ? 'R' : ts[0];
        if (t == 'C') {
            relays.push_back({id, x, y, t});
        } else {
            robots.push_back({id, x, y, t});
        }
    }

    int n = (int)robots.size();
    int k = (int)relays.size();

    if (n == 0) {
        cout << "#\n#\n";
        return 0;
    }

    // Precompute distances robot<->relay
    int Ttop = min(k, 30); // number of nearest relays to consider (heuristic)
    vector<int> drc;
    drc.resize((size_t)n * (size_t)k);
    if (k > 0) {
        for (int i = 0; i < n; ++i) {
            int xi = robots[i].x, yi = robots[i].y;
            for (int c = 0; c < k; ++c) {
                drc[(size_t)i * k + c] = (int)sqDist(xi, yi, relays[c].x, relays[c].y);
            }
        }
    }

    // For each robot, keep Ttop nearest relays (index and distance)
    vector<vector<pair<int,int>>> topCIdx; // per robot: (relayIndex, dist)
    if (k > 0 && Ttop > 0) {
        topCIdx.assign(n, {});
        for (int i = 0; i < n; ++i) {
            auto &top = topCIdx[i];
            top.reserve(Ttop);
            int maxIdx = -1;
            int maxDist = -1;
            for (int c = 0; c < k; ++c) {
                int d = drc[(size_t)i * k + c];
                if ((int)top.size() < Ttop) {
                    top.emplace_back(c, d);
                    if (d > maxDist) {
                        maxDist = d;
                        maxIdx = (int)top.size() - 1;
                    }
                } else if (d < top[maxIdx].second) {
                    top[maxIdx] = {c, d};
                    // recompute max
                    maxDist = -1;
                    maxIdx = -1;
                    for (int idx = 0; idx < Ttop; ++idx) {
                        if (top[idx].second > maxDist) {
                            maxDist = top[idx].second;
                            maxIdx = idx;
                        }
                    }
                }
            }
        }
    }

    // Prim's algorithm on robots using edge weight = min(direct, via best relay from top sets)
    const double INF = numeric_limits<double>::infinity();
    vector<double> key(n, INF);
    vector<int> parent(n, -1);
    vector<int> bestC(n, -1); // chosen relay index for connection, -1 for direct
    vector<char> inMST(n, 0);

    key[0] = 0.0;
    for (int it = 0; it < n; ++it) {
        int u = -1;
        double best = INF;
        for (int i = 0; i < n; ++i) {
            if (!inMST[i] && key[i] < best) {
                best = key[i];
                u = i;
            }
        }
        if (u == -1) break; // should not happen
        inMST[u] = 1;

        for (int v = 0; v < n; ++v) {
            if (inMST[v]) continue;

            long long D = sqDist(robots[u].x, robots[u].y, robots[v].x, robots[v].y);
            double factor = (robots[u].t == 'S' || robots[v].t == 'S') ? 0.8 : 1.0;
            double wDirect = (double)D * factor;

            double w = wDirect;
            int chosenC = -1;

            if (k > 0 && Ttop > 0) {
                double minVia = INF;
                // consider v's top relays
                const auto &topV = topCIdx[v];
                for (const auto &p : topV) {
                    int c = p.first;
                    int dv = p.second;
                    int du = drc[(size_t)u * k + c];
                    double cand = (double)dv + (double)du;
                    if (cand < minVia) {
                        minVia = cand;
                        chosenC = c;
                    }
                }
                // also consider u's top relays
                const auto &topU = topCIdx[u];
                for (const auto &p : topU) {
                    int c = p.first;
                    int du = p.second;
                    int dv = drc[(size_t)v * k + c];
                    double cand = (double)dv + (double)du;
                    if (cand < minVia) {
                        minVia = cand;
                        chosenC = c;
                    }
                }
                if (minVia < w) {
                    w = minVia;
                } else {
                    chosenC = -1; // prefer direct if tie or direct better
                }
            }

            if (w < key[v]) {
                key[v] = w;
                parent[v] = u;
                bestC[v] = chosenC;
            }
        }
    }

    // Build output edges and selected relays
    vector<char> usedRelay(k, 0);
    struct Edge { int a, b; };
    vector<Edge> edges;
    edges.reserve(2 * (size_t)(n - 1));

    auto add_edge = [&](int ida, int idb, unordered_set<unsigned long long> &seen) {
        int a = ida, b = idb;
        if (a > b) swap(a, b);
        unsigned long long keyh = ( (unsigned long long)(uint32_t)a << 32 ) ^ (uint32_t)b;
        if (seen.insert(keyh).second) {
            edges.push_back({a, b});
        }
    };

    unordered_set<unsigned long long> seen;
    seen.reserve((size_t)(n * 2));

    for (int v = 1; v < n; ++v) {
        if (parent[v] == -1) continue;
        int u = parent[v];
        if (bestC[v] == -1) {
            add_edge(robots[v].id, robots[u].id, seen);
        } else {
            int cidx = bestC[v];
            usedRelay[cidx] = 1;
            add_edge(robots[v].id, relays[cidx].id, seen);
            add_edge(robots[u].id, relays[cidx].id, seen);
        }
    }

    // Prepare output
    vector<int> selectedRelays;
    for (int i = 0; i < k; ++i) if (usedRelay[i]) selectedRelays.push_back(relays[i].id);
    sort(selectedRelays.begin(), selectedRelays.end());
    sort(edges.begin(), edges.end(), [](const Edge &e1, const Edge &e2){
        if (e1.a != e2.a) return e1.a < e2.a;
        return e1.b < e2.b;
    });

    if (selectedRelays.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < selectedRelays.size(); ++i) {
            if (i) cout << "#";
            cout << selectedRelays[i];
        }
        cout << "\n";
    }

    if (edges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < edges.size(); ++i) {
            if (i) cout << "#";
            cout << edges[i].a << "-" << edges[i].b;
        }
        cout << "\n";
    }

    return 0;
}