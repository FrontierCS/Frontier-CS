#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>
#include <tuple>

using namespace std;

// Global to track current S state
vector<int> s_state;

vector<int> perform_query(const vector<int>& ops) {
    if (ops.empty()) return {};
    cout << ops.size();
    for (int x : ops) cout << " " << x;
    cout << endl;
    
    vector<int> res(ops.size());
    for (int i = 0; i < ops.size(); ++i) {
        cin >> res[i];
    }
    return res;
}

vector<int> clear_s_ops() {
    vector<int> ops = s_state;
    s_state.clear();
    return ops;
}

struct RawBits {
    int has_neighbor_mask = 0; 
    int has_zero_mask = 0;     
};
map<pair<int, int>, RawBits> raw_results;

struct DisambiguationRes {
    int u, s_idx, p, k, val;
};
vector<DisambiguationRes> dis_results_vec;

// Meta for batch processing
struct QueryMeta {
    int mode; // 0: Phase 2, 1: Phase 3
    int u, s_idx, bit, type; // For mode 0
    int p, k; // For mode 1
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int subtask, n;
    if (!(cin >> subtask >> n)) return 0;

    mt19937 rng(1337);
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);

    vector<bool> placed(n + 1, false);
    vector<vector<int>> independent_sets;
    int placed_cnt = 0;

    // Phase 1: Partition
    while (placed_cnt < n) {
        vector<int> candidates;
        for (int x : p) {
            if (!placed[x]) candidates.push_back(x);
        }

        vector<int> ops = clear_s_ops();
        ops.insert(ops.end(), candidates.begin(), candidates.end());
        vector<int> res = perform_query(ops);
        
        int offset = ops.size() - candidates.size();
        vector<int> current_is;
        for (int x : candidates) s_state.push_back(x);

        for (int i = 0; i < candidates.size(); ++i) {
            if (res[offset + i] == 0) {
                current_is.push_back(candidates[i]);
            }
        }
        
        for (int x : current_is) {
            placed[x] = true;
            placed_cnt++;
        }
        independent_sets.push_back(current_is);
    }
    
    vector<int> clr = clear_s_ops();
    if(!clr.empty()) perform_query(clr);

    // Phase 2 Preparation
    vector<int> batch_ops;
    vector<int> probe_indices;
    vector<QueryMeta> batch_meta;
    int LIMIT = 8000000;

    auto flush_batch = [&]() {
        if (batch_ops.empty()) return;
        vector<int> res = perform_query(batch_ops);
        
        for (size_t i = 0; i < batch_meta.size(); ++i) {
            int idx = probe_indices[i];
            int val = res[idx];
            const auto& m = batch_meta[i];
            
            if (m.mode == 0) {
                if (val) {
                    if (m.type == 0) raw_results[{m.u, m.s_idx}].has_neighbor_mask |= (1 << m.bit);
                    else raw_results[{m.u, m.s_idx}].has_zero_mask |= (1 << m.bit);
                }
            } else {
                dis_results_vec.push_back({m.u, m.s_idx, m.p, m.k, val});
            }
        }
        batch_ops.clear();
        batch_meta.clear();
        probe_indices.clear();
    };

    int num_sets = independent_sets.size();
    vector<pair<int, int>> pairs;
    for (int i = 0; i < num_sets; ++i) {
        for (int j = 0; j < num_sets; ++j) {
            if (i == j) continue;
            pairs.push_back({i, j});
        }
    }

    // Phase 2 Execution
    for (auto& pr : pairs) {
        int i = pr.first;
        int j = pr.second;
        const auto& S_src = independent_sets[i];
        const auto& S_tgt = independent_sets[j];
        if (S_src.empty() || S_tgt.empty()) continue;

        for (int b = 0; b < 17; ++b) {
            vector<int> T_or, T_and;
            for (int v : S_tgt) {
                if ((v >> b) & 1) T_or.push_back(v);
                else T_and.push_back(v);
            }
            
            if (!T_or.empty()) {
                if (batch_ops.size() + T_or.size() * 2 + S_src.size() * 2 > LIMIT) flush_batch();
                for (int v : T_or) batch_ops.push_back(v);
                for (int u : S_src) {
                    batch_ops.push_back(u);
                    probe_indices.push_back(batch_ops.size() - 1);
                    batch_meta.push_back({0, u, j, b, 0, 0, 0});
                    batch_ops.push_back(u);
                }
                for (int v : T_or) batch_ops.push_back(v);
            }
            if (!T_and.empty()) {
                if (batch_ops.size() + T_and.size() * 2 + S_src.size() * 2 > LIMIT) flush_batch();
                for (int v : T_and) batch_ops.push_back(v);
                for (int u : S_src) {
                    batch_ops.push_back(u);
                    probe_indices.push_back(batch_ops.size() - 1);
                    batch_meta.push_back({0, u, j, b, 1, 0, 0});
                    batch_ops.push_back(u);
                }
                for (int v : T_and) batch_ops.push_back(v);
            }
        }
    }
    flush_batch();

    // Analyze for Disambiguation
    struct DisReq { int u, s_idx, p, k; };
    map<tuple<int, int, int>, vector<int>> req_map;

    for (auto& entry : raw_results) {
        int u = entry.first.first;
        int s_idx = entry.first.second;
        int or_mask = entry.second.has_neighbor_mask;
        int zero_mask = entry.second.has_zero_mask;
        
        if ((or_mask | zero_mask) == 0) continue; 
        
        int full_mask = (1 << 17) - 1;
        int and_mask = (~zero_mask) & full_mask;
        int diff = or_mask ^ and_mask;
        
        if (diff != 0) {
            int p = 0;
            while (!((diff >> p) & 1)) p++;
            for (int k = p + 1; k < 17; ++k) {
                if ((diff >> k) & 1) {
                    req_map[{s_idx, p, k}].push_back(u);
                }
            }
        }
    }

    // Phase 3 Execution
    for (auto& group : req_map) {
        int s_idx = get<0>(group.first);
        int p = get<1>(group.first);
        int k = get<2>(group.first);
        const vector<int>& us = group.second;
        
        vector<int> T;
        for (int v : independent_sets[s_idx]) {
            if ( !((v >> p) & 1) && !((v >> k) & 1) ) T.push_back(v);
        }
        
        if (T.empty()) {
            for (int u : us) dis_results_vec.push_back({u, s_idx, p, k, 0});
            continue;
        }
        
        if (batch_ops.size() + T.size() * 2 + us.size() * 2 > LIMIT) flush_batch();
        for (int v : T) batch_ops.push_back(v);
        for (int u : us) {
            batch_ops.push_back(u);
            probe_indices.push_back(batch_ops.size() - 1);
            batch_meta.push_back({1, u, s_idx, 0, 0, p, k});
            batch_ops.push_back(u);
        }
        for (int v : T) batch_ops.push_back(v);
    }
    flush_batch();

    // Build Graph
    map<tuple<int, int, int, int>, int> dis_res_map;
    for (const auto& res : dis_results_vec) {
        dis_res_map[{res.u, res.s_idx, res.p, res.k}] = res.val;
    }

    vector<vector<int>> adj(n + 1);
    auto add_edge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };

    for (auto& entry : raw_results) {
        int u = entry.first.first;
        int s_idx = entry.first.second;
        int or_mask = entry.second.has_neighbor_mask;
        int zero_mask = entry.second.has_zero_mask;
        
        if ((or_mask | zero_mask) == 0) continue;

        int full_mask = (1 << 17) - 1;
        int and_mask = (~zero_mask) & full_mask;
        int diff = or_mask ^ and_mask;

        if (diff == 0) {
            add_edge(u, or_mask);
        } else {
            int p = 0;
            while (!((diff >> p) & 1)) p++;
            
            // Reconstruct x and y
            // x has bit p=0, y has bit p=1
            int x = and_mask; // base
            int y = and_mask | (1 << p);
            
            // For other bits in diff
            for (int k = 0; k < 17; ++k) {
                if (k == p) continue;
                if ((diff >> k) & 1) {
                    if (k < p) {
                        // Impossible as p is lowest
                    } else {
                        // Check result
                        int match_zero = 0;
                        if (dis_res_map.count({u, s_idx, p, k})) match_zero = dis_res_map[{u, s_idx, p, k}];
                        // match_zero=1 means neighbor with p=0 has k=0
                        if (match_zero) {
                            // x (p=0) has k=0. y must have k=1.
                            y |= (1 << k);
                        } else {
                            // x (p=0) has k=1. y must have k=0.
                            x |= (1 << k);
                        }
                    }
                }
            }
            add_edge(u, x);
            add_edge(u, y);
        }
    }

    // Traverse Cycle
    vector<int> res_p;
    vector<bool> vis(n + 1, false);
    int curr = 1;
    for(int i=0; i<n; ++i) {
        res_p.push_back(curr);
        vis[curr] = true;
        for (int nxt : adj[curr]) {
            if (!vis[nxt]) {
                curr = nxt;
                break;
            }
        }
    }

    cout << "-1";
    for (int x : res_p) cout << " " << x;
    cout << endl;

    return 0;
}