#include <bits/stdc++.h>
using namespace std;

int main() {
    int R, H;
    cin >> R >> H;
    const int t = 64;
    const double prob = 1.0 - sqrt(0.5);
    srand(42);
    vector<uint64_t> code(1001, 0);
    // Generate codes
    set<uint64_t> used;
    bool distinct = true;
    for (int i = 1; i <= 1000; ++i) {
        uint64_t m = 0;
        for (int b = 0; b < t; ++b) {
            if ((double)rand() / RAND_MAX < prob) {
                m |= (1ULL << b);
            }
        }
        if (used.count(m)) {
            distinct = false;
            break;
        }
        used.insert(m);
        code[i] = m;
    }
    if (!distinct) {
        // In practice, won't happen, but to handle
        assert(false);
    }
    // Now check ORs and build map
    unordered_map<uint64_t, pair<int, int>> mp;
    mp.reserve(500500);
    bool collision = false;
    // Singles
    for (int i = 1; i <= 1000; ++i) {
        uint64_t m = code[i];
        if (mp.find(m) != mp.end()) {
            collision = true;
            break;
        }
        mp[m] = {i, i};
    }
    if (collision) {
        assert(false);
    }
    // Pairs
    for (int i = 1; i <= 1000 && !collision; ++i) {
        for (int j = i + 1; j <= 1000 && !collision; ++j) {
            uint64_t m = code[i] | code[j];
            if (mp.find(m) != mp.end()) {
                collision = true;
                break;
            }
            mp[m] = {i, j};
        }
    }
    if (collision) {
        assert(false);
    }
    // Now send queries
    vector<vector<int>> queries(t);
    for (int k = 0; k < t; ++k) {
        for (int pos = 1; pos <= 1000; ++pos) {
            if (code[pos] & (1ULL << k)) {
                queries[k].push_back(pos);
            }
        }
    }
    for (int k = 0; k < t; ++k) {
        cout << "? " << queries[k].size();
        for (int p : queries[k]) {
            cout << " " << p;
        }
        cout << endl;
    }
    cout.flush();
    cout << "@" << endl;
    cout.flush();
    // Read response
    int L;
    cin >> L;
    uint64_t observed = 0;
    for (int i = 0; i < L; ++i) {
        int res;
        cin >> res;
        if (res) {
            observed |= (1ULL << i);
        }
    }
    auto it = mp.find(observed);
    assert(it != mp.end());
    pair<int, int> ans = it->second;
    int a = ans.first, b = ans.second;
    cout << "! " << a << " " << b << endl;
    cout.flush();
    return 0;
}