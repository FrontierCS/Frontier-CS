#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <functional>

int subtask, n;
std::vector<std::vector<int>> adj;
std::vector<int> degree;

// Function to perform a query to the interactive system.
// It sends a list of operations and receives a list of results.
std::vector<int> ask(const std::vector<int>& ops) {
    if (ops.empty()) {
        return {};
    }
    std::cout << ops.size();
    for (int x : ops) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    std::vector<int> res(ops.size());
    for (size_t i = 0; i < ops.size(); ++i) {
        std::cin >> res[i];
    }
    return res;
}

// Helper function to add an edge between two nodes and update their degrees.
void add_edge(int u, int v) {
    adj[u].push_back(v);
    adj[v].push_back(u);
    degree[u]++;
    degree[v]++;
}

void find_cross_edges(std::vector<int> U, std::vector<int> W);

// Main recursive function to find all edges in a set of vertices V.
// It uses a divide and conquer approach.
void find_edges(const std::vector<int>& V) {
    if (V.size() <= 1) {
        return;
    }
    
    int mid = V.size() / 2;
    std::vector<int> V1(V.begin(), V.begin() + mid);
    std::vector<int> V2(V.begin() + mid, V.end());
    
    find_edges(V1);
    find_edges(V2);
    
    std::vector<int> U_cand, W_cand;
    for(int u : V1) {
        if (degree[u] < 2) U_cand.push_back(u);
    }
    for(int w : V2) {
        if (degree[w] < 2) W_cand.push_back(w);
    }
    
    find_cross_edges(U_cand, W_cand);
}

// Recursive function to find edges between two disjoint sets of vertices U and W.
void find_cross_edges(std::vector<int> U, std::vector<int> W) {
    if (U.empty() || W.empty()) {
        return;
    }

    if (U.size() > W.size()) {
        std::swap(U, W);
    }

    if (W.size() == 1) {
        int w = W[0];
        if (degree[w] >= 2) return;
        
        std::vector<int> u_cand;
        for (int u : U) {
            if (degree[u] < 2) {
                u_cand.push_back(u);
            }
        }
        if (u_cand.empty()) return;

        ask({w}); // Turn on w, S = {w}
        
        std::vector<int> test_ops;
        for (int u : u_cand) {
            test_ops.push_back(u);
            test_ops.push_back(u);
        }
        std::vector<int> res = ask(test_ops); // Toggle each candidate
        
        for (size_t i = 0; i < u_cand.size(); ++i) {
            if (res[2 * i] == 1) { // An edge exists
                if (degree[u_cand[i]] < 2 && degree[w] < 2) {
                    add_edge(u_cand[i], w);
                }
            }
        }
        
        ask({w}); // Turn off w, S = {}
        return;
    }

    int mid = W.size() / 2;
    std::vector<int> W1(W.begin(), W.begin() + mid);
    std::vector<int> W2(W.begin() + mid, W.end());

    std::vector<int> u_cand_1;
    for (int u : U) {
        if (degree[u] < 2) {
            u_cand_1.push_back(u);
        }
    }
    
    std::vector<int> U1;
    if (!u_cand_1.empty()) {
        std::vector<int> res_w1 = ask(W1);
        int R_W1 = res_w1.empty() ? 0 : res_w1.back();
        
        std::vector<int> test_ops;
        for (int u : u_cand_1) {
            test_ops.push_back(u);
            test_ops.push_back(u);
        }
        std::vector<int> res = ask(test_ops);
        
        for (size_t i = 0; i < u_cand_1.size(); ++i) {
            if (res[2*i] > R_W1) {
                U1.push_back(u_cand_1[i]);
            }
        }
        ask(W1); // Clear S
    }

    find_cross_edges(U1, W1);

    std::vector<int> u_cand_2;
    for (int u : U) {
        if (degree[u] < 2) {
            u_cand_2.push_back(u);
        }
    }
    
    std::vector<int> U2;
    if (!u_cand_2.empty()) {
        std::vector<int> res_w2 = ask(W2);
        int R_W2 = res_w2.empty() ? 0 : res_w2.back();
        
        std::vector<int> test_ops;
        for (int u : u_cand_2) {
            test_ops.push_back(u);
            test_ops.push_back(u);
        }
        std::vector<int> res = ask(test_ops);
        
        for (size_t i = 0; i < u_cand_2.size(); ++i) {
            if (res[2*i] > R_W2) {
                U2.push_back(u_cand_2[i]);
            }
        }
        ask(W2); // Clear S
    }
    
    find_cross_edges(U2, W2);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> subtask >> n;
    adj.resize(n + 1);
    degree.resize(n + 1, 0);
    
    std::vector<int> V(n);
    std::iota(V.begin(), V.end(), 1);
    
    find_edges(V);
    
    std::vector<int> p;
    if (n > 0) {
        p.push_back(1);
        if (n > 1) {
            int prev = 1;
            int curr = adj[1][0];
            p.push_back(curr);
            
            while(p.size() < n) {
                int next_node;
                if (adj[curr].size() > 1 && adj[curr][0] == prev) {
                    next_node = adj[curr][1];
                } else {
                    next_node = adj[curr][0];
                }
                prev = curr;
                curr = next_node;
                p.push_back(curr);
            }
        }
    }
    
    std::cout << -1;
    for (int i = 0; i < n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}