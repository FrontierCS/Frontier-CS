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
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }
    m = (int)edges.size();
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }
    
    auto now = [](){ return chrono::steady_clock::now(); };
    auto ms = [](auto d){ return chrono::duration_cast<chrono::milliseconds>(d).count(); };
    auto start_time = now();
    const long long TIME_LIMIT_MS = 1800; // soft time budget
    
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    auto build_sumOpp_and_cut = [&](const vector<int>& side, vector<int>& sumOpp, long long& cut) {
        fill(sumOpp.begin(), sumOpp.end(), 0);
        cut = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if ((side[u] ^ side[v]) == 1) {
                sumOpp[u]++; sumOpp[v]++;
                cut++;
            }
        }
    };
    
    auto local_improve = [&](vector<int>& side, vector<int>& sumOpp, long long& cut) {
        int n_local = (int)side.size();
        vector<int> gain(n_local);
        vector<char> in_stack(n_local, 0);
        vector<int> st;
        st.reserve(n_local * 2);
        for (int i = 0; i < n_local; ++i) {
            gain[i] = deg[i] - 2 * sumOpp[i];
            if (gain[i] > 0) {
                st.push_back(i);
                in_stack[i] = 1;
            }
        }
        while (!st.empty()) {
            int v = st.back(); st.pop_back();
            in_stack[v] = 0;
            if (gain[v] <= 0) continue;
            int oldSide = side[v];
            side[v] ^= 1;
            cut += gain[v];
            sumOpp[v] = deg[v] - sumOpp[v];
            gain[v] = -gain[v];
            for (int u : adj[v]) {
                if (side[u] == oldSide) sumOpp[u] += 1;
                else sumOpp[u] -= 1;
                int newGain = deg[u] - 2 * sumOpp[u];
                if (newGain > 0 && !in_stack[u]) {
                    st.push_back(u);
                    in_stack[u] = 1;
                }
                gain[u] = newGain;
            }
        }
    };
    
    vector<int> bestSide(n, 0);
    long long bestCut = -1;
    
    int run_id = 0;
    while (ms(now() - start_time) < TIME_LIMIT_MS) {
        vector<int> side(n, 0);
        if (run_id == 0) {
            // BFS parity initialization
            vector<int> vis(n, 0);
            deque<int> dq;
            for (int i = 0; i < n; ++i) {
                if (vis[i]) continue;
                vis[i] = 1;
                side[i] = 0;
                dq.push_back(i);
                while (!dq.empty()) {
                    int v = dq.front(); dq.pop_front();
                    for (int u : adj[v]) {
                        if (!vis[u]) {
                            vis[u] = 1;
                            side[u] = side[v] ^ 1;
                            dq.push_back(u);
                        }
                    }
                }
            }
        } else if (run_id == 1) {
            // Greedy constructive by degree
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });
            vector<int> assigned(n, 0);
            fill(side.begin(), side.end(), -1);
            for (int v : order) {
                int c0 = 0, c1 = 0;
                for (int u : adj[v]) {
                    if (side[u] == 0) c0++;
                    else if (side[u] == 1) c1++;
                }
                if (c0 > c1) side[v] = 1;
                else if (c1 > c0) side[v] = 0;
                else side[v] = (int)(rng() & 1);
                assigned[v] = 1;
            }
            for (int i = 0; i < n; ++i) if (side[i] == -1) side[i] = (int)(rng() & 1);
        } else {
            // Random initialization
            for (int i = 0; i < n; ++i) side[i] = (int)(rng() & 1);
        }
        
        vector<int> sumOpp(n, 0);
        long long cut = 0;
        build_sumOpp_and_cut(side, sumOpp, cut);
        local_improve(side, sumOpp, cut);
        
        if (cut > bestCut) {
            bestCut = cut;
            bestSide = side;
        }
        
        ++run_id;
        if (run_id > 100000) break; // safety
        if (ms(now() - start_time) >= TIME_LIMIT_MS) break;
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestSide[i];
    }
    cout << '\n';
    return 0;
}