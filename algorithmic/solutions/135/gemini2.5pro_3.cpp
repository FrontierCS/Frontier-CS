#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <set>
#include <numeric>

using namespace std;

// Function to ask a query and parse the response
set<pair<int, int>> ask(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    set<pair<int, int>> result;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        result.insert({u, v});
    }
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int k, n;
    cin >> k >> n;

    if (n == 3) {
        set<pair<int,int>> res = ask(0,1,2);
        if (res.count({0,1}) && res.count({1,2})) {
            cout << "! 0 1 2" << endl;
        } else if (res.count({0,2}) && res.count({1,2})) { // same as {0,2}, {2,1}
            cout << "! 0 2 1" << endl;
        } else { // {0,1}, {0,2}
            cout << "! 1 0 2" << endl;
        }
        return 0;
    }

    // Step 1: Find a neighbor of door 0. This neighbor is the door closest to 0.
    int p0 = 0;
    int p1_cand = 1;
    for (int i = 2; i < n; ++i) {
        set<pair<int, int>> res = ask(p0, p1_cand, i);
        // If i is strictly closer to p0 than p1_cand is, {p0, p1_cand} won't be a minimal pair.
        if (res.count({p0, i}) && !res.count({p0, p1_cand})) {
            p1_cand = i;
        }
    }
    int p1 = p1_cand;

    vector<int> p_final;
    p_final.push_back(p0);
    p_final.push_back(p1);

    vector<int> others;
    for (int i = 0; i < n; ++i) {
        if (i != p0 && i != p1) {
            others.push_back(i);
        }
    }

    // Step 2: Sort the other points.
    // The comparator determines if i is on the shorter arc between p0 and j.
    // If so, i is "further" from p0's other neighbor than j is.
    // This sorts points in order p_{n-1}, p_{n-2}, ..., p_2.
    sort(others.begin(), others.end(), [&](int i, int j) {
        set<pair<int, int>> res = ask(p0, i, j);
        pair<int, int> pair_p0_j = {min(p0, j), max(p0, j)};
        
        // If i is on the shorter arc between p0 and j, then the pair {p0, j}
        // corresponds to the longest of the three sides of triangle (p0, i, j),
        // so it cannot be a minimal distance pair.
        // This means i is "between" p0 and j.
        return res.find(pair_p0_j) == res.end();
    });

    // The sorted 'others' list is p_{n-1}, p_{n-2}, ... p_2.
    // We need p_2, p_3, ... p_{n-1} to append to p_0, p_1.
    reverse(others.begin(), others.end());

    for (int node : others) {
        p_final.push_back(node);
    }
    
    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << p_final[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}