#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<vector<int>> adj;
    vector<pair<int,int>> edges;
    mt19937 rng;

    Solver() : rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count()) {}

    vector<char> random_assignment() {
        vector<char> s(n);
        for (int i = 0; i < n; i++) s[i] = (char)(rng() & 1u);
        return s;
    }

    vector<char> greedy_assignment() {
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 0);
        shuffle(perm.begin(), perm.end(), rng);

        vector<char> s(n, 0), assigned(n, 0);
        for (int v : perm) {
            int c0 = 0, c1 = 0;
            for (int u : adj[v]) {
                if (!assigned[u]) continue;
                if (s[u] == 0) c0++;
                else c1++;
            }
            if (c0 > c1) s[v] = 1;
            else if (c1 > c0) s[v] = 0;
            else s[v] = (char)(rng() & 1u);
            assigned[v] = 1;
        }
        return s;
    }

    void eval_from_s(const vector<char>& s, vector<int>& gain, int &cut) {
        cut = 0;
        for (auto [a, b] : edges) cut += (s[a] != s[b]);
        gain.assign(n, 0);
        for (int v = 0; v < n; v++) {
            int g = 0;
            char sv = s[v];
            for (int u : adj[v]) g += (s[u] == sv) ? 1 : -1;
            gain[v] = g;
        }
    }

    inline void flip_vertex(int v, vector<char>& s, vector<int>& gain, int &cut) {
        int g = gain[v];
        char old = s[v];
        s[v] ^= 1;
        cut += g;
        gain[v] = -g;
        for (int u : adj[v]) {
            if (s[u] == old) gain[u] -= 2;
            else gain[u] += 2;
        }
    }

    void kick(vector<char>& s, vector<int>& gain, int &cut, int k) {
        uniform_int_distribution<int> dist(0, n - 1);
        for (int i = 0; i < k; i++) {
            int v = dist(rng);
            flip_vertex(v, s, gain, cut);
        }
    }

    void hillclimb(vector<char>& s, vector<int>& gain, int &cut) {
        priority_queue<pair<int,int>> pq;
        for (int v = 0; v < n; v++) pq.push({gain[v], v});

        while (!pq.empty()) {
            auto [g, v] = pq.top(); pq.pop();
            if (g != gain[v]) continue;
            if (g <= 0) break;

            char old = s[v];
            s[v] ^= 1;
            cut += g;
            gain[v] = -g;
            pq.push({gain[v], v});

            for (int u : adj[v]) {
                if (s[u] == old) gain[u] -= 2;
                else gain[u] += 2;
                pq.push({gain[u], u});
            }
        }
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> n >> m;
        adj.assign(n, {});
        edges.reserve(m);

        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
            --u; --v;
            edges.push_back({u, v});
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        if (m == 0) {
            for (int i = 0; i < n; i++) {
                if (i) cout << ' ';
                cout << 0;
            }
            cout << "\n";
            return;
        }

        vector<char> bestS;
        vector<int> bestGain;
        int bestCut = -1;

        auto consider = [&](vector<char> s) {
            vector<int> gain;
            int cut;
            eval_from_s(s, gain, cut);
            hillclimb(s, gain, cut);
            if (cut > bestCut) {
                bestCut = cut;
                bestS = std::move(s);
                bestGain = std::move(gain);
            }
        };

        consider(greedy_assignment());
        for (int t = 0; t < 6; t++) consider(random_assignment());

        auto start = chrono::steady_clock::now();
        auto deadline = start + chrono::milliseconds(1800);

        vector<char> s;
        vector<int> gain;
        int cut = 0;

        int iter = 0;
        while (chrono::steady_clock::now() < deadline) {
            if (iter % 32 == 0) {
                s = random_assignment();
                eval_from_s(s, gain, cut);
                hillclimb(s, gain, cut);
            } else {
                s = bestS;
                gain = bestGain;
                cut = bestCut;

                int maxk = min(n, 20);
                int k = 1 + (int)(rng() % (uint32_t)maxk);
                if (iter % 128 == 0) k = min(n, 50);

                kick(s, gain, cut, k);
                hillclimb(s, gain, cut);
            }

            if (cut > bestCut) {
                bestCut = cut;
                bestS = s;
                bestGain = gain;
            }
            iter++;
        }

        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << int(bestS[i]);
        }
        cout << "\n";
    }
};

int main() {
    Solver s;
    s.solve();
    return 0;
}