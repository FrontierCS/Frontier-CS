#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <numeric>
#include <cstring>
#include <cmath>

using namespace std;

map<vector<int>, int> cache;

int query(const vector<int>& s) {
    vector<int> sorted = s;
    sort(sorted.begin(), sorted.end());
    if (cache.count(sorted)) return cache[sorted];
    cout << "? " << sorted.size();
    for (int x : sorted) cout << " " << x;
    cout << endl;
    cout.flush();
    int ans;
    cin >> ans;
    cache[sorted] = ans;
    return ans;
}

int main() {
    int n;
    cin >> n;

    // Step 1: parity groups
    vector<int> same(n+1, 0);
    same[1] = 1; // by convention
    for (int i = 2; i <= n; ++i) {
        vector<int> s = {1, i};
        same[i] = query(s);
    }

    // Step 2: find candidates for 1 and n (indices where query all except i returns 1)
    vector<int> cand;
    for (int i = 1; i <= n; ++i) {
        vector<int> s;
        for (int j = 1; j <= n; ++j) if (j != i) s.push_back(j);
        int ans = query(s);
        if (ans == 1) cand.push_back(i);
    }

    // There should be exactly two candidates
    int c1 = cand[0], c2 = cand[1];
    vector<int> p(n+1, 0);
    p[c1] = 1;
    p[c2] = n;

    // Determine parity of p1
    bool p1_odd;
    if (c1 == 1) {
        p1_odd = true;