#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cstdlib>
#include <ctime>

using namespace std;

// Function to perform a query and parse the response
// A pair of doors {u, v} is always stored with u < v
struct Pair {
    int u, v;
};

vector<Pair> query(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    vector<Pair> result;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        result.push_back({u, v});
    }
    return result;
}

// Checks if a pair {u, v} is present in the query response
bool in_response(int u, int v, const vector<Pair>& response) {
    if (u > v) swap(u, v);
    for (const auto& p : response) {
        if (p.u == u && p.v == v) return true;
    }
    return false;
}

// "Betweenness" test: checks if door x is on the shorter arc between a and b.
// This is true if {a, b} is NOT the pair with the minimum distance.
bool is_between(int a, int x, int b) {
    vector<Pair> res = query(a, x, b);
    return !in_response(a, b, res);
}

// Recursively sorts the doors on an arc defined by anchors a and b
vector<int> sort_arc(int a, int b, vector<int>& doors) {
    if (doors.size() <= 1) {
        return doors;
    }

    // Select a random pivot to ensure good average-case performance
    int pivot_idx = rand() % doors.size();
    int pivot = doors[pivot_idx];
    
    vector<int> left, right;
    for (size_t i = 0; i < doors.size(); ++i) {
        if ((int)i == pivot_idx) continue;
        if (is_between(a, doors[i], pivot)) {
            left.push_back(doors[i]);
        } else {
            right.push_back(doors[i]);
        }
    }

    vector<int> sorted_left = sort_arc(a, pivot, left);
    vector<int> sorted_right = sort_arc(pivot, b, right);

    vector<int> result;
    result.insert(result.end(), sorted_left.begin(), sorted_left.end());
    result.push_back(pivot);
    result.insert(result.end(), sorted_right.begin(), sorted_right.end());
    
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(0));

    int k_max, n;
    cin >> k_max >> n;

    if (n <= 2) {
        cout << "! 0";
        for (int i = 1; i < n; ++i) cout << " " << i;
        cout << endl;
        return 0;
    }

    // Use doors 0 and 1 as initial anchors
    int anchor1 = 0;
    int anchor2 = 1;

    vector<int> other_doors;
    for (int i = 2; i < n; ++i) {
        other_doors.push_back(i);
    }
    
    // Partition remaining doors into two arcs based on anchors 0 and 1
    vector<int> arc1_doors, arc2_doors;
    for (int door : other_doors) {
        if (is_between(anchor1, door, anchor2)) {
            arc1_doors.push_back(door);
        } else {
            arc2_doors.push_back(door);
        }
    }
    
    // Sort each arc
    vector<int> sorted_arc1 = sort_arc(anchor1, anchor2, arc1_doors);
    vector<int> sorted_arc2 = sort_arc(anchor2, anchor1, arc2_doors);

    // Output the final circular order
    cout << "! " << anchor1;
    for (int door : sorted_arc1) {
        cout << " " << door;
    }
    cout << " " << anchor2;
    for (int door : sorted_arc2) {
        cout << " " << door;
    }
    cout << endl;

    return 0;
}