#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 512;

struct Timer {
    chrono::steady_clock::time_point start, deadline;
    Timer(long long ms) {
        start = chrono::steady_clock::now();
        deadline = start + chrono::milliseconds(ms);
    }
    bool time_left(long long reserve_ms = 0) const {
        return chrono::steady_clock::now() + chrono::milliseconds(reserve_ms) < deadline;
    }
    bool expired() const {
        return chrono::steady_clock::now() >= deadline;
    }
};

int computeMaxColor(const vector<int>& color) {
    int mx = 0;
    for (int c : color) if (c > mx) mx = c;
    return mx;
}

vector<int> dsatur_coloring(const vector<vector<int>>& adj, const vector<int>& degree, mt19937 &rng, int bestK_so_far) {
    int N = (int)adj.size();
    vector<int> color(N, 0);
    vector<int> satCount(N, 0);
    vector< bitset<MAXC> > usedColors(N);
    for (int i = 0; i < N; ++i) usedColors[i].reset();

    // Choose initial vertex: highest degree (random tie)
    int maxDeg = -1;
    vector<int> ties;
    for (int i = 0; i < N; ++i) {
        if (degree[i] > maxDeg) {
            maxDeg = degree[i];
            ties.clear();
            ties.push_back(i);
        } else if (degree[i] == maxDeg) {
            ties.push_back(i);
        }
    }
    uniform_int_distribution<int> dist;
    int current = ties.size() == 1 ? ties[0] : ties[ uniform_int_distribution<int>(0, (int)ties.size()-1)(rng) ];

    int colored = 0;
    int currentK = 0;

    auto select_next = [&](void) -> int {
        int bestSat = -1, bestDeg = -1;
        vector<int> tie;
        for (int i = 0; i < N; ++i) {
            if (color[i] != 0) continue;
            int s = satCount[i];
            if (s > bestSat) {
                bestSat = s;
                bestDeg = degree[i];
                tie.clear();
                tie.push_back(i);
            } else if (s == bestSat) {
                if (degree[i] > bestDeg) {
                    bestDeg = degree[i];
                    tie.clear();
                    tie.push_back(i);
                } else if (degree[i] == bestDeg) {
                    tie.push_back(i);
                }
            }
        }
        if (tie.empty()) return -1;
        if (tie.size() == 1) return tie[0];
        return tie[ uniform_int_distribution<int>(0, (int)tie.size()-1)(rng) ];
    };

    while (colored < N) {
        // Assign smallest available color
        int chosenColor = 1;
        while (chosenColor <= currentK && usedColors[current].test(chosenColor)) ++chosenColor;
        if (chosenColor > currentK) currentK = chosenColor;
        color[current] = chosenColor;
        ++colored;

        // Early abort if cannot beat best
        if (bestK_so_far > 0 && currentK >= bestK_so_far) {
            // Return partial; caller will ignore due to worse K
            return color;
        }

        // Update neighbors
        for (int nb : adj[current]) {
            if (color[nb] == 0) {
                if (!usedColors[nb].test(chosenColor)) {
                    usedColors[nb].set(chosenColor);
                    ++satCount[nb];
                }
            }
        }

        if (colored == N) break;
        current = select_next();
        if (current == -1) {
            // Shouldn't happen; but if it does, assign remaining by trivial
            for (int i = 0; i < N; ++i) if (color[i] == 0) {
                bitset<MAXC> used;
                used.reset();
                for (int nb : adj[i]) if (color[nb] != 0) used.set(color[nb]);
                int c = 1;
                while (c <= currentK && used.test(c)) ++c;
                if (c > currentK) currentK = c;
                color[i] = c;
            }
            break;
        }
    }
    return color;
}

inline bitset<MAXC> neighbor_used_colors(const vector<vector<int>>& adj, const vector<int>& color, int v) {
    bitset<MAXC> used;
    used.reset();
    for (int nb : adj[v]) {
        int c = color[nb];
        if (c > 0 && c < MAXC) used.set(c);
    }
    return used;
}

bool greedy_lower_colors_once(vector<int>& color, const vector<vector<int>>& adj, int &K, mt19937 &rng, const Timer &timer) {
    int N = (int)color.size();
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);

    bool changed = false;
    for (int v : order) {
        if (!timer.time_left()) break;
        int oldc = color[v];
        if (oldc <= 1) continue;
        bitset<MAXC> used = neighbor_used_colors(adj, color, v);
        for (int c = 1; c < oldc; ++c) {
            if (!used.test(c)) {
                color[v] = c;
                changed = true;
                break;
            }
        }
    }
    if (changed) {
        int newK = computeMaxColor(color);
        if (newK < K) K = newK;
    }
    return changed;
}

