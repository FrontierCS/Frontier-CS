#include <bits/stdc++.h>
using namespace std;

int n, k;
int queries_used = 0;

// Returns a bitset: bit 0 for pair (x,y), bit 1 for (y,z), bit 2 for (z,x)
int query(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    queries_used++;
    int r;
    cin >> r;
    int res = 0;
    for (int i = 0; i < r; i++) {
        int a, b;
        cin >> a >> b;
        if (a > b) swap(a, b);
        if (a == x && b == y) res |= 1;
        else if (a == y && b == z) res |= 2;
        else if (a == z && b == x) res |= 4;
        else {
            // Should not happen
        }
    }
    return res;
}

// Given a set of candidates (indices) and a door X, find the candidate closest to X using tournament elimination.
int find_closest(int X, vector<int>& candidates) {
    if (candidates.empty()) return -1;
    while (candidates.size() > 1) {
        // Pick two candidates
        int a = candidates.back(); candidates.pop_back();
        int b = candidates.back(); candidates.pop_back();
        int res = query(X, a, b);
        bool has_Xa = (res & 1) != 0;
        bool has_ab = (res & 2) != 0;
        bool has_Xb = (res & 4) != 0;
        
        if (has_Xa && !has_Xb) {
            // a is closer than b
            candidates.push_back(a);
        } else if (has_Xb && !has_Xa) {
            // b is closer than a
            candidates.push_back(b);
        } else if (has_Xa && has_Xb) {
            // both are equally close
            candidates.push_back(a);
        } else {
            // only (a,b) is present
            candidates.push_back(a);
        }
    }
    return candidates[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> k >> n; // k is max queries, n is number of doors
    
    vector<int> order; // will store the cyclic order
    vector<bool> visited(n, false);
    
    // Start with door 0
    int current = 0;
    visited[current] = true;
    order.push_back(current);
    
    // We'll build the cycle by finding next door for each current.
    // We need to find n-1 more doors.
    for (int step = 0; step < n-1; step++) {
        // Collect unvisited doors
        vector<int> unvisited;
        for (int i = 0; i < n; i++) if (!visited[i]) unvisited.push_back(i);
        
        // If few unvisited, use all as candidates
        vector<int> candidates;
        if (unvisited.size() <= 24) {
            candidates = unvisited;
        } else {
            // Randomly sample 24 doors from unvisited
            random_shuffle(unvisited.begin(), unvisited.end());
            candidates.assign(unvisited.begin(), unvisited.begin() + 24);
        }
        
        int next_door = find_closest(current, candidates);
        if (next_door == -1) {
            // fallback: pick first unvisited
            next_door = unvisited[0];
        }
        
        order.push_back(next_door);
        visited[next_door] = true;
        current = next_door;
    }
    
    // Output order
    cout << "!";
    for (int x : order) cout << " " << x;
    cout << endl;
    
    return 0;
}