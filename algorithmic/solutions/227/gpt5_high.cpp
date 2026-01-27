#include <bits/stdc++.h>
using namespace std;

struct Partition {
    vector<int> A, B, C, D; // store indices (0-based) of original permutation
    long long score;
};

vector<int> lis_positions(const vector<pair<int,int>>& cur, bool increasing) {
    int m = (int)cur.size();
    vector<int> a(m);
    for (int i = 0; i < m; ++i) a[i] = increasing ? cur[i].second : -cur[i].second;

    vector<int> d(m + 1), id(m + 1), parent(m, -1);
    int L = 0;
    for (int j = 0; j < m; ++j) {
        int x = a[j];
        int pos = int(lower_bound(d.begin() + 1, d.begin() + L + 1, x) - d.begin());
        parent[j] = (pos == 1 ? -1 : id[pos - 1]);
        if (pos > L) {
            ++L;
            d[L] = x;
            id[L] = j;
        } else {
            d[pos] = x;
            id[pos] = j;
        }
    }
    vector<int> seq;
    int idx = (L >= 1 ? id[L] : -1);
    while (idx != -1) {
        seq.push_back(idx);
        idx = parent[idx];
    }
    reverse(seq.begin(), seq.end());
    return seq;
}

int lis_length_values(const vector<int>& vals, bool increasing) {
    int m = (int)vals.size();
    vector<int> d;
    d.reserve(m);
    for (int i = 0; i < m; ++i) {
        int x = increasing ? vals[i] : -vals[i];
        auto it = lower_bound(d.begin(), d.end(), x);
        if (it == d.end()) d.push_back(x);
        else *it = x;
    }
    return (int)d.size();
}

Partition attempt(const vector<int>& P, const vector<int>& types) {
    // types size = 3, elements: 1 for LIS, 0 for LDS
    vector<pair<int,int>> cur;
    cur.reserve(P.size());
    for (int i = 0; i < (int)P.size(); ++i) cur.emplace_back(i, P[i]);

    vector<vector<int>> passIndices; // original indices selected at each pass
    passIndices.reserve(3);

    for (int t = 0; t < 3; ++t) {
        vector<int> posList = lis_positions(cur, types[t] == 1);
        vector<int> selectedOriginal;
        selectedOriginal.reserve(posList.size());
        vector<char> mark(cur.size(), 0);
        for (int j : posList) {
            mark[j] = 1;
            selectedOriginal.push_back(cur[j].first);
        }
        passIndices.push_back(move(selectedOriginal));
        vector<pair<int,int>> nxt;
        nxt.reserve(cur.size() - posList.size());
        for (size_t i = 0; i < cur.size(); ++i) if (!mark[i]) nxt.push_back(cur[i]);
        cur.swap(nxt);
    }
    vector<int> leftover;
    leftover.reserve(cur.size());
    for (auto &pr : cur) leftover.push_back(pr.first);

    // Map passes to A (LIS), B (LDS), C (LIS), D (leftover)
    vector<int> lisPos, ldsPos;
    for (int i = 0; i < 3; ++i) {
        if (types[i] == 1) lisPos.push_back(i);
        else ldsPos.push_back(i);
    }
    Partition res;
    res.A = passIndices[lisPos[0]];
    res.C = passIndices[lisPos[1]];
    res.B = passIndices[ldsPos[0]];
    res.D = leftover;

    // Score = size(A) + size(B) + size(C) + LDS(D)
    vector<int> Dvals;
    Dvals.reserve(res.D.size());
    for (int idx : res.D) Dvals.push_back(P[idx]);
    int ldsD = lis_length_values(Dvals, false);
    res.score = (long long)res.A.size() + (long long)res.B.size() + (long long)res.C.size() + ldsD;

    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> P(n);
    for (int i = 0; i < n; ++i) cin >> P[i];

    vector<vector<int>> variants = {
        {1,1,0},
        {1,0,1},
        {0,1,1}
    };

    Partition best;
    best.score = -1;
    for (auto &var : variants) {
        Partition cand = attempt(P, var);
        if (cand.score > best.score) best = move(cand);
    }

    cout << best.A.size() << " " << best.B.size() << " " << best.C.size() << " " << best.D.size() << "\n";
    auto print_group = [&](const vector<int>& idxs) {
        for (size_t i = 0; i < idxs.size(); ++i) {
            if (i) cout << " ";
            cout << P[idxs[i]];
        }
        cout << "\n";
    };
    print_group(best.A);
    print_group(best.B);
    print_group(best.C);
    print_group(best.D);

    return 0;
}