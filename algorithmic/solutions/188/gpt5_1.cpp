#include <bits/stdc++.h>
using namespace std;

static inline int cidx(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0');
}

using VecPos = array<vector<int>, 36>;

void buildPositions(const string& s, VecPos &pos) {
    int cnt[36] = {0};
    for (char ch : s) cnt[cidx(ch)]++;
    for (int i = 0; i < 36; ++i) pos[i].reserve(cnt[i]);
    for (int i = 0; i < (int)s.size(); ++i) pos[cidx(s[i])].push_back(i);
}

string embedUsingPositions(const VecPos &pos, const string &other) {
    int total = 0;
    for (int i = 0; i < 36; ++i) total += (int)pos[i].size();
    string res;
    res.reserve(min(total, (int)other.size()));
    int cur = -1;
    int ptr[36] = {0};
    for (int j = 0; j < (int)other.size(); ++j) {
        int id = cidx(other[j]);
        const vector<int> &v = pos[id];
        int &p = ptr[id];
        while (p < (int)v.size() && v[p] <= cur) ++p;
        if (p < (int)v.size()) {
            res.push_back(other[j]);
            cur = v[p];
            ++p;
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if (!getline(cin, s1)) return 0;
    getline(cin, s2);

    // Embed S2 into S1
    VecPos pos1;
    buildPositions(s1, pos1);
    string res1 = embedUsingPositions(pos1, s2);
    for (int i = 0; i < 36; ++i) {
        vector<int>().swap(pos1[i]);
    }

    // Embed S1 into S2
    VecPos pos2;
    buildPositions(s2, pos2);
    string res2 = embedUsingPositions(pos2, s1);
    for (int i = 0; i < 36; ++i) {
        vector<int>().swap(pos2[i]);
    }

    if (res2.size() > res1.size()) {
        cout << res2 << '\n';
    } else {
        cout << res1 << '\n';
    }
    return 0;
}