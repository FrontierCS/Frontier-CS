#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        ++deg[u];
        ++deg[v];
    }

    // Helper to compute total conflicting edges from conflict array
    auto compute_b = [](const vector<int>& conf) -> long long {
        long long sum = 0;
        for (int x : conf) sum += x;
        return sum / 2;
    };

    // Helper to compute conflict array from a coloring
    auto compute_conflict = [&](const vector<int>& col, vector<int>& conf) {
        fill(conf.begin(), conf.end(), 0);
        for (int u = 0; u < n; ++u) {
            for (int v : adj[u]) {
                if (col[u] == col[v]) {
                    conf[u]++;
                }
            }
        }
    };

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // ---------- Greedy initialization ----------
    vector<int> color_greedy(n, -1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    // sort by degree descending
    sort(order.begin(), order.end(), [&](int a, int b) { return deg[a] > deg[b]; });
    for (int v : order) {
        int cnt[3] = {0, 0, 0};
        for (int u : adj[v]) {
            if (color_greedy[u] != -1) {
                cnt[color_greedy[u]]++;
            }
        }
        // choose color with smallest count, break ties randomly
        int best = 0;
        for (int c = 1; c < 3; ++c) {
            if (cnt[c] < cnt[best]) {
                best = c;
            } else if (cnt[c] == cnt[best] && uniform_int_distribution<>(0,1)(rng)) {
                best = c;
            }
        }
        color_greedy[v] = best;
    }

    vector<int> conflict_greedy(n);
    compute_conflict(color_greedy, conflict_greedy);
    long long b_greedy = compute_b(conflict_greedy);
    vector<int> best_color = color_greedy;
    long long best_b = b_greedy;

    // ---------- Local search function ----------
    auto local_search = [&](vector<int>& col, vector<int>& conf, long long& b, int max_iter) {
        int n = col.size();
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 0);
        for (int iter = 0; iter < max_iter; ++iter) {
            bool improved = false;
            shuffle(perm.begin(), perm.end(), rng);
            for (int v : perm) {
                int cnt[3] = {0, 0, 0};
                for (int u : adj[v]) {
                    cnt[col[u]]++;
                }
                int old_c = col[v];
                int old_conf = cnt[old_c];
                int best_c = old_c;
                int min_conf = old_conf;
                for (int c = 0; c < 3; ++c) {
                    if (c == old_c) continue;
                    if (cnt[c] < min_conf) {
                        min_conf = cnt[c];
                        best_c = c;
                    }
                }
                if (best_c != old_c) {
                    improved = true;
                    // update total conflicts
                    b += (min_conf - old_conf);
                    // update vertex color
                    col[v] = best_c;
                    // update its conflict count
                    conf[v] = min_conf;
                    // update neighbors' conflict counts
                    for (int u : adj[v]) {
                        if (col[u] == old_c) {
                            conf[u]--;
                        } else if (col[u] == best_c) {
                            conf[u]++;
                        }
                    }
                }
            }
            if (!improved) break;
        }
    };

    // ---------- Improve greedy coloring ----------
    local_search(color_greedy, conflict_greedy, b_greedy, 100);
    if (b_greedy < best_b) {
        best_b = b_greedy;
        best_color = color_greedy;
    }

    // ---------- Random restarts ----------
    const int num_restarts = 5;
    for (int restart = 0; restart < num_restarts; ++restart) {
        vector<int> col_rand(n);
        for (int i = 0; i < n; ++i) {
            col_rand[i] = uniform_int_distribution<>(0, 2)(rng);
        }
        vector<int> conf_rand(n);
        compute_conflict(col_rand, conf_rand);
        long long b_rand = compute_b(conf_rand);
        local_search(col_rand, conf_rand, b_rand, 100);
        if (b_rand < best_b) {
            best_b = b_rand;
            best_color = col_rand;
        }
    }

    // ---------- Output ----------
    for (int i = 0; i < n; ++i) {
        cout << best_color[i] + 1 << " \n"[i == n-1];
    }

    return 0;
}