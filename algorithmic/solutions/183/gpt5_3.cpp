#include <bits/stdc++.h>
using namespace std;

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
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Deduplicate adjacency lists
    for (int i = 0; i < N; ++i) {
        auto &g = adj[i];
        sort(g.begin(), g.end());
        g.erase(unique(g.begin(), g.end()), g.end());
    }
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();
    // Second-degree scores: sum of neighbor degrees
    vector<int> deg2(N, 0);
    for (int i = 0; i < N; ++i) {
        int s = 0;
        for (int v : adj[i]) s += deg[v];
        deg2[i] = s;
    }
    
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    auto greedy_build = [&](const vector<int>& order, vector<char>& selected_out) -> int {
        selected_out.assign(N, 0);
        vector<char> banned(N, 0);
        int K = 0;
        for (int v : order) {
            if (!banned[v]) {
                selected_out[v] = 1;
                ++K;
                for (int u : adj[v]) banned[u] = 1;
            }
        }
        return K;
    };
    
    auto now = [&]() {
        return chrono::high_resolution_clock::now();
    };
    auto start_time = now();
    double T1 = 1.2;  // seconds for multi-start greedy
    double T2 = 1.85; // seconds for local improvement (total time budget)
    
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    vector<char> best_selected(N, 0), selected_tmp(N, 0);
    int bestK = -1;
    
    vector<uint32_t> rkey(N);
    
    // Multi-start: different orderings
    for (int run = 0; ; ++run) {
        double elapsed = chrono::duration<double>(now() - start_time).count();
        if (elapsed > T1) break;
        // Decide ordering
        int mode = run % 4;
        if (mode == 0) {
            // degree ascending with random tie-break
            for (int i = 0; i < N; ++i) rkey[i] = rng();
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return rkey[a] < rkey[b];
            });
        } else if (mode == 1) {
            // second-degree ascending, then degree, then random
            for (int i = 0; i < N; ++i) rkey[i] = rng();
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return rkey[a] < rkey[b];
            });
        } else if (mode == 2) {
            // degree ascending with stronger randomization: bucketed random within small windows
            for (int i = 0; i < N; ++i) rkey[i] = rng();
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b) {
                int da = deg[a], db = deg[b];
                if (da != db) return da < db;
                return rkey[a] < rkey[b];
            });
            // small local shuffle windows to diversify
            int W = 16;
            for (int i = 0; i < N; i += W) {
                int j = min(N, i + W);
                shuffle(order.begin() + i, order.begin() + j, rng);
            }
        } else {
            // random shuffle
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
        }
        int K = greedy_build(order, selected_tmp);
        if (K > bestK) {
            bestK = K;
            best_selected = selected_tmp;
        }
    }
    
    // 2-improvement local search on the best solution
    auto two_improve = [&](vector<char>& selected, int& K) {
        vector<int> sel_cnt(N, 0);
        for (int v = 0; v < N; ++v) if (selected[v]) {
            for (int u : adj[v]) sel_cnt[u]++;
        }
        vector<char> cand_flag(N, 0);
        vector<int> seen(N, 0);
        int stamp = 1;
        vector<int> cand;
        while (true) {
            double elapsed = chrono::duration<double>(now() - start_time).count();
            if (elapsed > T2) break;
            bool improved = false;
            for (int u = 0; u < N; ++u) {
                double elapsed_inner = chrono::duration<double>(now() - start_time).count();
                if (elapsed_inner > T2) break;
                if (!selected[u]) continue;
                cand.clear();
                for (int v : adj[u]) {
                    if (!selected[v] && sel_cnt[v] == 1) {
                        cand.push_back(v);
                        cand_flag[v] = 1;
                    }
                }
                bool local = false;
                if ((int)cand.size() >= 2) {
                    // Try to find two non-adjacent in cand
                    // randomize iteration order a bit to diversify
                    if ((int)cand.size() > 16) {
                        // shuffle a small prefix to increase diversity
                        int L = min<int>((int)cand.size(), 64);
                        shuffle(cand.begin(), cand.begin() + L, rng);
                    }
                    int L = (int)cand.size();
                    for (int i = 0; i < L && !local; ++i) {
                        int a = cand[i];
                        ++stamp;
                        for (int w : adj[a]) {
                            if (cand_flag[w]) seen[w] = stamp;
                        }
                        for (int j = i + 1; j < L; ++j) {
                            int b = cand[j];
                            if (seen[b] != stamp) {
                                // Found a pair (a, b) non-adjacent
                                // Apply improvement: remove u, add a and b
                                selected[u] = 0;
                                --K;
                                for (int t : adj[u]) --sel_cnt[t];
                                selected[a] = 1;
                                ++K;
                                for (int t : adj[a]) ++sel_cnt[t];
                                selected[b] = 1;
                                ++K;
                                for (int t : adj[b]) ++sel_cnt[t];
                                local = true;
                                improved = true;
                                break;
                            }
                        }
                    }
                }
                for (int x : cand) cand_flag[x] = 0;
                if (improved) break;
            }
            if (!improved) break;
        }
    };
    
    int Kbest = bestK;
    two_improve(best_selected, Kbest);
    // Output solution
    for (int i = 0; i < N; ++i) {
        cout << (best_selected[i] ? 1 : 0) << '\n';
    }
    return 0;
}