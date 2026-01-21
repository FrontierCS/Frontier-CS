#include <bits/stdc++.h>
using namespace std;

static const int MAXM = 2200000;

int n, q;
vector<int> a, posv;

// Global data for sets
int cnt;
vector<int> Fminv, Gmaxv;                 // f(S), g(S)
vector<pair<int,int>> ops;                // merge operations

// Value segment tree to build all canonical value intervals
struct ValSegTree {
    int n;
    vector<int> setID; // setID for node interval
    ValSegTree(int n_) : n(n_) {
        setID.assign(4*n + 5, 0);
    }
    int build(int idx, int l, int r) {
        if (l == r) {
            setID[idx] = posv[l]; // leaf corresponds to S_{pos(value)}
            return setID[idx];
        }
        int mid = (l + r) >> 1;
        int LID = build(idx<<1, l, mid);
        int RID = build(idx<<1|1, mid+1, r);
        // Merge left and right canonical intervals
        int nid = ++cnt;
        ops.emplace_back(LID, RID);
        Fminv[nid] = Fminv[LID]; // equals l
        Gmaxv[nid] = Gmaxv[RID]; // equals r
        setID[idx] = nid;
        return nid;
    }
    void cover(int idx, int l, int r, int ql, int qr, vector<int>& out) const {
        if (ql <= l && r <= qr) {
            out.push_back(setID[idx]);
            return;
        }
        int mid = (l + r) >> 1;
        if (ql <= mid) cover(idx<<1, l, mid, ql, min(qr, mid), out);
        if (qr > mid) cover(idx<<1|1, mid+1, r, max(ql, mid+1), qr, out);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> q;
    a.assign(n+1, 0);
    posv.assign(n+1, 0);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        posv[a[i]] = i;
    }

    // Initialize sets: S_i = {a_i}
    cnt = n;
    Fminv.assign(n + MAXM + 10, 0);
    Gmaxv.assign(n + MAXM + 10, 0);
    for (int i = 1; i <= n; i++) {
        Fminv[i] = a[i];
        Gmaxv[i] = a[i];
    }
    ops.reserve(MAXM);

    // Build canonical value segment tree: creates n-1 new sets
    ValSegTree st(n);
    st.build(1, 1, n);

    vector<int> answers(q);

    for (int qi = 0; qi < q; qi++) {
        int l, r;
        cin >> l >> r;

        // Find components: consecutive values v..w with pos[v..w] in [l, r]
        vector<pair<int,int>> comps;
        int v = 1;
        while (v <= n) {
            if (posv[v] >= l && posv[v] <= r) {
                int w = v;
                while (w + 1 <= n && posv[w+1] >= l && posv[w+1] <= r) w++;
                comps.emplace_back(v, w);
                v = w + 1;
            } else v++;
        }

        // Collect canonical nodes for all components in ascending value order
        vector<int> pieces;
        pieces.reserve(16);
        for (auto &pr : comps) {
            st.cover(1, 1, n, pr.first, pr.second, pieces);
        }

        // Merge pieces in order
        int curID = pieces[0];
        for (size_t i = 1; i < pieces.size(); i++) {
            int nxt = pieces[i];
            int nid = ++cnt;
            ops.emplace_back(curID, nxt);
            Fminv[nid] = Fminv[curID];
            Gmaxv[nid] = Gmaxv[nxt];
            curID = nid;
        }
        answers[qi] = curID;
    }

    // Output
    cout << cnt << '\n';
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    for (int i = 0; i < q; i++) {
        if (i) cout << ' ';
        cout << answers[i];
    }
    cout << '\n';
    return 0;
}