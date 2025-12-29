#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m_input, k;
    double eps;
    cin >> n >> m_input >> k >> eps;

    vector<pair<int,int>> edges;
    edges.reserve(m_input);
    for (int i = 0; i < m_input; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        edges.emplace_back(u, v);
    }
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    int m = edges.size();

    vector<vector<int>> adj(n);
    for (auto& e : edges) {
        adj[e.first].push_back(e.second);
        adj[e.second].push_back(e.first);
    }

    int ideal = (n + k - 1) / k;
    int max_part_size = floor((1.0 + eps) * ideal);

    vector<int> part(n, -1);
    vector<int> part_sizes(k, 0);
    int base = n / k;
    int extra = n % k;
    vector<int> targets(k, base);
    for (int i = 0; i < extra; ++i) targets[i] = base + 1;

    vector<int> part_order(k);
    iota(part_order.begin(), part_order.end(), 0);
    shuffle(part_order.begin(), part_order.end(), mt19937(random_device{}()));

    vector<int> vertices(n);
    iota(vertices.begin(), vertices.end(), 0);
    shuffle(vertices.begin(), vertices.end(), mt19937(random_device{}()));

    int idx = 0;
    for (int p_idx = 0; p_idx < k; ++p_idx) {
        int p = part_order[p_idx];
        int cnt = targets[p];
        for (int j = 0; j < cnt; ++j) {
            int v = vertices[idx++];
            part[v] = p;
            part_sizes[p]++;
        }
    }

    // ---------- EC refinement ----------
    int num_ec_passes = 10;
    bool use_vector = (k <= 2048);
    for (int pass = 0; pass < num_ec_passes; ++pass) {
        bool improved = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), mt19937(random_device{}()));

        for (int v : order) {
            int cur_part = part[v];
            vector<int> cnt_vec;
            unordered_map<int, int> cnt_map;
            vector<int> used_parts;

            if (use_vector) {
                cnt_vec.assign(k, 0);
                for (int u : adj[v]) {
                    int p = part[u];
                    if (cnt_vec[p]++ == 0) used_parts.push_back(p);
                }
            } else {
                for (int u : adj[v]) {
                    int p = part[u];
                    cnt_map[p]++;
                }
            }

            int cur_cnt = (use_vector ? cnt_vec[cur_part] : cnt_map[cur_part]);
            int best_gain = 0, best_part = -1;

            if (use_vector) {
                for (int p : used_parts) {
                    if (p == cur_part) continue;
                    int gain = cnt_vec[p] - cur_cnt;
                    if (gain > best_gain && part_sizes[p] < max_part_size) {
                        best_gain = gain;
                        best_part = p;
                    }
                }
            } else {
                for (auto& it : cnt_map) {
                    int p = it.first;
                    if (p == cur_part) continue;
                    int gain = it.second - cur_cnt;
                    if (gain > best_gain && part_sizes[p] < max_part_size) {
                        best_gain = gain;
                        best_part = p;
                    }
                }
            }

            if (best_gain > 0) {
                part_sizes[cur_part]--;
                part_sizes[best_part]++;
                part[v] = best_part;
                improved = true;
            }
        }
        if (!improved) break;
    }

    // ---------- CV refinement ----------
    int num_cv_passes = 10;
    for (int pass = 0; pass < num_cv_passes; ++pass) {
        bool improved = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), mt19937(random_device{}()));

        for (int v : order) {
            int cur_part = part[v];
            vector<int> cnt_vec;
            unordered_map<int, int> cnt_map;
            vector<int> used_parts;

            if (use_vector) {
                cnt_vec.assign(k, 0);
                for (int u : adj[v]) {
                    int p = part[u];
                    if (cnt_vec[p]++ == 0) used_parts.push_back(p);
                }
            } else {
                for (int u : adj[v]) {
                    int p = part[u];
                    cnt_map[p]++;
                }
            }

            int cur_F = 0;
            if (use_vector) {
                for (int p : used_parts) {
                    if (p != cur_part) cur_F++;
                }
            } else {
                for (auto& it : cnt_map) {
                    if (it.first != cur_part) cur_F++;
                }
            }

            int best_gain = -1, best_part = -1;
            if (use_vector) {
                for (int cand_part : used_parts) {
                    if (cand_part == cur_part) continue;
                    if (part_sizes[cand_part] >= max_part_size) continue;
                    int new_F = 0;
                    for (int p : used_parts) {
                        if (p != cand_part) new_F++;
                    }
                    int delta_F = new_F - cur_F;
                    int cur_cnt = cnt_vec[cur_part];
                    int cand_cnt = cnt_vec[cand_part];
                    int delta_EC = cand_cnt - cur_cnt;
                    if (delta_EC >= 0 && delta_F < 0) {
                        int gain = -delta_F + delta_EC;
                        if (gain > best_gain) {
                            best_gain = gain;
                            best_part = cand_part;
                        }
                    }
                }
            } else {
                for (auto& it : cnt_map) {
                    int cand_part = it.first;
                    if (cand_part == cur_part) continue;
                    if (part_sizes[cand_part] >= max_part_size) continue;
                    int new_F = 0;
                    for (auto& it2 : cnt_map) {
                        if (it2.first != cand_part) new_F++;
                    }
                    int delta_F = new_F - cur_F;
                    int cur_cnt = cnt_map[cur_part];
                    int cand_cnt = it.second;
                    int delta_EC = cand_cnt - cur_cnt;
                    if (delta_EC >= 0 && delta_F < 0) {
                        int gain = -delta_F + delta_EC;
                        if (gain > best_gain) {
                            best_gain = gain;
                            best_part = cand_part;
                        }
                    }
                }
            }

            if (best_part != -1) {
                part_sizes[cur_part]--;
                part_sizes[best_part]++;
                part[v] = best_part;
                improved = true;
            }
        }
        if (!improved) break;
    }

    for (int i = 0; i < n; ++i) {
        cout << part[i] + 1 << (i + 1 == n ? '\n' : ' ');
    }

    return 0;
}