#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<pair<int, vector<int>>> lines;
    string s;
    while (true) {
        string line;
        if (!getline(cin, line)) break;
        bool any = false;
        for (char c : line) {
            if (!isspace((unsigned char)c)) { any = true; break; }
        }
        if (!any) continue;
        stringstream ss(line);
        long long tll;
        if (!(ss >> tll)) continue;
        int t = (int)tll;
        vector<int> a;
        int x;
        while (ss >> x) a.push_back(x);
        lines.push_back({t, a});
    }
    
    if (lines.empty()) return 0;
    
    int n = -1;
    for (auto &pr : lines) {
        if (!pr.second.empty()) { n = (int)pr.second.size(); break; }
    }
    if (n <= 0) return 0;
    
    vector<int> perm;
    for (auto &pr : lines) {
        if (pr.first == 1) {
            perm = pr.second;
        }
    }
    if ((int)perm.size() != n) return 0;
    
    for (auto &pr : lines) {
        if (pr.first == 0) {
            const auto &q = pr.second;
            int cnt = 0;
            int len = min((int)q.size(), n);
            for (int i = 0; i < len; ++i) if (q[i] == perm[i]) ++cnt;
            cout << cnt << "\n";
        }
    }
    return 0;
}