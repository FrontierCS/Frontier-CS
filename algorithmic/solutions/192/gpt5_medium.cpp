#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point start;
    double limit_sec;
    Timer(double sec) : start(chrono::steady_clock::now()), limit_sec(sec) {}
    bool time_up() const {
        using namespace chrono;
        return duration<double>(steady_clock::now() - start).count() >= limit_sec;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (int)edges.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto compute_all = [&](const vector<int>& s, vector<int>& ext, vector<int>& gain) -> int {
        fill(ext.begin(), ext.end(), 0);
        int cut = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (s[u] != s[v]) {
                cut++;
                ext[u]++; ext[v]++;
            }
        }
        for (int i = 0; i < n; ++i) {
            gain[i] = deg[i] - 2 * ext[i];
        }
        return cut;
    };

    auto init_random = [&](vector<int>& s) {
        for (int i = 0; i < n; ++i) s[i] = (int)(rng() & 1);
    };

    auto init_greedy_incremental = [&](vector<int>& s) {
        vector<int> assigned(n, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int c0 = 0, c1 = 0;
            for (int u : adj[v]) {
                if (assigned[u] == 0) c0++;
                else if (assigned[u] == 1) c1++;
            }
            if (c0 > c1) assigned[v] = 1;
            else if (c1 > c0) assigned[v] = 0;
            else assigned[v] = (int)(rng() & 1);
        }
        for (int i = 0; i < n; ++i) s[i] = assigned[i];
    };

    auto init_bfs_parity = [&](vector<int>& s) {
        vector<int> vis(n, 0);
        for (int i = 0; i < n; ++i) s[i] = -1;
        for (int i = 0; i < n; ++i) {
            if (s[i] != -1) continue;
            s[i] = (int)(rng() & 1);
            queue<int> q; q.push(i);
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (s[v] == -1) {
                        s[v] = s[u] ^ 1;
                        q.push(v);
                    }
                }
            }
        }
    };

    auto flip_noPQ = [&](int v, vector<int>& s, vector<int>& ext, vector<int>& gain, int& cut) {
        int g = gain[v];
        int oldExt = ext[v];
        s[v] ^= 1;
        // Update neighbors first using new s[v]
        for (int u : adj[v]) {
            if (s[u] == s[v]) {
                ext[u]--;
            } else {
                ext[u]++;
            }
            gain[u] = deg[u] - 2 * ext[u];
        }
        ext[v] = deg[v] - oldExt;
        gain[v] = deg[v] - 2 * ext[v];
        cut += g;
    };

    struct PQItem {
        int gain;
        int v;
        bool operator<(PQItem const& other) const {
            return gain < other.gain; // max-heap
        }
    };

    auto hill_climb = [&](vector<int>& s, vector<int>& ext, vector<int>& gain, int& cut, const Timer& timer) {
        priority_queue<PQItem> pq;
        for (int i = 0; i < n; ++i) pq.push({gain[i], i});
        int steps = 0;
        while (!pq.empty()) {
            if ((steps++ & 255) == 0 && timer.time_up()) break;
            auto top = pq.top(); pq.pop();
            int v = top.v;
            if (top.gain != gain[v]) continue;
            if (gain[v] <= 0) break;
            int g = gain[v];
            int oldExt = ext[v];
            s[v] ^= 1;
            for (int u : adj[v]) {
                if (s[u] == s[v]) ext[u]--;
                else ext[u]++;
                gain[u] = deg[u] - 2 * ext[u];
                pq.push({gain[u], u});
            }
            ext[v] = deg[v] - oldExt;
            gain[v] = deg[v] - 2 * ext[v];
            pq.push({gain[v], v});
            cut += g;
        }
    };

    auto kl_pass = [&](vector<int>& s, vector<int>& ext, vector<int>& gain, int& cut, const Timer& timer) -> pair<bool,bool> {
        // returns {improved, aborted_due_to_time}
        vector<char> locked(n, 0);
        priority_queue<PQItem> pq;
        for (int i = 0; i < n; ++i) pq.push({gain[i], i});
        vector<int> order;
        vector<int> gvals;
        order.reserve(n);
        gvals.reserve(n);
        int steps = 0;
        while ((int)order.size() < n) {
            if ((steps++ & 255) == 0 && timer.time_up()) {
                // revert all flips done in this pass
                for (int i = (int)order.size() - 1; i >= 0; --i) {
                    int v = order[i];
                    flip_noPQ(v, s, ext, gain, cut);
                }
                return {false, true};
            }
            PQItem cur;
            bool found = false;
            while (!pq.empty()) {
                cur = pq.top(); pq.pop();
                int v = cur.v;
                if (locked[v]) continue;
                if (cur.gain != gain[v]) continue;
                found = true;
                break;
            }
            if (!found) break;
            int v = cur.v;
            int g = gain[v];
            // record
            order.push_back(v);
            gvals.push_back(g);
            locked[v] = 1;
            // apply flip and update pq
            int oldExt = ext[v];
            s[v] ^= 1;
            for (int u : adj[v]) {
                if (s[u] == s[v]) ext[u]--;
                else ext[u]++;
                gain[u] = deg[u] - 2 * ext[u];
                if (!locked[u]) pq.push({gain[u], u});
            }
            ext[v] = deg[v] - oldExt;
            gain[v] = deg[v] - 2 * ext[v];
            pq.push({gain[v], v});
            cut += g;
        }
        if (order.empty()) return {false, false};
        int bestk = 0;
        int bestSum = INT_MIN;
        int pref = 0;
        for (int i = 0; i < (int)gvals.size(); ++i) {
            pref += gvals[i];
            if (pref > bestSum) {
                bestSum = pref;
                bestk = i + 1;
            }
        }
        if (bestSum > 0) {
            for (int i = (int)order.size() - 1; i >= bestk; --i) {
                int v = order[i];
                flip_noPQ(v, s, ext, gain, cut);
            }
            return {true, false};
        } else {
            // revert all
            for (int i = (int)order.size() - 1; i >= 0; --i) {
                int v = order[i];
                flip_noPQ(v, s, ext, gain, cut);
            }
            return {false, false};
        }
    };

    // Time budget
    double TIME_LIMIT = 0.95;
    Timer timer(TIME_LIMIT);

    vector<int> bestS(n, 0);
    vector<int> s(n, 0), ext(n, 0), gain(n, 0);
    int bestCut = -1;

    int iter = 0;
    while (!timer.time_up()) {
        // Initialization method rotation
        int mode = iter % 3;
        if (mode == 0) init_random(s);
        else if (mode == 1) init_greedy_incremental(s);
        else init_bfs_parity(s);

        // Optional small random shake
        if (n > 0) {
            int flips = max(0, min(n, n / 50)); // ~2%
            uniform_int_distribution<int> dist(0, n - 1);
            for (int i = 0; i < flips; ++i) {
                int v = dist(rng);
                s[v] ^= 1;
            }
        }

        int cut = compute_all(s, ext, gain);
        if (timer.time_up()) break;

        hill_climb(s, ext, gain, cut, timer);
        if (timer.time_up()) break;

        while (true) {
            auto [improved, aborted] = kl_pass(s, ext, gain, cut, timer);
            if (aborted) break;
            if (!improved) break;
            if (timer.time_up()) break;
            // Optional extra hill climb between KL passes
            hill_climb(s, ext, gain, cut, timer);
            if (timer.time_up()) break;
        }

        if (cut > bestCut) {
            bestCut = cut;
            bestS = s;
        }
        iter++;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestS[i] & 1);
    }
    cout << '\n';
    return 0;
}