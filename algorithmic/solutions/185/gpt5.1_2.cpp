#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000;
int N;
vector< bitset<MAXN> > adj;

vector<int> greedy(const vector<int>& order) {
    bitset<MAXN> cand;
    cand.reset();
    for (int i = 0; i < N; ++i) cand.set(i);

    vector<int> clique;
    clique.reserve(N);

    for (int pos = 0; pos < N; ++pos) {
        int v = order[pos];
        if (!cand.test(v)) continue;
        clique.push_back(v);
        cand &= adj[v];
    }
    return clique;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int M;
    if (!(cin >> N >> M)) return 0;

    adj.assign(N, bitset<MAXN>());

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    vector<int> vertices(N);
    for (int i = 0; i < N; ++i) vertices[i] = i;

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = adj[i].count();

    vector<int> base_desc = vertices;
    sort(base_desc.begin(), base_desc.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    vector<int> base_asc = vertices;
    sort(base_asc.begin(), base_asc.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    vector<int> bestClique = greedy(base_desc);
    vector<int> tmpClique = greedy(base_asc);
    if (tmpClique.size() > bestClique.size()) bestClique.swap(tmpClique);

    mt19937 rng(712367821);

    using namespace std::chrono;
    auto start = steady_clock::now();
    const double timeLimit = 1.9;

    long long iter = 0;
    while (true) {
        ++iter;
        if ((iter & 0x3F) == 0) {
            auto now = steady_clock::now();
            double elapsed = duration<double>(now - start).count();
            if (elapsed > timeLimit) break;
        }

        const vector<int>& base = (rng() & 1) ? base_desc : base_asc;
        vector<int> order = base;

        int kind = rng() % 4;
        if (kind == 0) {
            shuffle(order.begin(), order.end(), rng);
        } else {
            int K = min(N, 50);
            for (int s = 0; s < K; ++s) {
                int i = rng() % N;
                int j = rng() % N;
                if (i != j) swap(order[i], order[j]);
            }
        }

        tmpClique = greedy(order);
        if (tmpClique.size() > bestClique.size()) bestClique.swap(tmpClique);
    }

    vector<int> inClique(N, 0);
    for (int v : bestClique) inClique[v] = 1;

    for (int i = 0; i < N; ++i) {
        cout << (inClique[i] ? 1 : 0) << '\n';
    }

    return 0;
}