#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cmath>
#include <functional>

using namespace std;

int n;
vector<vector<int>> adj;

vector<int> do_query(const vector<int>& q) {
    if (q.empty()) {
        return {};
    }
    cout << q.size();
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    vector<int> res(q.size());
    for (size_t i = 0; i < q.size(); ++i) {
        cin >> res[i];
    }
    return res;
}

struct Ask {
    vector<int> p1, p2;
    vector<int> p1_res_indices;
    vector<size_t> p2_res_indices;
};

void solve(const vector<int>& pids, int level, vector<vector<Ask>>& level_asks) {
    if (pids.size() <= 1) {
        return;
    }
    if (pids.size() <= 32) { // Base case
        for (size_t i = 0; i < pids.size(); ++i) {
            for (size_t j = i + 1; j < pids.size(); ++j) {
                level_asks[level].push_back({{pids[i]}, {pids[j]}});
            }
        }
        return;
    }

    vector<int> pids1(pids.begin(), pids.begin() + pids.size() / 2);
    vector<int> pids2(pids.begin() + pids.size() / 2, pids.end());
    
    solve(pids1, level + 1, level_asks);
    solve(pids2, level + 1, level_asks);

    map<int, vector<int>> current_adj;
    for (int pid : pids) {
        for (int neighbor : adj[pid]) {
            current_adj[pid].push_back(neighbor);
        }
    }

    vector<vector<int>> pids1_parts(2), pids2_parts(2);
    map<int, int> pids1_color_map, pids2_color_map;
    
    auto find_components_and_color = [&](const vector<int>& component_pids, map<int, int>& color_map) {
        map<int, bool> visited;
        for (int pid : component_pids) {
            if (!visited[pid]) {
                vector<int> component_nodes;
                vector<int> q_bfs;
                q_bfs.push_back(pid);
                visited[pid] = true;
                int head = 0;
                while(head < q_bfs.size()){
                    int u = q_bfs[head++];
                    component_nodes.push_back(u);
                    for(int v : current_adj[u]){
                        bool is_in_pids = false;
                        for(int p : component_pids) if(v == p) is_in_pids = true;
                        if(is_in_pids && !visited[v]){
                            visited[v] = true;
                            q_bfs.push_back(v);
                        }
                    }
                }
                
                function<void(int, int)>_dfs = 
                    [&](int u, int c) {
                    color_map[u] = c;
                    for (int v : current_adj[u]) {
                        bool is_in_component = false;
                        for(int node : component_nodes) if(v == node) is_in_component = true;
                        if (is_in_component && color_map[v] == 0) {
                            _dfs(v, 3 - c);
                        }
                    }
                };
                _dfs(pid, 1);
            }
        }
    };
    
    find_components_and_color(pids1, pids1_color_map);
    find_components_and_color(pids2, pids2_color_map);
    
    for (int pid : pids1) pids1_parts[pids1_color_map[pid] - 1].push_back(pid);
    for (int pid : pids2) pids2_parts[pids2_color_map[pid] - 1].push_back(pid);

    for (int i = 0; i < 2; ++i) {
        for (int j = 0; j < 2; ++j) {
            if (!pids1_parts[i].empty() && !pids2_parts[j].empty()) {
                level_asks[level].push_back({pids1_parts[i], pids2_parts[j]});
                level_asks[level].push_back({pids2_parts[j], pids1_parts[i]});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int subtask;
    cin >> subtask >> n;

    adj.resize(n + 1);

    int max_levels = 0;
    if (n > 1) max_levels = floor(log2(n/16.0)) + 2;
    if (n <= 32) max_levels = 1;

    vector<vector<Ask>> level_asks(max_levels);

    vector<int> all_pids(n);
    iota(all_pids.begin(), all_pids.end(), 1);

    if (n > 1) {
        solve(all_pids, 0, level_asks);
    }

    for (int l = max_levels - 1; l >= 0; --l) {
        if(level_asks[l].empty()) continue;

        vector<int> query_vec;
        size_t current_res_idx = 0;
        
        for (auto& ask : level_asks[l]) {
            vector<int> p1 = ask.p1, p2 = ask.p2;
            query_vec.insert(query_vec.end(), p1.begin(), p1.end());
            query_vec.insert(query_vec.end(), p2.begin(), p2.end());
            
            for (size_t i = 0; i < p1.size(); ++i) ask.p1_res_indices.push_back(current_res_idx + i);
            current_res_idx += p1.size();
            for (size_t i = 0; i < p2.size(); ++i) ask.p2_res_indices.push_back(current_res_idx + i);
            current_res_idx += p2.size();
        }

        vector<int> full_query = query_vec;
        vector<int> query_vec_rev = query_vec;
        reverse(query_vec_rev.begin(), query_vec_rev.end());
        full_query.insert(full_query.end(), query_vec_rev.begin(), query_vec_rev.end());
        
        vector<int> responses = do_query(full_query);
        vector<int> has_adj_res(responses.begin(), responses.begin() + query_vec.size());

        vector<pair<int, vector<int>>> specific_neighbor_queries;

        for (const auto& ask : level_asks[l]) {
             if (ask.p1.size() == 1 && ask.p2.size() == 1) { // Base case
                if (has_adj_res[ask.p2_res_indices[0]] == 1) {
                    adj[ask.p1[0]].push_back(ask.p2[0]);
                    adj[ask.p2[0]].push_back(ask.p1[0]);
                }
                continue;
            }
            
            bool p1_has_adj = (ask.p1.empty() || ask.p1_res_indices.empty()) ? false : (bool)has_adj_res[ask.p1_res_indices.back()];
            
            int last_res = p1_has_adj;
            for (size_t i = 0; i < ask.p2.size(); ++i) {
                int current_res = has_adj_res[ask.p2_res_indices[i]];
                if (current_res == 1 && last_res == 0) {
                    specific_neighbor_queries.push_back({ask.p2[i], ask.p1});
                }
                last_res = current_res;
            }
        }
        
        if (!specific_neighbor_queries.empty()) {
            vector<int> big_q;
            vector<tuple<int, vector<int>, int>> q_meta;
            for(const auto& sq : specific_neighbor_queries) {
                big_q.push_back(sq.first);
                big_q.insert(big_q.end(), sq.second.begin(), sq.second.end());
                q_meta.emplace_back(sq.first, sq.second, big_q.size() - 1);
                big_q.insert(big_q.end(), sq.second.rbegin(), sq.second.rend());
                big_q.push_back(sq.first);
            }
            vector<int> res_big_q = do_query(big_q);

            int base_idx = 0;
            for(const auto& meta : q_meta) {
                int u = get<0>(meta);
                const vector<int>& p = get<1>(meta);
                int u_on_idx = base_idx;
                int last_res = res_big_q[u_on_idx];
                for (size_t i = 0; i < p.size(); ++i) {
                    int current_res = res_big_q[u_on_idx + 1 + i];
                    if (current_res == 1 && last_res == 0) {
                        int v = p[i];
                        adj[u].push_back(v);
                        adj[v].push_back(u);
                    }
                    last_res = current_res;
                }
                base_idx += 2 * p.size() + 2;
            }
        }
    }

    cout << -1;
    vector<int> p;
    if (n > 0) {
        p.resize(n);
        p[0] = 1;
        if (n > 1) {
            p[1] = adj[1][0];
            for (int i = 2; i < n; ++i) {
                int last = p[i - 1];
                int prev = p[i - 2];
                for (int neighbor : adj[last]) {
                    if (neighbor != prev) {
                        p[i] = neighbor;
                        break;
                    }
                }
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}