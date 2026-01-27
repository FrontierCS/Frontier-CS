#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <map>
#include <set>
#include <algorithm>
#include <iterator>

// Global state
int n;
std::map<int, int> next_node_cache;

// Helper to ask a query and get response
int ask_query(int u, int k, const std::vector<int>& S) {
    if (S.empty()) {
        // The room can't be in an empty set. This case shouldn't be reached with the current logic.
        return 0;
    }
    std::cout << "? " << u << " " << k << " " << S.size();
    for (int s_node : S) {
        std::cout << " " << s_node;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) exit(0); // For safety in case of judge error or malformed query
    return response;
}

// Finds a[u] using binary search over possible rooms
int find_next(int u) {
    if (next_node_cache.count(u)) {
        return next_node_cache[u];
    }

    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        std::vector<int> S;
        S.reserve(mid - low + 1);
        for (int i = low; i <= mid; ++i) {
            S.push_back(i);
        }
        if (ask_query(u, 1, S)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    
    next_node_cache[u] = low;
    return low;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    // Step 1: Find the path and cycle from room 1.
    // Michael and Brian can meet if and only if they start in the same functional component.
    // A component is uniquely identified by its cycle. We first find the component for Brian (starting at 1).
    std::vector<int> path_from_1;
    std::map<int, int> visited_on_path; // node -> index in path_from_1
    int current_node = 1;
    while (visited_on_path.find(current_node) == visited_on_path.end()) {
        visited_on_path[current_node] = path_from_1.size();
        path_from_1.push_back(current_node);
        current_node = find_next(current_node);
    }

    int cycle_start_index = visited_on_path[current_node];
    std::vector<int> cycle_1;
    for (size_t i = cycle_start_index; i < path_from_1.size(); ++i) {
        cycle_1.push_back(path_from_1[i]);
    }
    
    // Step 2: Determine set A. A is the set of all rooms that reach the same cycle as room 1.
    std::set<int> A_set;
    for (int node : path_from_1) {
        A_set.insert(node);
    }
    
    for (int i = 1; i <= n; ++i) {
        if (A_set.count(i)) {
            continue;
        }
        // A node `i` is in the same component if its path eventually reaches cycle_1.
        // After n steps, any node's path is guaranteed to be on its cycle.
        // So we check if a^n(i) is in cycle_1. If so, Cycle(i) must be cycle_1.
        if (ask_query(i, n, cycle_1)) {
            A_set.insert(i);
        }
    }

    // Step 3: Print the answer
    std::cout << "! " << A_set.size();
    for (int node : A_set) {
        std::cout << " " << node;
    }
    std::cout << std::endl;

    return 0;
}