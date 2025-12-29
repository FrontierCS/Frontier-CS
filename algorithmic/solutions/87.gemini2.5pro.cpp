#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

const long long INF = 1e18;

int n, m;
vector<int> initial_state;
vector<int> target_state;
vector<vector<int>> adj;

vector<int> bfs(const vector<int>& sources) {
    vector<int> dist(n + 1, 1e9);
    queue<int> q;
    for (int s : sources) {
        dist[s] = 0;
        q.push(s);
    }
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (dist[v] > dist[u] + 1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    return dist;
}

bool check(int k, const vector<int>& d0, const vector<int>& d1, vector<long long>& potentials) {
    vector<long long> L(n + 1), U(n + 1);

    for (int i = 1; i <= n; ++i) {
        if (initial_state[i - 1] == 1) { // M0 node
            L[i] = max({1LL, (long long)d0[i], (long long)d1[i] + 1});
            U[i] = INF;
            if (target_state[i - 1] == 0) {
                U[i] = min(U[i], (long long)k);
            } else {
                L[i] = max(L[i], (long long)k + 1);
            }
        } else { // M1 node
            L[i] = max({1LL, (long long)d1[i], (long long)d0[i] + 1});
            U[i] = INF;
            if (target_state[i - 1] == 1) {
                U[i] = min(U[i], (long long)k);
            } else {
                L[i] = max(L[i], (long long)k + 1);
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (L[i] > U[i]) {
            return false;
        }
    }

    vector<vector<pair<int, int>>> bf_adj(n + 2);
    int s = 0; // source for bellman-ford

    for (int i = 1; i <= n; ++i) {
        bf_adj[s].push_back({i, U[i]});
        bf_adj[i].push_back({s, -L[i]});
    }

    for (int i = 1; i <= n; ++i) {
        bool i_is_m0 = (initial_state[i - 1] == 1);
        for (int neighbor : adj[i]) {
            bool neighbor_is_m0 = (initial_state[neighbor - 1] == 1);
            if (i_is_m0 == neighbor_is_m0) {
                bf_adj[neighbor].push_back({i, 1});
                bf_adj[i].push_back({neighbor, 1});
            } else {
                if (i_is_m0) { // i in M0, neighbor in M1
                    bf_adj[neighbor].push_back({i, 0});
                } else { // i in M1, neighbor in M0
                    bf_adj[neighbor].push_back({i, 0});
                }
            }
        }
    }
    
    potentials.assign(n + 1, INF);
    potentials[s] = 0;
    
    for (int i = 0; i <= n; ++i) {
        bool updated = false;
        for (int u = 0; u <= n; ++u) {
            if (potentials[u] >= INF) continue;
            for (auto& edge : bf_adj[u]) {
                int v = edge.first;
                int w = edge.second;
                if (potentials[v] > potentials[u] + w) {
                    potentials[v] = potentials[u] + w;
                    updated = true;
                }
            }
        }
        if (!updated) break;
    }

    for (int u = 0; u <= n; ++u) {
        if (potentials[u] >= INF) continue;
        for (auto& edge : bf_adj[u]) {
            int v = edge.first;
            int w = edge.second;
            if (potentials[v] > potentials[u] + w) {
                return false; // Negative cycle
            }
        }
    }

    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    initial_state.resize(n);
    target_state.resize(n);
    adj.resize(n + 1);

    vector<int> sources0, sources1;
    for (int i = 0; i < n; ++i) {
        cin >> initial_state[i];
        if (initial_state[i] == 0) {
            sources0.push_back(i + 1);
        } else {
            sources1.push_back(i + 1);
        }
    }
    for (int i = 0; i < n; ++i) {
        cin >> target_state[i];
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> d0 = bfs(sources0);
    vector<int> d1 = bfs(sources1);

    int low = 0, high = 2*n+5, ans_k = high;
    vector<long long> potentials;
    vector<long long> best_potentials;

    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (check(mid, d0, d1, potentials)) {
            ans_k = mid;
            best_potentials = potentials;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    check(ans_k, d0, d1, best_potentials);

    cout << ans_k << endl;
    
    for (int t = 0; t <= ans_k; ++t) {
        for (int i = 0; i < n; ++i) {
            if (initial_state[i] == 1) { // M0
                cout << (best_potentials[i + 1] > t);
            } else { // M1
                cout << (best_potentials[i + 1] <= t);
            }
            if (i < n - 1) {
                cout << " ";
            }
        }
        cout << endl;
    }

    return 0;
}