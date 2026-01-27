#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<vector<int>> adj;
    mt19937 rng;

    Solver(int n_, int m_) : n(n_), m(m_), adj(n_) {
        rng.seed((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    }

    vector<int> randomInit() {
        vector<int> side(n);
        for (int i = 0; i < n; i++) side[i] = (int)(rng() & 1u);
        return side;
    }

    vector<int> greedyInit() {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        vector<int> side(n, 0);
        vector<char> assigned(n, 0);

        for (int v : order) {
            int cutIf0 = 0, cutIf1 = 0;
            for (int u : adj[v]) if (assigned[u]) {
                if (side[u] == 0) cutIf1++;
                else cutIf0++;
            }
            if (cutIf1 > cutIf0) side[v] = 1;
            else if (cutIf1 == cutIf0) side[v] = (int)(rng() & 1u);
            assigned[v] = 1;
        }
        return side;
    }

    vector<int> perturbFrom(const vector<int>& base) {
        vector<int> side = base;
        int k = max(1, (int)std::sqrt((double)n));
        for (int t = 0; t < k; t++) {
            int v = (int)(rng() % (uint32_t)n);
            side[v] ^= 1;
        }
        return side;
    }

    long long localSearch(vector<int>& side) {
        vector<int> gain(n, 0);
        long long sumOpp = 0;

        for (int v = 0; v < n; v++) {
            int same = 0, opp = 0;
            int sv = side[v];
            for (int u : adj[v]) {
                if (side[u] == sv) same++;
                else opp++;
            }
            gain[v] = same - opp;
            sumOpp += opp;
        }
        long long cut = sumOpp / 2;

        priority_queue<pair<int,int>> pq;
        for (int v = 0; v < n; v++) if (gain[v] > 0) pq.push({gain[v], v});

        while (!pq.empty()) {
            auto [g, v] = pq.top();
            pq.pop();
            if (g != gain[v] || g <= 0) continue;

            int oldSide = side[v];
            side[v] ^= 1;
            cut += gain[v];
            gain[v] = -gain[v];

            for (int u : adj[v]) {
                if (side[u] == oldSide) gain[u] -= 2;
                else gain[u] += 2;
                if (gain[u] > 0) pq.push({gain[u], u});
            }
            if (gain[v] > 0) pq.push({gain[v], v});
        }

        return cut;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    Solver solver(n, m);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        solver.adj[u].push_back(v);
        solver.adj[v].push_back(u);
    }

    vector<int> bestSide(n, 0);
    long long bestCut = -1;

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 0.95;

    auto try_candidate = [&](vector<int> side) {
        long long cut = solver.localSearch(side);
        if (cut > bestCut) {
            bestCut = cut;
            bestSide = std::move(side);
        }
    };

    try_candidate(solver.greedyInit());
    try_candidate(solver.randomInit());

    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed >= TIME_LIMIT) break;

        vector<int> side;
        if (iter % 5 == 0) side = solver.greedyInit();
        else if (bestCut >= 0 && (iter % 3 == 0)) side = solver.perturbFrom(bestSide);
        else side = solver.randomInit();

        try_candidate(std::move(side));
        iter++;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << bestSide[i];
    }
    cout << '\n';
    return 0;
}