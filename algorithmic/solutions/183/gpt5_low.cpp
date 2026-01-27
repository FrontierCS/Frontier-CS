#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<int>> adj(N + 1);
    adj.reserve(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(N + 1);
    for (int i = 1; i <= N; ++i) deg[i] = (int)adj[i].size();

    // Random engine
    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    // Helper arrays reused
    vector<unsigned char> blocked(N + 1, 0);
    vector<unsigned char> picked(N + 1, 0);
    vector<unsigned char> bestPicked(N + 1, 0);

    auto run_with_order = [&](const vector<int>& order)->int{
        fill(blocked.begin(), blocked.end(), 0);
        fill(picked.begin(), picked.end(), 0);
        int cnt = 0;
        for (int v : order) {
            if (!blocked[v]) {
                picked[v] = 1;
                ++cnt;
                blocked[v] = 1;
                for (int u : adj[v]) blocked[u] = 1;
            }
        }
        return cnt;
    };

    int bestK = 0;

    // Run deterministic ascending-degree order
    vector<int> order(N);
    iota(order.begin(), order.end(), 1);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });
    {
        int k = run_with_order(order);
        if (k > bestK) {
            bestK = k;
            bestPicked = picked;
        }
    }

    // Run degree order with random tie-breaking once
    {
        vector<pair<pair<int,uint32_t>, int>> arr;
        arr.reserve(N);
        for (int i = 1; i <= N; ++i) {
            uint32_t r = rng();
            arr.push_back({{deg[i], r}, i});
        }
        sort(arr.begin(), arr.end(), [](const auto& A, const auto& B){
            if (A.first.first != B.first.first) return A.first.first < B.first.first;
            return A.first.second < B.first.second;
        });
        for (int i = 0; i < N; ++i) order[i] = arr[i].second;
        int k = run_with_order(order);
        if (k > bestK) {
            bestK = k;
            bestPicked = picked;
        }
    }

    // Time-bounded random restarts
    auto start = chrono::steady_clock::now();
    const double time_limit_sec = 1.8;
    int iterations = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > time_limit_sec) break;
        // Random permutation
        for (int i = N - 1; i > 0; --i) {
            int j = (int)(rng() % (uint32_t)(i + 1));
            swap(order[i], order[j]);
        }
        int k = run_with_order(order);
        if (k > bestK) {
            bestK = k;
            bestPicked = picked;
        }
        ++iterations;
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << (bestPicked[i] ? 1 : 0) << '\n';
    }
    return 0;
}