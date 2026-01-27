#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>
#include <utility>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<int> deg(N + 1, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u < 1 || u > N || v < 1 || v > N) continue;
        edges.emplace_back(u, v);
        ++deg[u];
        ++deg[v];
    }

    vector<vector<int>> adj(N + 1);
    for (int i = 1; i <= N; ++i) {
        adj[i].reserve(deg[i]);
    }
    for (const auto &e : edges) {
        int u = e.first;
        int v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    using Clock = chrono::steady_clock;
    auto start = Clock::now();
    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<char> globalBest(N + 1, 1);
    int globalBestSize = N;

    vector<int> vertexOrder(N);
    iota(vertexOrder.begin(), vertexOrder.end(), 1);

    int maxMatchIter = 3;
    int passesPerMatching = 10;
    double timeLimit = 1.8;

    if (M == 0) {
        for (int v = 1; v <= N; ++v) {
            cout << 0 << '\n';
        }
        return 0;
    }

    for (int iter = 0; iter < maxMatchIter; ++iter) {
        auto now = Clock::now();
        chrono::duration<double> elapsed = now - start;
        if (elapsed.count() > timeLimit) break;

        if (iter > 0) {
            shuffle(edges.begin(), edges.end(), rng);
        }

        vector<char> matched(N + 1, 0);
        for (const auto &e : edges) {
            int u = e.first;
            int v = e.second;
            if (!matched[u] && !matched[v]) {
                matched[u] = 1;
                matched[v] = 1;
            }
        }

        vector<char> baseCover = matched;
        int baseSize = 0;
        for (int v = 1; v <= N; ++v) {
            if (baseCover[v]) ++baseSize;
        }
        if (baseSize < globalBestSize) {
            globalBest = baseCover;
            globalBestSize = baseSize;
        }

        int passes = 0;
        while (passes < passesPerMatching) {
            auto now2 = Clock::now();
            chrono::duration<double> elapsed2 = now2 - start;
            if (elapsed2.count() > timeLimit) break;

            if (passes > 0) {
                shuffle(vertexOrder.begin(), vertexOrder.end(), rng);
            }

            vector<char> cover = baseCover;

            for (int idx = 0; idx < N; ++idx) {
                int v = vertexOrder[idx];
                if (!cover[v]) continue;
                bool canRemove = true;
                for (int u : adj[v]) {
                    if (!cover[u]) { canRemove = false; break; }
                }
                if (canRemove) cover[v] = 0;
            }

            int curSize = 0;
            for (int v = 1; v <= N; ++v) {
                if (cover[v]) ++curSize;
            }

            if (curSize < globalBestSize) {
                globalBest = cover;
                globalBestSize = curSize;
            }

            ++passes;
        }
    }

    for (int v = 1; v <= N; ++v) {
        cout << (globalBest[v] ? 1 : 0) << '\n';
    }

    return 0;
}