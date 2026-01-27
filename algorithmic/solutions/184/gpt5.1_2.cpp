#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u;
        --v;
        if (u < 0 || v < 0 || u >= N || v >= N) continue;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Remove duplicate neighbors
    for (int i = 0; i < N; ++i) {
        auto &vec = adj[i];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) {
        deg[i] = (int)adj[i].size();
    }

    static bitset<MAXN> adjBit[MAXN];
    for (int i = 0; i < N; ++i) {
        adjBit[i].reset();
        for (int v : adj[i]) {
            adjBit[i].set(v);
        }
    }

    vector<char> inSet(N, 0), bestSet(N, 0);
    vector<int> conflicts(N, 0);

    auto start = chrono::steady_clock::now();
    const double TOTAL_TIME = 1.8;
    const double GREEDY_PHASE = 0.9;

    mt19937_64 rng((unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count());

    int bestSize = 0;

    vector<int> order(N);
    int iter = 0;

    // Greedy randomized construction phase
    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > GREEDY_PHASE) break;

        iota(order.begin(), order.end(), 0);

        if (iter % 5 == 0) {
            shuffle(order.begin(), order.end(), rng);
        } else {
            shuffle(order.begin(), order.end(), rng);
            sort(order.begin(), order.end(), [&](int a, int b) {
                return deg[a] < deg[b];
            });
        }

        fill(inSet.begin(), inSet.end(), 0);
        fill(conflicts.begin(), conflicts.end(), 0);
        int curSize = 0;

        for (int id = 0; id < N; ++id) {
            int v = order[id];
            if (!inSet[v] && conflicts[v] == 0) {
                inSet[v] = 1;
                ++curSize;
                for (int to : adj[v]) {
                    ++conflicts[to];
                }
            }
        }

        if (curSize > bestSize) {
            bestSize = curSize;
            bestSet = inSet;
        }
        ++iter;
    }

    // Local search phase with 2-improvements
    inSet = bestSet;
    fill(conflicts.begin(), conflicts.end(), 0);
    vector<int> Svertices;
    Svertices.reserve(N);
    for (int v = 0; v < N; ++v) {
        if (inSet[v]) {
            Svertices.push_back(v);
            for (int to : adj[v]) {
                ++conflicts[to];
            }
        }
    }
    int curSize = bestSize;

    vector<int> cand;
    cand.reserve(N);
    bool timeOver = false;

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > TOTAL_TIME) {
            timeOver = true;
            break;
        }
        bool improved = false;

        for (size_t idx = 0; idx < Svertices.size(); ++idx) {
            double el2 = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (el2 > TOTAL_TIME) {
                timeOver = true;
                break;
            }

            int u = Svertices[idx];

            cand.clear();
            for (int v : adj[u]) {
                if (!inSet[v] && conflicts[v] == 1) {
                    cand.push_back(v);
                }
            }
            if ((int)cand.size() < 2) continue;

            if ((int)cand.size() > 50) {
                for (int i = 0; i < 50; ++i) {
                    uniform_int_distribution<int> dist(i, (int)cand.size() - 1);
                    int j = dist(rng);
                    if (i != j) swap(cand[i], cand[j]);
                }
                cand.resize(50);
            }

            int v1 = -1, v2 = -1;
            int C = (int)cand.size();
            bool found = false;
            for (int i = 0; i < C && !found; ++i) {
                int a = cand[i];
                for (int j = i + 1; j < C; ++j) {
                    int b = cand[j];
                    if (!adjBit[a].test(b)) {
                        v1 = a;
                        v2 = b;
                        found = true;
                        break;
                    }
                }
            }
            if (!found) continue;

            // Apply 2-improvement: remove u, add v1 and v2
            inSet[u] = 0;
            --curSize;
            for (int x : adj[u]) {
                --conflicts[x];
            }
            Svertices[idx] = Svertices.back();
            Svertices.pop_back();
            if (idx < Svertices.size()) {
                --idx; // reprocess swapped-in vertex
            }

            auto addVertex = [&](int v) {
                inSet[v] = 1;
                ++curSize;
                Svertices.push_back(v);
                for (int x : adj[v]) {
                    ++conflicts[x];
                }
            };

            addVertex(v1);
            addVertex(v2);

            // Greedy fill to restore maximality
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
            for (int id = 0; id < N; ++id) {
                int v = order[id];
                if (!inSet[v] && conflicts[v] == 0) {
                    addVertex(v);
                }
            }

            if (curSize > bestSize) {
                bestSize = curSize;
                bestSet = inSet;
            }

            improved = true;
            break;
        }

        if (timeOver || !improved) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestSet[i] ? 1 : 0) << '\n';
    }

    return 0;
}