bool attempt_remove_top_color_step(vector<int>& color, const vector<vector<int>>& adj, int &K, mt19937 &rng, const Timer &timer) {
    if (K <= 1) return false;
    int N = (int)color.size();
    vector<int> tops;
    tops.reserve(N);
    for (int i = 0; i < N; ++i) if (color[i] == K) tops.push_back(i);
    if (tops.empty()) {
        K = computeMaxColor(color);
        return false;
    }
    shuffle(tops.begin(), tops.end(), rng);

    for (int v : tops) {
        if (!timer.time_left()) return false;
        // Count colors among neighbors
        vector<int> uniqueNeighbor(K, -1); // index by color 0..K-1, but we will use 1..K-1
        bool direct_possible = false;
        for (int nb : adj[v]) {
            int c = color[nb];
            if (c >= 1 && c <= K-1) {
                if (uniqueNeighbor[c] == -1) uniqueNeighbor[c] = nb;
                else if (uniqueNeighbor[c] >= 0) uniqueNeighbor[c] = -2;
            }
        }
        // Check direct recolor first (no neighbor of that color)
        for (int c = 1; c <= K-1; ++c) {
            if (uniqueNeighbor[c] == -1) {
                color[v] = c;
                return true;
            }
        }
        // Try single-step recolor: colors that appear exactly once among neighbors
        vector<int> candidates;
        candidates.reserve(K);
        for (int c = 1; c <= K-1; ++c) if (uniqueNeighbor[c] >= 0) candidates.push_back(c);
        shuffle(candidates.begin(), candidates.end(), rng);
        for (int c : candidates) {
            if (!timer.time_left()) return false;
            int w = uniqueNeighbor[c];
            if (w < 0) continue;
            // Try to recolor w to some d in 1..K-1, d != c
            bitset<MAXC> usedW = neighbor_used_colors(adj, color, w);
            for (int d = 1; d <= K-1; ++d) {
                if (d == c) continue;
                if (!usedW.test(d)) {
                    int oldw = color[w];
                    color[w] = d;
                    // Now v has no neighbors with color c (since it was unique)
                    color[v] = c;
                    (void)oldw;
                    return true;
                }
            }
        }
    }
    return false;
}

void refine_coloring(vector<int>& color, const vector<vector<int>>& adj, mt19937 &rng, const Timer &timer) {
    int K = computeMaxColor(color);
    // A couple of greedy lowering passes
    for (int pass = 0; pass < 2; ++pass) {
        if (!timer.time_left()) break;
        greedy_lower_colors_once(color, adj, K, rng, timer);
    }
    // Try to remove top colors via single-step recolors
    while (timer.time_left()) {
        bool improved = attempt_remove_top_color_step(color, adj, K, rng, timer);
        if (!improved) break;
        // After improvement, do a quick greedy pass
        greedy_lower_colors_once(color, adj, K, rng, timer);
        // If top color is eliminated entirely, continue to try removing next
        int newK = computeMaxColor(color);
        if (newK < K) K = newK;
    }
    // Final greedy pass
    if (timer.time_left()) greedy_lower_colors_once(color, adj, K, rng, timer);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<vector<uint8_t>> mat(N, vector<uint8_t>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!mat[u][v]) {
            mat[u][v] = mat[v][u] = 1;
        }
    }

    vector<vector<int>> adj(N);
    vector<int> degree(N, 0);
    for (int i = 0; i < N; ++i) {
        adj[i].reserve(N);
        for (int j = 0; j < N; ++j) {
            if (mat[i][j]) adj[i].push_back(j);
        }
        degree[i] = (int)adj[i].size();
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Timing: allow up to ~1.85s
    Timer timer(1850);

    // Baseline and restarts
    vector<int> bestColor;
    int bestK = N + 1;

    // Ensure at least one run
    int runs = 0;
    while (timer.time_left(300) || runs == 0) {
        vector<int> color = dsatur_coloring(adj, degree, rng, bestK);
        int K = computeMaxColor(color);
        if (K > 0 && K < bestK) {
            bestK = K;
            bestColor = color;
            if (bestK == 1) break;
        }
        runs++;
        if (!timer.time_left(300)) break;
    }

    if (bestColor.empty()) {
        // Fallback: trivial greedy coloring by order
        bestColor.assign(N, 0);
        int K = 0;
        for (int v = 0; v < N; ++v) {
            bitset<MAXC> used = neighbor_used_colors(adj, bestColor, v);
            int c = 1;
            while (c <= K && used.test(c)) ++c;
            if (c > K) K = c;
            bestColor[v] = c;
        }
        bestK = computeMaxColor(bestColor);
    }

    // Refine best coloring with remaining time
    refine_coloring(bestColor, adj, rng, timer);

    // Output
    for (int i = 0; i < N; ++i) {
        int c = bestColor[i];
        if (c <= 0) c = 1;
        cout << c << '\n';
    }
    return 0;
}