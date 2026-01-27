#include <bits/stdc++.h>
using namespace std;

struct VertexCoverSolver {
    int N;
    int M;
    vector<int> U, V;
    vector<vector<int>> adj;
    vector<int> degree;
    mt19937 rng;

    VertexCoverSolver(int n, int m) : N(n), M(m), U(m), V(m), adj(n + 1), degree(n + 1, 0) {
        rng.seed(123456789);
    }

    void add_edge(int idx, int u, int v) {
        U[idx] = u;
        V[idx] = v;
        degree[u]++;
        degree[v]++;
    }

    void build_adj() {
        for (int i = 0; i < M; ++i) {
            adj[U[i]].push_back(i);
            adj[V[i]].push_back(i);
        }
    }

    vector<uint8_t> pruneCover(const vector<uint8_t>& initial) {
        vector<uint8_t> inCover = initial;
        vector<int> countOut(N + 1, 0);
        deque<int> q;

        for (int v = 1; v <= N; ++v) {
            if (!inCover[v]) continue;
            int ct = 0;
            for (int eid : adj[v]) {
                int u = (U[eid] == v) ? V[eid] : U[eid];
                if (!inCover[u]) ct++;
            }
            countOut[v] = ct;
            if (ct == 0) q.push_back(v);
        }

        while (!q.empty()) {
            int v = q.front(); q.pop_front();
            if (!inCover[v] || countOut[v] != 0) continue;
            inCover[v] = 0;
            for (int eid : adj[v]) {
                int u = (U[eid] == v) ? V[eid] : U[eid];
                if (inCover[u]) {
                    countOut[u]++; // v becomes out-of-cover neighbor for u
                    if (countOut[u] == 0) q.push_back(u);
                }
            }
        }
        return inCover;
    }

    vector<uint8_t> greedyLeafDegreeCover() {
        vector<uint8_t> inCover(N + 1, 0);
        vector<uint8_t> coveredEdge(M, 0);
        vector<int> remDeg = degree;
        long long uncovered = M;

        deque<int> leafQueue;
        for (int i = 1; i <= N; ++i) {
            if (remDeg[i] == 1) leafQueue.push_back(i);
        }

        priority_queue<pair<int,int>> heap;
        for (int i = 1; i <= N; ++i) {
            if (remDeg[i] > 0) heap.push({remDeg[i], i});
        }

        auto coverVertex = [&](int v) {
            if (inCover[v]) return;
            inCover[v] = 1;
            for (int eid : adj[v]) {
                if (!coveredEdge[eid]) {
                    coveredEdge[eid] = 1;
                    --uncovered;
                    int u = (U[eid] == v) ? V[eid] : U[eid];
                    if (remDeg[u] > 0) {
                        remDeg[u]--;
                        if (!inCover[u]) {
                            if (remDeg[u] == 1) leafQueue.push_back(u);
                            heap.push({remDeg[u], u});
                        }
                    }
                }
            }
            remDeg[v] = 0;
        };

        while (uncovered > 0) {
            while (!leafQueue.empty()) {
                int u = leafQueue.front(); leafQueue.pop_front();
                if (inCover[u] || remDeg[u] != 1) continue;
                int v = -1;
                for (int eid : adj[u]) {
                    if (!coveredEdge[eid]) {
                        v = (U[eid] == u) ? V[eid] : U[eid];
                        break;
                    }
                }
                if (v == -1) {
                    remDeg[u] = 0;
                    continue;
                }
                coverVertex(v);
                if (uncovered == 0) break;
            }
            if (uncovered == 0) break;

            int v = -1;
            while (!heap.empty()) {
                auto [d, x] = heap.top();
                if (inCover[x] || remDeg[x] != d || d == 0) {
                    heap.pop();
                    continue;
                }
                v = x;
                break;
            }
            if (v == -1) {
                for (int i = 1; i <= N; ++i) {
                    if (!inCover[i] && remDeg[i] > 0) { v = i; break; }
                }
            }
            if (v == -1) break;
            coverVertex(v);
        }

        return pruneCover(inCover);
    }

    vector<uint8_t> matchingCover(const vector<int>& order) {
        vector<uint8_t> inCover(N + 1, 0);
        for (int eid : order) {
            int a = U[eid], b = V[eid];
            if (!inCover[a] && !inCover[b]) {
                inCover[a] = 1;
                inCover[b] = 1;
            }
        }
        return pruneCover(inCover);
    }

    int countCover(const vector<uint8_t>& cover) {
        int cnt = 0;
        for (int i = 1; i <= N; ++i) cnt += cover[i] ? 1 : 0;
        return cnt;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    VertexCoverSolver solver(N, M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        solver.add_edge(i, u, v);
    }
    solver.build_adj();

    auto start = chrono::steady_clock::now();
    auto best = solver.greedyLeafDegreeCover();
    int bestK = solver.countCover(best);

    vector<int> order(M);
    iota(order.begin(), order.end(), 0);

    // Natural order matching
    {
        auto cand = solver.matchingCover(order);
        int k = solver.countCover(cand);
        if (k < bestK) {
            bestK = k;
            best.swap(cand);
        }
    }

    // Randomized matching runs within time budget
    for (int t = 0; t < 3; ++t) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > 1.85) break;
        shuffle(order.begin(), order.end(), solver.rng);
        auto cand = solver.matchingCover(order);
        int k = solver.countCover(cand);
        if (k < bestK) {
            bestK = k;
            best.swap(cand);
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }

    return 0;
}