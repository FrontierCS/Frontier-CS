#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

using namespace std;

struct Edge {
    int u, v;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<Edge> edges;
    edges.reserve(M);
    vector<vector<int>> incident(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v});
        incident[u].push_back(i);
        incident[v].push_back(i);
    }

    // Precompute vertex order (by increasing degree)
    vector<int> vertexOrder(N);
    iota(vertexOrder.begin(), vertexOrder.end(), 1);
    sort(vertexOrder.begin(), vertexOrder.end(),
         [&](int a, int b) { return incident[a].size() < incident[b].size(); });

    mt19937 rng(123456);

    vector<int> edgeOrder(M);
    iota(edgeOrder.begin(), edgeOrder.end(), 0);

    const int ITERS = 10;

    vector<char> bestInCover(N + 1, 0);
    int bestK = N + 1;

    vector<char> inCover(N + 1);
    vector<char> matched(N + 1);
    vector<int> coverCount(M);

    for (int it = 0; it < ITERS; ++it) {
        shuffle(edgeOrder.begin(), edgeOrder.end(), rng);

        fill(matched.begin(), matched.end(), 0);
        fill(inCover.begin(), inCover.end(), 0);

        // Maximal matching to get initial cover
        for (int idx : edgeOrder) {
            int u = edges[idx].u;
            int v = edges[idx].v;
            if (!matched[u] && !matched[v]) {
                matched[u] = matched[v] = 1;
                inCover[u] = inCover[v] = 1;
            }
        }

        // Initialize coverage counts, ensure all edges covered (safety)
        for (int i = 0; i < M; ++i) {
            int u = edges[i].u;
            int v = edges[i].v;
            int c = (inCover[u] ? 1 : 0) + (inCover[v] ? 1 : 0);
            if (c == 0) {
                // Add endpoint with larger degree
                if (incident[u].size() >= incident[v].size()) {
                    inCover[u] = 1;
                } else {
                    inCover[v] = 1;
                }
                c = 1;
            }
            coverCount[i] = c;
        }

        // Greedy removal to obtain minimal cover
        for (int v : vertexOrder) {
            if (!inCover[v]) continue;
            bool canRemove = true;
            for (int ei : incident[v]) {
                if (coverCount[ei] <= 1) {
                    canRemove = false;
                    break;
                }
            }
            if (!canRemove) continue;
            inCover[v] = 0;
            for (int ei : incident[v]) {
                --coverCount[ei];
            }
        }

        int K = 0;
        for (int i = 1; i <= N; ++i) {
            if (inCover[i]) ++K;
        }

        if (K < bestK) {
            bestK = K;
            bestInCover = inCover;
        }
    }

    // Final safety check; if something went wrong, fall back to all-ones cover
    bool valid = true;
    for (const auto &e : edges) {
        if (!(bestInCover[e.u] || bestInCover[e.v])) {
            valid = false;
            break;
        }
    }
    if (!valid) {
        fill(bestInCover.begin(), bestInCover.end(), 1);
    }

    for (int i = 1; i <= N; ++i) {
        cout << (bestInCover[i] ? 1 : 0) << '\n';
    }

    return 0;
}