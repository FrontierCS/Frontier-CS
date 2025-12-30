#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>

using namespace std;

typedef long long ll;

struct Query {
    int d;
    vector<pair<int, int>> probes;
    vector<ll> response;
};

int B_limit;
int K;
int W_max;
vector<Query> history_queries;
vector<ll> U, V;
bool adj[25][25];
int match_l[25], match_r[25];
bool vis[25];

// Helper to interact
vector<ll> query(vector<pair<int, int>> probes) {
    cout << "? " << probes.size();
    for (auto p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
    vector<ll> resp(probes.size() * K);
    for (int i = 0; i < (int)probes.size() * K; ++i) {
        cin >> resp[i];
    }
    return resp;
}

bool dfs(int u) {
    for (int v = 0; v < K; ++v) {
        if (adj[u][v] && !vis[v]) {
            vis[v] = true;
            if (match_r[v] < 0 || dfs(match_r[v])) {
                match_l[u] = v;
                match_r[v] = u;
                return true;
            }
        }
    }
    return false;
}

bool solve_matching() {
    fill(match_l, match_l + K, -1);
    fill(match_r, match_r + K, -1);
    int cnt = 0;
    for (int i = 0; i < K; ++i) {
        fill(vis, vis + K, false);
        if (dfs(i)) cnt++;
    }
    return cnt == K;
}

bool verify_solution(const vector<pair<int, int>>& points) {
    // Check against all history
    for (const auto& q : history_queries) {
        vector<ll> expected;
        expected.reserve(points.size() * q.probes.size());
        for (auto p : points) {
            for (auto probe : q.probes) {
                expected.push_back((ll)abs(p.first - probe.first) + (ll)abs(p.second - probe.second));
            }
        }
        sort(expected.begin(), expected.end());
        if (expected != q.response) return false;
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> B_limit >> K >> W_max)) return 0;

    // Use a fixed large coordinate for initial scanning
    int M = 100000000; 

    // Query 1: (-M, -M) -> gives x + y + 2M
    // x in [-B, B] -> x >= -10^8 >= -M
    // |x - (-M)| = x + M
    // dist = x + y + 2M
    vector<pair<int, int>> q1_probes = {{-M, -M}};
    vector<ll> r1 = query(q1_probes);
    history_queries.push_back({1, q1_probes, r1});
    for (ll val : r1) U.push_back(val - 2LL * M);

    // Query 2: (-M, M) -> gives x - y + 2M
    // |x - (-M)| + |y - M| = (x + M) + (M - y) = x - y + 2M
    // Valid since y <= B <= M
    vector<pair<int, int>> q2_probes = {{-M, M}};
    vector<ll> r2 = query(q2_probes);
    history_queries.push_back({1, q2_probes, r2});
    for (ll val : r2) V.push_back(val - 2LL * M);

    // Initialize adjacency matrix based on bounds
    for (int i = 0; i < K; ++i) {
        for (int j = 0; j < K; ++j) {
            ll sum = U[i];
            ll diff = V[j];
            // x + y = sum, x - y = diff
            // 2x = sum + diff, 2y = sum - diff
            if (abs(sum + diff) % 2 != 0) {
                adj[i][j] = false;
            } else {
                ll x = (sum + diff) / 2;
                ll y = (sum - diff) / 2;
                if (x >= -B_limit && x <= B_limit && y >= -B_limit && y <= B_limit) {
                    adj[i][j] = true;
                } else {
                    adj[i][j] = false;
                }
            }
        }
    }

    // Random generator
    mt19937 rng(1337);
    uniform_int_distribution<int> dist_coord(-100000000, 100000000);

    while (true) {
        // Try to find a matching
        if (solve_matching()) {
            vector<pair<int, int>> points;
            for (int i = 0; i < K; ++i) {
                int j = match_l[i];
                ll x = (U[i] + V[j]) / 2;
                ll y = (U[i] - V[j]) / 2;
                points.push_back({(int)x, (int)y});
            }

            if (verify_solution(points)) {
                // Found!
                cout << "!";
                for (auto p : points) {
                    cout << " " << p.first << " " << p.second;
                }
                cout << endl;
                return 0;
            }
        }

        // If not found or not verified, add a random query
        int sx = dist_coord(rng);
        int sy = dist_coord(rng);
        vector<pair<int, int>> q_probes = {{sx, sy}};
        vector<ll> resp = query(q_probes);
        history_queries.push_back({1, q_probes, resp});

        // Filter edges
        // Edge (i, j) is valid only if dist(P_ij, probe) exists in response
        for (int i = 0; i < K; ++i) {
            for (int j = 0; j < K; ++j) {
                if (adj[i][j]) {
                    ll x = (U[i] + V[j]) / 2;
                    ll y = (U[i] - V[j]) / 2;
                    ll d = abs(x - sx) + abs(y - sy);
                    
                    auto it = lower_bound(resp.begin(), resp.end(), d);
                    if (it == resp.end() || *it != d) {
                        adj[i][j] = false;
                    }
                }
            }
        }
    }

    return 0;
}