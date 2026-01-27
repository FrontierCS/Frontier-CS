#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t &x) {
    x += 0x9e3779b97f4a7c15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Solver {
    int n, m;
    vector<vector<int>> adj;
    vector<pair<int,int>> edges;
    vector<int> deg;

    uint64_t seed;
    inline int rndInt(int lo, int hi) {
        uint64_t r = splitmix64(seed);
        return lo + (int)(r % (uint64_t)(hi - lo + 1));
    }
    inline bool rndBit() { return (splitmix64(seed) >> 63) & 1ULL; }

    int computeCut(const vector<char>& lab) const {
        int cut = 0;
        for (auto [u, v] : edges) cut += (lab[u] != lab[v]);
        return cut;
    }

    void computeGains(const vector<char>& lab, vector<int>& gain) const {
        gain.assign(n, 0);
        for (int v = 0; v < n; v++) {
            int diff = 0;
            const auto &nb = adj[v];
            for (int u : nb) diff += (lab[u] != lab[v]);
            gain[v] = deg[v] - 2 * diff;
        }
    }

    bool KLPass(vector<char>& lab, int& cut) {
        vector<int> gain;
        computeGains(lab, gain);

        vector<char> locked(n, 0);
        vector<int> order;
        vector<int> gsel;
        order.reserve(n);
        gsel.reserve(n);

        for (int step = 0; step < n; step++) {
            int bestV = -1;
            int bestG = INT_MIN;
            for (int v = 0; v < n; v++) {
                if (!locked[v] && gain[v] > bestG) {
                    bestG = gain[v];
                    bestV = v;
                }
            }

            locked[bestV] = 1;
            order.push_back(bestV);
            gsel.push_back(bestG);

            char old = lab[bestV];
            lab[bestV] ^= 1;

            for (int u : adj[bestV]) {
                if (locked[u]) continue;
                if (lab[u] == old) gain[u] -= 2;   // uncut -> cut
                else gain[u] += 2;                 // cut -> uncut
            }
            // gain[bestV] not needed after lock
        }

        long long sum = 0, bestSum = LLONG_MIN;
        int bestK = 0;
        for (int i = 0; i < n; i++) {
            sum += gsel[i];
            if (sum > bestSum) {
                bestSum = sum;
                bestK = i + 1;
            }
        }

        if (bestSum > 0) {
            for (int i = n - 1; i >= bestK; i--) lab[order[i]] ^= 1;
            cut += (int)bestSum;
            return true;
        } else {
            for (int i = n - 1; i >= 0; i--) lab[order[i]] ^= 1;
            return false;
        }
    }

    void oneFlipImprove(vector<char>& lab, int& cut) {
        vector<int> gain;
        computeGains(lab, gain);
        priority_queue<pair<int,int>> pq;
        pq = {};
        for (int v = 0; v < n; v++) pq.push({gain[v], v});

        while (!pq.empty()) {
            auto [g, v] = pq.top();
            pq.pop();
            if (g != gain[v]) continue;
            if (g <= 0) break;

            char old = lab[v];
            lab[v] ^= 1;
            cut += g;

            gain[v] = -gain[v];
            pq.push({gain[v], v});

            for (int u : adj[v]) {
                if (lab[u] == old) gain[u] -= 2;
                else gain[u] += 2;
                pq.push({gain[u], u});
            }
        }
    }

    int optimize(vector<char>& lab) {
        int cut = computeCut(lab);
        for (int it = 0; it < 40; it++) {
            if (!KLPass(lab, cut)) break;
            cut = computeCut(lab); // safety
        }
        oneFlipImprove(lab, cut);
        cut = computeCut(lab);
        return cut;
    }

    vector<char> initRandom() {
        vector<char> lab(n, 0);
        for (int i = 0; i < n; i++) lab[i] = rndBit();
        return lab;
    }

    vector<char> initGreedy() {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);
        for (int i = n - 1; i > 0; i--) swap(ord[i], ord[rndInt(0, i)]);

        vector<char> lab(n, -1);
        for (int v : ord) {
            int c0 = 0, c1 = 0;
            for (int u : adj[v]) {
                if (lab[u] == -1) continue;
                if (lab[u] == 0) c0++;
                else c1++;
            }
            // if lab[v] = 0, cut gained with assigned neighbors in 1 => c1
            // if lab[v] = 1, cut gained with assigned neighbors in 0 => c0
            if (c0 > c1) lab[v] = 1;
            else if (c1 > c0) lab[v] = 0;
            else lab[v] = rndBit();
        }

        for (int i = 0; i < n; i++) if (lab[i] == -1) lab[i] = 0;
        return lab;
    }

    vector<char> perturb(const vector<char>& base, int flips) {
        vector<char> lab = base;
        for (int i = 0; i < flips; i++) {
            int v = rndInt(0, n - 1);
            lab[v] ^= 1;
        }
        return lab;
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> n >> m;
        adj.assign(n, {});
        edges.reserve(m);
        deg.assign(n, 0);

        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
            --u; --v;
            adj[u].push_back(v);
            adj[v].push_back(u);
            edges.push_back({u, v});
            deg[u]++; deg[v]++;
        }

        if (m == 0) {
            for (int i = 0; i < n; i++) {
                if (i) cout << ' ';
                cout << 0;
            }
            cout << '\n';
            return;
        }

        seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)(uintptr_t)this;
        seed ^= (uint64_t)n * 0x9e3779b97f4a7c15ULL;

        vector<char> bestLab(n, 0);
        int bestCut = -1;

        auto consider = [&](vector<char> lab) {
            int cut = optimize(lab);
            if (cut > bestCut) {
                bestCut = cut;
                bestLab = std::move(lab);
            }
        };

        consider(initGreedy());
        consider(initRandom());

        auto t0 = chrono::steady_clock::now();
        const double TIME_LIMIT_SEC = 0.95;

        int rounds = 0;
        while (true) {
            auto t1 = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(t1 - t0).count();
            if (elapsed >= TIME_LIMIT_SEC) break;

            int type = rndInt(0, 4);
            vector<char> lab;
            if (type == 0) lab = initGreedy();
            else if (type == 1) lab = initRandom();
            else if (type == 2 && bestCut >= 0) lab = perturb(bestLab, max(1, n / 30));
            else if (type == 3 && bestCut >= 0) lab = perturb(bestLab, max(1, n / 15));
            else lab = initRandom();

            consider(std::move(lab));
            rounds++;
            if (rounds > 200) break;
        }

        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << int(bestLab[i] != 0);
        }
        cout << '\n';
    }
};

int main() {
    Solver s;
    s.solve();
    return 0;
}