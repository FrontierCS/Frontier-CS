#include <bits/stdc++.h>
using namespace std;

static vector<int> getLISIndices(const vector<pair<int,int>>& seq) {
    int m = (int)seq.size();
    if (m == 0) return {};

    vector<int> tailVal;
    vector<int> tailPos;
    vector<int> parent(m, -1);
    tailVal.reserve(m);
    tailPos.reserve(m);

    for (int i = 0; i < m; i++) {
        int x = seq[i].first;
        int pos = (int)(lower_bound(tailVal.begin(), tailVal.end(), x) - tailVal.begin());
        if (pos == (int)tailVal.size()) {
            tailVal.push_back(x);
            tailPos.push_back(i);
        } else {
            tailVal[pos] = x;
            tailPos[pos] = i;
        }
        if (pos > 0) parent[i] = tailPos[pos - 1];
    }

    vector<int> res;
    res.reserve(tailPos.size());
    int cur = tailPos.back();
    while (cur != -1) {
        res.push_back(seq[cur].second);
        cur = parent[cur];
    }
    reverse(res.begin(), res.end());
    return res;
}

struct Sol {
    vector<int> label; // 0=a,1=b,2=c,3=d
    long long base = -1;
};

static Sol simulateOrder(const vector<int>& perm, const vector<int>& order) {
    int n = (int)perm.size();
    vector<int> label(n, -1);
    long long base = 0;

    for (int g : order) {
        bool inc = (g == 0 || g == 2);
        vector<pair<int,int>> seq;
        seq.reserve(n);
        for (int i = 0; i < n; i++) {
            if (label[i] != -1) continue;
            int v = perm[i];
            if (!inc) v = -v;
            seq.push_back({v, i});
        }
        auto picked = getLISIndices(seq);
        base += (long long)picked.size();
        for (int idx : picked) label[idx] = g;
    }

    for (int i = 0; i < n; i++) if (label[i] == -1) label[i] = 3;
    return {std::move(label), base};
}

static void printLine(const vector<int>& v) {
    for (int i = 0; i < (int)v.size(); i++) {
        if (i) cout << ' ';
        cout << v[i];
    }
    cout << '\n';
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> perm(n);
    for (int i = 0; i < n; i++) cin >> perm[i];

    vector<vector<int>> orders = {
        {0,1,2,3},
        {1,0,3,2},
        {0,2,1,3},
        {1,3,0,2},
        {2,3,0,1},
        {3,2,1,0},
        {0,1,3,2},
        {1,0,2,3}
    };

    Sol best;
    best.base = -1;
    for (const auto& ord : orders) {
        Sol s = simulateOrder(perm, ord);
        if (s.base > best.base) best = std::move(s);
    }

    array<vector<int>, 4> groups;
    for (int i = 0; i < n; i++) {
        int g = best.label[i];
        if (g < 0 || g > 3) g = 3;
        groups[g].push_back(perm[i]);
    }

    cout << groups[0].size() << ' ' << groups[1].size() << ' ' << groups[2].size() << ' ' << groups[3].size() << "\n";
    printLine(groups[0]);
    printLine(groups[1]);
    printLine(groups[2]);
    printLine(groups[3]);

    return 0;
}