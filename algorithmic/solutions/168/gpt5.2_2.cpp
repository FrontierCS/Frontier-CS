#include <bits/stdc++.h>
using namespace std;

static const int INF = 1e9;

struct Result {
    vector<int> parent;
    long long score = -(1LL << 60);
    vector<int> roots;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    cin >> N >> M >> H;

    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];

    vector<vector<int>> g(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    vector<int> X(N), Y(N);
    for (int i = 0; i < N; i++) cin >> X[i] >> Y[i];

    auto multiSourceDist = [&](const vector<int>& roots) -> vector<int> {
        vector<int> dist(N, INF);
        queue<int> q;
        for (int r : roots) {
            if (r < 0 || r >= N) continue;
            if (dist[r] == 0) continue;
            dist[r] = 0;
            q.push(r);
        }
        while (!q.empty()) {
            int v = q.front(); q.pop();
            int nd = dist[v] + 1;
            for (int to : g[v]) {
                if (dist[to] > nd) {
                    dist[to] = nd;
                    q.push(to);
                }
            }
        }
        return dist;
    };

    auto farthestVertex = [&](const vector<int>& dist) -> int {
        int u = 0;
        int best = -1;
        for (int i = 0; i < N; i++) {
            if (dist[i] > best) {
                best = dist[i];
                u = i;
            }
        }
        return u;
    };

    auto minInBall = [&](int start, int radius) -> int {
        vector<int> dist(N, INF);
        queue<int> q;
        dist[start] = 0;
        q.push(start);
        int bestV = start;
        int bestA = A[start];
        while (!q.empty()) {
            int v = q.front(); q.pop();
            if (A[v] < bestA || (A[v] == bestA && v < bestV)) {
                bestA = A[v];
                bestV = v;
            }
            if (dist[v] == radius) continue;
            for (int to : g[v]) {
                if (dist[to] > dist[v] + 1) {
                    dist[to] = dist[v] + 1;
                    if (dist[to] <= radius) q.push(to);
                }
            }
        }
        return bestV;
    };

    auto normalizeRoots = [&](vector<int> roots) -> vector<int> {
        sort(roots.begin(), roots.end());
        roots.erase(unique(roots.begin(), roots.end()), roots.end());
        if (roots.empty()) roots.push_back(0);
        return roots;
    };

    auto greedyRoots = [&](vector<int> initRoots) -> vector<int> {
        vector<int> roots = normalizeRoots(initRoots);

        // Add roots until all vertices are within distance H of some root.
        for (int iter = 0; iter < 5000; iter++) {
            auto dist = multiSourceDist(roots);
            int u = farthestVertex(dist);
            if (dist[u] <= H) break;
            int r = minInBall(u, H);
            roots.push_back(r);
            roots = normalizeRoots(roots);
        }

        // Prune redundant roots (try removing high-A roots first).
        for (int pass = 0; pass < 5; pass++) {
            bool changed = false;
            if ((int)roots.size() <= 1) break;

            vector<int> order = roots;
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (A[a] != A[b]) return A[a] > A[b];
                return a > b;
            });

            vector<char> alive(N, 0);
            for (int r : roots) alive[r] = 1;

            for (int r : order) {
                if ((int)roots.size() <= 1) break;
                if (!alive[r]) continue;

                vector<int> roots2;
                roots2.reserve(roots.size() - 1);
                for (int x : roots) if (x != r) roots2.push_back(x);
                auto dist = multiSourceDist(roots2);
                int u = farthestVertex(dist);
                if (dist[u] <= H) {
                    roots.swap(roots2);
                    alive[r] = 0;
                    changed = true;
                }
            }
            roots = normalizeRoots(roots);
            if (!changed) break;
        }

        return roots;
    };

    auto buildForestFromRoots = [&](const vector<int>& roots) -> Result {
        Result res;
        res.roots = roots;
        res.parent.assign(N, -2);
        vector<int> dist(N, INF);

        queue<int> q;
        for (int r : roots) {
            dist[r] = 0;
            res.parent[r] = -1;
            q.push(r);
        }

        while (!q.empty()) {
            int v = q.front(); q.pop();
            if (dist[v] == H) continue;
            for (int to : g[v]) {
                if (dist[to] > dist[v] + 1) {
                    dist[to] = dist[v] + 1;
                    res.parent[to] = v;
                    q.push(to);
                }
            }
        }

        // Safety: if somehow unreachable within H, make it a new root.
        for (int i = 0; i < N; i++) {
            if (dist[i] == INF) {
                dist[i] = 0;
                res.parent[i] = -1;
            }
        }

        long long score = 0;
        for (int i = 0; i < N; i++) score += 1LL * (dist[i] + 1) * A[i];
        res.score = score;
        return res;
    };

    auto bfsFarthestFrom = [&](int s) -> int {
        vector<int> dist(N, INF);
        queue<int> q;
        dist[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) {
                if (dist[to] > dist[v] + 1) {
                    dist[to] = dist[v] + 1;
                    q.push(to);
                }
            }
        }
        return farthestVertex(dist);
    };

    // Initial roots candidates
    int minA_v = 0;
    for (int i = 1; i < N; i++) if (A[i] < A[minA_v]) minA_v = i;

    int maxA_v = 0;
    for (int i = 1; i < N; i++) if (A[i] > A[maxA_v]) maxA_v = i;

    int center_v = 0;
    long long bestd = (1LL << 60);
    for (int i = 0; i < N; i++) {
        long long dx = X[i] - 500;
        long long dy = Y[i] - 500;
        long long d = dx * dx + dy * dy;
        if (d < bestd) bestd = d, center_v = i;
    }

    int minSum_v = 0, maxSum_v = 0;
    for (int i = 1; i < N; i++) {
        if (X[i] + Y[i] < X[minSum_v] + Y[minSum_v]) minSum_v = i;
        if (X[i] + Y[i] > X[maxSum_v] + Y[maxSum_v]) maxSum_v = i;
    }

    int farFromMinA = bfsFarthestFrom(minA_v);

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> uni(0, N - 1);

    vector<vector<int>> initialSets;
    initialSets.push_back({minA_v});
    initialSets.push_back({center_v});
    initialSets.push_back({minSum_v});
    initialSets.push_back({maxSum_v});
    initialSets.push_back({maxA_v});
    initialSets.push_back({minA_v, farFromMinA});
    for (int t = 0; t < 12; t++) initialSets.push_back({uni(rng)});

    Result bestRes;
    bestRes.score = -(1LL << 60);

    for (auto init : initialSets) {
        auto roots = greedyRoots(init);
        auto res = buildForestFromRoots(roots);
        if (res.score > bestRes.score) bestRes = std::move(res);
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << bestRes.parent[i];
    }
    cout << '\n';
    return 0;
}