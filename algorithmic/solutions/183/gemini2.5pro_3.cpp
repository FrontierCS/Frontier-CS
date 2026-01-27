#include <iostream>
#include <vector>
#include <algorithm>
#include <list>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();
    
    int n, m;
    std::cin >> n >> m;
    
    std::vector<std::pair<int, int>> edge_list;
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edge_list.push_back({u, v});
    }

    std::sort(edge_list.begin(), edge_list.end());
    edge_list.erase(std::unique(edge_list.begin(), edge_list.end()), edge_list.end());

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> degree(n + 1, 0);

    for (const auto& edge : edge_list) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    std::vector<std::list<int>> nodes_by_degree(n);
    std::vector<std::list<int>::iterator> pos_in_list(n + 1);
    
    for (int i = 1; i <= n; ++i) {
        nodes_by_degree[degree[i]].push_front(i);
        pos_in_list[i] = nodes_by_degree[degree[i]].begin();
    }
    
    std::vector<int> solution(n + 1, 0);
    std::vector<bool> removed(n + 1, false);
    std::vector<bool> is_being_removed(n + 1, false);
    int min_curr_degree = 0;
    int vertices_left = n;
    
    while (vertices_left > 0) {
        while (min_curr_degree < n && nodes_by_degree[min_curr_degree].empty()) {
            min_curr_degree++;
        }
        if (min_curr_degree == n) break;
        
        int u = nodes_by_degree[min_curr_degree].front();
        
        solution[u] = 1;
        
        std::vector<int> to_remove_now;
        
        to_remove_now.push_back(u);
        is_being_removed[u] = true;

        for (int v : adj[u]) {
            if (!removed[v] && !is_being_removed[v]) {
                to_remove_now.push_back(v);
                is_being_removed[v] = true;
            }
        }
        
        for (int v : to_remove_now) {
            removed[v] = true;
            vertices_left--;
            
            nodes_by_degree[degree[v]].erase(pos_in_list[v]);
            
            for (int w : adj[v]) {
                if (!removed[w] && !is_being_removed[w]) {
                    nodes_by_degree[degree[w]].erase(pos_in_list[w]);
                    degree[w]--;
                    nodes_by_degree[degree[w]].push_front(w);
                    pos_in_list[w] = nodes_by_degree[degree[w]].begin();
                    if (degree[w] < min_curr_degree) {
                        min_curr_degree = degree[w];
                    }
                }
            }
        }
        
        for (int v : to_remove_now) {
            is_being_removed[v] = false;
        }
    }
    
    for (int i = 1; i <= n; ++i) {
        std::cout << solution[i] << "\n";
    }
    
    return 0;
}