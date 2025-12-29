#include <bits/stdc++.h>
using namespace std;

int ask(const string& s, map<string, int>& cache) {
    auto it = cache.find(s);
    if (it != cache.end()) return it->second;
    cout << "? " << s << endl;
    cout.flush();
    int ans;
    cin >> ans;
    cache[s] = ans;
    return ans;
}

string union_str(const string& a, const string& b, int n) {
    string res(n, '0');
    for (int i = 0; i < n; ++i) {
        if (a[i] == '1' || b[i] == '1') res[i] = '1';
    }
    return res;
}

bool has_edge(const string& A, const string& B, map<string, int>& cache, int n) {
    int fA = ask(A, cache);
    int fB = ask(B, cache);
    string AB = union_str(A, B, n);
    int fAB = ask(AB, cache);
    return fAB <= fA + fB - 2;
}

string get_mask(const vector<int>& verts, int n) {
    string s(n, '0');
    for (int v : verts) s[v] = '1';
    return s;
}

string get_union_mask(const vector<int>& comp_indices, const vector<vector<int>>& components, int n) {
    string s(n, '0');
    for (int idx : comp_indices) {
        for (int v : components[idx]) s[v] = '1';
    }
    return s;
}

string get_range_mask(int l, int r, const vector<int>& indices,
                      const vector<vector<int>>& components, int n) {
    string s(n, '0');
    for (int i = l; i <= r; ++i) {
        int idx = indices[i];
        for (int v : components[idx]) s[v] = '1';
    }
    return s;
}

int main() {
    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        map<string, int> cache;
        vector<vector<int>> components(n);
        for (int i = 0; i < n; ++i) components[i] = {i};
        vector<int> comp_list(n);
        iota(comp_list.begin(), comp_list.end(), 0);

        bool disconnected = false;
        while (comp_list.size() > 1) {
            int idxA = comp_list[0];
            vector<int> other_indices(comp_list.begin() + 1, comp_list.end());
            string A_str = get_mask(components[idxA], n);
            string B_str = get_union_mask(other_indices, components, n);
            if (!has_edge(A_str, B_str, cache, n)) {
                disconnected = true;
                break;
            }
            int lo = 0, hi = other_indices.size() - 1;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                string L_str = get_range_mask(lo, mid, other_indices, components, n);
                if (has_edge(A_str, L_str, cache, n)) {
                    hi = mid;
                } else {
                    lo = mid + 1;
                }
            }
            int idxC = other_indices[lo];
            components[idxA].insert(components[idxA].end(),
                                    components[idxC].begin(),
                                    components[idxC].end());
            vector<int> new_list;
            new_list.push_back(idxA);
            for (size_t j = 1; j < comp_list.size(); ++j) {
                int idx = comp_list[j];
                if (idx != idxC) new_list.push_back(idx);
            }
            comp_list = new_list;
        }
        if (disconnected) {
            cout << "! 0" << endl;
        } else {
            cout << "! 1" << endl;
        }
        cout.flush();
    }
    return 0;
}