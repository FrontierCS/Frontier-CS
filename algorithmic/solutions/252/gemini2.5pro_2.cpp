#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Function to ask a query to the interactor
bool ask(int u, int k, const vector<int>& S) {
    if (S.empty()) {
        return false;
    }
    cout << "? " << u << " " << k << " " << S.size();
    for (int s : S) {
        cout << " " << s;
    }
    cout << endl;
    int response;
    cin >> response;
    if (response == -1) {
        // This case would typically indicate an error or end of interaction
        // in some competitive programming platforms.
        exit(0);
    }
    return response == 1;
}

// Finds the room a_u by performing a binary search on the destination room.
// This is used to trace the path from a given room.
int find_next(int u, int n) {
    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> S;
        S.reserve(mid - low + 1);
        for (int i = low; i <= mid; ++i) {
            S.push_back(i);
        }
        if (ask(u, 1, S)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    // Step 1: Find the path starting from room 1 until a cycle is detected.
    // This forms a "rho" shape (a path leading into a cycle).
    // All nodes on this path are in the component of room 1.
    set<int> path_from_1_set;
    vector<bool> visited(n + 1, false);

    int current = 1;
    for (int i = 0; i < n; ++i) {
        if (visited[current]) {
            break;
        }
        visited[current] = true;
        path_from_1_set.insert(current);
        current = find_next(current, n);
    }
    
    // The set of rooms in the component of room 1, initialized with the path found.
    set<int> component_A = path_from_1_set;
    
    // Prepare the set S for queries.
    vector<int> S_query_vec;
    S_query_vec.reserve(path_from_1_set.size());
    for(int node : path_from_1_set) {
        S_query_vec.push_back(node);
    }

    // Step 2: For all other rooms, check if they belong to the component of room 1.
    // A room `i` is in the same component as room 1 if and only if its path
    // eventually merges with the path from room 1. This is equivalent to checking
    // if after a large number of steps (n is sufficient), room `i` lands on
    // a node in the path from room 1.
    for (int i = 1; i <= n; ++i) {
        if (path_from_1_set.find(i) == path_from_1_set.end()) {
            if (ask(i, n, S_query_vec)) {
                component_A.insert(i);
            }
        }
    }

    // Step 3: Output the final answer.
    cout << "! " << component_A.size();
    for (int node : component_A) {
        cout << " " << node;
    }
    cout << endl;

    return 0;
}