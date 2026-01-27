#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& left, const vector<int>& right) {
    int l = left.size();
    int rgt = right.size();
    if (l == 0 || rgt == 0) {
        return 0;
    }
    cout << "? " << l << " " << rgt << endl;
    for (size_t i = 0; i < left.size(); ++i) {
        cout << left[i];
        if (i + 1 < left.size()) cout << " ";
    }
    cout << endl;
    for (size_t i = 0; i < right.size(); ++i) {
        cout << right[i];
        if (i + 1 < right.size()) cout << " ";
    }
    cout << endl;
    cout.flush();
    int f;
    cin >> f;
    return f;
}

struct Result {
    bool found;
    vector<vector<int>> new_items;
    vector<int> g1, g2;
};

Result find_good_pair(vector<vector<int>> items) {
    Result res;
    res.found = false;
    int num = items.size();
    if (num < 2) {
        res.new_items = items;
        return res;
    }
    vector<vector<vector<int>>> meta_groups;
    int i = 0;
    while (i < num) {
        int sz = min(3, num - i);
        vector<vector<int>> mg(sz);
        for (int j = 0; j < sz; ++j) {
            mg[j] = items[i + j];
        }
        meta_groups.push_back(mg);
        i += sz;
    }
    vector<vector<int>> temp_new;
    bool broke = false;
    for (auto& mg : meta_groups) {
        int mgsz = mg.size();
        for (int p = 0; p < mgsz; ++p) {
            for (int q = p + 1; q < mgsz; ++q) {
                int f = query(mg[p], mg[q]);
                if (f != 0) {
                    res.found = true;
                    res.g1 = mg[p];
                    res.g2 = mg[q];
                    broke = true;
                    goto done;
                }
            }
        }
        // no find, create higher
        vector<int> higher;
        for (auto& itm : mg) {
            higher.insert(higher.end(), itm.begin(), itm.end());
        }
        temp_new.push_back(higher);
    }
done:
    if (!res.found) {
        res.new_items = temp_new;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        vector<vector<int>> base(n);
        for (int i = 0; i < n; ++i) {
            base[i] = {i + 1};
        }
        vector<vector<int>> current = base;
        vector<int> comp1, comp2;
        Result res;
        bool done = false;
        while (!done) {
            res = find_good_pair(current);
            if (res.found) {
                comp1 = res.g1;
                comp2 = res.g2;
                done = true;
            } else {
                current = res.new_items;
                if (current.size() < 2) {
                    // Should not happen
                    assert(false);
                }
            }
        }
        // Find ref in comp1
        int ref = -1;
        for (int idx : comp1) {
            vector<int> L = {idx};
            int f = query(L, comp2);
            if (f != 0) {
                ref = idx;
                break;
            }
        }
        assert(ref != -1);
        // Classify
        vector<int> demag;
        for (int i = 1; i <= n; ++i) {
            if (i == ref) continue;
            vector<int> L = {ref};
            vector<int> R = {i};
            int f = query(L, R);
            if (f == 0) {
                demag.push_back(i);
            }
        }
        // Output
        cout << "! " << demag.size();
        for (int x : demag) {
            cout << " " << x;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}