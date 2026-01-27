#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;

int N, M;
vector< bitset<MAXN> > adj;
vector<int> degv;
mt19937 rng((unsigned int)chrono::steady_clock::now().time_since_epoch().count());

vector<int> greedy_from_seed(int seed) {
    bitset<MAXN> cand = adj[seed];
    vector<int> clique;
    clique.reserve(N);
    clique.push_back(seed);

    while (cand.any()) {
        int bestDeg = -1;
        for (int u = 0; u < N; ++u) {
            if (cand[u]) {
                int d = degv[u];
                if (d > bestDeg) bestDeg = d;
            }
        }
        if (bestDeg < 0) break;

        int threshold = bestDeg - 2;
        if (threshold < 0) threshold = 0;

        vector<int> candidates;
        candidates.reserve(16);
        for (int u = 0; u < N; ++u) {
            if (cand[u] && degv[u] >= threshold) {
                candidates.push_back(u);
            }
        }
        if (candidates.empty()) break;

        int v = candidates[rng() % candidates.size()];
        clique.push_back(v);
        cand &= adj[v];
    }

    return clique;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) {
        return 0;
    }

    adj.assign(N, bitset<MAXN>());
    degv.assign(N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!adj[u].test(v)) {
            adj[u].set(v);
            adj[v].set(u);
            ++degv[u];
            ++degv[v];
        }
    }

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (degv[a] != degv[b]) return degv[a] > degv[b];
        return a < b;
    });

    const int maxHighSeeds = 50;
    const int maxRandomSeeds = 50;
    int highSeeds = min(N, maxHighSeeds);
    int randSeeds = min(N - highSeeds, maxRandomSeeds);

    vector<int> seeds;
    seeds.reserve(highSeeds + randSeeds);

    for (int i = 0; i < highSeeds; ++i) {
        seeds.push_back(order[i]);
    }

    if (randSeeds > 0) {
        vector<int> rest(order.begin() + highSeeds, order.end());
        shuffle(rest.begin(), rest.end(), rng);
        for (int i = 0; i < randSeeds; ++i) {
            seeds.push_back(rest[i]);
        }
    }

    vector<int> best_clique;

    for (int s : seeds) {
        if ((int)best_clique.size() >= degv[s] + 1) continue;
        vector<int> clique = greedy_from_seed(s);
        if (clique.size() > best_clique.size()) {
            best_clique.swap(clique);
        }
    }

    vector<int> out(N, 0);
    for (int v : best_clique) {
        out[v] = 1;
    }

    for (int i = 0; i < N; ++i) {
        cout << out[i] << '\n';
    }

    return 0;
}