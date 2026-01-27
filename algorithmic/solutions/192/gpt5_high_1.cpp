#include <bits/stdc++.h>
using namespace std;

struct FastRand {
    uint64_t x;
    FastRand() {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = seed ^ (seed << 13) ^ 0x9E3779B97F4A7C15ULL;
    }
    inline uint64_t operator()() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int randint(int l, int r) { // inclusive
        return int(l + (operator()() % (uint64_t)(r - l + 1)));
    }
    inline int randbit() {
        return int(operator()() & 1ULL);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    auto compute_cut = [&](const vector<int>& s)->long long {
        long long c = 0;
        for (auto &e : edges) {
            if (s[e.first] != s[e.second]) ++c;
        }
        return c;
    };

    auto compute_d = [&](const vector<int>& s, vector<int>& d) {
        fill(d.begin(), d.end(), 0);
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (s[u] == s[v]) {
                d[u] += 1;
                d[v] += 1;
            } else {
                d[u] -= 1;
                d[v] -= 1;
            }
        }
    };

    struct Node {
        int gain, v;
        bool operator<(Node const& other) const {
            if (gain != other.gain) return gain < other.gain;
            return v < other.v;
        }
    };

    auto greedy_improve = [&](vector<int>& s, vector<int>& d, long long& c) {
        priority_queue<Node> pq;
        for (int i = 0; i < n; ++i) pq.push({d[i], i});
        while (!pq.empty()) {
            Node cur = pq.top(); pq.pop();
            int v = cur.v;
            if (cur.gain != d[v]) continue; // stale
            if (d[v] <= 0) break;
            int oldSide = s[v];
            s[v] ^= 1;
            c += cur.gain;
            d[v] = -d[v];
            pq.push({d[v], v});
            for (int u : adj[v]) {
                if (s[u] != oldSide) {
                    d[u] += 2;
                } else {
                    d[u] -= 2;
                }
                pq.push({d[u], u});
            }
        }
    };

    auto KL_pass = [&](vector<int>& s, long long& c, FastRand& rng)->bool {
        vector<int> s_tmp = s;
        vector<int> d(n, 0);
        compute_d(s_tmp, d);
        vector<char> locked(n, 0);
        priority_queue<Node> pq;
        for (int i = 0; i < n; ++i) pq.push({d[i], i});
        vector<int> order;
        order.reserve(n);
        vector<int> gains;
        gains.reserve(n);
        for (int step = 0; step < n; ++step) {
            Node cur;
            bool found = false;
            while (!pq.empty()) {
                cur = pq.top(); pq.pop();
                int v = cur.v;
                if (locked[v]) continue;
                if (cur.gain != d[v]) continue;
                found = true;
                break;
            }
            if (!found) {
                // Rebuild heap if needed
                for (int i = 0; i < n; ++i) if (!locked[i]) pq.push({d[i], i});
                while (!pq.empty()) {
                    cur = pq.top(); pq.pop();
                    int v = cur.v;
                    if (locked[v]) continue;
                    if (cur.gain != d[v]) continue;
                    found = true;
                    break;
                }
                if (!found) break; // no candidates (shouldn't happen)
            }
            int v = cur.v;
            int g = d[v];
            order.push_back(v);
            gains.push_back(g);
            locked[v] = 1;
            int oldSide = s_tmp[v];
            s_tmp[v] ^= 1;
            // update neighbors' gains
            for (int u : adj[v]) {
                if (locked[u]) continue;
                if (s_tmp[u] != oldSide) {
                    d[u] += 2;
                } else {
                    d[u] -= 2;
                }
                pq.push({d[u], u});
            }
            // d[v] not needed as it's locked
        }
        if (gains.empty()) return false;
        long long bestSum = LLONG_MIN, curSum = 0;
        int bestK = -1;
        for (int i = 0; i < (int)gains.size(); ++i) {
            curSum += gains[i];
            if (curSum > bestSum) {
                bestSum = curSum;
                bestK = i;
            }
        }
        if (bestSum > 0) {
            for (int i = 0; i <= bestK; ++i) {
                s[order[i]] ^= 1;
            }
            c += bestSum;
            return true;
        } else {
            return false;
        }
    };

    FastRand rng;

    vector<int> bestS(n, 0);
    long long bestC = -1;

    if (m == 0) {
        // Any assignment is optimal
        for (int i = 0; i < n; ++i) {
            cout << 0 << (i+1==n?'\n':' ');
        }
        return 0;
    }

    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds
    int attempts = 0;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > TIME_LIMIT) break;

        // Random initial assignment
        vector<int> s(n);
        for (int i = 0; i < n; ++i) s[i] = rng.randbit();

        vector<int> d(n, 0);
        compute_d(s, d);
        long long c = compute_cut(s);

        // Greedy single-vertex local improvement
        greedy_improve(s, d, c);

        // KL passes
        for (int pass = 0; pass < 3; ++pass) {
            now = chrono::steady_clock::now();
            elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > TIME_LIMIT) break;
            bool improved = KL_pass(s, c, rng);
            if (!improved) break;
            // After pass, optionally do a quick greedy polish
            fill(d.begin(), d.end(), 0);
            compute_d(s, d);
            greedy_improve(s, d, c);
        }

        if (c > bestC) {
            bestC = c;
            bestS = s;
        }

        attempts++;
        if (attempts >= 50) break; // safeguard against too many restarts
    }

    if (bestC < 0) {
        // Fallback
        vector<int> s(n, 0);
        long long c = compute_cut(s);
        bestS = s;
        bestC = c;
    }

    for (int i = 0; i < n; ++i) {
        cout << bestS[i] << (i+1==n?'\n':' ');
    }
    return 0;
}