#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int n;
std::vector<std::vector<int>> adj;
std::vector<bool> empty_set_state_tracker;

void do_query(const std::vector<int>& q, std::vector<int>& res) {
    if (q.empty()) {
        res.clear();
        return;
    }
    std::cout << q.size();
    for (int x : q) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    res.resize(q.size());
    for (size_t i = 0; i < q.size(); ++i) {
        std::cin >> res[i];
    }
}

void add_edge(int u, int v) {
    adj[u].push_back(v);
    adj[v].push_back(u);
}

void find_edges_between_independent(const std::vector<int>& I1, const std::vector<int>& I2) {
    if (I1.empty() || I2.empty()) {
        return;
    }

    std::vector<int> C2_candidates;
    if (!I2.empty()) {
        std::vector<int> q1;
        q1.reserve(I1.size() + I2.size());
        q1.insert(q1.end(), I1.begin(), I1.end());
        q1.insert(q1.end(), I2.begin(), I2.end());
        
        std::vector<int> res1;
        do_query(q1, res1);

        int last_res = 0; // S becomes I1, which is independent.
        for (size_t i = 0; i < I2.size(); ++i) {
            int current_res = res1[I1.size() + i];
            if (current_res && !last_res) {
                C2_candidates.push_back(I2[i]);
            }
            last_res = current_res;
        }
    }
    
    std::vector<int> C1_candidates;
    if (!I1.empty()) {
        std::vector<int> q2;
        q2.reserve(I1.size() + I2.size());
        q2.insert(q2.end(), I2.begin(), I2.end());
        q2.insert(q2.end(), I1.begin(), I1.end());

        std::vector<int> res2;
        do_query(q2, res2);

        int last_res = 0;
        for (size_t i = 0; i < I1.size(); ++i) {
            int current_res = res2[I2.size() + i];
            if (current_res && !last_res) {
                C1_candidates.push_back(I1[i]);
            }
            last_res = current_res;
        }
    }
    
    if (C1_candidates.empty() || C2_candidates.empty()) {
        return;
    }

    for (int u : C2_candidates) {
        std::vector<int> p_nodes = C1_candidates;
        while (p_nodes.size() > 1) {
            std::vector<int> half1(p_nodes.begin(), p_nodes.begin() + p_nodes.size() / 2);
            std::vector<int> q_half;
            q_half.reserve(half1.size() + 1);
            q_half.insert(q_half.end(), half1.begin(), half1.end());
            q_half.push_back(u);

            std::vector<int> res_half;
            do_query(q_half, res_half);

            if (res_half.back()) {
                p_nodes = half1;
            } else {
                p_nodes.assign(p_nodes.begin() + p_nodes.size() / 2, p_nodes.end());
            }
        }
        if (!p_nodes.empty()) {
             add_edge(u, p_nodes[0]);
        }
    }
}

void solve(const std::vector<int>& nodes) {
    if (nodes.size() <= 1) {
        return;
    }
    
    std::vector<int> V1, V2;
    V1.reserve(nodes.size()/2);
    V2.reserve(nodes.size() - nodes.size()/2);
    for (size_t i = 0; i < nodes.size(); ++i) {
        if (i < nodes.size() / 2) {
            V1.push_back(nodes[i]);
        } else {
            V2.push_back(nodes[i]);
        }
    }

    solve(V1);
    solve(V2);
    
    std::map<int, int> color;
    std::vector<int> V1_0, V1_1, V2_0, V2_1;

    for (int start_node : V1) {
        if (color.find(start_node) == color.end()) {
            std::vector<int> q_bfs;
            q_bfs.push_back(start_node);
            color[start_node] = 0;
            int head = 0;
            while(head < q_bfs.size()){
                int u = q_bfs[head++];
                for(int v : adj[u]){
                    bool is_in_V1 = false;
                    for(int node_v1 : V1) if(v == node_v1) is_in_V1 = true;
                    
                    if(is_in_V1 && color.find(v) == color.end()){
                        color[v] = 1 - color[u];
                        q_bfs.push_back(v);
                    }
                }
            }
        }
    }
    for (int node : V1) {
        if (color[node] == 0) V1_0.push_back(node);
        else V1_1.push_back(node);
    }

    color.clear();
    for (int start_node : V2) {
        if (color.find(start_node) == color.end()) {
            std::vector<int> q_bfs;
            q_bfs.push_back(start_node);
            color[start_node] = 0;
            int head = 0;
            while(head < q_bfs.size()){
                int u = q_bfs[head++];
                for(int v : adj[u]){
                    bool is_in_V2 = false;
                    for(int node_v2 : V2) if(v == node_v2) is_in_V2 = true;

                    if(is_in_V2 && color.find(v) == color.end()){
                        color[v] = 1 - color[u];
                        q_bfs.push_back(v);
                    }
                }
            }
        }
    }
    for (int node : V2) {
        if (color[node] == 0) V2_0.push_back(node);
        else V2_1.push_back(node);
    }
    
    find_edges_between_independent(V1_0, V2_0);
    find_edges_between_independent(V1_0, V2_1);
    find_edges_between_independent(V1_1, V2_0);
    find_edges_between_independent(V1_1, V2_1);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int subtask;
    std::cin >> subtask >> n;

    adj.resize(n + 1);
    std::vector<int> all_nodes(n);
    std::iota(all_nodes.begin(), all_nodes.end(), 1);

    solve(all_nodes);

    std::vector<int> p(n);
    p[0] = 1;
    if(n > 1) {
        p[1] = adj[1][0];
        int prev = 1;
        for (int i = 2; i < n; ++i) {
            int u = p[i - 1];
            int next_node = -1;
            for (int v : adj[u]) {
                if (v != prev) {
                    next_node = v;
                    break;
                }
            }
            p[i] = next_node;
            prev = u;
        }
    }
    
    std::cout << -1;
    for (int i = 0; i < n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}