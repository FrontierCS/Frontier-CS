#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N + 1);
    adj.reserve(N + 1);

    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue; // ignore self-loops if any
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> deg(N + 1);
    for (int v = 1; v <= N; ++v) {
        deg[v] = (int)adj[v].size();
    }

    // Base orders
    vector<int> base(N);
    for (int i = 0; i < N; ++i) base[i] = i + 1;

    sort(base.begin(), base.end(), [&](int a, int b) {
        return deg[a] < deg[b];
    });

    vector<int> baseDesc = base;
    reverse(baseDesc.begin(), baseDesc.end());

    vector<int> natOrder(N);
    for (int i = 0; i < N; ++i) natOrder[i] = i + 1;

    vector<char> bestCover(N + 1, 1); // 1: in cover, 0: not in cover
    int bestK = N;

    vector<char> inMIS(N + 1, 0);

    auto runFromOrder = [&](const vector<int>& ord) {
        fill(inMIS.begin(), inMIS.end(), 0);
        int MISsize = 0;
        for (int idx = 0; idx < N; ++idx) {
            int v = ord[idx];
            bool hasNeighborInMIS = false;
            const auto& neighbors = adj[v];
            for (int u : neighbors) {
                if (inMIS[u]) {
                    hasNeighborInMIS = true;
                    break;
                }
            }
            if (!hasNeighborInMIS) {
                inMIS[v] = 1;
                ++MISsize;
            }
        }
        int cov = N - MISsize;
        if (cov < bestK) {
            bestK = cov;
            for (int v = 1; v <= N; ++v) {
                bestCover[v] = inMIS[v] ? 0 : 1;
            }
        }
    };

    // Deterministic runs
    runFromOrder(base);
    runFromOrder(baseDesc);
    runFromOrder(natOrder);

    // Randomized runs within time limit
    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> ord = base;

    auto start = chrono::steady_clock::now();
    const double timeLimit = 1.7; // seconds for randomization

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeLimit) break;
        shuffle(ord.begin(), ord.end(), rng);
        runFromOrder(ord);
    }

    for (int v = 1; v <= N; ++v) {
        cout << (bestCover[v] ? 1 : 0) << '\n';
    }

    return 0;
}