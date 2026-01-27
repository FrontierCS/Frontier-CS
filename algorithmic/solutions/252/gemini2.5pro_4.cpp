#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <queue>

// Helper function to ask a query.
int ask(int u, int k, const std::vector<int>& s) {
    std::cout << "? " << u << " " << k << " " << s.size();
    for (int room : s) {
        std::cout << " " << room;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) {
        // Exit if the interactor signals an error.
        exit(0);
    }
    return response;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> a(n + 1);
    
    // Stage 1: Discover the graph structure.
    std::vector<int> initial_candidates(n);
    std::iota(initial_candidates.begin(), initial_candidates.end(), 1);

    for (int i = 1; i <= n; ++i) {
        std::vector<int> candidates = initial_candidates;

        // Binary search for a_i.
        while (candidates.size() > 1) {
            int mid_idx = candidates.size() / 2;
            std::vector<int> s(candidates.begin(), candidates.begin() + mid_idx);
            
            int response = ask(i, 1, s);
            
            if (response == 1) {
                // a_i is in the first half.
                candidates.erase(candidates.begin() + mid_idx, candidates.end());
            } else {
                // a_i is in the second half.
                candidates.erase(candidates.begin(), candidates.begin() + mid_idx);
            }
        }
        a[i] = candidates[0];
    }

    // Stage 2: Find the connected component of room 1.
    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 1; i <= n; ++i) {
        adj[i].push_back(a[i]);
        adj[a[i]].push_back(i);
    }
    
    std::vector<int> component;
    std::vector<bool> visited(n + 1, false);
    std::queue<int> q;

    q.push(1);
    visited[1] = true;

    // Standard BFS to find the connected component.
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        component.push_back(u);

        for (int v : adj[u]) {
            if (!visited[v]) {
                visited[v] = true;
                q.push(v);
            }
        }
    }
    
    std::sort(component.begin(), component.end());

    // Output the final answer.
    std::cout << "! " << component.size();
    for (int room : component) {
        std::cout << " " << room;
    }
    std::cout << std::endl;

    return 0;
}