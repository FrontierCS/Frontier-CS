#include <bits/stdc++.h>
using namespace std;

template <class KeyFunc>
static vector<int> longest_increasing_subsequence_indices(const vector<int>& idxs, const vector<int>& p, int N, KeyFunc key) {
    vector<int> prev(N, -1);
    vector<long long> tails;
    vector<int> tails_idx;
    tails.reserve(idxs.size());
    tails_idx.reserve(idxs.size());

    for (int idx : idxs) {
        long long x = key(p[idx]);
        auto it = lower_bound(tails.begin(), tails.end(), x);
        int pos = (int)(it - tails.begin());

        if (pos == (int)tails.size()) {
            tails.push_back(x);
            tails_idx.push_back(idx);
        } else {
            tails[pos] = x;
            tails_idx[pos] = idx;
        }

        prev[idx] = (pos > 0 ? tails_idx[pos - 1] : -1);
    }

    vector<int> res;
    if (tails_idx.empty()) return res;

    int cur = tails_idx.back();
    while (cur != -1) {
        res.push_back(cur);
        cur = prev[cur];
    }
    reverse(res.begin(), res.end());
    return res;
}

static void print_vec(const vector<int>& v) {
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
    vector<int> p(n);
    for (int i = 0; i < n; i++) cin >> p[i];

    vector<int> assignment(n, -1);
    vector<int> remaining;
    remaining.reserve(n);
    for (int i = 0; i < n; i++) remaining.push_back(i);

    int incPtr = 0; // groups: 0 (a), 2 (c)
    int decPtr = 0; // groups: 1 (b), 3 (d)

    while (!remaining.empty() && (incPtr < 2 || decPtr < 2)) {
        vector<int> lis, lds;
        int lisLen = -1, ldsLen = -1;

        if (incPtr < 2) {
            lis = longest_increasing_subsequence_indices(
                remaining, p, n,
                [](int v) -> long long { return (long long)v; }
            );
            lisLen = (int)lis.size();
        }
        if (decPtr < 2) {
            lds = longest_increasing_subsequence_indices(
                remaining, p, n,
                [n](int v) -> long long { return (long long)(n + 1 - v); }
            );
            ldsLen = (int)lds.size();
        }

        bool chooseInc;
        if (incPtr >= 2) chooseInc = false;
        else if (decPtr >= 2) chooseInc = true;
        else chooseInc = (lisLen >= ldsLen);

        const vector<int>& chosen = chooseInc ? lis : lds;
        int g;
        if (chooseInc) {
            g = (incPtr == 0 ? 0 : 2);
            incPtr++;
        } else {
            g = (decPtr == 0 ? 1 : 3);
            decPtr++;
        }

        for (int idx : chosen) assignment[idx] = g;

        vector<int> newRemaining;
        newRemaining.reserve(remaining.size());
        for (int idx : remaining) {
            if (assignment[idx] == -1) newRemaining.push_back(idx);
        }
        remaining.swap(newRemaining);
    }

    for (int idx : remaining) assignment[idx] = 3;

    vector<int> A, B, C, D;
    A.reserve(n); B.reserve(n); C.reserve(n); D.reserve(n);
    for (int i = 0; i < n; i++) {
        if (assignment[i] == 0) A.push_back(p[i]);
        else if (assignment[i] == 1) B.push_back(p[i]);
        else if (assignment[i] == 2) C.push_back(p[i]);
        else D.push_back(p[i]);
    }

    cout << A.size() << ' ' << B.size() << ' ' << C.size() << ' ' << D.size() << "\n";
    print_vec(A);
    print_vec(B);
    print_vec(C);
    print_vec(D);

    return 0;
}