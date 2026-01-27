#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (int)edges.size();

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    auto start_time = chrono::steady_clock::now();
    const int TIME_LIMIT_MS = 1800;
    auto deadline = start_time + chrono::milliseconds(TIME_LIMIT_MS);

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<int> degree(n);
    for (int i = 0; i < n; ++i) degree[i] = (int)adj[i].size();

    auto greedy_init = [&](vector<int>& col) {
        col.assign(n, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            if (degree[a] != degree[b]) return degree[a] > degree[b];
            return a < b;
        });

        for (int v : order) {
            int cnt[3] = {0,0,0};
            for (int u : adj[v]) {
                if (col[u] != -1) cnt[col[u]]++;
            }
            int bestc = 0;
            int bestv = cnt[0];
            for (int c = 1; c < 3; ++c) {
                if (cnt[c] < bestv) {
                    bestv = cnt[c];
                    bestc = c;
                } else if (cnt[c] == bestv) {
                    if (uniform_int_distribution<int>(0,1)(rng)) bestc = c;
                }
            }
            col[v] = bestc;
        }
    };

    auto build_cnt_and_b = [&](const vector<int>& col, vector<array<int,3>>& cnt)->long long{
        for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
        long long b = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            cnt[u][col[v]]++;
            cnt[v][col[u]]++;
            if (col[u] == col[v]) b++;
        }
        return b;
    };

    auto local_search = [&](vector<int>& col, vector<array<int,3>>& cnt, long long& b, long long& best_b, vector<int>& best_col) {
        int stall = 0;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);

        while (chrono::steady_clock::now() < deadline) {
            bool improvement = false;
            shuffle(order.begin(), order.end(), rng);

            for (int v : order) {
                int c = col[v];
                int cur_same = cnt[v][c];
                int bestDelta = 0;
                int bestT = c;
                for (int t = 0; t < 3; ++t) {
                    if (t == c) continue;
                    int delta = cnt[v][t] - cur_same;
                    if (delta < bestDelta) {
                        bestDelta = delta;
                        bestT = t;
                    }
                }
                if (bestT != c) {
                    // perform move
                    int old = c;
                    int nw = bestT;
                    b += bestDelta;
                    col[v] = nw;
                    for (int u : adj[v]) {
                        cnt[u][old]--;
                        cnt[u][nw]++;
                    }
                    improvement = true;
                    if (b < best_b) {
                        best_b = b;
                        best_col = col;
                        if (best_b == 0) return;
                    }
                }
                if (chrono::steady_clock::now() >= deadline) break;
            }

            if (!improvement) {
                stall++;
                if (stall >= 2) {
                    int K = max(1, min((int)n/10, 30));
                    uniform_int_distribution<int> pickV(0, n-1);
                    for (int i = 0; i < K; ++i) {
                        int v = pickV(rng);
                        int c = col[v];
                        int cur_same = cnt[v][c];
                        int bestDelta = INT_MAX;
                        int bestT = c;
                        for (int t = 0; t < 3; ++t) {
                            if (t == c) continue;
                            int delta = cnt[v][t] - cur_same;
                            if (delta < bestDelta) {
                                bestDelta = delta;
                                bestT = t;
                            }
                        }
                        if (bestT != c) {
                            b += bestDelta;
                            int old = c, nw = bestT;
                            col[v] = nw;
                            for (int u : adj[v]) {
                                cnt[u][old]--;
                                cnt[u][nw]++;
                            }
                            if (b < best_b) {
                                best_b = b;
                                best_col = col;
                                if (best_b == 0) return;
                            }
                        }
                        if (chrono::steady_clock::now() >= deadline) break;
                    }
                    stall = 0;
                }
            } else {
                stall = 0;
            }
            if (chrono::steady_clock::now() >= deadline) break;
        }
    };

    vector<int> best_col(n, 0);
    long long best_b = LLONG_MAX;

    // Multiple attempts: greedy + local search, maybe a random restart if time allows
    int attempts = 0;
    while (chrono::steady_clock::now() < deadline && attempts < 5) {
        vector<int> col(n, 0);
        greedy_init(col);

        vector<array<int,3>> cnt(n);
        long long b = build_cnt_and_b(col, cnt);

        if (b < best_b) {
            best_b = b;
            best_col = col;
            if (best_b == 0) break;
        }

        local_search(col, cnt, b, best_b, best_col);
        attempts++;
    }

    // If time remains and best is not perfect, try a quick random restart
    if (best_b > 0 && chrono::steady_clock::now() < deadline) {
        vector<int> col(n, 0);
        uniform_int_distribution<int> pickC(0,2);
        for (int i = 0; i < n; ++i) col[i] = pickC(rng);
        vector<array<int,3>> cnt(n);
        long long b = build_cnt_and_b(col, cnt);
        if (b < best_b) {
            best_b = b;
            best_col = col;
        }
        auto now = chrono::steady_clock::now();
        if (now < deadline) {
            local_search(col, cnt, b, best_b, best_col);
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_col[i] + 1);
    }
    cout << '\n';
    return 0;
}