#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <set>

using namespace std;

// Helper to represent a pair of doors, always sorted
pair<int, int> make_sorted_pair(int u, int v) {
    if (u > v) swap(u, v);
    return {u, v};
}

// Function to perform a query and get the response
set<pair<int, int>> ask_query(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    set<pair<int, int>> result;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        result.insert(make_sorted_pair(u, v));
    }
    return result;
}

// Check if a pair is in the set of shortest pairs
bool is_shortest(int u, int v, const set<pair<int, int>>& shortest_pairs) {
    return shortest_pairs.count(make_sorted_pair(u, v));
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int k, n;
    cin >> k >> n;

    vector<int> others;
    for (int i = 1; i < n; ++i) {
        others.push_back(i);
    }

    // Sort points {1, ..., n-1} by distance from 0
    // d(0,i) < d(0,j) iff i is "between" 0 and j on a short arc.
    // This means (0,j) is the longest side of triangle 0,i,j.
    // In that case, {0,j} will not be a shortest pair.
    // This holds if 0,i,j are on a short arc together.
    // If not, this comparison still works to establish a distance-based ordering.
    stable_sort(others.begin(), others.end(), [&](int i, int j) {
        set<pair<int, int>> res = ask_query(0, i, j);
        bool i_is_short = is_shortest(0, i, res);
        bool j_is_short = is_shortest(0, j, res);
        
        if (i_is_short && !j_is_short) {
            return true;
        }
        if (!i_is_short && j_is_short) {
            return false;
        }
        if (i_is_short && j_is_short) { // Equidistant
            return false;
        }
        
        // Neither {0,i} nor {0,j} is shortest, so {i,j} is.
        // This implies they are on the same side of 0.
        // We need a third point to break the tie. Let's use others[0] but it's not fixed yet.
        // A fixed point like 1 (if not i or j) is not guaranteed to be on the same side.
        // However, the simplest point to use is the one we know must be a neighbor of 0: others[0] after one pass of sorting.
        // But we can't do that inside a comparator.
        // Let's test against one of the other points which must exist if N >= 4.
        // A query involving an arbitrary fourth point can resolve this ambiguity.
        int ref = others[0];
        if (ref == i || ref == j) ref = others[1];

        auto res2 = ask_query(ref, i, j);
        return is_shortest(ref, i, res2) && !is_shortest(ref, j, res2);
    });

    vector<int> side1, side2;
    side1.push_back(others[0]);
    if (n > 2) {
      side2.push_back(others[1]);
    }

    for (size_t i = 2; i < others.size(); i += 2) {
        int u = others[i];
        int v = (i + 1 < others.size()) ? others[i + 1] : -1;

        int last1 = side1.back();
        
        set<pair<int, int>> res = ask_query(last1, 0, u);
        
        if (is_shortest(last1, u, res)) {
            side1.push_back(u);
            if (v != -1) side2.push_back(v);
        } else {
            side1.push_back(v);
            if (u != -1) side2.push_back(u);
        }
    }
    
    cout << "! ";
    reverse(side2.begin(), side2.end());
    for (int door : side2) {
        cout << door << " ";
    }
    cout << 0 << " ";
    for (size_t i = 0; i < side1.size(); ++i) {
        cout << side1[i] << (i == side1.size() - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}