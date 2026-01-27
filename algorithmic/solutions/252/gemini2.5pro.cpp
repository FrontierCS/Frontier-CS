#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>
#include <queue>

using namespace std;

// Function to ask a query and get the result
bool ask_query(int u, long long k, const vector<int>& s) {
    cout << "? " << u << " " << k << " " << s.size();
    for (int room : s) {
        cout << " " << room;
    }
    cout << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0); // Exit on error
    return result == 1;
}

// Function to find the destination from room u after k steps
// using binary search on the possible destination rooms.
int find_destination(int u, long long k, int n) {
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    while (candidates.size() > 1) {
        vector<int> first_half;
        int half_size = candidates.size() / 2;
        for (int i = 0; i < half_size; ++i) {
            first_half.push_back(candidates[i]);
        }

        if (ask_query(u, k, first_half)) {
            candidates = first_half;
        } else {
            vector<int> second_half;
            for (int i = half_size; i < candidates.size(); ++i) {
                second_half.push_back(candidates[i]);
            }
            candidates = second_half;
        }
    }
    return candidates[0];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    // Step 1: Determine the entire functional graph by finding a_i for all i.
    // The most efficient way to find a single a_i is to binary search over
    // all possible destination rooms. This has a logarithmic number of queries.
    // k=1 is the cheapest for log10(k) term.
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        a[i] = find_destination(i, 1, n);
    }

    // Step 2: Two rooms u and v can reach each other if and only if they are
    // in the same connected component in the underlying undirected graph.
    // We build this undirected graph.
    vector<vector<int>> undirected_adj(n + 1);
    for (int i = 1; i <= n; ++i) {
        undirected_adj[i].push_back(a[i]);
        undirected_adj[a[i]].push_back(i);
    }
    
    // Step 3: Find the connected component containing room 1 using BFS.
    // All rooms in this component form the set A.
    vector<int> component_nodes;
    queue<int> q;
    vector<bool> visited(n + 1, false);

    q.push(1);
    visited[1] = true;
    
    while(!q.empty()){
        int u = q.front();
        q.pop();
        component_nodes.push_back(u);

        for(int v : undirected_adj[u]){
            if(!visited[v]){
                visited[v] = true;
                q.push(v);
            }
        }
    }

    sort(component_nodes.begin(), component_nodes.end());

    cout << "! " << component_nodes.size();
    for (int room : component_nodes) {
        cout << " " << room;
    }
    cout << endl;

    return 0;
}