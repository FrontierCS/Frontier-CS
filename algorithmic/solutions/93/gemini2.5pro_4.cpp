#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int n, ty;
std::vector<int> par;

int do_query(const std::vector<int>& nodes) {
    std::cout << "? " << nodes.size();
    for (int node : nodes) {
        std::cout << " " << node;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> ty;

    par.resize(n + 1, 0);

    int root = -1;
    if (n > 1) {
        std::vector<int> all_nodes_except_i;
        for (int j = 2; j <= n; ++j) all_nodes_except_i.push_back(j);

        for (int i = 1; i <= n; ++i) {
            std::vector<int> query_nodes;
            query_nodes.push_back(i);
            query_nodes.insert(query_nodes.end(), all_nodes_except_i.begin(), all_nodes_except_i.end());
            
            if (do_query(query_nodes) == 1) {
                root = i;
                break;
            }
            if (i < n) {
                // To avoid re-creating the vector, we swap `i` into the position of `i+1`
                auto it = std::find(all_nodes_except_i.begin(), all_nodes_except_i.end(), i + 1);
                if (it != all_nodes_except_i.end()) {
                    *it = i;
                }
            }
        }
    } else {
        root = 1;
    }
    
    par[root] = 0;

    if (n == 1) {
        std::cout << "! 0" << std::endl;
        return 0;
    }
    
    std::vector<int> non_root_nodes;
    for(int i = 1; i <= n; ++i) {
        if (i != root) {
            non_root_nodes.push_back(i);
        }
    }

    std::vector<std::vector<int>> Rel(n + 1);
    for (int i = 0; i < (int)non_root_nodes.size(); ++i) {
        for (int j = i + 1; j < (int)non_root_nodes.size(); ++j) {
            int u = non_root_nodes[i];
            int v = non_root_nodes[j];
            if (do_query({u, v, root}) == 1) {
                Rel[u].push_back(v);
                Rel[v].push_back(u);
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i == root) {
            Rel[i] = non_root_nodes;
        } else {
            Rel[i].push_back(root);
        }
    }

    for (int u : non_root_nodes) {
        std::vector<int> ancestors_of_u;
        for (int v : Rel[u]) {
            if (u == v) continue;
            
            if (Rel[u].size() <= Rel[v].size()) {
                bool is_subset = true;
                std::vector<bool> v_rel_flags(n + 1, false);
                for(int node : Rel[v]) v_rel_flags[node] = true;
                for(int node : Rel[u]) {
                    if(!v_rel_flags[node]) {
                        is_subset = false;
                        break;
                    }
                }
                if (is_subset) {
                    ancestors_of_u.push_back(v);
                }
            }
        }
        
        int parent_of_u = -1;
        size_t max_ancestors_count = 0;

        for (int v : ancestors_of_u) {
            size_t v_ancestor_count = 0;
            for(int w : ancestors_of_u){
                if(v==w) continue;
                bool w_is_ancestor_of_v = false;
                if (Rel[v].size() <= Rel[w].size()) {
                     bool is_subset = true;
                    std::vector<bool> w_rel_flags(n + 1, false);
                    for(int node : Rel[w]) w_rel_flags[node] = true;
                    for(int node : Rel[v]) {
                        if(!w_rel_flags[node]) {
                            is_subset = false;
                            break;
                        }
                    }
                    if(is_subset) v_ancestor_count++;
                }
            }

            if (parent_of_u == -1 || v_ancestor_count > max_ancestors_count) {
                max_ancestors_count = v_ancestor_count;
                parent_of_u = v;
            }
        }
        par[u] = parent_of_u;
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << par[i];
    }
    std::cout << std::endl;

    return 0;
}