#include <bits/stdc++.h>
using namespace std;

int get_idx(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return 10 + (c - 'A');
}

string compute_cs(const string& s1, const string& s2, bool from_s1) {
    int n = from_s1 ? s1.size() : s2.size();
    int m = from_s1 ? s2.size() : s1.size();
    const string& iterate = from_s1 ? s1 : s2;
    const string& pos_str = from_s1 ? s2 : s1;
    
    vector<vector<int>> pos(36);
    for (int i = 0; i < m; ++i) {
        int idx = get_idx(pos_str[i]);
        pos[idx].push_back(i);
    }
    
    string z;
    int current = 0;
    for (char ch : iterate) {
        int idx = get_idx(ch);
        const auto& vec = pos[idx];
        auto it = lower_bound(vec.begin(), vec.end(), current);
        if (it != vec.end()) {
            z += ch;
            current = *it + 1;
        }
    }
    return z;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string s1, s2;
    cin >> s1 >> s2;
    
    string z1 = compute_cs(s1, s2, true);
    string z2 = compute_cs(s1, s2, false);
    
    if (z1.size() >= z2.size()) {
        cout << z1 << '\n';
    } else {
        cout << z2 << '\n';
    }
    
    return 0;
}