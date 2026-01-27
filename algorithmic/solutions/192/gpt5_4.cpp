#include <bits/stdc++.h>
using namespace std;

struct MaxCutSolver {
    int n, m;
    vector<vector<int>> g;
    vector<pair<int,int>> edges;
    vector<int> deg;
    mt19937 rng;

    MaxCutSolver(int n, int m): n(n), m(m), g(n), deg(n,0) {
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    void add_edge(int u, int v) {
        g[u].push_back(v);
        g[v].push_back(u);
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }

    long long cut_value(const vector<char>& s) const {
        long long c = 0;
        for (const auto& e : edges) {
            if (s[e.first] != s[e.second]) ++c;
        }
        return c;
    }

    vector<char> random_init() {
        vector<char> s(n);
        uniform_int_distribution<int> dist(0,1);
        for (int i = 0; i < n; ++i) s[i] = (char)dist(rng);
        return s;
    }

    vector<char> greedy_init() {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        vector<int> assigned(n, -1);
        uniform_int_distribution<int> dist(0,1);

        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int cnt0 = 0, cnt1 = 0;
            for (int u : g[v]) {
                if (assigned[u] == 0) cnt0++;
                else if (assigned[u] == 1) cnt1++;
            }
            if (cnt0 > cnt1) assigned[v] = 1;
            else if (cnt1 > cnt0) assigned[v] = 0;
            else assigned[v] = dist(rng);
        }
        vector<char> s(n);
        for (int i = 0; i < n; ++i) s[i] = (char)assigned[i];
        return s;
    }

    bool FM_pass(vector<char>& s, long long& currCut, const chrono::steady_clock::time_point& deadline) {
        // If time is up, skip
        if (chrono::steady_clock::now() > deadline) return false;

        vector<char> tempS = s;
        vector<int> opp(n, 0);
        for (int v = 0; v < n; ++v) {
            int c = 0;
            for (int u : g[v]) c += (tempS[u] != tempS[v]);
            opp[v] = c;
        }

        vector<char> locked(n, 0);
        // gains can be in range [-deg, +deg]
        auto calc_gain = [&](int v) -> int {
            return deg[v] - 2 * opp[v];
        };

        priority_queue<pair<int,int>> pq;
        vector<int> curGain(n);
        for (int v = 0; v < n; ++v) {
            curGain[v] = calc_gain(v);
            pq.emplace(curGain[v], v);
        }

        vector<int> flipOrder;
        vector<int> flipGain;
        flipOrder.reserve(n);
        flipGain.reserve(n);

        long long sumGain = 0;
        long long bestSum = 0;
        int bestK = 0;

        for (int step = 0; step < n; ++step) {
            if (chrono::steady_clock::now() > deadline) break;

            int v = -1;
            int gbest = INT_MIN;
            while (!pq.empty()) {
                auto [gval, u] = pq.top(); pq.pop();
                if (locked[u]) continue;
                int current = calc_gain(u);
                if (gval != current) {
                    // stale entry, push updated and continue
                    pq.emplace(current, u);
                    continue;
                }
                v = u;
                gbest = current;
                break;
            }
            if (v == -1) break;

            // lock and virtually flip v
            locked[v] = 1;
            flipOrder.push_back(v);
            flipGain.push_back(gbest);
            sumGain += gbest;
            if (sumGain > bestSum) {
                bestSum = sumGain;
                bestK = (int)flipOrder.size();
            }

            // apply virtual flip
            tempS[v] ^= 1;
            opp[v] = deg[v] - opp[v];

            // update neighbors
            for (int u : g[v]) {
                if (locked[u]) continue;
                bool nowOpp = (tempS[u] != tempS[v]);
                opp[u] += (nowOpp ? 1 : -1);
                int ngu = calc_gain(u);
                pq.emplace(ngu, u);
            }
        }

        if (bestSum > 0) {
            for (int i = 0; i < bestK; ++i) {
                s[flipOrder[i]] ^= 1;
            }
            currCut += bestSum;
            return true;
        }
        return false;
    }

    void improve(vector<char>& s, long long& cut, const chrono::steady_clock::time_point& deadline) {
        // Repeated FM passes until no improvement or time runs out
        while (chrono::steady_clock::now() < deadline) {
            bool improved = FM_pass(s, cut, deadline);
            if (!improved) break;
        }
    }

    vector<char> solve() {
        auto start = chrono::steady_clock::now();
        // Set a conservative time budget ~0.95s
        auto deadline = start + chrono::milliseconds(950);

        vector<char> bestS = random_init();
        long long bestCut = cut_value(bestS);

        // Try greedy init
        {
            vector<char> s = greedy_init();
            long long cut = cut_value(s);
            improve(s, cut, deadline);
            if (cut > bestCut) {
                bestCut = cut;
                bestS = s;
            }
        }

        // Random restarts while time remains
        while (chrono::steady_clock::now() < deadline) {
            vector<char> s = random_init();
            long long cut = cut_value(s);
            improve(s, cut, deadline);
            if (cut > bestCut) {
                bestCut = cut;
                bestS = s;
            }
        }

        return bestS;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    MaxCutSolver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        solver.add_edge(u, v);
    }

    vector<char> s = solver.solve();
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << int(s[i]);
    }
    cout << '\n';
    return 0;
}