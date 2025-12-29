#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    int R, H;
    cin >> R >> H;
    const int n = 1000;
    const int r = 36;
    vector<uint64_t> codes(n);
    mt19937_64 rng(42);
    bool found = false;
    while (!found) {
        for (int i = 0; i < n; i++) {
            codes[i] = rng() & ((1ULL << r) - 1);
        }
        unordered_set<uint64_t> all_sigs;
        bool distinct_singles = true;
        for (int i = 0; i < n; i++) {
            if (all_sigs.count(codes[i])) {
                distinct_singles = false;
                break;
            }
            all_sigs.insert(codes[i]);
        }
        if (!distinct_singles) continue;
        bool collision = false;
        for (int i = 0; i < n && !collision; i++) {
            for (int j = i + 1; j < n && !collision; j++) {
                uint64_t o = codes[i] | codes[j];
                if (all_sigs.count(o)) {
                    collision = true;
                } else {
                    all_sigs.insert(o);
                }
            }
        }
        if (!collision) {
            found = true;
        }
    }
    vector<vector<int>> sets(r);
    for (int j = 0; j < r; j++) {
        for (int pos = 0; pos < n; pos++) {
            if (codes[pos] & (1ULL << j)) {
                sets[j].push_back(pos + 1);
            }
        }
    }
    for (int j = 0; j < r; j++) {
        cout << "? " << sets[j].size();
        for (int p : sets[j]) {
            cout << " " << p;
        }
        cout << "\n";
        cout.flush();
    }
    cout << "@\n";
    cout.flush();
    int L;
    cin >> L;
    vector<int> results(r);
    for (int j = 0; j < r; j++) {
        cin >> results[j];
    }
    uint64_t v = 0;
    for (int j = 0; j < r; j++) {
        if (results[j]) {
            v |= (1ULL << j);
        }
    }
    int a = -1, b = -1;
    bool is_double = false;
    for (int i = 0; i < n; i++) {
        if (codes[i] == v) {
            a = i + 1;
            b = i + 1;
            is_double = true;
            break;
        }
    }
    if (!is_double) {
        for (int i = 0; i < n; i++) {
            for (int jj = i + 1; jj < n; jj++) {
                if ((codes[i] | codes[jj]) == v) {
                    a = i + 1;
                    b = jj + 1;
                    goto found_pair;
                }
            }
        }
    }
found_pair:
    if (a > b) swap(a, b);
    cout << "! " << a << " " << b << "\n";
    cout.flush();
    return 0;
}