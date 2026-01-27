#include <bits/stdc++.h>
using namespace std;

static inline int mapChar(unsigned char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();
    int n = (int)s1.size();
    int m = (int)s2.size();
    
    const int SIGMA = 36;
    vector<int> cnt1(SIGMA, 0), cnt2(SIGMA, 0);
    for (int i = 0; i < n; ++i) cnt1[mapChar((unsigned char)s1[i])]++;
    for (int j = 0; j < m; ++j) cnt2[mapChar((unsigned char)s2[j])]++;
    
    vector<vector<int>> pos1(SIGMA), pos2(SIGMA);
    for (int c = 0; c < SIGMA; ++c) {
        pos1[c].reserve(cnt1[c]);
        pos2[c].reserve(cnt2[c]);
    }
    for (int i = 0; i < n; ++i) pos1[mapChar((unsigned char)s1[i])].push_back(i);
    for (int j = 0; j < m; ++j) pos2[mapChar((unsigned char)s2[j])].push_back(j);
    
    vector<int> ptr1(SIGMA, 0), ptr2(SIGMA, 0);
    auto nextOcc = [](const vector<int>& v, int &k, int threshold)->int {
        while (k < (int)v.size() && v[k] < threshold) ++k;
        if (k < (int)v.size()) return v[k];
        return INT_MAX;
    };
    
    long long cap = 0;
    for (int c = 0; c < SIGMA; ++c) cap += min((long long)cnt1[c], (long long)cnt2[c]);
    if (cap > (long long)min(n, m)) cap = min(n, m);
    
    string out;
    out.reserve((size_t)cap);
    
    int i = 0, j = 0;
    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            out.push_back(s1[i]);
            ++i; ++j;
            continue;
        }
        int c1 = mapChar((unsigned char)s1[i]);
        int c2 = mapChar((unsigned char)s2[j]);
        
        int i1 = nextOcc(pos1[c2], ptr1[c2], i);
        int j1 = nextOcc(pos2[c1], ptr2[c1], j);
        
        if (i1 == INT_MAX && j1 == INT_MAX) {
            ++i; ++j;
        } else if (j1 == INT_MAX) {
            ++i;
        } else if (i1 == INT_MAX) {
            ++j;
        } else {
            if (j1 - j <= i1 - i) {
                j = j1;
                out.push_back(s1[i]);
                ++i; ++j;
            } else {
                i = i1;
                out.push_back(s2[j]);
                ++i; ++j;
            }
        }
    }
    
    cout << out << '\n';
    return 0;
}