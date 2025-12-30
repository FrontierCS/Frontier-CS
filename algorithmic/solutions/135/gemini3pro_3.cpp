#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <deque>
#include <random>
#include <set>

using namespace std;

// Global variables for problem constraints
int K, N;

// Memoization for comparisons to save queries
// Key: {min(u, v), max(u, v)}
// Value: 1 if u < v (closer to 0), -1 if v < u, 0 if equal
map<pair<int, int>, int> memo_cmp;

// Function to perform a query
// Returns a set of pairs that are closest among {x, y, z}
set<pair<int, int>> query(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    set<pair<int, int>> res;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        res.insert({u, v});
    }
    return res;
}

// Comparator for sorting vertices by distance from 0
// Returns true if 'a' is closer to 0 than 'b'
bool compare_dist(int a, int b) {
    if (a == b) return false;
    
    int u = min(a, b);
    int v = max(a, b);
    
    // Check memoization
    if (memo_cmp.count({u, v})) {
        int res = memo_cmp[{u, v}];
        if (a == u) { 
            return res == 1; 
        } else { 
            return res == -1; 
        }
    }

    // Perform query with 0 as reference
    set<pair<int, int>> res = query(0, a, b);
    
    bool a_close = res.count({min(0, a), max(0, a)});
    bool b_close = res.count({min(0, b), max(0, b)});
    
    int result = 0;
    if (a_close && !b_close) {
        result = 1; // a is closer to 0
    } else if (b_close && !a_close) {
        result = -1; // b is closer to 0
    } else {
        // Either both are closest (tie), or {a, b} is closest.
        // If {a, b} is closest, it means d(a, b) < d(0, a) and d(a, b) < d(0, b).
        // This implies a and b are clustered together, so their distance from 0 is similar.
        // We treat them as equal distance for sorting layers.
        result = 0;
    }

    memo_cmp[{u, v}] = result;
    
    if (a == u) return result == 1;
    else return result == -1;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> K >> N)) return 0;

    // List of doors excluding 0
    vector<int> p(N - 1);
    for (int i = 0; i < N - 1; ++i) {
        p[i] = i + 1;
    }

    // Shuffle to avoid worst-case scenarios for sort
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);

    // Sort vertices based on distance from 0
    // This groups vertices into layers of increasing distance
    sort(p.begin(), p.end(), compare_dist);

    // Reconstruct the cycle
    // Start with 0
    deque<int> d;
    d.push_back(0);

    // Iteratively attach sorted vertices to the current path ends
    for (int x : p) {
        int f = d.front();
        int b = d.back();
        
        if (f == b) {
            // First vertex attaches to 0
            d.push_back(x);
            continue;
        }

        // Query to decide which end 'x' is closer to
        // f and b are the current "tips" of the path on the circle
        // x is the next closest point to 0, so it extends one of the tips
        set<pair<int, int>> res = query(f, x, b);
        
        bool close_to_f = res.count({min(f, x), max(f, x)});
        bool close_to_b = res.count({min(b, x), max(b, x)});
        
        if (close_to_f && !close_to_b) {
            d.push_front(x);
        } else if (close_to_b && !close_to_f) {
            d.push_back(x);
        } else {
            // Tie or ambiguous case.
            // If it's a tie, x is equidistant to f and b.
            // This happens at the closing of the loop (opposite to 0).
            // We can attach to either side.
            d.push_back(x);
        }
    }

    // Output the result
    cout << "!";
    for (int x : d) {
        cout << " " << x;
    }
    cout << endl;

    return 0;
}